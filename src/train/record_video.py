from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
import torch

from src.envs.registry import make_env
from src.rl.networks import QNetwork


def record(
    run_id: str, checkpoint: Path | None, out_path: Path, steps: int = 400, seed: int = 0
) -> None:
    env = make_env(seed=seed)
    q_net: QNetwork | None = None
    if checkpoint is not None:
        q_net = QNetwork(env.observation_space.shape, env.action_space.n)
        q_net.load_state_dict(torch.load(checkpoint, map_location="cpu"))
        q_net.eval()

    obs, _ = env.reset(seed=seed)
    frames = []
    for _ in range(steps):
        if q_net is None:
            action = env.action_space.sample()
        else:
            with torch.no_grad():
                q = q_net(torch.tensor(obs).unsqueeze(0))
            action = int(torch.argmax(q, dim=1).item())
        obs, _, term, trunc, _ = env.step(action)
        frames.append(env.unwrapped.render())
        if term or trunc:
            obs, _ = env.reset(seed=seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(out_path, frames, fps=30)
    env.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--label", required=True)
    args = p.parse_args()

    out = Path("artifacts") / args.run_id / "videos" / f"{args.label}.mp4"
    record(args.run_id, Path(args.checkpoint) if args.checkpoint else None, out)
    print(out)


if __name__ == "__main__":
    main()
