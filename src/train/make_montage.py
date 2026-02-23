"""Make demo index for videos."""

from __future__ import annotations

import argparse
from pathlib import Path


def make_index(run_id: str) -> Path:
    run_dir = Path("artifacts") / run_id
    video_dir = run_dir / "videos"
    demo_dir = run_dir / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    videos = sorted(video_dir.glob("*.mp4"))
    html = ["<html><body><h1>MiniPong Progression</h1>"]
    for v in videos:
        rel = f"../videos/{v.name}"
        html.append(f"<h3>{v.name}</h3><video controls width='320' src='{rel}'></video>")
    html.append("</body></html>")
    out = demo_dir / "index.html"
    out.write_text("\n".join(html), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", required=True)
    args = parser.parse_args()
    out = make_index(args.run_id)
    print(out)


if __name__ == "__main__":
    main()
