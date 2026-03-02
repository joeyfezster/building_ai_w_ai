"""Train DQN on MiniPong."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
import yaml

from src.agents.dqn_agent import DQNAgent, DQNConfig
from src.envs.minipong import MiniPongEnv
from src.envs.wrappers import wrap_env
from src.obs.logging import MetricsLogger
from src.rl.replay import ReplayBuffer, Transition
from src.rl.schedules import linear_schedule
from src.train.evaluate import evaluate_policy
from src.train.record_video import record_video


def resolve_device(choice: str) -> torch.device:
    """Resolve device from CLI choice, validating availability."""
    if choice == "auto":
        if torch.backends.mps.is_available():
            return torch.device("mps")
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")
    if choice == "mps":
        if not torch.backends.mps.is_available():
            print("Error: --device mps requested but MPS is not available.", file=sys.stderr)
            sys.exit(1)
        return torch.device("mps")
    if choice == "cuda":
        if not torch.cuda.is_available():
            print("Error: --device cuda requested but CUDA is not available.", file=sys.stderr)
            sys.exit(1)
        return torch.device("cuda")
    return torch.device("cpu")


def _format_elapsed(seconds: float) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_eta(seconds: float) -> str:
    """Format ETA seconds as human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m < 60:
        return f"{m}:{s:02d}"
    h = m // 60
    m = m % 60
    return f"{h}:{m:02d}:{s:02d}"


