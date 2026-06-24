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
    flip_augment: bool = False,
) -> dict[str, Any]:
    all_returns: list[float] = []
    all_hits: list[float] = []
    all_misses: list[float] = []
    all_rally_lengths: list[float] = []
    for seed in seeds:
        env = wrap_env(MiniPongEnv(), frame_stack=frame_stack)
        obs, _ = env.reset(seed=seed)
        replay = ReplayBuffer(capacity=10)
        agent = DQNAgent(
            obs.shape, env.action_space.n, replay,
            DQNConfig(flip_augment=flip_augment),
        )
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
            all_misses.append(float(info.get("misses", 0)))
            all_rally_lengths.append(float(info.get("rally_length", 0)))
    total_hits = float(np.sum(all_hits)) if all_hits else 0.0
    total_misses = float(np.sum(all_misses)) if all_misses else 0.0
    hit_ratio = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0.0
    return {
        "mean_return": float(np.mean(all_returns)) if all_returns else 0.0,
        "std_return": float(np.std(all_returns)) if all_returns else 0.0,
        "mean_hits": float(np.mean(all_hits)) if all_hits else 0.0,
        "mean_misses": float(np.mean(all_misses)) if all_misses else 0.0,
        "mean_rally_length": float(np.mean(all_rally_lengths)) if all_rally_lengths else 0.0,
        "hit_ratio": hit_ratio,
        "episodes": len(all_returns),
        "seeds": seeds,
    }


def evaluate_ppo_policy(
    checkpoint: Path | None,
    episodes: int,
    seeds: list[int],
    frame_stack: int,
    max_steps: int,
) -> dict[str, Any]:
    """Evaluate a PPO agent against the rule-based opponent."""
    from src.agents.ppo_agent import PPOAgent, PPOConfig

    all_returns: list[float] = []
    all_hits: list[float] = []
    all_misses: list[float] = []
    all_rally_lengths: list[float] = []
    for seed in seeds:
        env = wrap_env(MiniPongEnv(), frame_stack=frame_stack)
        obs, _ = env.reset(seed=seed)
        agent = PPOAgent(obs.shape, env.action_space.n, PPOConfig())
        if checkpoint is not None:
            data = torch.load(checkpoint, map_location=agent.device, weights_only=True)
            agent.network.load_state_dict(data["model"])
        for ep in range(episodes):
            obs, _ = env.reset(seed=seed + ep)
            done = False
            truncated = False
            ep_ret = 0.0
            steps = 0
            info: dict[str, Any] = {}
            while not done and not truncated and steps < max_steps:
                action = agent.act_deterministic(obs) if checkpoint else env.action_space.sample()
                obs, reward, done, truncated, info = env.step(action)
                ep_ret += reward
                steps += 1
            all_returns.append(ep_ret)
            all_hits.append(float(info.get("hits", 0)))
            all_misses.append(float(info.get("misses", 0)))
            all_rally_lengths.append(float(info.get("rally_length", 0)))
    total_hits = float(np.sum(all_hits)) if all_hits else 0.0
    total_misses = float(np.sum(all_misses)) if all_misses else 0.0
    hit_ratio = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0.0
    return {
        "mean_return": float(np.mean(all_returns)) if all_returns else 0.0,
        "std_return": float(np.std(all_returns)) if all_returns else 0.0,
        "mean_hits": float(np.mean(all_hits)) if all_hits else 0.0,
        "mean_misses": float(np.mean(all_misses)) if all_misses else 0.0,
        "mean_rally_length": float(np.mean(all_rally_lengths)) if all_rally_lengths else 0.0,
        "hit_ratio": hit_ratio,
        "episodes": len(all_returns),
        "seeds": seeds,
    }


def evaluate_ppo_selfplay(
    checkpoint: Path | None,
    n_rallies: int,
    frame_stack: int,
    max_steps: int,
) -> dict[str, Any]:
    """Evaluate PPO agent vs itself (both sides use same network)."""
    import collections as col

    from src.agents.ppo_agent import PPOAgent, PPOConfig

    env = MiniPongEnv()
    wrapped = wrap_env(env, frame_stack=frame_stack)
    agent = PPOAgent(wrapped.observation_space.shape, wrapped.action_space.n, PPOConfig())
    if checkpoint is not None:
        data = torch.load(checkpoint, map_location=agent.device, weights_only=True)
        agent.network.load_state_dict(data["model"])

    # Opponent frame stack (mirror-flipped)
    opp_frames: col.deque[np.ndarray] = col.deque(maxlen=frame_stack)

    rally_lengths: list[int] = []
    rallies_done = 0
    seed = 42

    while rallies_done < n_rallies:
        obs, _ = wrapped.reset(seed=seed + rallies_done)
        raw = env._obs()
        flipped = np.ascontiguousarray(np.flip(raw, axis=1))
        opp_frames.clear()
        for _ in range(frame_stack):
            opp_frames.append(flipped)

        done = False
        truncated = False
        steps = 0
        while not done and not truncated and steps < max_steps:
            action = agent.act_deterministic(obs)
            opp_obs = np.concatenate(list(opp_frames), axis=2)
            opp_action = agent.act_deterministic(opp_obs)
            env.set_opponent_action(opp_action)
            obs, _, done, truncated, info = wrapped.step(action)
            raw = env._obs()
            flipped = np.ascontiguousarray(np.flip(raw, axis=1))
            opp_frames.append(flipped)
            steps += 1

        rally_lengths.append(info.get("rally_length", 0))
        rallies_done += 1
        env.set_opponent_action(None)

    return {
        "mean_rally_length": float(np.mean(rally_lengths)) if rally_lengths else 0.0,
        "max_rally_length": int(np.max(rally_lengths)) if rally_lengths else 0,
        "std_rally_length": float(np.std(rally_lengths)) if rally_lengths else 0.0,
        "n_rallies": len(rally_lengths),
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
