"""Run logging utilities."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from torch.utils.tensorboard import SummaryWriter


class MetricsLogger:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = run_dir / "logs.jsonl"
        self.tb_dir = run_dir / "tensorboard"
        self.tb = SummaryWriter(str(self.tb_dir))
        self._start_time = time.time()

    def log_metrics(self, step: int, metrics: dict[str, Any]) -> None:
        now = time.time()
        line = {"step": step, "wall_time": now, "elapsed_s": now - self._start_time, **metrics}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                self.tb.add_scalar(k, v, step)

    def close(self) -> None:
        self.tb.flush()
        self.tb.close()
