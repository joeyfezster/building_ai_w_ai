from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces


@dataclass
class MiniPongConfig:
    width: int = 84
    height: int = 84
    paddle_height: int = 14
    paddle_width: int = 2
    paddle_speed: int = 3
    ball_size: int = 2
    max_steps: int = 1000
    reward_shaping: bool = False


class MiniPongEnv(gym.Env[np.ndarray, int]):
    metadata = {"render_modes": ["rgb_array"], "render_fps": 30}

    def __init__(
        self, render_mode: str | None = None, config: MiniPongConfig | None = None
    ) -> None:
        super().__init__()
        self.render_mode = render_mode
        self.cfg = config or MiniPongConfig()
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(
            low=0,
            high=255,
            shape=(self.cfg.height, self.cfg.width, 1),
            dtype=np.uint8,
        )
        self._rng = np.random.default_rng(0)
        self._steps = 0
        self.agent_score = 0
        self.opponent_score = 0
        self.hits = 0
        self.misses = 0
        self.rally_length = 0
        self.agent_y = 0
        self.opp_y = 0
        self.ball_x = 0.0
        self.ball_y = 0.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self._steps = 0
        self.agent_score = 0
        self.opponent_score = 0
        self.hits = 0
        self.misses = 0
        self.rally_length = 0
        self.agent_y = (self.cfg.height - self.cfg.paddle_height) // 2
        self.opp_y = (self.cfg.height - self.cfg.paddle_height) // 2
        self._spawn_ball()
        return self._render_gray(), self._info("reset")

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        self._steps += 1
        self._move_paddle(action)
        self._move_opponent()

        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        if self.ball_y <= 0 or self.ball_y >= self.cfg.height - self.cfg.ball_size:
            self.ball_vy *= -1
            self.ball_y = float(np.clip(self.ball_y, 0, self.cfg.height - self.cfg.ball_size))

        reward = 0.0
        reason = "running"

        if self.ball_vx < 0 and self.ball_x <= self.cfg.paddle_width:
            if self.agent_y <= self.ball_y <= self.agent_y + self.cfg.paddle_height:
                self.ball_vx *= -1
                self.ball_x = float(self.cfg.paddle_width)
                self.hits += 1
                self.rally_length += 1
                if self.cfg.reward_shaping:
                    reward += 0.05
            else:
                reward = -1.0
                self.opponent_score += 1
                self.misses += 1
                reason = "agent_miss"
                self._spawn_ball(direction=1)
                self.rally_length = 0

        right_x = self.cfg.width - self.cfg.paddle_width - self.cfg.ball_size
        if self.ball_vx > 0 and self.ball_x >= right_x:
            if self.opp_y <= self.ball_y <= self.opp_y + self.cfg.paddle_height:
                self.ball_vx *= -1
                self.ball_x = float(right_x)
            else:
                reward = 1.0
                self.agent_score += 1
                reason = "opponent_miss"
                self._spawn_ball(direction=-1)
                self.rally_length = 0

        terminated = False
        truncated = self._steps >= self.cfg.max_steps
        if truncated and reason == "running":
            reason = "time_limit"

        return self._render_gray(), reward, terminated, truncated, self._info(reason)

    def render(self) -> np.ndarray:
        rgb = np.zeros((self.cfg.height, self.cfg.width, 3), dtype=np.uint8)
        rgb[:, :, :] = 20
        rgb[self.agent_y : self.agent_y + self.cfg.paddle_height, 0 : self.cfg.paddle_width, :] = (
            220
        )
        rgb[self.opp_y : self.opp_y + self.cfg.paddle_height, -self.cfg.paddle_width :, :] = 220
        bx = int(self.ball_x)
        by = int(self.ball_y)
        rgb[by : by + self.cfg.ball_size, bx : bx + self.cfg.ball_size, :] = [255, 255, 255]
        return rgb

    def _render_gray(self) -> np.ndarray:
        frame = self.render()
        return frame.mean(axis=2, keepdims=True).astype(np.uint8)

    def _spawn_ball(self, direction: int | None = None) -> None:
        self.ball_x = self.cfg.width / 2
        self.ball_y = float(self._rng.integers(10, self.cfg.height - 10))
        horizontal = direction if direction is not None else int(self._rng.choice([-1, 1]))
        self.ball_vx = 2.0 * horizontal
        self.ball_vy = float(self._rng.choice([-1, 1])) * 1.5

    def _move_paddle(self, action: int) -> None:
        if action == 0:
            self.agent_y -= self.cfg.paddle_speed
        elif action == 1:
            self.agent_y += self.cfg.paddle_speed
        self.agent_y = int(np.clip(self.agent_y, 0, self.cfg.height - self.cfg.paddle_height))

    def _move_opponent(self) -> None:
        center = self.opp_y + self.cfg.paddle_height / 2
        if self.ball_y < center:
            self.opp_y -= self.cfg.paddle_speed
        elif self.ball_y > center:
            self.opp_y += self.cfg.paddle_speed
        self.opp_y = int(np.clip(self.opp_y, 0, self.cfg.height - self.cfg.paddle_height))

    def _info(self, reason: str) -> dict[str, Any]:
        return {
            "rally_length": self.rally_length,
            "hits": self.hits,
            "misses": self.misses,
            "agent_score": self.agent_score,
            "opponent_score": self.opponent_score,
            "episode_reason": reason,
            "ball_speed": float(np.sqrt(self.ball_vx**2 + self.ball_vy**2)),
            "paddle_position": self.agent_y,
        }
