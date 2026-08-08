"""Shared utilities for the pr-review-pack package.

Functions extracted from scaffold_review_pack_data.py to eliminate
duplication across scaffold, CLI, and assembler scripts.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from fnmatch import fnmatch


def _get_repo_slug(override: str | None = None) -> str:
    """Return owner/repo from CLI flag or git remote origin."""
    if override:
        return override
    url = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True).strip()
    # SCP-style (git@host:owner/repo.git) has no scheme prefix
    if ":" in url and not url.startswith(("https://", "http://", "ssh://")):
        slug = url.split(":")[-1]
    else:
        slug = "/".join(url.split("/")[-2:])
    return slug.removesuffix(".git")


def run_gh(args: list[str]) -> str:
    """Run a gh CLI command and return stdout."""
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"WARNING: gh {' '.join(args)} failed: {result.stderr}", file=sys.stderr)
        return ""
    return result.stdout.strip()


def match_file_to_zones(filepath: str, zones: dict) -> list[str]:
    """Match a file path to zone IDs using glob patterns."""
    matched = []
    for zone_id, zone_def in zones.items():
        for pattern in zone_def.get("paths", []):
            if fnmatch(filepath, pattern):
                matched.append(zone_id)
                break
    return matched


def health_tag(seconds: float) -> str:
    """Categorise CI job duration into a health bucket."""
    if seconds < 60:
        return "normal"
    if seconds < 300:
        return "acceptable"
    if seconds < 600:
        return "watch"
    return "refactor"


def format_time(seconds: float) -> str:
    """Human-readable duration string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def parse_ci_time(started: str, completed: str) -> float:
    """Parse ISO timestamps and return duration in seconds."""
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        start = datetime.strptime(started, fmt).replace(tzinfo=UTC)
        end = datetime.strptime(completed, fmt).replace(tzinfo=UTC)
        return max((end - start).total_seconds(), 0)
    except (ValueError, TypeError):
        return 0
