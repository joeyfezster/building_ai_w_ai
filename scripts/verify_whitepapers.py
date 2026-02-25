from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader


def main() -> None:
    manifest = json.loads(Path("docs/whitepapers/manifest.json").read_text(encoding="utf-8"))
    for paper in manifest["papers"]:
        path = Path("docs/whitepapers/pdfs") / paper["filename"]
        if not path.exists():
            raise SystemExit(f"Missing pdf: {path}")
        reader = PdfReader(str(path))
        if len(reader.pages) == 0:
            raise SystemExit(f"Invalid pdf: {path}")
    print("whitepapers verified")


if __name__ == "__main__":
    main()
