"""Learning verification gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.train.evaluate import evaluate_policy


def verify_learning(run_id: str, min_return_gain: float, min_hits_gain: float) -> int:
    run_dir = Path("artifacts") / run_id
    eval_dir = run_dir / "eval"
    checkpoints = sorted((run_dir / "checkpoints").glob("step_*.pt"))
    if not checkpoints:
        print("No checkpoints found")
        return 2
    last = checkpoints[-1]
    baseline = evaluate_policy(None, episodes=4, seeds=[11, 22], frame_stack=4, max_steps=600)
    trained = evaluate_policy(last, episodes=4, seeds=[11, 22], frame_stack=4, max_steps=600)
    pass_return = trained["mean_return"] - baseline["mean_return"] >= min_return_gain
    pass_hits = trained["mean_hits"] - baseline["mean_hits"] >= min_hits_gain
    summary = {
        "baseline": baseline,
        "trained": trained,
        "pass_return": pass_return,
        "pass_hits": pass_hits,
        "passed": pass_return and pass_hits,
        "checkpoint": str(last),
    }
    (eval_dir / "learning_verification.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return 0 if summary["passed"] else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--min-return-gain", type=float, default=0.05)
    parser.add_argument("--min-hits-gain", type=float, default=1.0)
    args = parser.parse_args()
    raise SystemExit(verify_learning(args.run_id, args.min_return_gain, args.min_hits_gain))


if __name__ == "__main__":
    main()
