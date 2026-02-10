"""Verify whitepaper downloads."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml
from pypdf import PdfReader


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("manifest.json must be a list")
    return [dict(item) for item in data]


def load_links(path: Path) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("links.yaml must be a list")
    return {str(item["id"]): dict(item) for item in data}


def extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks = []
    for page in reader.pages:
        text = page.extract_text() or ""
        chunks.append(text)
    return "\n".join(chunks)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "docs" / "whitepapers" / "manifest.json"
    links_path = repo_root / "docs" / "whitepapers" / "links.yaml"
    errors: list[str] = []
    manifest_entries = load_manifest(manifest_path)
    link_map = load_links(links_path)
    for entry in manifest_entries:
        file_path = repo_root / str(entry["file_path"])
        if not file_path.exists():
            errors.append(f"Missing file: {file_path}")
            continue
        expected_hash = str(entry["sha256"])
        actual_hash = sha256_file(file_path)
        if actual_hash != expected_hash:
            errors.append(f"SHA256 mismatch for {file_path}")
        text = extract_text(file_path)
        expected_title = str(entry["expected_title"])
        if expected_title.lower() not in text.lower():
            errors.append(f"Title missing in {file_path}")
        link_entry = link_map.get(str(entry["id"]), {})
        arxiv_id = link_entry.get("arxiv_id")
        if arxiv_id and str(arxiv_id) not in text:
            errors.append(f"arXiv id missing in {file_path}")
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"Verified {len(manifest_entries)} whitepapers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
