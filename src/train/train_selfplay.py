"""Train DQN with self-play: opponent is a Q-network updated periodically."""

from __future__ import annotations

import argparse
import collections
import json
import time
from pathlib import Path

import numpy as np
import torch
import yaml

from src.agents.dqn_agent import DQNAgent, DQNConfig
from src.envs.minipong import MiniPongEnv
from src.envs.wrappers import wrap_env
from src.obs.logging import MetricsLogger
from src.rl.networks import create_q_network
from src.rl.replay import ReplayBuffer, Transition
from src.rl.schedules import linear_schedule
from src.train.evaluate import evaluate_policy
from src.train.record_video import record_video
from src.train.train_dqn import _format_elapsed, _format_eta, resolve_device


class SelfPlayOpponent:
    """Q-network opponent with its own frame stack and mirror-flipped view."""

    def __init__(
        self,
        obs_shape: tuple[int, ...],
        num_actions: int,
        frame_stack: int,
        device: torch.device,
    ) -> None:
        self.device = device
        self.frame_stack = frame_stack
        self.network = create_q_network(obs_shape, num_actions).to(device)
        self.network.eval()
        self.frames: collections.deque[np.ndarray] = collections.deque(maxlen=frame_stack)

    def reset(self, raw_obs: np.ndarray) -> None:
        """Reset frame stack with mirror-flipped observation."""
        flipped = np.ascontiguousarray(np.flip(raw_obs, axis=1))
        self.frames.clear()
        for _ in range(self.frame_stack):
            self.frames.append(flipped)

    def observe(self, raw_obs: np.ndarray) -> None:
        """Update frame stack with new mirror-flipped observation."""
        flipped = np.ascontiguousarray(np.flip(raw_obs, axis=1))
        self.frames.append(flipped)

    def get_obs(self) -> np.ndarray:
        """Return current frame-stacked observation (mirrored perspective)."""
        return np.concatenate(list(self.frames), axis=2)

    def act(self) -> int:
        """Pick greedy action from current frame stack."""
        stacked = self.get_obs()
        with torch.no_grad():
            obs_t = torch.tensor(stacked[None], dtype=torch.float32, device=self.device)
            q = self.network(obs_t)
            return int(torch.argmax(q, dim=1).item())

    def load_weights(self, state_dict: dict) -> None:
        """Update opponent network weights."""
        self.network.load_state_dict(state_dict)
        self.network.eval()


