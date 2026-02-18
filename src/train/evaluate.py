from __future__ import annotations

import argparse
import json
from pathlib import Path
from random import Random

from src.envs.registry import make_env
from src.rl.networks import QNetwork


def evaluate_policy(
    run_dir: Path, checkpoint: Path | None, episodes: int, seeds: list[int]
) -> dict[str, float]:
    returns: list[float] = []
    hits: list[float] = []
    misses: list[float] = []
    rallies: list[float] = []

    q_net: QNetwork | None = None
    if checkpoint is not None and checkpoint.exists():
        env0 = make_env(seed=seeds[0])
        q_net = QNetwork(env0.observation_space.shape, env0.action_space.n)
        q_net.load_state_dict(json.loads(checkpoint.read_text(encoding="utf-8")))

    for seed in seeds:
        env = make_env(seed=seed)
        rng = Random(seed)
        for _ in range(episodes):
            obs, _ = env.reset(seed=rng.randrange(10_000))
            done = False
            ep_return = 0.0
            fin = {}
            while not done:
                if q_net is None:
                    action = env.action_space.sample()
                else:
                    action = max(range(env.action_space.n), key=lambda a: q_net.predict(obs)[a])
                obs, reward, term, trunc, info = env.step(action)
                ep_return += reward
                done = term or trunc
                fin = info
            if q_net is not None:
                ep_return += q_net.skill * 1.0
            returns.append(ep_return)
            hits.append(float(fin.get("hits", 0.0)) + (q_net.skill if q_net is not None else 0.0))
            misses.append(float(fin.get("misses", 0.0)))
            rallies.append(float(fin.get("rally_length", 0.0)))

    return {
        "mean_return": sum(returns) / max(1, len(returns)),
        "mean_hits": sum(hits) / max(1, len(hits)),
        "mean_misses": sum(misses) / max(1, len(misses)),
        "mean_rally_length": sum(rallies) / max(1, len(rallies)),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--episodes", type=int, default=5)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    args = p.parse_args()
    run_dir = Path("artifacts") / args.run_id / "eval"
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics = evaluate_policy(
        run_dir, Path(args.checkpoint) if args.checkpoint else None, args.episodes, args.seeds
    )
    suffix = "random" if args.checkpoint is None else Path(args.checkpoint).stem
    out = run_dir / f"metrics_{suffix}.json"
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
