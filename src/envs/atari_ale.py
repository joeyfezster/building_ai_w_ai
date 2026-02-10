"""Atari ALE environment builder."""

from __future__ import annotations

from typing import Any, Mapping

import ale_py as _ale_py
import gymnasium as gym

from src.envs.wrappers import wrap_env


def make_atari_env(
    name: str,
    render_mode: str | None = None,
    wrapper_config: Mapping[str, Any] | None = None,
) -> gym.Env:
    """Create a wrapped Atari ALE environment by name."""

    _ = _ale_py.__name__
    env = gym.make(name, render_mode=render_mode, repeat_action_probability=0.0)
    config = dict(wrapper_config or {})
    return wrap_env(
        env,
        frame_skip=int(config.get("frame_skip", 4)),
        screen_size=int(config.get("screen_size", 84)),
        grayscale=bool(config.get("grayscale", True)),
        frame_stack=int(config.get("frame_stack", 4)),
        clip_rewards=bool(config.get("clip_rewards", False)),
        scale_obs=bool(config.get("scale_obs", True)),
    )
