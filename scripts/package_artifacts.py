from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    src = Path("artifacts") / args.run_id
    dst = Path("demo_pack/training_data") / args.run_id
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(dst)


if __name__ == "__main__":
    main()
