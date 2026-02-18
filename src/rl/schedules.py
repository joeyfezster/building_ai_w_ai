from __future__ import annotations


def linear_schedule(start: float, end: float, step: int, duration: int) -> float:
    if step >= duration:
        return end
    frac = step / max(duration, 1)
    return start + frac * (end - start)
