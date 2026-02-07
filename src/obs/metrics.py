"""Metrics stubs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSummary:
    """Summary for a metric stream."""

    name: str
    value: float
