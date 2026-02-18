from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any


class Discrete:
    def __init__(self, n: int, rng: Random) -> None:
        self.n = n
        self._rng = rng

    def sample(self) -> int:
        return self._rng.randrange(self.n)


class Box:
    def __init__(self, shape: tuple[int, int, int], dtype: str = "uint8") -> None:
        self.shape = shape
        self.dtype = dtype


@dataclass
class MiniPongConfig:
    width: int = 84
    height: int = 84
    paddle_height: int = 14
    paddle_width: int = 2
    paddle_speed: int = 3
    ball_size: int = 2
    max_steps: int = 80
    reward_shaping: bool = False


class MiniPongEnv:
    metadata = {"render_modes": ["rgb_array"], "render_fps": 30}

    def __init__(
        self, render_mode: str | None = None, config: MiniPongConfig | None = None
    ) -> None:
        self.render_mode = render_mode
        self.cfg = config or MiniPongConfig()
        self._rng = Random(0)
        self.action_space = Discrete(3, self._rng)
        self.observation_space = Box((self.cfg.height, self.cfg.width, 1))
        self.reset(seed=0)

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[list[list[list[int]]], dict[str, Any]]:
        if seed is not None:
            self._rng = Random(seed)
            self.action_space = Discrete(3, self._rng)
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

    def _spawn_ball(self, direction: int | None = None) -> None:
        self.ball_x = self.cfg.width // 2
        self.ball_y = self._rng.randrange(10, self.cfg.height - 10)
        dx = direction if direction is not None else (-1 if self._rng.random() < 0.5 else 1)
        self.ball_vx = dx * 2
        self.ball_vy = -1 if self._rng.random() < 0.5 else 1

    def _clip_paddles(self) -> None:
        max_y = self.cfg.height - self.cfg.paddle_height
        self.agent_y = max(0, min(max_y, self.agent_y))
        self.opp_y = max(0, min(max_y, self.opp_y))

    def step(self, action: int) -> tuple[list[list[list[int]]], float, bool, bool, dict[str, Any]]:
        self._steps += 1
        if action == 0:
            self.agent_y -= self.cfg.paddle_speed
        elif action == 1:
            self.agent_y += self.cfg.paddle_speed
        if self.ball_y < self.opp_y + self.cfg.paddle_height // 2:
            self.opp_y -= self.cfg.paddle_speed
        elif self.ball_y > self.opp_y + self.cfg.paddle_height // 2:
            self.opp_y += self.cfg.paddle_speed
        self._clip_paddles()

        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        if self.ball_y <= 0 or self.ball_y >= self.cfg.height - self.cfg.ball_size:
            self.ball_vy *= -1
            self.ball_y = max(0, min(self.cfg.height - self.cfg.ball_size, self.ball_y))

        reward = 0.0
        reason = "running"

        if self.ball_vx < 0 and self.ball_x <= self.cfg.paddle_width:
            if self.agent_y <= self.ball_y <= self.agent_y + self.cfg.paddle_height:
                self.ball_vx *= -1
                self.hits += 1
                self.rally_length += 1
                if self.cfg.reward_shaping:
                    reward += 0.05
            else:
                reward = -1.0
                self.opponent_score += 1
                self.misses += 1
                reason = "agent_miss"
                self.rally_length = 0
                self._spawn_ball(direction=1)

        if (
            self.ball_vx > 0
            and self.ball_x >= self.cfg.width - self.cfg.paddle_width - self.cfg.ball_size
        ):
            if self.opp_y <= self.ball_y <= self.opp_y + self.cfg.paddle_height:
                self.ball_vx *= -1
            else:
                reward = 1.0
                self.agent_score += 1
                reason = "opponent_miss"
                self.rally_length = 0
                self._spawn_ball(direction=-1)

        terminated = False
        truncated = self._steps >= self.cfg.max_steps
        if truncated and reason == "running":
            reason = "time_limit"

        return self._render_gray(), reward, terminated, truncated, self._info(reason)

    def render(self) -> list[list[list[int]]]:
        h, w = self.cfg.height, self.cfg.width
        frame = [[[20, 20, 20] for _ in range(w)] for _ in range(h)]
        for y in range(self.agent_y, self.agent_y + self.cfg.paddle_height):
            for x in range(self.cfg.paddle_width):
                frame[y][x] = [220, 220, 220]
        for y in range(self.opp_y, self.opp_y + self.cfg.paddle_height):
            for x in range(w - self.cfg.paddle_width, w):
                frame[y][x] = [220, 220, 220]
        bx, by = int(self.ball_x), int(self.ball_y)
        for y in range(by, min(by + self.cfg.ball_size, h)):
            for x in range(bx, min(bx + self.cfg.ball_size, w)):
                frame[y][x] = [255, 255, 255]
        return frame

    def _render_gray(self) -> list[list[list[int]]]:
        rgb = self.render()
        return [[[sum(px) // 3] for px in row] for row in rgb]

    def _info(self, reason: str) -> dict[str, Any]:
        return {
            "rally_length": self.rally_length,
            "hits": self.hits,
            "misses": self.misses,
            "agent_score": self.agent_score,
            "opponent_score": self.opponent_score,
            "episode_reason": reason,
            "ball_speed": abs(self.ball_vx) + abs(self.ball_vy),
            "paddle_position": self.agent_y,
        }

    @property
    def unwrapped(self) -> "MiniPongEnv":
        return self

    def close(self) -> None:
        return
