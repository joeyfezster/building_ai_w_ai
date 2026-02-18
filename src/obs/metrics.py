"""Metrics helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSummary:
    name: str
    value: float
