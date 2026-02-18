from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    src = Path("artifacts")
    dst = Path("demo_pack/training_data")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


if __name__ == "__main__":
    main()
