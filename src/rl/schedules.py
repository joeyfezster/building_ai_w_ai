"""Schedule utilities."""

from __future__ import annotations


def linear_schedule(step: int, start: float, end: float, duration: int) -> float:
    """Linearly interpolate between start and end over duration steps."""

    if duration <= 0:
        raise ValueError("duration must be positive")
    progress = min(max(step, 0), duration) / duration
    return start + (end - start) * progress
