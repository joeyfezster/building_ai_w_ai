"""Record gameplay videos for a policy."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Mapping

import imageio
import torch

from src.agents.dqn_agent import DQNAgent, DQNHyperparams
from src.configs import ConfigError, load_config, require_keys
from src.envs.atari_ale import make_atari_env
from src.obs.logging import MetricsLogger
from src.utils import OutputPathError, ensure_writable_dir, seed_env, set_global_seeds


def record_video(config: Mapping[str, Any]) -> None:
    """Record gameplay video using the provided configuration."""

    require_keys(config, {"env_id", "seed", "num_episodes", "output_dir", "video"})
    output_dir = ensure_writable_dir(Path(str(config["output_dir"])))
    env_config = config.get("env", {})
    env_id = str(config["env_id"])
    seed = int(config["seed"])
    num_episodes = int(config["num_episodes"])
    set_global_seeds(seed)
    video_config = config["video"]
    enabled = bool(video_config.get("enabled", True))
    fps = int(video_config.get("fps", 30))
    max_frames = video_config.get("max_frames")
    frame_limit = int(max_frames) if max_frames is not None else None
    prefix = str(video_config.get("prefix", "episode"))
    policy_config = config.get("policy", {"type": "random"})
    policy_type = str(policy_config.get("type", "random"))
    env = make_atari_env(env_id, render_mode="rgb_array", wrapper_config=env_config)
    seed_env(env, seed)
    logger = MetricsLogger(output_dir)
    agent: DQNAgent | None = None
    if policy_type == "checkpoint":
        require_keys(config, {"dqn"})
        checkpoint_path = str(policy_config.get("checkpoint_path", ""))
        if not checkpoint_path:
            raise ConfigError("checkpoint_path must be set for checkpoint policy")
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
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        agent = DQNAgent(obs_shape, env.action_space.n, hyperparams, device)
        agent.load(checkpoint_path)
        agent.epsilon = 0.0
    videos_dir = output_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    for episode in range(1, num_episodes + 1):
        obs, _ = env.reset(seed=seed + episode)
        episode_return = 0.0
        episode_length = 0
        writer = None
        video_path = videos_dir / f"{prefix}_{episode:03d}.mp4"
        if enabled:
            writer = imageio.get_writer(video_path, fps=fps)
        done = False
        frames = 0
        while not done:
            if agent is None:
                action = env.action_space.sample()
            else:
                action = agent.act(obs, explore=False)
            obs, reward, terminated, truncated, _ = env.step(action)
            done = bool(terminated or truncated)
            episode_return += float(reward)
            episode_length += 1
            if writer is not None:
                frame = env.render()
                if frame is not None:
                    writer.append_data(frame)
            frames += 1
            if frame_limit is not None and frames >= frame_limit:
                done = True
        if writer is not None:
            writer.close()
        logger.log_metrics(
            {
                "episode": episode,
                "episode_return": episode_return,
                "episode_length": episode_length,
                "policy": policy_type,
                "video_path": str(video_path) if enabled else "",
            }
        )
    logger.close()
    env.close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record gameplay videos.")
    parser.add_argument("--config", required=True, help="Path to YAML config file.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        config = load_config(Path(args.config))
        record_video(config)
    except (ConfigError, OutputPathError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
        sys.exit(2)


if __name__ == "__main__":
    main()
