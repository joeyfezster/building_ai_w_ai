from __future__ import annotations

import json
from pathlib import Path

import requests
import yaml

MINIMAL_PDF = (
    b"%PDF-1.1\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R>>endobj\n"
    b"4 0 obj<</Length 44>>stream\n"
    b"BT /F1 12 Tf 20 100 Td (Offline whitepaper placeholder) Tj ET\n"
    b"endstream\n"
    b"endobj\n"
    b"xref\n"
    b"0 5\n"
    b"0000000000 65535 f \n"
    b"0000000010 00000 n \n"
    b"0000000053 00000 n \n"
    b"0000000108 00000 n \n"
    b"0000000195 00000 n \n"
    b"trailer<</Size 5/Root 1 0 R>>\n"
    b"startxref\n"
    b"289\n"
    b"%%EOF\n"
)


def main() -> None:
    links = yaml.safe_load(Path("docs/whitepapers/links.yaml").read_text(encoding="utf-8"))
    pdf_dir = Path("docs/whitepapers/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []
    for entry in links["papers"]:
        out = pdf_dir / entry["filename"]
        source = "remote"
        if not out.exists():
            try:
                r = requests.get(entry["url"], timeout=30)
                r.raise_for_status()
                out.write_bytes(r.content)
            except Exception:
                out.write_bytes(MINIMAL_PDF)
                source = "offline_placeholder"
        manifest.append(
            {
                "title": entry["title"],
                "filename": entry["filename"],
                "url": entry["url"],
                "source": source,
            }
        )
    Path("docs/whitepapers/manifest.json").write_text(
        json.dumps({"papers": manifest}, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
