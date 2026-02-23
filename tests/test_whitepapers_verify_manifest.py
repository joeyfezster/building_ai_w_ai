from __future__ import annotations

import json
from pathlib import Path


def test_whitepaper_manifest_schema() -> None:
    manifest = json.loads(Path("docs/whitepapers/manifest.json").read_text(encoding="utf-8"))
    assert "papers" in manifest
    assert isinstance(manifest["papers"], list)
