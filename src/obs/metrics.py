from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalMetrics:
    mean_return: float
    mean_hits: float
    mean_misses: float
    mean_rally_length: float
