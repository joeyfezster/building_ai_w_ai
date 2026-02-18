from __future__ import annotations

import json
from pathlib import Path

import requests
import yaml


def main() -> None:
    links_path = Path("docs/whitepapers/links.yaml")
    links = yaml.safe_load(links_path.read_text(encoding="utf-8"))["papers"]
    out_dir = Path("docs/whitepapers/pdfs")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for item in links:
        url = item["url"]
        name = item["filename"]
        content = requests.get(url, timeout=30).content
        fpath = out_dir / name
        fpath.write_bytes(content)
        manifest.append(
            {"title": item["title"], "filename": name, "bytes": len(content), "url": url}
        )
    Path("docs/whitepapers/manifest.json").write_text(
        json.dumps({"papers": manifest}, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
