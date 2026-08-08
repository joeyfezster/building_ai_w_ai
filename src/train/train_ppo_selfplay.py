"""Train PPO with self-play: opponent sampled from checkpoint pool."""

from __future__ import annotations

import argparse
import collections
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.distributions import Categorical

from src.agents.ppo_agent import PPOAgent, PPOConfig
from src.envs.minipong import MiniPongConfig, MiniPongEnv
from src.envs.wrappers import wrap_env
from src.obs.logging import MetricsLogger
from src.rl.networks import create_actor_critic
from src.rl.rollout import RolloutBuffer
from src.train.evaluate import evaluate_ppo_policy, evaluate_ppo_selfplay
from src.train.train_dqn import _format_elapsed, _format_eta, resolve_device


class PPOSelfPlayOpponent:
    """PPO opponent with mirror-flipped frame stack and stochastic policy."""

    def __init__(
        self,
        obs_shape: tuple[int, ...],
        num_actions: int,
        frame_stack: int,
        device: torch.device,
    ) -> None:
        self.device = device
        self.frame_stack = frame_stack
        self.network = create_actor_critic(obs_shape, num_actions).to(device)
        self.network.eval()
        self.frames: collections.deque[np.ndarray] = collections.deque(maxlen=frame_stack)

    def reset(self, raw_obs: np.ndarray) -> None:
        flipped = np.ascontiguousarray(np.flip(raw_obs, axis=1))
        self.frames.clear()
        for _ in range(self.frame_stack):
            self.frames.append(flipped)

    def observe(self, raw_obs: np.ndarray) -> None:
        flipped = np.ascontiguousarray(np.flip(raw_obs, axis=1))
        self.frames.append(flipped)

    def act(self) -> int:
        """Stochastic action from policy (natural diversity, no epsilon needed)."""
        stacked = np.concatenate(list(self.frames), axis=2)
        with torch.no_grad():
            obs_t = torch.tensor(stacked[None], dtype=torch.float32, device=self.device)
            logits, _ = self.network(obs_t)
            dist = Categorical(logits=logits)
            return int(dist.sample().item())

    def load_weights(self, state_dict: dict) -> None:
        self.network.load_state_dict(state_dict)
        self.network.eval()


