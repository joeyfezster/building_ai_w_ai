from __future__ import annotations

from collections import deque
from typing import Any


class FrameStackGray:
    def __init__(self, env: Any, k: int = 4) -> None:
        self.env = env
        self.k = k
        self.frames: deque[list[list[int]]] = deque(maxlen=k)
        h, w, _ = env.observation_space.shape
        self.observation_space = type("Box", (), {"shape": (h, w, k), "dtype": "uint8"})()
        self.action_space = env.action_space

    def reset(self, **kwargs: Any) -> tuple[list[list[list[int]]], dict[str, Any]]:
        obs, info = self.env.reset(**kwargs)
        first = [[pix[0] for pix in row] for row in obs]
        for _ in range(self.k):
            self.frames.append(first)
        return self.observation(obs), info

    def observation(self, obs: list[list[list[int]]]) -> list[list[list[int]]]:
        self.frames.append([[pix[0] for pix in row] for row in obs])
        h = len(self.frames[0])
        w = len(self.frames[0][0])
        return [[[self.frames[i][y][x] for i in range(self.k)] for x in range(w)] for y in range(h)]

    def step(self, action: int) -> tuple[list[list[list[int]]], float, bool, bool, dict[str, Any]]:
        obs, reward, terminated, truncated, info = self.env.step(action)
        return self.observation(obs), reward, terminated, truncated, info

    @property
    def unwrapped(self) -> Any:
        return self.env.unwrapped

    def close(self) -> None:
        self.env.close()
