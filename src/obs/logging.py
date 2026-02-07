"""Logging stubs."""

from __future__ import annotations

from typing import Any, Mapping


class MetricsLogger:
    """Placeholder metrics logger."""

    def log_metrics(self, metrics: Mapping[str, Any]) -> None:
        """Log a batch of metrics."""

        raise NotImplementedError("Metrics logging not implemented yet.")
