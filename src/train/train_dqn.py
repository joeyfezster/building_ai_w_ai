"""Train DQN on MiniPong."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from src.agents.dqn_agent import DQNAgent, DQNConfig
from src.envs.minipong import MiniPongEnv
from src.envs.wrappers import wrap_env
from src.obs.logging import MetricsLogger
from src.rl.replay import ReplayBuffer, Transition
from src.rl.schedules import linear_schedule
from src.train.evaluate import evaluate_policy


def train(config: dict) -> str:
    run_id = config.get("run_id", "local_run")
    run_dir = Path("artifacts") / run_id
    (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    (run_dir / "eval").mkdir(exist_ok=True)
    (run_dir / "videos").mkdir(exist_ok=True)

    env = wrap_env(MiniPongEnv(), frame_stack=int(config["frame_stack"]))
    obs, _ = env.reset(seed=int(config["seed"]))
    replay = ReplayBuffer(capacity=int(config["replay_capacity"]))
    agent = DQNAgent(
        obs.shape,
        env.action_space.n,
        replay,
        DQNConfig(
            lr=float(config["lr"]),
            gamma=float(config["gamma"]),
            batch_size=int(config["batch_size"]),
        ),
    )
    logger = MetricsLogger(run_dir)

    episode_return = 0.0
    total_steps = int(config["total_steps"])
    for step in range(1, total_steps + 1):
        eps = linear_schedule(
            step,
            float(config["epsilon_start"]),
            float(config["epsilon_end"]),
            int(config["epsilon_decay_steps"]),
        )
        action = agent.act(obs, epsilon=eps)
        next_obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        agent.observe(
            Transition(obs=obs, action=action, reward=reward, next_obs=next_obs, done=done)
        )
        episode_return += reward
        obs = next_obs

        loss = None
        if step > int(config["replay_warmup_steps"]) and len(replay) >= int(config["batch_size"]):
            loss = agent.update()
        if step % int(config["target_update_period"]) == 0:
            agent.sync_target()

        if done:
            logger.log_metrics(
                step,
                {
                    "train/episode_return": episode_return,
                    "train/hits": info.get("hits", 0),
                    "train/epsilon": eps,
                },
            )
            episode_return = 0.0
            obs, _ = env.reset(seed=int(config["seed"]) + step)

        if loss is not None and step % 10 == 0:
            logger.log_metrics(step, {"train/loss": loss, "train/epsilon": eps})

        if step % int(config["eval_every_steps"]) == 0:
            ckpt_path = run_dir / "checkpoints" / f"step_{step}.pt"
            import torch

            torch.save({"model": agent.online.state_dict(), "step": step}, ckpt_path)
            metrics = evaluate_policy(
                ckpt_path,
                int(config["eval_episodes"]),
                list(config["eval_seeds"]),
                int(config["frame_stack"]),
                int(config["max_episode_steps"]),
            )
            (run_dir / "eval" / f"metrics_step_{step}.json").write_text(
                json.dumps(metrics, indent=2), encoding="utf-8"
            )
            logger.log_metrics(
                step,
                {
                    "eval/mean_return": metrics["mean_return"],
                    "eval/mean_hits": metrics["mean_hits"],
                },
            )

    logger.close()
    return run_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/dqn_minipong.yaml")
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    if args.run_id:
        config["run_id"] = args.run_id
    run_id = train(config)
    print(run_id)


if __name__ == "__main__":
    main()