def train_ppo_selfplay(config: dict, device: torch.device | None = None) -> str:
    run_id = config.get("run_id", "ppo_selfplay_run")
    run_dir = Path("artifacts") / run_id
    (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    (run_dir / "eval").mkdir(exist_ok=True)
    (run_dir / "videos").mkdir(exist_ok=True)

    frame_stack = int(config["frame_stack"])
    n_steps = int(config["n_steps"])
    total_steps = int(config["total_steps"])

    # Environment setup with reward shaping
    env_config = MiniPongConfig(
        reward_shaping=bool(config.get("reward_shaping", False)),
        hit_reward=float(config.get("hit_reward", 0.1)),
        rally_bonus_per_step=float(config.get("rally_bonus_per_step", 0.02)),
    )
    raw_env = MiniPongEnv(config=env_config)
    env = wrap_env(raw_env, frame_stack=frame_stack)
    obs, _ = env.reset(seed=int(config["seed"]))

    # PPO agent
    ppo_config = PPOConfig(
        clip_epsilon=float(config.get("clip_epsilon", 0.1)),
        entropy_coef=float(config.get("entropy_coef", 0.02)),
        vf_coef=float(config.get("vf_coef", 0.5)),
        max_grad_norm=float(config.get("max_grad_norm", 0.5)),
        n_epochs=int(config.get("n_epochs", 4)),
        n_minibatches=int(config.get("n_minibatches", 4)),
        lr=float(config.get("lr", 2.5e-4)),
        lr_anneal_total_steps=total_steps if config.get("lr_anneal", False) else 0,
    )
    agent = PPOAgent(obs.shape, env.action_space.n, ppo_config, device=device)

    # Self-play opponent
    opponent = PPOSelfPlayOpponent(obs.shape, env.action_space.n, frame_stack, agent.device)
    opponent.load_weights(agent.network.state_dict())
    opponent.reset(raw_env._obs())

    # Checkpoint pool for Fictitious Self-Play
    checkpoint_pool: list[dict] = []
    pool_size = int(config.get("checkpoint_pool_size", 20))

    # Rollout buffer
    rollout = RolloutBuffer(n_steps, obs.shape, agent.device)

    logger = MetricsLogger(run_dir)

    opponent_update_period = int(config.get("opponent_update_period", 50000))
    eval_every = int(config.get("eval_every_steps", 100000))
    log_every = int(config.get("log_every_steps", 10000))
    start_time = time.monotonic()
    global_step = 0
    episode_return = 0.0
    episode_count = 0
    last_eval_metrics: dict[str, float] | None = None
    last_ckpt_path: str | None = None
    opponent_updates = 0

    n_updates = total_steps // n_steps

    for _update in range(1, n_updates + 1):
        # Collect n_steps of experience
        rollout.reset()
        for _ in range(n_steps):
            global_step += 1

            action, log_prob, value = agent.act(obs)

            # Opponent acts from mirror-flipped view
            opp_action = opponent.act()
            raw_env.set_opponent_action(opp_action)

            next_obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            opponent.observe(raw_env._obs())

            rollout.add(obs, action, reward, done, value, log_prob)
            episode_return += reward
            obs = next_obs

            if done:
                hits = info.get("hits", 0)
                misses = info.get("misses", 0)
                hit_ratio = hits / (hits + misses) if (hits + misses) > 0 else 0.0
                logger.log_metrics(
                    global_step,
                    {
                        "train/episode_return": episode_return,
                        "train/hits": hits,
                        "train/misses": misses,
                        "train/rally_length": info.get("rally_length", 0),
                        "train/hit_ratio": hit_ratio,
                    },
                )
                episode_return = 0.0
                episode_count += 1
                obs, _ = env.reset(seed=int(config["seed"]) + global_step)
                opponent.reset(raw_env._obs())

        # Compute GAE — track whether the last collected step was terminal
        last_done = bool(rollout.dones[rollout.pos - 1])
        last_value = 0.0 if last_done else agent.get_value(obs)
        rollout.compute_advantages(
            last_value,
            last_done,
            gamma=float(config.get("gamma", 0.99)),
            gae_lambda=float(config.get("gae_lambda", 0.95)),
        )

        # PPO update: n_epochs over minibatches
        epoch_losses: list[dict[str, float]] = []
        for _ in range(ppo_config.n_epochs):
            minibatches = rollout.get_minibatches(ppo_config.n_minibatches)
            losses = agent.update(minibatches, global_step)
            epoch_losses.append(losses)

        avg_losses = {
            k: float(np.mean([d[k] for d in epoch_losses])) for k in epoch_losses[0]
        }
        logger.log_metrics(
            global_step,
            {
                "train/pg_loss": avg_losses["pg_loss"],
                "train/vf_loss": avg_losses["vf_loss"],
                "train/entropy": avg_losses["entropy"],
                "train/clipfrac": avg_losses["clipfrac"],
            },
        )

        # Checkpoint pool management (Fictitious Self-Play 80/20)
        if global_step % opponent_update_period < n_steps:
            # Save current weights to pool
            current_weights = {
                k: v.cpu().clone() for k, v in agent.network.state_dict().items()
            }
            if len(checkpoint_pool) >= pool_size:
                checkpoint_pool.pop(0)
            checkpoint_pool.append(current_weights)
            opponent_updates += 1

            # 80% from pool, 20% current weights
            if checkpoint_pool and random.random() < 0.8:
                pool_weights = random.choice(checkpoint_pool)
                opponent.load_weights(pool_weights)
            else:
                opponent.load_weights(current_weights)

            print(
                f"  [Step {global_step}] Opponent updated "
                f"(#{opponent_updates}, pool size={len(checkpoint_pool)})"
            )
            logger.log_metrics(
                global_step,
                {
                    "selfplay/opponent_updates": opponent_updates,
                    "selfplay/pool_size": len(checkpoint_pool),
                },
            )

        # Evaluation
        eval_at_this_step = False
        if global_step % eval_every < n_steps:
            eval_at_this_step = True
            ckpt_path = run_dir / "checkpoints" / f"step_{global_step}.pt"
            torch.save(
                {"model": agent.network.state_dict(), "step": global_step}, ckpt_path
            )
            last_ckpt_path = str(ckpt_path)

            # Eval vs rule-based
            metrics = evaluate_ppo_policy(
                ckpt_path,
                int(config.get("eval_episodes", 10)),
                list(config.get("eval_seeds", [11, 22, 33, 44, 55])),
                frame_stack,
                int(config.get("max_episode_steps", 800)),
            )
            last_eval_metrics = {
                "mean_return": metrics["mean_return"],
                "mean_hits": metrics["mean_hits"],
                "mean_misses": metrics["mean_misses"],
                "mean_rally_length": metrics["mean_rally_length"],
                "hit_ratio": metrics["hit_ratio"],
                "episodes": float(metrics["episodes"]),
            }
            (run_dir / "eval" / f"metrics_step_{global_step}.json").write_text(
                json.dumps(metrics, indent=2), encoding="utf-8"
            )
            logger.log_metrics(
                global_step,
                {
                    "eval/mean_return": metrics["mean_return"],
                    "eval/mean_hits": metrics["mean_hits"],
                    "eval/mean_rally_length": metrics["mean_rally_length"],
                    "eval/hit_ratio": metrics["hit_ratio"],
                },
            )

            # Self-play eval
            sp_metrics = evaluate_ppo_selfplay(
                ckpt_path, n_rallies=100, frame_stack=frame_stack, max_steps=800
            )
            logger.log_metrics(
                global_step,
                {
                    "eval/selfplay_mean_rally": sp_metrics["mean_rally_length"],
                    "eval/selfplay_max_rally": sp_metrics["max_rally_length"],
                },
            )
            (run_dir / "eval" / f"selfplay_step_{global_step}.json").write_text(
                json.dumps(sp_metrics, indent=2), encoding="utf-8"
            )

        # Progress reporting
        if global_step % log_every < n_steps:
            elapsed = time.monotonic() - start_time
            speed = global_step / elapsed if elapsed > 0 else 0.0
            eta = (total_steps - global_step) / speed if speed > 0 else 0.0
            step_width = len(str(total_steps))
            print(
                f"[Step {global_step:>{step_width}}/{total_steps}]  "
                f"pg={avg_losses['pg_loss']:.4f}  "
                f"vf={avg_losses['vf_loss']:.4f}  "
                f"ent={avg_losses['entropy']:.4f}  "
                f"clip={avg_losses['clipfrac']:.3f}  "
                f"opp_updates={opponent_updates}  "
                f"elapsed={_format_elapsed(elapsed)}  "
                f"speed={speed:.1f} steps/s  "
                f"ETA={_format_eta(eta)}"
            )
            logger.log_metrics(
                global_step,
                {"progress/speed_steps_per_s": speed, "progress/elapsed_s": elapsed},
            )

            if eval_at_this_step and last_eval_metrics is not None:
                print(
                    f"  \u21b3 Eval @ step {global_step}: "
                    f"mean_return={last_eval_metrics['mean_return']:.2f}  "
                    f"mean_hits={last_eval_metrics['mean_hits']:.2f}  "
                    f"hit_ratio={last_eval_metrics['hit_ratio']:.3f}  "
                    f"rally={last_eval_metrics['mean_rally_length']:.1f}"
                )
            if eval_at_this_step and last_ckpt_path is not None:
                print(f"  \u21b3 Checkpoint saved: {last_ckpt_path}")

    logger.close()

    total_elapsed = time.monotonic() - start_time
    m = int(total_elapsed // 60)
    s = int(total_elapsed % 60)
    time_str = f"{m}m {s:02d}s" if m > 0 else f"{s}s"
    final_eval_str = "N/A"
    if last_eval_metrics is not None:
        final_eval_str = (
            f"mean_return={last_eval_metrics['mean_return']:.2f}  "
            f"mean_hits={last_eval_metrics['mean_hits']:.2f}  "
            f"rally={last_eval_metrics['mean_rally_length']:.1f}"
        )

    print()
    print("\u2550" * 56)
    print(f"PPO Self-play training complete: {run_id}")
    print(f"  Device: {agent.device} | Steps: {total_steps:,} | Time: {time_str}")
    print(f"  Opponent updates: {opponent_updates} (pool size: {len(checkpoint_pool)})")
    print(f"  Final eval (vs rule-based): {final_eval_str}")
    print("\u2550" * 56)

    return run_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/ppo_selfplay_1m.yaml")
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "mps", "cuda"],
        default="auto",
    )
    parser.add_argument("--total-steps", type=int, default=None)
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    if args.run_id:
        config["run_id"] = args.run_id
    if args.total_steps is not None:
        config["total_steps"] = args.total_steps

    device = resolve_device(args.device)
    print(f"PPO Self-play training on device: {device}")

    train_ppo_selfplay(config, device=device)


if __name__ == "__main__":
    main()
