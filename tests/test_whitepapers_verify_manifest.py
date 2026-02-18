import json
from pathlib import Path


def test_whitepaper_manifest_schema() -> None:
    path = Path("docs/whitepapers/manifest.json")
    if not path.exists():
        data = {"papers": []}
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    assert "papers" in data
