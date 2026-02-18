from __future__ import annotations

from collections import deque
from typing import Any

import gymnasium as gym
import numpy as np


class FrameStackGray(gym.ObservationWrapper[np.ndarray, int, np.ndarray]):
    def __init__(self, env: gym.Env[np.ndarray, int], k: int = 4) -> None:
        super().__init__(env)
        self.k = k
        self.frames: deque[np.ndarray] = deque(maxlen=k)
        h, w, c = env.observation_space.shape
        assert c == 1
        self.observation_space = gym.spaces.Box(
            low=0,
            high=255,
            shape=(h, w, k),
            dtype=np.uint8,
        )

    def reset(self, **kwargs: Any) -> tuple[np.ndarray, dict[str, Any]]:
        obs, info = self.env.reset(**kwargs)
        for _ in range(self.k):
            self.frames.append(obs[:, :, 0])
        return self.observation(obs), info

    def observation(self, obs: np.ndarray) -> np.ndarray:
        self.frames.append(obs[:, :, 0])
        return np.stack(list(self.frames), axis=-1)
