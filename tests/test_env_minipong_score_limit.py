from __future__ import annotations

from src.envs.minipong import MiniPongConfig, MiniPongEnv


def _force_left_miss(env: MiniPongEnv) -> tuple[float, bool, bool, dict[str, object]]:
    env.ball_vx = -2.0
    env.ball_x = 0.0
    env.ball_y = env.config.height - env.config.ball_size
    _, reward, terminated, truncated, info = env.step(2)
    return reward, terminated, truncated, info


def test_score_limit_one_keeps_single_rally_termination() -> None:
    env = MiniPongEnv(config=MiniPongConfig(score_limit=1))
    env.reset(seed=0)

    reward, terminated, truncated, info = _force_left_miss(env)

    assert reward == -1.0
    assert terminated is True
    assert truncated is False
    assert info["episode_reason"] == "agent_miss"


def test_score_limit_multi_rally_resets_ball_and_continues() -> None:
    env = MiniPongEnv(config=MiniPongConfig(score_limit=2))
    env.reset(seed=0)

    reward, terminated, truncated, info = _force_left_miss(env)

    assert reward == -1.0
    assert terminated is False
    assert truncated is False
    assert info["opponent_score"] == 1
    assert info["episode_reason"] == "running"
    assert env.ball_x == env.config.width / 2
    assert env.ball_y == env.config.height / 2

    reward, terminated, _, info = _force_left_miss(env)
    assert reward == -1.0
    assert terminated is True
    assert info["opponent_score"] == 2
    assert info["episode_reason"] == "score_limit"
