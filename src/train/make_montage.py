from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run_id", required=True)
    args = p.parse_args()

    run_dir = Path("artifacts") / args.run_id
    vids = sorted((run_dir / "videos").glob("*.mp4"))
    demo_dir = run_dir / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    html = demo_dir / "index.html"
    rows = "\n".join(
        [
            f'<h3>{v.stem}</h3><video controls width="480" src="../videos/{v.name}"></video>'
            for v in vids
        ]
    )
    html.write_text(
        f"<html><body><h1>Training progression</h1>{rows}</body></html>", encoding="utf-8"
    )
    print(html)


if __name__ == "__main__":
    main()
