# MiniPong Environment Spec

## Overview

Custom "MiniPong" Gymnasium environment implemented in pure Python + NumPy with deterministic physics. Supports `render_mode="rgb_array"` and returns pixel observations (uint8).

## Action Space

Discrete(3): UP (0), DOWN (1), STAY (2)

## Observation Space

Pixel image only (uint8). Default 84x84 grayscale (single channel). Shape: `(84, 84, 1)`.

The policy receives ONLY pixel observations. No privileged info dict data is consumed by the agent.

## Reward

- +1 when opponent misses (agent scores)
- -1 when agent misses (opponent scores)
- Optional light reward shaping behind a config flag (`reward_shaping: bool`)

## Physics

Deterministic given seed:
- Ball spawn position and velocity determined by RNG seeded at reset
- Paddle speed is a fixed config parameter
- Ball bounces off top/bottom walls
- Ball resets to center after scoring

## Configuration

Via `MiniPongConfig` dataclass:
- `width`: 84
- `height`: 84
- `paddle_height`: 16
- `paddle_width`: 3
- `paddle_speed`: 3
- `ball_size`: 3
- `max_steps`: 1200
- `reward_shaping`: False
- `score_limit`: 1 (default — terminates after 1 point, preserving existing RL training behavior; set higher for multi-rally interactive play, e.g., 11)

## Multi-Rally Mode

When `score_limit > 1`, a point does NOT end the episode. Instead:
- The ball resets to center with a new random velocity (using the episode's RNG).
- Cumulative scores (`agent_score`, `opponent_score`) are tracked across rallies within the episode.
- The episode terminates when either side reaches `score_limit`.
- `episode_reason` is set to `"score_limit"` when the game ends via score limit.
- With `score_limit=1`, behavior is identical to the current single-point termination (backward compatible).

## Info Dict

Every step and reset returns an info dict containing:
- `rally_length`: current rally count
- `hits`: total paddle hits this episode
- `misses`: total misses this episode
- `agent_score`: agent's cumulative score
- `opponent_score`: opponent's cumulative score
- `episode_reason`: why episode ended ("running", "max_steps", "score_limit", "agent_miss", "opponent_miss")

## Rendering

`render_mode="rgb_array"` produces frames suitable for video recording. Frame shape matches observation space.

## Determinism

Given the same seed, `reset()` and a fixed sequence of actions must produce identical observations, rewards, and info dicts. This is load-bearing for reproducible evaluation.

## Registration

Environment should be registered with Gymnasium as `MiniPong-v0` for standard API usage.