def train_selfplay(config: dict, device: torch.device | None = None) -> str:
    run_id = config.get("run_id", "selfplay_run")
    run_dir = Path("artifacts") / run_id
    (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    (run_dir / "eval").mkdir(exist_ok=True)
    (run_dir / "videos").mkdir(exist_ok=True)

    frame_stack = int(config["frame_stack"])
    raw_env = MiniPongEnv()
    env = wrap_env(raw_env, frame_stack=frame_stack)
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
            flip_augment=bool(config.get("flip_augment", False)),
        ),
        device=device,
    )

    opponent = SelfPlayOpponent(
        obs.shape,
        env.action_space.n,
        frame_stack,
        agent.device,
    )

    # Load initial checkpoint if provided
    initial_ckpt = config.get("initial_checkpoint", "")
    if initial_ckpt:
        ckpt_data = torch.load(initial_ckpt, map_location=agent.device, weights_only=True)
        state = (
            ckpt_data["model"]
            if isinstance(ckpt_data, dict) and "model" in ckpt_data
            else ckpt_data
        )
        agent.online.load_state_dict(state)
        agent.target.load_state_dict(state)
        opponent.load_weights(state)
        print(f"Loaded initial checkpoint: {initial_ckpt}")

    # Initialize opponent frame stack
    opponent.reset(raw_env._obs())

    logger = MetricsLogger(run_dir)

    episode_return = 0.0
    total_steps = int(config["total_steps"])
    log_every = int(config.get("log_every_steps", 1000))
    opponent_update_period = int(config.get("opponent_update_period", 10000))
    start_time = time.monotonic()
    interval_loss_sum = 0.0
    interval_loss_count = 0
    last_eval_metrics: dict[str, float] | None = None
    last_ckpt_path: str | None = None
    opponent_updates = 0
    best_adversary_score = -float("inf")
    best_adversary_step = 0
    quick_eval_episodes = int(config.get("quick_eval_episodes", 5))
    quick_eval_seeds = [42]

    for step in range(1, total_steps + 1):
        eps = linear_schedule(
            step,
            float(config["epsilon_start"]),
            float(config["epsilon_end"]),
            int(config["epsilon_decay_steps"]),
        )

        # Agent picks action
        action = agent.act(obs, epsilon=eps)

        # Opponent picks action from mirror-flipped view
        opp_action = opponent.act()
        raw_env.set_opponent_action(opp_action)

        # Step environment (both paddles move)
        next_obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated

        # Update opponent's frame stack with post-step observation
        opponent.observe(raw_env._obs())

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
            opponent.reset(raw_env._obs())

        if loss is not None and step % 10 == 0:
            logger.log_metrics(step, {"train/loss": loss, "train/epsilon": eps})

        # Evaluate and maybe update opponent (best-adversary selection)
        if step % opponent_update_period == 0:
            # Quick eval against rule-based opponent
            ckpt_tmp = run_dir / "checkpoints" / f"candidate_{step}.pt"
            torch.save({"model": agent.online.state_dict(), "step": step}, ckpt_tmp)
            quick_metrics = evaluate_policy(
                ckpt_tmp,
                quick_eval_episodes,
                quick_eval_seeds,
                int(config["frame_stack"]),
                int(config["max_episode_steps"]),
                flip_augment=bool(config.get("flip_augment", False)),
            )
            score = quick_metrics["hit_ratio"]
            ckpt_tmp.unlink()  # clean up temporary checkpoint

            if score > best_adversary_score:
                best_adversary_score = score
                best_adversary_step = step
                opponent.load_weights(agent.online.state_dict())
                opponent_updates += 1
                print(
                    f"  [Step {step}] New best adversary "
                    f"(hit_ratio={score:.3f}), "
                    f"opponent updated (#{opponent_updates})"
                )
            logger.log_metrics(
                step,
                {
                    "selfplay/candidate_hit_ratio": score,
                    "selfplay/best_adversary_score": best_adversary_score,
                    "selfplay/best_adversary_step": best_adversary_step,
                    "selfplay/opponent_updates": opponent_updates,
                },
            )

        # Evaluation (against rule-based opponent for consistent baseline)
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
                flip_augment=bool(config.get("flip_augment", False)),
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
            if not config.get("skip_eval_video", False):
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
                f"opp_updates={opponent_updates}  "
                f"elapsed={_format_elapsed(elapsed)}  "
                f"speed={speed:.1f} steps/s  "
                f"ETA={_format_eta(eta)}"
            )
            logger.log_metrics(
                step,
                {"progress/speed_steps_per_s": speed, "progress/elapsed_s": elapsed},
            )
            interval_loss_sum = 0.0
            interval_loss_count = 0

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

    # Final progress sample
    if total_steps % log_every != 0:
        elapsed = time.monotonic() - start_time
        speed = total_steps / elapsed if elapsed > 0 else 0.0
        logger.log_metrics(
            total_steps,
            {"progress/speed_steps_per_s": speed, "progress/elapsed_s": elapsed},
        )

    logger.close()

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
    print(f"Self-play training complete: {run_id}")
    print(f"  Device: {device_name} | Steps: {total_steps:,} | Time: {time_str}")
    print(f"  Opponent updates: {opponent_updates} (every {opponent_update_period:,} steps)")
    print(f"  Final eval (vs rule-based): {final_eval_str}")
    print()
    if last_ckpt_path:
        print("  Play against the trained agent:")
        print(f"    python -m src.play.play_minipong --checkpoint {last_ckpt_path}")
        print()
        print("  Agent vs agent:")
        print(f"    python -m src.play.play_minipong --run-id {run_id} --left-agent --right-agent")
    print("\u2550" * 56)

    return run_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/dqn_selfplay_1m.yaml")
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "mps", "cuda"],
        default="auto",
    )
    parser.add_argument("--total-steps", type=int, default=None)
    parser.add_argument(
        "--checkpoint", default="", help="Initial checkpoint for agent+opponent",
    )
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    if args.run_id:
        config["run_id"] = args.run_id
    if args.total_steps is not None:
        config["total_steps"] = args.total_steps
    if args.checkpoint:
        config["initial_checkpoint"] = args.checkpoint

    device = resolve_device(args.device)
    print(f"Self-play training on device: {device}")

    train_selfplay(config, device=device)


if __name__ == "__main__":
    main()
