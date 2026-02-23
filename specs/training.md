# Training Pipeline Spec

## Overview

The training pipeline orchestrates DQN training on MiniPong, producing all artifacts needed for learning proof and observability.

## Entry Point

`python -m src.train.train_dqn --config configs/dqn_minipong.yaml --run-id <run_id>`

## Config

YAML config file specifying all hyperparameters. See `configs/dqn_minipong.yaml` for defaults:
- `run_id`, `seed`, `frame_stack`
- `total_steps`, `max_episode_steps`
- Replay: `replay_capacity`, `replay_warmup_steps`, `batch_size`
- RL: `gamma`, `lr`, `epsilon_start`, `epsilon_end`, `epsilon_decay_steps`, `target_update_period`
- Eval: `eval_every_steps`, `eval_episodes`, `eval_seeds`

## Training Loop

1. Initialize environment, agent, replay buffer
2. Collect transitions with epsilon-greedy policy
3. After warmup, sample batches and update Q-network
4. Periodically evaluate current policy (every `eval_every_steps`)
5. Periodically save checkpoints
6. Log metrics to TensorBoard and JSONL

## Artifact Output

All artifacts saved under `artifacts/<run_id>/`:

| Artifact | Path | Format |
|----------|------|--------|
| TensorBoard logs | `artifacts/<run_id>/tensorboard/` | TensorBoard event files |
| Training log | `artifacts/<run_id>/logs.jsonl` | JSON Lines (one entry per step/episode) |
| Checkpoints | `artifacts/<run_id>/checkpoints/*.pt` | PyTorch state dicts |
| Eval metrics | `artifacts/<run_id>/eval/metrics_*.json` | JSON per evaluation |
| Eval videos | `artifacts/<run_id>/videos/eval_step_<k>.mp4` | MP4 video |

## Evaluation

- Uses fixed seeds and fixed number of episodes
- Records: mean return, hit rate, rally length, episode count
- Saves evaluation videos at configurable intervals

## Reproducibility

- Training is seeded via config
- Evaluation uses explicit seed list
- All randomness flows through the configured RNG
