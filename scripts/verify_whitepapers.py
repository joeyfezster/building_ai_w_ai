from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    manifest = json.loads(Path("docs/whitepapers/manifest.json").read_text(encoding="utf-8"))
    for p in manifest["papers"]:
        f = Path("docs/whitepapers/pdfs") / p["filename"]
        if not f.exists() or f.stat().st_size <= 1000:
            print(f"invalid whitepaper: {f}")
            sys.exit(1)
    print("whitepapers verified")


if __name__ == "__main__":
    main()
