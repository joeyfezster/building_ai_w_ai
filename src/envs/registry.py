from __future__ import annotations

from src.envs.minipong import MiniPongConfig, MiniPongEnv
from src.envs.wrappers import FrameStackGray


def make_env(seed: int, frame_stack: int = 4, reward_shaping: bool = False):
    env = MiniPongEnv(render_mode="rgb_array", config=MiniPongConfig(reward_shaping=reward_shaping))
    env.reset(seed=seed)
    if frame_stack > 1:
        env = FrameStackGray(env, k=frame_stack)
    return env
