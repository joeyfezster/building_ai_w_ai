"""Open-source deterministic MiniPong environment."""

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
    paddle_height: int = 16
    paddle_width: int = 3
    paddle_speed: int = 3
    ball_size: int = 3
    max_steps: int = 1200
    reward_shaping: bool = False
    score_limit: int = 1


class MiniPongEnv(gym.Env[np.ndarray, int]):
    metadata = {"render_modes": ["rgb_array"], "render_fps": 30}

    def __init__(
        self, render_mode: str | None = None, config: MiniPongConfig | None = None
    ) -> None:
        self.config = config or MiniPongConfig()
        self.render_mode = render_mode
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(
            low=0,
            high=255,
            shape=(self.config.height, self.config.width, 1),
            dtype=np.uint8,
        )
        self._rng = np.random.default_rng(0)
        self.steps = 0
        self.agent_score = 0
        self.opponent_score = 0
        self.hits = 0
        self.misses = 0
        self.rally_length = 0
        self.episode_reason = "running"
        self._manual_opponent_action: int | None = None

        self.agent_y = 0.0
        self.opponent_y = 0.0
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
        self.steps = 0
        self.hits = 0
        self.misses = 0
        self.rally_length = 0
        self.agent_score = 0
        self.opponent_score = 0
        self.episode_reason = "running"
        self._manual_opponent_action = None

        self.agent_y = (self.config.height - self.config.paddle_height) / 2
        self.opponent_y = self.agent_y
        self._reset_ball()
        return self._obs(), self._info()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        self.steps += 1
        self._move_agent(int(action))
        self._move_opponent()
        reward = 0.0

        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        if self.ball_y <= 0 or self.ball_y >= self.config.height - self.config.ball_size:
            self.ball_vy *= -1
            self.ball_y = np.clip(self.ball_y, 0, self.config.height - self.config.ball_size)

        left_x = 4
        right_x = self.config.width - 4 - self.config.paddle_width

        if self.ball_vx < 0 and self.ball_x <= left_x + self.config.paddle_width:
            if self.agent_y <= self.ball_y <= self.agent_y + self.config.paddle_height:
                self.ball_vx = abs(self.ball_vx)
                self.hits += 1
                self.rally_length += 1
                if self.config.reward_shaping:
                    reward += 0.01
            else:
                reward -= 1.0
                self.opponent_score += 1
                self.misses += 1
                return self._finish_point(reward=reward, scorer="opponent")

        if self.ball_vx > 0 and self.ball_x + self.config.ball_size >= right_x:
            if self.opponent_y <= self.ball_y <= self.opponent_y + self.config.paddle_height:
                self.ball_vx = -abs(self.ball_vx)
                self.rally_length += 1
            else:
                reward += 1.0
                self.agent_score += 1
                return self._finish_point(reward=reward, scorer="agent")

        truncated = self.steps >= self.config.max_steps
        if truncated:
            self.episode_reason = "max_steps"
        return self._obs(), reward, False, truncated, self._info()

    def render(self) -> np.ndarray:
        gray = self._obs().squeeze(-1)
        rgb = np.repeat(gray[..., None], 3, axis=2)
        return rgb

    def _move_agent(self, action: int) -> None:
        if action == 0:
            self.agent_y -= self.config.paddle_speed
        elif action == 1:
            self.agent_y += self.config.paddle_speed
        self.agent_y = float(
            np.clip(self.agent_y, 0, self.config.height - self.config.paddle_height)
        )

    def _move_opponent(self) -> None:
        if self._manual_opponent_action is not None:
            if self._manual_opponent_action == 0:
                self.opponent_y -= self.config.paddle_speed
            elif self._manual_opponent_action == 1:
                self.opponent_y += self.config.paddle_speed
            self.opponent_y = float(
                np.clip(self.opponent_y, 0, self.config.height - self.config.paddle_height)
            )
            return

        center = self.opponent_y + self.config.paddle_height / 2
        target = self.ball_y + self.config.ball_size / 2
        if target > center:
            self.opponent_y += self.config.paddle_speed * 0.9
        else:
            self.opponent_y -= self.config.paddle_speed * 0.9
        self.opponent_y = float(
            np.clip(self.opponent_y, 0, self.config.height - self.config.paddle_height)
        )

    def set_opponent_action(self, action: int | None) -> None:
        self._manual_opponent_action = action

    def _reset_ball(self) -> None:
        self.ball_x = self.config.width / 2
        self.ball_y = self.config.height / 2
        self.ball_vx = float(self._rng.choice([-2, 2]))
        self.ball_vy = float(self._rng.choice([-1, 1]))

    def _finish_point(
        self, reward: float, scorer: str
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self.config.score_limit <= 1:
            self.episode_reason = "opponent_miss" if scorer == "agent" else "agent_miss"
            return self._obs(), reward, True, False, self._info()

        if (
            self.agent_score >= self.config.score_limit
            or self.opponent_score >= self.config.score_limit
        ):
            self.episode_reason = "score_limit"
            return self._obs(), reward, True, False, self._info()

        self.rally_length = 0
        self.episode_reason = "running"
        self._reset_ball()
        return self._obs(), reward, False, False, self._info()

    def _obs(self) -> np.ndarray:
        frame = np.zeros((self.config.height, self.config.width), dtype=np.uint8)
        left_x = 4
        right_x = self.config.width - 4 - self.config.paddle_width
        ay = int(self.agent_y)
        oy = int(self.opponent_y)
        bx = int(self.ball_x)
        by = int(self.ball_y)
        frame[ay : ay + self.config.paddle_height, left_x : left_x + self.config.paddle_width] = 255
        frame[oy : oy + self.config.paddle_height, right_x : right_x + self.config.paddle_width] = (
            255
        )
        frame[by : by + self.config.ball_size, bx : bx + self.config.ball_size] = 255
        return frame[..., None]

    def _info(self) -> dict[str, Any]:
        return {
            "rally_length": self.rally_length,
            "hits": self.hits,
            "misses": self.misses,
            "agent_score": self.agent_score,
            "opponent_score": self.opponent_score,
            "episode_reason": self.episode_reason,
        }
