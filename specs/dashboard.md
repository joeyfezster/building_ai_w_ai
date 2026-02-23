# Dashboard Spec

## Overview

Streamlit application that loads a training run folder and provides visual observability into the training process.

## Entry Point

`streamlit run src/dashboard/app.py`

Or via Makefile: `make dashboard`

## Data Source

Reads artifacts from `artifacts/<run_id>/`:
- `logs.jsonl` — training step/episode logs
- `eval/metrics_*.json` — evaluation results at checkpoints
- `videos/eval_step_<k>.mp4` — evaluation videos
- `tensorboard/` — TensorBoard event files (optional)

## Required Visualizations

1. **Training reward curve** — episode return over training steps
2. **Eval mean return** — mean return at each evaluation checkpoint
3. **Hit rate** — hits / (hits + misses) over time
4. **Loss curves** — DQN loss over training steps
5. **Epsilon over time** — exploration rate decay
6. **Checkpoint table** — list of saved checkpoints with embedded evaluation videos
7. **Strategy correlation** — correlate strategy proxy metrics (rally length, hit rate) with return

## Interaction

- Run selector: choose which `run_id` to display
- All charts should be interactive (Streamlit default)
- Videos embedded inline in checkpoint table

## Requirements

- Must render without a running training job (reads saved artifacts)
- Must handle missing artifacts gracefully (show placeholder, not crash)
- No GPU required
