"""Environment wrappers for Atari preprocessing."""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np


class NumpyObservation(gym.ObservationWrapper):
    """Ensure observations are NumPy arrays."""

    def observation(self, observation: Any) -> np.ndarray:
        return np.asarray(observation)


class ChannelFirstObservation(gym.ObservationWrapper):
    """Move channel axis to the first dimension."""

    def __init__(self, env: gym.Env) -> None:
        super().__init__(env)
        obs_space = env.observation_space
        if isinstance(obs_space, gym.spaces.Box) and len(obs_space.shape) == 3:
            height, width, channels = obs_space.shape
            low = float(np.min(obs_space.low))
            high = float(np.max(obs_space.high))
            self.observation_space = gym.spaces.Box(
                low=low,
                high=high,
                shape=(channels, height, width),
                dtype=obs_space.dtype,
            )

    def observation(self, observation: np.ndarray) -> np.ndarray:
        if observation.ndim == 3:
            return np.moveaxis(observation, -1, 0)
        return observation


class ScaleObservation(gym.ObservationWrapper):
    """Scale observations to [0, 1] float32."""

    def __init__(self, env: gym.Env) -> None:
        super().__init__(env)
        obs_space = env.observation_space
        if isinstance(obs_space, gym.spaces.Box):
            self.observation_space = gym.spaces.Box(
                low=0.0,
                high=1.0,
                shape=obs_space.shape,
                dtype=np.float32,
            )

    def observation(self, observation: np.ndarray) -> np.ndarray:
        return observation.astype(np.float32) / 255.0


def wrap_env(
    env: gym.Env,
    frame_skip: int = 4,
    screen_size: int = 84,
    grayscale: bool = True,
    frame_stack: int = 4,
    clip_rewards: bool = False,
    scale_obs: bool = True,
) -> gym.Env:
    """Apply standard Atari wrappers to an environment."""

    env = gym.wrappers.AtariPreprocessing(
        env,
        frame_skip=frame_skip,
        screen_size=screen_size,
        grayscale_obs=grayscale,
        scale_obs=False,
    )
    if clip_rewards:
        env = gym.wrappers.ClipReward(env)
    if frame_stack > 1:
        env = gym.wrappers.FrameStack(env, num_stack=frame_stack)
    env = NumpyObservation(env)
    env = ChannelFirstObservation(env)
    if scale_obs:
        env = ScaleObservation(env)
    return env
