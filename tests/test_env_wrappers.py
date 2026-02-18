from __future__ import annotations

from src.envs.minipong import MiniPongEnv
from src.envs.wrappers import wrap_env
from src.rl.schedules import linear_schedule


def test_linear_schedule_bounds() -> None:
    assert linear_schedule(step=-1, start=1.0, end=0.0, duration=10) == 1.0
    assert linear_schedule(step=10, start=1.0, end=0.0, duration=10) == 0.0


def test_wrap_env_frame_stack() -> None:
    env = wrap_env(MiniPongEnv(), frame_stack=4)
    obs, _ = env.reset(seed=1)
    assert obs.shape[2] == 4
