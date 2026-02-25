#!/usr/bin/env python3
"""Create GitHub issues from post-merge items in a PR review pack.

Simple script that parses post-merge items and creates labeled GH issues.
Designed to run after a factory PR is merged.

Usage:
    python scripts/create_postmerge_issues.py --pr 5                    # create issues
    python scripts/create_postmerge_issues.py --pr 5 --dry-run          # preview only
    python scripts/create_postmerge_issues.py --pr 5 --file data.json   # custom data file
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


# Post-merge items — hardcoded for now, will be read from review pack data when available
# Each item: {title, priority, zones, body}
# This structure matches what the PR review pack generates

def load_postmerge_items(filepath: Path | None, pr_number: int) -> list[dict]:
    """Load post-merge items from a JSON file.

    Expected format:
    {
        "post_merge_items": [
            {
                "title": "Short description",
                "priority": "low|medium|high",
                "zones": ["factory-orchestration", "holdout-isolation"],
                "body": "Detailed description of what needs to happen",
                "code_refs": ["scripts/nfr_checks.py:187"]
            }
        ]
    }
    """
    if filepath and filepath.exists():
        data = json.loads(filepath.read_text())
        return data.get("post_merge_items", [])

    # If no file provided, return empty — caller should provide data
    print(f"No post-merge data file found. Provide --file path or create:")
    print(f"  artifacts/factory/postmerge_pr{pr_number}.json")
    return []


def create_issue(
    item: dict,
    pr_number: int,
    repo: str,
    dry_run: bool = False,
) -> str | None:
    """Create a single GitHub issue from a post-merge item.

    Returns the issue URL if created, None if dry-run or error.
    """
    title = item.get("title", "Untitled post-merge item")
    priority = item.get("priority", "low")
    zones = item.get("zones", [])
    body_text = item.get("body", "")
    code_refs = item.get("code_refs", [])

    # Build issue body
    body_parts = [
        f"## From PR #{pr_number}",
        f"",
        f"**Priority:** {priority}",
        f"**Zones:** {', '.join(zones) if zones else 'unassigned'}",
        f"",
    ]

    if body_text:
        body_parts.append(body_text)
        body_parts.append("")

    if code_refs:
        body_parts.append("### Code References")
        for ref in code_refs:
            body_parts.append(f"- `{ref}`")
        body_parts.append("")

    body_parts.append(f"---")
    body_parts.append(f"Created from post-merge items in PR #{pr_number}")

    body = "\n".join(body_parts)

    # Build labels
    labels = ["technical-debt", priority]
    for zone in zones:
        labels.append(zone)

    if dry_run:
        print(f"\n{'='*60}")
        print(f"ISSUE: {title}")
        print(f"Labels: {', '.join(labels)}")
        print(f"Body:\n{body}")
        return None

    # Create issue via gh CLI
    cmd = [
        "gh", "issue", "create",
        "--repo", repo,
        "--title", title,
        "--body", body,
    ]
    for label in labels:
        cmd.extend(["--label", label])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            print(f"  Created: {url}")
            return url
        else:
            print(f"  ERROR creating issue: {result.stderr.strip()}")
            return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create GitHub issues from PR post-merge items"
    )
    parser.add_argument(
        "--pr",
        type=int,
        required=True,
        help="PR number that introduced the post-merge items",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to JSON file with post-merge items",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="joeyfezster/building_ai_w_ai",
        help="GitHub repo (owner/name)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview issues without creating them",
    )
    args = parser.parse_args()

    # Determine data file
    filepath = Path(args.file) if args.file else None
    if not filepath:
        # Default location
        default = Path(__file__).resolve().parent.parent / f"artifacts/factory/postmerge_pr{args.pr}.json"
        if default.exists():
            filepath = default

    items = load_postmerge_items(filepath, args.pr)

    if not items:
        print("No post-merge items found. Nothing to create.")
        return 0

    print(f"{'DRY RUN — ' if args.dry_run else ''}Creating {len(items)} issues from PR #{args.pr}...")

    created = 0
    for item in items:
        url = create_issue(item, args.pr, args.repo, dry_run=args.dry_run)
        if url:
            created += 1

    if not args.dry_run:
        print(f"\nCreated {created}/{len(items)} issues")
    else:
        print(f"\nDry run complete — {len(items)} issues would be created")

    return 0


if __name__ == "__main__":
    sys.exit(main())
