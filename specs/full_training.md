# Full Training Spec

## Overview

The existing training pipeline (`src/train/train_dqn.py`) works but only ships a smoke-test config (2,000 steps). At 2,000 steps the DQN agent never exits the exploration phase and performs at or below random. This spec adds the wiring for production-grade training that produces agents capable of sustained rally play.

**Target hardware:** Apple M4-Pro (12 CPU cores, 16-core GPU, 24 GB RAM). Training must also work on any CPU-only machine.

## 1. Full Training Config

Create `configs/dqn_minipong_full.yaml`:

```yaml
run_id: full_train
seed: 42
frame_stack: 4
total_steps: 100000
max_episode_steps: 800
replay_capacity: 50000
replay_warmup_steps: 1000
batch_size: 32
gamma: 0.99
lr: 0.001
epsilon_start: 1.0
epsilon_end: 0.05
epsilon_decay_steps: 80000
target_update_period: 500
eval_every_steps: 10000
eval_episodes: 10
eval_seeds: [11, 22, 33, 44, 55]
```

**Rationale for changes vs smoke config:**

| Parameter | Smoke (2k) | Full (100k) | Why |
|-----------|-----------|-------------|-----|
| `total_steps` | 2,000 | 100,000 | DQN needs 50k+ steps to learn paddle tracking from pixels |
| `epsilon_decay_steps` | 1,500 | 80,000 | Gradual exploration decay — agent explores for most of training |
| `replay_capacity` | 20,000 | 50,000 | More experience diversity for stable learning |
| `replay_warmup_steps` | 200 | 1,000 | Better initial replay buffer before learning starts |
| `target_update_period` | 100 | 500 | More stable target network updates |
| `eval_every_steps` | 500 | 10,000 | Don't waste time on constant eval during long runs |
| `eval_episodes` | 4 | 10 | More reliable evaluation statistics |
| `eval_seeds` | [11, 22] | [11, 22, 33, 44, 55] | 5 seeds for lower-variance eval |

The existing `configs/dqn_minipong.yaml` must NOT be modified — it serves scenario smoke tests.

## 2. Device Selection

Add a `--device` CLI flag to `python -m src.train.train_dqn`:

| Value | Behavior |
|-------|----------|
| `auto` | Auto-detect best available: MPS > CUDA > CPU. **This is the default.** |
| `cpu` | Force CPU training |
| `mps` | Force Apple GPU (Metal Performance Shaders) training |
| `cuda` | Force NVIDIA GPU training |

### Requirements

- The training script must print the selected device at startup: `Training on device: mps`
- The Q-network (online and target), optimizer, and all training tensors (observations, actions, rewards, next_obs, dones) must live on the selected device.
- Replay buffer stores transitions as NumPy arrays on CPU. Tensors are moved to the training device only when sampled for a batch — do not store GPU tensors in the replay buffer.
- `evaluate_policy()` runs on CPU regardless of training device (evaluation is not performance-critical).
- If `--device mps` is requested but MPS is not available, exit with a clear error message. Same for `cuda`.

### CLI overrides

The following CLI flags override config file values at runtime:

| Flag | Overrides | Type |
|------|-----------|------|
| `--device` | N/A (CLI-only) | `auto\|cpu\|mps\|cuda` |
| `--total-steps` | `total_steps` | int |

- `--device` is a runtime concern, not a training hyperparameter — it does NOT appear in config files.
- `--total-steps` lets the user run shorter or longer training without editing the config: `python -m src.train.train_dqn --config configs/dqn_minipong_full.yaml --total-steps 50000`
- If provided, the CLI value overrides the config file value. If not provided, the config file value is used.

## 3. Progress Reporting

During training, print a progress line every 1,000 steps to stdout:

```
[Step  1000/100000]  eps=0.988  loss=0.0142  elapsed=0:00:14  speed=71.4 steps/s  ETA=23:05
[Step  2000/100000]  eps=0.975  loss=0.0089  elapsed=0:00:28  speed=71.2 steps/s  ETA=22:51
...
[Step 10000/100000]  eps=0.888  loss=0.0034  elapsed=0:02:20  speed=71.4 steps/s  ETA=20:55
  ↳ Eval @ step 10000: mean_return=-0.80  mean_hits=1.40 (10 episodes)
  ↳ Checkpoint saved: artifacts/full_train/checkpoints/step_10000.pt
```

### Requirements

- Progress lines print every 1,000 steps (configurable via a new `log_every_steps` config key, default 1000).
- Eval results and checkpoint saves print as indented sub-lines immediately after the progress line where they occur.
- All output goes to stdout (not stderr), so it can be piped or tee'd.
- Loss is the average loss over the last `log_every_steps` interval (not instantaneous).

## 4. Training Completion Summary

When training finishes, print a summary block:

```
════════════════════════════════════════════════════════
Training complete: full_train
  Device: mps | Steps: 100,000 | Time: 8m 42s
  Final eval: mean_return=-0.20  mean_hits=5.80

  Play against the trained agent:
    python -m src.play.play_minipong --checkpoint artifacts/full_train/checkpoints/step_100000.pt

  Or use the shorthand:
    python -m src.play.play_minipong --run-id full_train

  Agent vs agent:
    python -m src.play.play_minipong --run-id full_train --left-agent --right-agent
════════════════════════════════════════════════════════
```

## 5. Run-ID Shorthand for Play

Add a `--run-id <id>` flag to `src/play/play_minipong.py` that resolves to the latest (highest step number) checkpoint in `artifacts/<run_id>/checkpoints/`:

```bash
# These are equivalent:
python -m src.play.play_minipong --checkpoint artifacts/full_train/checkpoints/step_100000.pt
python -m src.play.play_minipong --run-id full_train
```

If both `--checkpoint` and `--run-id` are provided, `--checkpoint` takes precedence. If the run directory has no checkpoints, exit with a clear error.

## 6. Makefile Targets

Add these targets to the Makefile:

```makefile
train-full:          ## Full 100k-step training (auto device)
    python -m src.train.train_dqn --config configs/dqn_minipong_full.yaml --run-id full_train

train-full-cpu:      ## Full training, force CPU
    python -m src.train.train_dqn --config configs/dqn_minipong_full.yaml --run-id full_train_cpu --device cpu

train-full-mps:      ## Full training, force Apple GPU
    python -m src.train.train_dqn --config configs/dqn_minipong_full.yaml --run-id full_train_mps --device mps

play-trained:        ## Play against the latest full-train agent
    python -m src.play.play_minipong --run-id full_train --debug

verify-learning-strict:  ## Verify learning with real thresholds
    python -m src.train.verify_learning --run-id full_train --min-return-gain 0.05 --min-hits-gain 2.0
```

All targets must appear in the `.PHONY` declaration.

## 7. Verification Gate

`make verify-learning-strict` uses real thresholds that the agent must actually beat:
- `--min-return-gain 0.05` — trained agent's mean return must exceed random by at least 0.05
- `--min-hits-gain 2.0` — trained agent must hit the ball at least 2.0 more times per episode than random

This is separate from the existing `make verify-learning` (which uses relaxed thresholds for smoke tests).

## Non-Functional Requirements

- The existing smoke config, smoke training, and all scenario validation must remain unchanged.
- `make validate` must still pass — no regressions.
- All new code must pass `ruff` and `mypy`.
- Device selection must not introduce conditional imports or platform-specific code paths that break on Linux/CI (where MPS is not available). The `auto` default gracefully falls back to CPU.
- Checkpoint files remain the same format: `{"model": state_dict, "step": int}`. No format changes.
- Training artifacts go under `artifacts/<run_id>/` following the existing directory structure.
