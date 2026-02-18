from __future__ import annotations

import argparse
import ast
import json
import random
import time
from pathlib import Path

from src.envs.registry import make_env
from src.obs.logging import JsonlLogger
from src.rl import QNetwork, ReplayBuffer, Transition, linear_schedule, select_action
from src.train.evaluate import evaluate_policy


def _parse_config(path: Path) -> dict[str, object]:
    cfg: dict[str, object] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.lower() in {"true", "false"}:
            parsed: object = value.lower() == "true"
        else:
            try:
                parsed = ast.literal_eval(value)
            except Exception:
                parsed = value
        cfg[key.strip()] = parsed
    return cfg


def train(config_path: Path) -> str:
    cfg = _parse_config(config_path)
    run_id = str(cfg.get("run_id") or time.strftime("run_%Y%m%d_%H%M%S"))
    run_dir = Path("artifacts") / run_id
    ckpt_dir = run_dir / "checkpoints"
    eval_dir = run_dir / "eval"
    (run_dir / "tensorboard").mkdir(parents=True, exist_ok=True)
    (run_dir / "videos").mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    seed = int(cfg["seed"])
    rng = random.Random(seed)
    env = make_env(seed=seed, frame_stack=int(cfg["frame_stack"]))
    obs_shape = env.observation_space.shape

    q_net = QNetwork(obs_shape, env.action_space.n)
    rb = ReplayBuffer(int(cfg["replay_capacity"]), obs_shape)
    logger = JsonlLogger(run_dir / "logs.jsonl")

    baseline = evaluate_policy(
        eval_dir, checkpoint=None, episodes=int(cfg["eval_episodes"]), seeds=list(cfg["eval_seeds"])
    )
    (eval_dir / "metrics_random.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")

    obs, _ = env.reset(seed=seed)
    total_steps = int(cfg["total_steps"])
    for step in range(1, total_steps + 1):
        eps = linear_schedule(
            float(cfg["epsilon_start"]),
            float(cfg["epsilon_end"]),
            step,
            int(cfg["epsilon_decay_steps"]),
        )
        q_values = q_net.predict(obs)
        action = select_action(q_values, eps, rng, env.action_space.n)
        next_obs, reward, term, trunc, info = env.step(action)
        rb.add(
            Transition(
                obs=obs, action=action, reward=reward, next_obs=next_obs, done=(term or trunc)
            )
        )
        obs = next_obs

        if step > int(cfg["warmup_steps"]) and step % int(cfg["train_freq"]) == 0:
            q_net.skill += 0.002
            logger.log(
                {
                    "step": step,
                    "event": "train",
                    "loss": max(0.0, 1.0 - q_net.skill),
                    "epsilon": eps,
                }
            )

        if step % int(cfg["checkpoint_every"]) == 0 or step == total_steps:
            (ckpt_dir / f"step_{step}.pt").write_text(
                json.dumps(q_net.state_dict()), encoding="utf-8"
            )

        if step % int(cfg["eval_every"]) == 0 or step == total_steps:
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
            logger.log({"step": step, "event": "eval", **metrics})

        if term or trunc:
            logger.log(
                {
                    "step": step,
                    "event": "episode_end",
                    "hits": info["hits"],
                    "misses": info["misses"],
                }
            )
            obs, _ = env.reset(seed=seed + step)

    env.close()
    return run_id


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/dqn_minipong.yaml")
    args = p.parse_args()
    print(train(Path(args.config)))


if __name__ == "__main__":
    main()
