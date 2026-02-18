from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--min-return-gain", type=float, default=0.2)
    p.add_argument("--min-hit-gain", type=float, default=0.5)
    args = p.parse_args()

    eval_dir = Path("artifacts") / args.run_id / "eval"
    baseline = json.loads((eval_dir / "metrics_random.json").read_text(encoding="utf-8"))
    latest = sorted(eval_dir.glob("metrics_step_*.json"))[-1]
    improved = json.loads(latest.read_text(encoding="utf-8"))

    ok_return = improved["mean_return"] >= baseline["mean_return"] + args.min_return_gain
    ok_hits = improved["mean_hits"] >= baseline["mean_hits"] + args.min_hit_gain

    report = {
        "baseline": baseline,
        "improved": improved,
        "checks": {"return_gain": ok_return, "hit_gain": ok_hits, "seeds": 2},
    }
    out = eval_dir / "learning_verification.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if ok_return and ok_hits:
        print("Learning verification passed")
        return
    print("Learning verification failed")
    sys.exit(1)


if __name__ == "__main__":
    main()
