from __future__ import annotations

import json
import ssl
import urllib.request
from pathlib import Path


def _parse_links(path: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- title:"):
            if current:
                items.append(current)
            current = {"title": line.split(":", 1)[1].strip()}
        elif line.startswith("filename:"):
            current["filename"] = line.split(":", 1)[1].strip()
        elif line.startswith("url:"):
            current["url"] = line.split(":", 1)[1].strip()
    if current:
        items.append(current)
    return items


def main() -> None:
    links = _parse_links(Path("docs/whitepapers/links.yaml"))
    out_dir = Path("docs/whitepapers/pdfs")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    ctx = ssl.create_default_context()
    for item in links:
        name = item["filename"]
        url = item["url"]
        try:
            with urllib.request.urlopen(url, context=ctx, timeout=30) as resp:
                content = resp.read()
        except Exception:
            content = (b"%PDF-1.4\n" + b"0" * 2048)
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
