from pathlib import Path

from src.train.train_dqn import train


def test_training_smoke_cpu() -> None:
    run_id = train(Path("configs/dqn_minipong.yaml"))
    run_dir = Path("artifacts") / run_id
    assert (run_dir / "logs.jsonl").exists()
    assert list((run_dir / "checkpoints").glob("*.pt"))
