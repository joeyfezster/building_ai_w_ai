from pathlib import Path

from src.train.train_dqn import train


def test_training_smoke_cpu() -> None:
    cfg = Path("artifacts/test_smoke.yaml")
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        """
run_id: test_smoke
seed: 1
frame_stack: 2
total_steps: 20
replay_capacity: 100
warmup_steps: 5
train_freq: 2
eval_every: 20
checkpoint_every: 10
epsilon_start: 1.0
epsilon_end: 0.1
epsilon_decay_steps: 20
eval_episodes: 1
eval_seeds: [0, 1]
batch_size: 8
gamma: 0.99
lr: 0.001
""".strip(),
        encoding="utf-8",
    )
    run_id = train(cfg)
    run_dir = Path("artifacts") / run_id
    assert (run_dir / "logs.jsonl").exists()
    assert list((run_dir / "checkpoints").glob("*.pt"))
