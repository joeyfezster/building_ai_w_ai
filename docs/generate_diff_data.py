#!/usr/bin/env python3
"""Generate per-file diff data for the PR review pack.

Produces pr_diff_data.json with:
- Per-file unified diffs (main...HEAD)
- Per-file raw content from HEAD
- File metadata (additions, deletions, status)

Usage:
    python docs/generate_diff_data.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    return result.stdout


def main() -> None:
    repo = Path(__file__).resolve().parent.parent

    # Get list of changed files with stats
    numstat = run(
        ["git", "diff", "--numstat", "main...HEAD"], cwd=repo
    ).strip().splitlines()

    name_status = run(
        ["git", "diff", "--name-status", "main...HEAD"], cwd=repo
    ).strip().splitlines()

    # Build status map
    status_map: dict[str, str] = {}
    for line in name_status:
        parts = line.split("\t")
        if len(parts) >= 2:
            status_code = parts[0][0]  # First char: A, M, D, R
            filepath = parts[-1]  # Last part (handles renames)
            status_map[filepath] = {
                "A": "added",
                "M": "modified",
                "D": "deleted",
                "R": "renamed",
            }.get(status_code, "modified")

    files_data: dict[str, dict] = {}

    for line in numstat:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        adds_str, dels_str, filepath = parts[0], parts[1], parts[2]

        # Binary files show as '-'
        adds = int(adds_str) if adds_str != "-" else 0
        dels = int(dels_str) if dels_str != "-" else 0
        is_binary = adds_str == "-"

        # Get unified diff for this file
        diff = ""
        if not is_binary:
            diff = run(
                ["git", "diff", "main...HEAD", "--", filepath], cwd=repo
            )

        # Get raw content from HEAD
        raw = ""
        if not is_binary:
            raw = run(
                ["git", "show", f"HEAD:{filepath}"], cwd=repo
            )

        # Get raw content from main (base) for side-by-side
        base = ""
        if not is_binary and status_map.get(filepath) != "added":
            base = run(
                ["git", "show", f"main:{filepath}"], cwd=repo
            )

        files_data[filepath] = {
            "additions": adds,
            "deletions": dels,
            "status": status_map.get(filepath, "modified"),
            "binary": is_binary,
            "diff": diff,
            "raw": raw,
            "base": base,
        }

    output = {
        "pr": 5,
        "base_branch": "main",
        "head_branch": "factory/v1",
        "head_sha": run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo
        ).strip(),
        "total_files": len(files_data),
        "total_additions": sum(f["additions"] for f in files_data.values()),
        "total_deletions": sum(f["deletions"] for f in files_data.values()),
        "files": files_data,
    }

    out_path = repo / "docs" / "pr_diff_data.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"Wrote {out_path} ({out_path.stat().st_size:,} bytes, {len(files_data)} files)")


if __name__ == "__main__":
    main()
