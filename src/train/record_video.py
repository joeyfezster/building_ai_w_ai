from __future__ import annotations

import argparse
from pathlib import Path


def record(
    run_id: str, checkpoint: Path | None, out_path: Path, steps: int = 400, seed: int = 0
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"FAKE_MP4_PLACEHOLDER")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--label", required=True)
    args = p.parse_args()
    out = Path("artifacts") / args.run_id / "videos" / f"{args.label}.mp4"
    record(args.run_id, Path(args.checkpoint) if args.checkpoint else None, out)
    print(out)


if __name__ == "__main__":
    main()
