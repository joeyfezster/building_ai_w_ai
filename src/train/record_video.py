"""Record evaluation video."""

from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
import torch

from src.agents.dqn_agent import DQNAgent, DQNConfig
from src.envs.minipong import MiniPongEnv
from src.envs.wrappers import wrap_env
from src.rl.replay import ReplayBuffer


def record_video(
    checkpoint: Path | None, output_path: Path, seed: int = 0, max_steps: int = 1000
) -> None:
    env = wrap_env(MiniPongEnv(render_mode="rgb_array"), frame_stack=4)
    obs, _ = env.reset(seed=seed)
    replay = ReplayBuffer(capacity=8)
    agent = DQNAgent(obs.shape, env.action_space.n, replay, DQNConfig())
    if checkpoint is not None:
        data = torch.load(checkpoint, map_location=agent.device)
        agent.online.load_state_dict(data["model"])
    frames = []
    done = False
    trunc = False
    steps = 0
    while not done and not trunc and steps < max_steps:
        action = agent.act(obs, epsilon=0.0) if checkpoint else env.action_space.sample()
        obs, _, done, trunc, _ = env.step(action)
        frame = env.unwrapped.render()
        frames.append(frame)
        steps += 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(output_path, frames, fps=30)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    ckpt = Path(args.checkpoint) if args.checkpoint else None
    record_video(ckpt, Path(args.output), seed=args.seed)


if __name__ == "__main__":
    main()
