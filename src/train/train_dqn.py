"""Minimal DQN training loop."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
from typing import Any, Mapping

import torch
from torch.utils.tensorboard import SummaryWriter

from src.agents.dqn_agent import DQNAgent, DQNHyperparams
from src.configs import ConfigError, load_config, require_keys
from src.envs.atari_ale import make_atari_env
from src.obs.logging import MetricsLogger
from src.rl.replay import Transition
from src.rl.schedules import linear_schedule
from src.utils import OutputPathError, ensure_writable_dir, seed_env, set_global_seeds


def train(config: Mapping[str, Any]) -> None:
    """Train a DQN agent using the provided configuration."""

    require_keys(
        config,
        {
            "env_id",
            "seed",
            "total_steps",
            "output_dir",
            "video",
            "dqn",
        },
    )
    output_dir = ensure_writable_dir(Path(str(config["output_dir"])))
    env_config = config.get("env", {})
    env_id = str(config["env_id"])
    seed = int(config["seed"])
    total_steps = int(config["total_steps"])
    set_global_seeds(seed)
    device_name = str(config.get("device", "auto"))
    if device_name == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device_name)
    env = make_atari_env(env_id, wrapper_config=env_config)
    seed_env(env, seed)
    obs_shape = env.observation_space.shape
    if obs_shape is None:
        raise RuntimeError("Observation space missing shape")
    dqn_config = config["dqn"]
    require_keys(
        dqn_config,
        {
            "gamma",
            "batch_size",
            "buffer_capacity",
            "learning_rate",
            "target_update_interval",
            "train_interval",
            "max_grad_norm",
            "epsilon_start",
            "epsilon_end",
            "epsilon_decay_steps",
        },
    )
    hyperparams = DQNHyperparams(
        gamma=float(dqn_config["gamma"]),
        batch_size=int(dqn_config["batch_size"]),
        buffer_capacity=int(dqn_config["buffer_capacity"]),
        learning_rate=float(dqn_config["learning_rate"]),
        target_update_interval=int(dqn_config["target_update_interval"]),
        train_interval=int(dqn_config["train_interval"]),
        max_grad_norm=float(dqn_config["max_grad_norm"]),
    )
    agent = DQNAgent(obs_shape, env.action_space.n, hyperparams, device)
    run_id = str(
        config.get(
            "run_id",
            f"dqn_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_seed{seed}",
        )
    )
    runs_dir = output_dir / "runs" / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    writer = SummaryWriter(str(runs_dir))
    logger = MetricsLogger(output_dir)
    obs, _ = env.reset()
    episode_return = 0.0
    episode_length = 0
    last_log_time = time.time()
    last_log_step = 0
    log_interval = int(dqn_config.get("log_interval", 1000))
    for step in range(1, total_steps + 1):
        epsilon = linear_schedule(
            step=step,
            start=float(dqn_config["epsilon_start"]),
            end=float(dqn_config["epsilon_end"]),
            duration=int(dqn_config["epsilon_decay_steps"]),
        )
        agent.epsilon = epsilon
        action = agent.act(obs, explore=True)
        next_obs, reward, terminated, truncated, _ = env.step(action)
        done = bool(terminated or truncated)
        transition = Transition(obs, action, float(reward), next_obs, done)
        agent.observe(transition)
        learn_metrics = agent.learn()
        episode_return += float(reward)
        episode_length += 1
        if learn_metrics:
            writer.add_scalar("loss", learn_metrics["loss"], step)
            logger.log_metrics(
                {
                    "step": step,
                    "loss": learn_metrics["loss"],
                    "epsilon": epsilon,
                }
            )
        if step % log_interval == 0:
            now = time.time()
            steps_per_second = (step - last_log_step) / max(now - last_log_time, 1e-6)
            writer.add_scalar("steps_per_second", steps_per_second, step)
            logger.log_metrics(
                {
                    "step": step,
                    "steps_per_second": steps_per_second,
                    "epsilon": epsilon,
                }
            )
            last_log_step = step
            last_log_time = now
        if done:
            writer.add_scalar("episode_return", episode_return, step)
            writer.add_scalar("episode_length", episode_length, step)
            logger.log_metrics(
                {
                    "step": step,
                    "episode_return": episode_return,
                    "episode_length": episode_length,
                }
            )
            obs, _ = env.reset()
            episode_return = 0.0
            episode_length = 0
        else:
            obs = next_obs
    checkpoints_dir = output_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    agent.save(str(checkpoints_dir / "latest.pt"))
    logger.close()
    writer.close()
    env.close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a DQN agent on Atari.")
    parser.add_argument("--config", required=True, help="Path to YAML config file.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        config = load_config(Path(args.config))
        train(config)
    except (ConfigError, OutputPathError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
        sys.exit(2)


if __name__ == "__main__":
    main()
