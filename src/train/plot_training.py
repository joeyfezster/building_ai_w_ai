"""Generate training charts from JSONL logs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def _load_eval_metrics(run_dir: Path) -> list[dict]:
    """Load eval metrics from JSON files in run_dir/eval/."""
    eval_dir = run_dir / "eval"
    if not eval_dir.is_dir():
        return []
    metrics = []
    for f in sorted(
        eval_dir.glob("metrics_step_*.json"),
        key=lambda p: int(p.stem.replace("metrics_step_", "")),
    ):
        step_str = f.stem.replace("metrics_step_", "")
        data = json.loads(f.read_text(encoding="utf-8"))
        data["step"] = int(step_str)
        metrics.append(data)
    return metrics


def _load_progress_metrics(run_dir: Path) -> list[dict]:
    """Load progress/speed data from JSONL logs."""
    log_path = run_dir / "logs.jsonl"
    if not log_path.exists():
        return []
    entries = []
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            if "progress/speed_steps_per_s" in data:
                entries.append(data)
    return entries


def _extract_device_from_run_id(run_id: str) -> str:
    """Extract device label from run ID naming convention."""
    lower = run_id.lower()
    if "mps" in lower:
        return "MPS"
    if "cpu" in lower:
        return "CPU"
    if "cuda" in lower:
        return "CUDA"
    return "auto"


def plot_hit_ratio_vs_steps(
    runs: dict[str, Path], output_dir: Path
) -> None:
    """Chart 1: Hit ratio vs training steps (log scale x)."""
    fig, ax = plt.subplots(figsize=(10, 6))
    for run_id, run_dir in runs.items():
        evals = _load_eval_metrics(run_dir)
        if not evals:
            continue
        steps = [e["step"] for e in evals]
        ratios = [e.get("hit_ratio", 0.0) for e in evals]
        device = _extract_device_from_run_id(run_id)
        ax.plot(steps, ratios, "o-", label=f"{run_id} ({device})", markersize=5)
    ax.set_xscale("log")
    ax.set_xlabel("Training Steps")
    ax.set_ylabel("Hit Ratio (hits / (hits + misses))")
    ax.set_title("Agent Hit Ratio vs Training Steps")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(output_dir / "hit_ratio_vs_steps.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {output_dir / 'hit_ratio_vs_steps.png'}")


def plot_speed_vs_steps(
    runs: dict[str, Path], output_dir: Path
) -> None:
    """Chart 2: Training speed (steps/s) vs steps."""
    fig, ax = plt.subplots(figsize=(10, 6))
    for run_id, run_dir in runs.items():
        progress = _load_progress_metrics(run_dir)
        if not progress:
            continue
        # Skip first entry (warmup speed is misleadingly high)
        progress = [p for p in progress if p["step"] > progress[0]["step"]]
        if not progress:
            continue
        steps = [p["step"] for p in progress]
        speeds = [p["progress/speed_steps_per_s"] for p in progress]
        device = _extract_device_from_run_id(run_id)
        ax.plot(steps, speeds, "o-", label=f"{run_id} ({device})", markersize=3)
    ax.set_xlabel("Training Steps")
    ax.set_ylabel("Speed (steps/s)")
    ax.set_title("Training Speed vs Steps")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "speed_vs_steps.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {output_dir / 'speed_vs_steps.png'}")


def plot_hit_ratio_vs_wallclock(
    runs: dict[str, Path], output_dir: Path
) -> None:
    """Chart 3: Hit ratio vs wall-clock time."""
    fig, ax = plt.subplots(figsize=(10, 6))
    for run_id, run_dir in runs.items():
        evals = _load_eval_metrics(run_dir)
        progress = _load_progress_metrics(run_dir)
        if not evals or not progress:
            continue
        # Build step->elapsed_s mapping from progress logs
        step_to_elapsed = {
            p["step"]: p.get("elapsed_s", p.get("progress/elapsed_s", 0))
            for p in progress
        }
        steps = [e["step"] for e in evals]
        ratios = [e.get("hit_ratio", 0.0) for e in evals]
        # Find closest elapsed_s for each eval step
        elapsed = []
        for s in steps:
            if s in step_to_elapsed:
                elapsed.append(step_to_elapsed[s] / 60.0)  # convert to minutes
            else:
                # Interpolate from nearest progress entry
                closest = min(step_to_elapsed.keys(), key=lambda k: abs(k - s), default=0)
                elapsed.append(step_to_elapsed.get(closest, 0) / 60.0)
        device = _extract_device_from_run_id(run_id)
        ax.plot(elapsed, ratios, "o-", label=f"{run_id} ({device})", markersize=5)
    ax.set_xlabel("Wall-Clock Time (minutes)")
    ax.set_ylabel("Hit Ratio (hits / (hits + misses))")
    ax.set_title("Agent Hit Ratio vs Wall-Clock Time")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(output_dir / "hit_ratio_vs_wallclock.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {output_dir / 'hit_ratio_vs_wallclock.png'}")


def plot_rally_length_vs_steps(
    runs: dict[str, Path], output_dir: Path
) -> None:
    """Chart 4: Mean rally length vs training steps."""
    fig, ax = plt.subplots(figsize=(10, 6))
    for run_id, run_dir in runs.items():
        evals = _load_eval_metrics(run_dir)
        if not evals:
            continue
        steps = [e["step"] for e in evals]
        rallies = [e.get("mean_rally_length", 0.0) for e in evals]
        device = _extract_device_from_run_id(run_id)
        ax.plot(steps, rallies, "o-", label=f"{run_id} ({device})", markersize=5)
    ax.set_xscale("log")
    ax.set_xlabel("Training Steps")
    ax.set_ylabel("Mean Rally Length (paddle contacts)")
    ax.set_title("Rally Length vs Training Steps")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "rally_length_vs_steps.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {output_dir / 'rally_length_vs_steps.png'}")


def _discover_runs(artifacts_dir: Path) -> dict[str, Path]:
    """Auto-discover runs that have eval directories."""
    runs: dict[str, Path] = {}
    if not artifacts_dir.is_dir():
        return runs
    for d in sorted(artifacts_dir.iterdir()):
        if d.is_dir() and (d / "eval").is_dir():
            runs[d.name] = d
    return runs


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate training charts")
    parser.add_argument(
        "--runs",
        nargs="*",
        default=[],
        help="Run IDs to include (default: auto-discover from artifacts/)",
    )
    parser.add_argument(
        "--output",
        default="artifacts/charts/",
        help="Output directory for PNGs",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/",
        help="Base artifacts directory",
    )
    args = parser.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.runs:
        runs = {r: artifacts_dir / r for r in args.runs}
    else:
        runs = _discover_runs(artifacts_dir)

    if not runs:
        print("No runs found. Specify --runs or check artifacts/ directory.")
        return

    print(f"Generating charts for {len(runs)} runs: {', '.join(runs.keys())}")
    plot_hit_ratio_vs_steps(runs, output_dir)
    plot_speed_vs_steps(runs, output_dir)
    plot_hit_ratio_vs_wallclock(runs, output_dir)
    plot_rally_length_vs_steps(runs, output_dir)
    print(f"All charts saved to {output_dir}/")


if __name__ == "__main__":
    main()
