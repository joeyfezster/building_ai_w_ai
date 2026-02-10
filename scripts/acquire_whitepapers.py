"""Acquire whitepapers into the repository."""

from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import yaml


class PdfLinkParser(HTMLParser):
    """HTML parser to collect PDF links."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                if ".pdf" in value.lower():
                    self.links.append(value)


def slugify(text: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in text)
    parts = [part for part in cleaned.split() if part]
    return "-".join(parts)


def read_links(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("links.yaml must be a list")
    return [dict(item) for item in data]


def fetch_url(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "retro-rl-milestones"})
    with urlopen(request) as response:
        return response.read()


def find_pdf_link(landing_url: str) -> str | None:
    if landing_url.lower().endswith(".pdf"):
        return landing_url
    try:
        html = fetch_url(landing_url).decode("utf-8", errors="ignore")
    except Exception:
        return None
    parser = PdfLinkParser()
    parser.feed(html)
    for link in parser.links:
        return urljoin(landing_url, link)
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    links_path = repo_root / "docs" / "whitepapers" / "links.yaml"
    pdf_dir = repo_root / "docs" / "whitepapers" / "pdfs"
    manifest_path = repo_root / "docs" / "whitepapers" / "manifest.json"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    entries = read_links(links_path)
    manifest_entries: list[dict[str, Any]] = []
    for entry in entries:
        paper_id = str(entry.get("id", ""))
        expected_title = str(entry.get("expected_title", ""))
        year = int(entry.get("year", 0))
        landing_url = str(entry.get("url_landing", ""))
        if not paper_id or not expected_title or not landing_url or year <= 0:
            print(f"Skipping invalid entry: {entry}")
            continue
        pdf_url = find_pdf_link(landing_url)
        if not pdf_url:
            print(f"Failed to locate PDF for {paper_id}")
            continue
        slug = str(entry.get("slug") or slugify(expected_title))
        filename = f"{paper_id}__{year}__{slug}.pdf"
        destination = pdf_dir / filename
        try:
            data = fetch_url(pdf_url)
            destination.write_bytes(data)
        except Exception as exc:
            print(f"Failed to download {paper_id}: {exc}")
            continue
        manifest_entries.append(
            {
                "id": paper_id,
                "expected_title": expected_title,
                "year": year,
                "source_final_url": pdf_url,
                "sha256": sha256_file(destination),
                "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
                "file_path": f"docs/whitepapers/pdfs/{filename}",
            }
        )
        print(f"Downloaded {paper_id} -> {destination}")
    manifest_path.write_text(
        json.dumps(manifest_entries, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
