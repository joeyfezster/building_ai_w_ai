"""Smoke test for ALE Pong environment."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

from src.configs import ConfigError, load_config, require_keys
from src.envs.atari_ale import make_atari_env
from src.utils import seed_env, set_global_seeds


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "configs" / "dqn_pong_smoke.yaml"
    config = load_config(config_path)
    require_keys(config, {"env_id", "seed"})
    env_id = str(config["env_id"])
    seed = int(config["seed"])
    env_config = config.get("env", {})
    set_global_seeds(seed)
    env = make_atari_env(env_id, wrapper_config=env_config)
    seed_env(env, seed)
    obs, _ = env.reset()
    if not isinstance(obs, np.ndarray):
        raise RuntimeError("Observation is not a numpy array")
    total_reward = 0.0
    steps = 0
    for _ in range(75):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, _ = env.step(action)
        if not isinstance(obs, np.ndarray):
            raise RuntimeError("Observation is not a numpy array")
        if not isinstance(float(reward), float):
            raise RuntimeError("Reward is not numeric")
        total_reward += float(reward)
        steps += 1
        if terminated or truncated:
            obs, _ = env.reset()
    env.close()
    shape = obs.shape
    print(f"Emulator smoke ok: steps={steps} obs_shape={shape} total_reward={total_reward}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ConfigError, RuntimeError, ValueError) as exc:
        print(f"Emulator smoke failed: {exc}")
        sys.exit(1)
