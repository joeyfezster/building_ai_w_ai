"""Environment wrappers for frame stacking."""

from __future__ import annotations

import collections
from typing import Any

import gymnasium as gym
import numpy as np


class FrameStackPixels(gym.Wrapper[np.ndarray, int, np.ndarray, int]):
    def __init__(self, env: gym.Env[np.ndarray, int], n_frames: int = 4) -> None:
        super().__init__(env)
        self.n_frames = n_frames
        self.frames: collections.deque[np.ndarray] = collections.deque(maxlen=n_frames)
        h, w, c = env.observation_space.shape
        self.observation_space = gym.spaces.Box(0, 255, shape=(h, w, c * n_frames), dtype=np.uint8)

    def reset(self, **kwargs: Any) -> tuple[np.ndarray, dict[str, Any]]:
        obs, info = self.env.reset(**kwargs)
        for _ in range(self.n_frames):
            self.frames.append(obs)
        return self._get_obs(), info

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        obs, reward, terminated, truncated, info = self.env.step(action)
        self.frames.append(obs)
        return self._get_obs(), reward, terminated, truncated, info

    def _get_obs(self) -> np.ndarray:
        return np.concatenate(list(self.frames), axis=2)


def wrap_env(env: Any, frame_stack: int = 1) -> Any:
    if frame_stack <= 1:
        return env
    return FrameStackPixels(env, n_frames=frame_stack)