def train(config: dict, device: torch.device | None = None) -> str:
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
        device=device,
    )
    logger = MetricsLogger(run_dir)

    episode_return = 0.0
    total_steps = int(config["total_steps"])
    log_every = int(config.get("log_every_steps", 1000))
    start_time = time.monotonic()
    interval_loss_sum = 0.0
    interval_loss_count = 0
    last_eval_metrics: dict[str, float] | None = None
    last_ckpt_path: str | None = None

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

        if loss is not None:
            interval_loss_sum += loss
            interval_loss_count += 1

        if done:
            hits = info.get("hits", 0)
            misses = info.get("misses", 0)
            hit_ratio = hits / (hits + misses) if (hits + misses) > 0 else 0.0
            logger.log_metrics(
                step,
                {
                    "train/episode_return": episode_return,
                    "train/hits": hits,
                    "train/misses": misses,
                    "train/rally_length": info.get("rally_length", 0),
                    "train/hit_ratio": hit_ratio,
                    "train/epsilon": eps,
                },
            )
            episode_return = 0.0
            obs, _ = env.reset(seed=int(config["seed"]) + step)

        if loss is not None and step % 10 == 0:
            logger.log_metrics(step, {"train/loss": loss, "train/epsilon": eps})

        eval_at_this_step = False
        if step % int(config["eval_every_steps"]) == 0:
            eval_at_this_step = True
            ckpt_path = run_dir / "checkpoints" / f"step_{step}.pt"
            torch.save({"model": agent.online.state_dict(), "step": step}, ckpt_path)
            last_ckpt_path = str(ckpt_path)
            metrics = evaluate_policy(
                ckpt_path,
                int(config["eval_episodes"]),
                list(config["eval_seeds"]),
                int(config["frame_stack"]),
                int(config["max_episode_steps"]),
            )
            last_eval_metrics = {
                "mean_return": metrics["mean_return"],
                "mean_hits": metrics["mean_hits"],
                "mean_misses": metrics["mean_misses"],
                "mean_rally_length": metrics["mean_rally_length"],
                "hit_ratio": metrics["hit_ratio"],
                "episodes": metrics["episodes"],
            }
            (run_dir / "eval" / f"metrics_step_{step}.json").write_text(
                json.dumps(metrics, indent=2), encoding="utf-8"
            )
            logger.log_metrics(
                step,
                {
                    "eval/mean_return": metrics["mean_return"],
                    "eval/mean_hits": metrics["mean_hits"],
                    "eval/mean_misses": metrics["mean_misses"],
                    "eval/mean_rally_length": metrics["mean_rally_length"],
                    "eval/hit_ratio": metrics["hit_ratio"],
                },
            )
            eval_seeds = config.get("eval_seeds", [])
            if eval_seeds:
                video_path = run_dir / "videos" / f"eval_step_{step}.mp4"
                record_video(
                    ckpt_path,
                    video_path,
                    seed=int(eval_seeds[0]),
                    frame_stack=int(config["frame_stack"]),
                )

        # Progress reporting
        if step % log_every == 0:
            elapsed = time.monotonic() - start_time
            speed = step / elapsed if elapsed > 0 else 0.0
            eta = (total_steps - step) / speed if speed > 0 else 0.0
            avg_loss = (
                interval_loss_sum / interval_loss_count if interval_loss_count > 0 else 0.0
            )
            loss_str = f"loss={avg_loss:.4f}" if interval_loss_count > 0 else "loss=N/A"
            step_width = len(str(total_steps))
            print(
                f"[Step {step:>{step_width}}/{total_steps}]  "
                f"eps={eps:.3f}  {loss_str}  "
                f"elapsed={_format_elapsed(elapsed)}  "
                f"speed={speed:.1f} steps/s  "
                f"ETA={_format_eta(eta)}"
            )
            logger.log_metrics(
                step,
                {"progress/speed_steps_per_s": speed, "progress/elapsed_s": elapsed},
            )
            # Reset interval accumulators
            interval_loss_sum = 0.0
            interval_loss_count = 0

            # Print eval and checkpoint sub-lines if they happened at this step
            if eval_at_this_step and last_eval_metrics is not None:
                print(
                    f"  \u21b3 Eval @ step {step}: "
                    f"mean_return={last_eval_metrics['mean_return']:.2f}  "
                    f"mean_hits={last_eval_metrics['mean_hits']:.2f}  "
                    f"hit_ratio={last_eval_metrics['hit_ratio']:.3f}  "
                    f"rally={last_eval_metrics['mean_rally_length']:.1f} "
                    f"({last_eval_metrics['episodes']} episodes)"
                )
            if eval_at_this_step and last_ckpt_path is not None:
                print(f"  \u21b3 Checkpoint saved: {last_ckpt_path}")

    # Final progress sample (ensures short runs have at least one entry)
    if total_steps % log_every != 0:
        elapsed = time.monotonic() - start_time
        speed = total_steps / elapsed if elapsed > 0 else 0.0
        logger.log_metrics(
            total_steps,
            {"progress/speed_steps_per_s": speed, "progress/elapsed_s": elapsed},
        )

    logger.close()

    # Training completion summary
    total_elapsed = time.monotonic() - start_time
    device_name = str(agent.device)
    final_eval_str = "N/A"
    if last_eval_metrics is not None:
        final_eval_str = (
            f"mean_return={last_eval_metrics['mean_return']:.2f}  "
            f"mean_hits={last_eval_metrics['mean_hits']:.2f}"
        )

    m = int(total_elapsed // 60)
    s = int(total_elapsed % 60)
    time_str = f"{m}m {s:02d}s" if m > 0 else f"{s}s"

    print()
    print("\u2550" * 56)
    print(f"Training complete: {run_id}")
    print(f"  Device: {device_name} | Steps: {total_steps:,} | Time: {time_str}")
    print(f"  Final eval: {final_eval_str}")
    print()
    if last_ckpt_path:
        print("  Play against the trained agent:")
        print(f"    python -m src.play.play_minipong --checkpoint {last_ckpt_path}")
        print()
        print("  Or use the shorthand:")
        print(f"    python -m src.play.play_minipong --run-id {run_id}")
        print()
        print("  Agent vs agent:")
        print(f"    python -m src.play.play_minipong --run-id {run_id} --left-agent --right-agent")
    print("\u2550" * 56)

    return run_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/dqn_minipong.yaml")
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
    print(f"Training on device: {device}")

    train(config, device=device)


if __name__ == "__main__":
    main()
