from __future__ import annotations

from src.envs.minipong import MiniPongEnv


def test_minipong_smoke() -> None:
    env = MiniPongEnv()
    obs, info = env.reset(seed=0)
    assert obs.shape == (84, 84, 1)
    assert obs.dtype.name == "uint8"
    assert "hits" in info


def test_set_opponent_action_manual_and_restore_ai() -> None:
    env = MiniPongEnv()
    env.reset(seed=0)
    start_y = env.opponent_y

    env.set_opponent_action(0)
    env.step(2)
    assert env.opponent_y < start_y

    manual_y = env.opponent_y
    env.set_opponent_action(None)
    env.ball_y = env.opponent_y + 40
    env.step(2)
    assert env.opponent_y > manual_y


def test_reset_clears_manual_opponent_action() -> None:
    env = MiniPongEnv()
    env.reset(seed=0)
    env.set_opponent_action(0)
    env.reset(seed=1)

    start_y = env.opponent_y
    env.ball_y = env.opponent_y + 40
    env.step(2)
    assert env.opponent_y > start_y
