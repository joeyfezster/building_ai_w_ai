"""Filesystem helpers."""

from __future__ import annotations

from pathlib import Path


class OutputPathError(RuntimeError):
    """Output path is not writable."""


def ensure_writable_dir(path: Path) -> Path:
    """Ensure that a directory exists and is writable."""

    path.mkdir(parents=True, exist_ok=True)
    test_path = path / ".write_test"
    try:
        test_path.write_text("ok", encoding="utf-8")
    except OSError as exc:
        raise OutputPathError(f"Output directory not writable: {path}") from exc
    finally:
        if test_path.exists():
            test_path.unlink()
    return path
