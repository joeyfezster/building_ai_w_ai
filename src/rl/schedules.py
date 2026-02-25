"""Schedule functions."""

from __future__ import annotations


def linear_schedule(step: int, start: float, end: float, duration: int) -> float:
    if step <= 0:
        return start
    if step >= duration:
        return end
    frac = step / duration
    return start + frac * (end - start)
