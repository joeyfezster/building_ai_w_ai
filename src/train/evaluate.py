"""Evaluation helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.agents.dqn_agent import DQNAgent, DQNConfig
from src.envs.minipong import MiniPongEnv
from src.envs.wrappers import wrap_env
from src.rl.replay import ReplayBuffer


def evaluate_policy(
    checkpoint: Path | None,
    episodes: int,
    seeds: list[int],
    frame_stack: int,
    max_steps: int,
) -> dict[str, Any]:
    all_returns: list[float] = []
    all_hits: list[float] = []
    for seed in seeds:
        env = wrap_env(MiniPongEnv(), frame_stack=frame_stack)
        obs, _ = env.reset(seed=seed)
        replay = ReplayBuffer(capacity=10)
        agent = DQNAgent(obs.shape, env.action_space.n, replay, DQNConfig())
        if checkpoint is not None:
            data = torch.load(checkpoint, map_location=agent.device)
            agent.online.load_state_dict(data["model"])
            agent.target.load_state_dict(data["model"])
        for ep in range(episodes):
            obs, _ = env.reset(seed=seed + ep)
            done = False
            truncated = False
            ep_ret = 0.0
            steps = 0
            info: dict[str, Any] = {}
            while not done and not truncated and steps < max_steps:
                action = agent.act(obs, epsilon=0.0) if checkpoint else env.action_space.sample()
                obs, reward, done, truncated, info = env.step(action)
                ep_ret += reward
                steps += 1
            all_returns.append(ep_ret)
            all_hits.append(float(info.get("hits", 0)))
    return {
        "mean_return": float(np.mean(all_returns)) if all_returns else 0.0,
        "std_return": float(np.std(all_returns)) if all_returns else 0.0,
        "mean_hits": float(np.mean(all_hits)) if all_hits else 0.0,
        "episodes": len(all_returns),
        "seeds": seeds,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1])
    parser.add_argument("--frame-stack", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=1000)
    args = parser.parse_args()

    run_dir = Path("artifacts") / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    eval_dir = run_dir / "eval"
    eval_dir.mkdir(exist_ok=True)
    ckpt = Path(args.checkpoint) if args.checkpoint else None
    metrics = evaluate_policy(ckpt, args.episodes, args.seeds, args.frame_stack, args.max_steps)
    out_name = (
        "metrics_random.json" if ckpt is None else f"metrics_{Path(args.checkpoint).stem}.json"
    )
    (eval_dir / out_name).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
