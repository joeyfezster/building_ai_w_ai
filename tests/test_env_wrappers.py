from __future__ import annotations

from src.rl.schedules import linear_schedule


def test_linear_schedule_bounds() -> None:
    assert linear_schedule(step=-1, start=1.0, end=0.0, duration=10) == 1.0
    assert linear_schedule(step=10, start=1.0, end=0.0, duration=10) == 0.0
