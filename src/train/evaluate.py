from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

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
        q_net.load_state_dict(torch.load(checkpoint, map_location="cpu"))
        q_net.eval()
        env0.close()

    for seed in seeds:
        env = make_env(seed=seed)
        rng = np.random.default_rng(seed)
        for _ in range(episodes):
            obs, _ = env.reset(seed=int(rng.integers(0, 10_000)))
            done = False
            ep_return = 0.0
            final_info: dict[str, float] = {}
            while not done:
                if q_net is None:
                    action = int(rng.integers(0, env.action_space.n))
                else:
                    with torch.no_grad():
                        q = q_net(torch.tensor(obs).unsqueeze(0))
                    action = int(torch.argmax(q, dim=1).item())
                obs, reward, terminated, truncated, info = env.step(action)
                ep_return += reward
                done = terminated or truncated
                final_info = info
            returns.append(ep_return)
            hits.append(float(final_info["hits"]))
            misses.append(float(final_info["misses"]))
            rallies.append(float(final_info["rally_length"]))
        env.close()

    run_dir.mkdir(parents=True, exist_ok=True)
    return {
        "mean_return": float(np.mean(returns)),
        "mean_hits": float(np.mean(hits)),
        "mean_misses": float(np.mean(misses)),
        "mean_rally_length": float(np.mean(rallies)),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--episodes", type=int, default=5)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    args = p.parse_args()

    run_dir = Path("artifacts") / args.run_id / "eval"
    metrics = evaluate_policy(
        run_dir,
        Path(args.checkpoint) if args.checkpoint else None,
        args.episodes,
        args.seeds,
    )
    suffix = "random" if args.checkpoint is None else Path(args.checkpoint).stem
    out = run_dir / f"metrics_{suffix}.json"
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
