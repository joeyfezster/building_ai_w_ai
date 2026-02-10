"""Logging utilities."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping


class MetricsLogger:
    """Placeholder metrics logger."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self.output_dir / "logs.jsonl"
        self._handle = self._log_path.open("a", encoding="utf-8")

    def log_metrics(self, metrics: Mapping[str, Any]) -> None:
        """Log a batch of metrics."""

        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            **metrics,
        }
        self._handle.write(json.dumps(record) + "\n")
        self._handle.flush()
        printable = " ".join(
            f"{key}={value}" for key, value in record.items() if key != "timestamp_utc"
        )
        print(f"{record['timestamp_utc']} {printable}".strip())

    def close(self) -> None:
        self._handle.close()
