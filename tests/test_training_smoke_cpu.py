from __future__ import annotations

from pathlib import Path

from src.train.train_dqn import train


def test_training_smoke_cpu() -> None:
    run_id = "pytest_smoke"
    config = {
        "run_id": run_id,
        "seed": 1,
        "frame_stack": 2,
        "total_steps": 100,
        "max_episode_steps": 200,
        "replay_capacity": 1000,
        "replay_warmup_steps": 10,
        "batch_size": 8,
        "gamma": 0.99,
        "lr": 0.001,
        "epsilon_start": 1.0,
        "epsilon_end": 0.1,
        "epsilon_decay_steps": 80,
        "target_update_period": 20,
        "eval_every_steps": 50,
        "eval_episodes": 2,
        "eval_seeds": [3, 4],
    }
    train(config)
    assert (Path("artifacts") / run_id / "checkpoints").exists()
