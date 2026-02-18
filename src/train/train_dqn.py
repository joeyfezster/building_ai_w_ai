from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
import yaml  # type: ignore[import-untyped]
from torch.utils.tensorboard import SummaryWriter

from src.envs.registry import make_env
from src.obs.logging import JsonlLogger
from src.rl import QNetwork, ReplayBuffer, Transition, linear_schedule, select_action, td_loss
from src.train.evaluate import evaluate_policy


def train(config_path: Path) -> str:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    run_id = cfg.get("run_id") or time.strftime("run_%Y%m%d_%H%M%S")
    run_dir = Path("artifacts") / run_id
    ckpt_dir = run_dir / "checkpoints"
    eval_dir = run_dir / "eval"
    video_dir = run_dir / "videos"
    for p in [ckpt_dir, eval_dir, video_dir]:
        p.mkdir(parents=True, exist_ok=True)

    seed = int(cfg["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    env = make_env(
        seed=seed,
        frame_stack=int(cfg["frame_stack"]),
        reward_shaping=bool(cfg.get("reward_shaping", False)),
    )
    obs_shape = env.observation_space.shape
    n_actions = env.action_space.n

    q_net = QNetwork(obs_shape, n_actions)
    target_net = QNetwork(obs_shape, n_actions)
    target_net.load_state_dict(q_net.state_dict())
    opt = torch.optim.Adam(q_net.parameters(), lr=float(cfg["lr"]))

    rb = ReplayBuffer(int(cfg["replay_capacity"]), obs_shape)
    writer = SummaryWriter(log_dir=str(run_dir / "tensorboard"))
    logger = JsonlLogger(run_dir / "logs.jsonl")

    total_steps = int(cfg["total_steps"])
    batch_size = int(cfg["batch_size"])
    gamma = float(cfg["gamma"])
    warmup = int(cfg["warmup_steps"])
    train_freq = int(cfg["train_freq"])
    target_period = int(cfg["target_update_period"])
    eval_every = int(cfg["eval_every"])
    ckpt_every = int(cfg["checkpoint_every"])

    baseline = evaluate_policy(
        eval_dir, checkpoint=None, episodes=int(cfg["eval_episodes"]), seeds=list(cfg["eval_seeds"])
    )
    (eval_dir / "metrics_random.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")

    obs, _ = env.reset(seed=seed)
    ep_ret = 0.0
    for step in range(1, total_steps + 1):
        eps = linear_schedule(
            float(cfg["epsilon_start"]),
            float(cfg["epsilon_end"]),
            step,
            int(cfg["epsilon_decay_steps"]),
        )
        with torch.no_grad():
            q_vals = q_net(torch.tensor(obs).unsqueeze(0))
        action = select_action(q_vals, eps, rng, n_actions)
        next_obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        rb.add(
            Transition(obs=obs, action=action, reward=float(reward), next_obs=next_obs, done=done)
        )
        obs = next_obs
        ep_ret += reward

        if done:
            logger.log(
                {
                    "step": step,
                    "event": "episode_end",
                    "episode_return": ep_ret,
                    "hits": info["hits"],
                    "misses": info["misses"],
                }
            )
            writer.add_scalar("train/episode_return", ep_ret, step)
            ep_ret = 0.0
            obs, _ = env.reset(seed=seed + step)

        if rb.size >= warmup and step % train_freq == 0:
            batch = rb.sample(batch_size, np_rng)
            loss = td_loss(q_net, target_net, batch, gamma=gamma, device=torch.device("cpu"))
            opt.zero_grad()
            loss.backward()
            opt.step()
            writer.add_scalar("train/loss", float(loss.item()), step)
            writer.add_scalar("train/epsilon", eps, step)
            logger.log({"step": step, "event": "train", "loss": float(loss.item()), "epsilon": eps})

        if step % target_period == 0:
            target_net.load_state_dict(q_net.state_dict())

        if step % ckpt_every == 0 or step == total_steps:
            ckpt = ckpt_dir / f"step_{step}.pt"
            torch.save(q_net.state_dict(), ckpt)

        if step % eval_every == 0 or step == total_steps:
            ckpt = ckpt_dir / f"step_{step}.pt"
            metrics = evaluate_policy(
                eval_dir,
                checkpoint=ckpt,
                episodes=int(cfg["eval_episodes"]),
                seeds=list(cfg["eval_seeds"]),
            )
            (eval_dir / f"metrics_step_{step}.json").write_text(
                json.dumps(metrics, indent=2), encoding="utf-8"
            )
            writer.add_scalar("eval/mean_return", metrics["mean_return"], step)
            writer.add_scalar("eval/mean_hits", metrics["mean_hits"], step)
            writer.add_scalar("eval/mean_rally_length", metrics["mean_rally_length"], step)
            logger.log({"step": step, "event": "eval", **metrics})

    writer.close()
    env.close()
    return run_id


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/dqn_minipong.yaml")
    args = p.parse_args()
    run_id = train(Path(args.config))
    print(run_id)


if __name__ == "__main__":
    main()
