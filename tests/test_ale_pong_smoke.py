from __future__ import annotations

from pathlib import Path

import ale_py as _ale_py
import numpy as np

from src.configs import load_config
from src.envs.atari_ale import make_atari_env
from src.utils import seed_env, set_global_seeds


def test_ale_pong_smoke() -> None:
    _ = _ale_py.__name__
    repo_root = Path(__file__).resolve().parents[1]
    config = load_config(repo_root / "configs" / "dqn_pong_smoke.yaml")
    env_id = str(config["env_id"])
    env_config = config.get("env", {})
    seed = int(config["seed"])
    set_global_seeds(seed)
    env = make_atari_env(env_id, wrapper_config=env_config)
    seed_env(env, seed)
    obs, _ = env.reset()
    assert isinstance(obs, np.ndarray)
    reward_total = 0.0
    for _ in range(60):
        obs, reward, terminated, truncated, _ = env.step(env.action_space.sample())
        assert isinstance(obs, np.ndarray)
        reward_total += float(reward)
        if terminated or truncated:
            obs, _ = env.reset()
    env.close()
    assert isinstance(reward_total, float)
