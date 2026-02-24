# System Spec

## Purpose

Build a complete, public, end-to-end system that proves a reinforcement learning agent can learn to play a simple 80s-style game from pixels + controls. The system must be reproducible and self-verifying.

## Proof Requirements

The final proof is ALL of:
1. Coded/system verification that learning happened (metrics and statistical checks)
2. A video demonstration showing qualitative improvement across training checkpoints
3. A dashboard that correlates learning curves with game outcomes and simple "strategy" indicators
4. All subcomponents validated for functional, architectural, and integration requirements

## Licensing Constraint

- No proprietary game ROMs
- MiniPong is built from scratch as an open-source Gymnasium environment (MIT license)
- The agent receives only pixels as observation and discrete controls as input

## Repository Standards

- Python 3.12+
- pip-based dependencies using requirements.in / requirements-dev.in compiled to requirements.txt / requirements-dev.txt (use pip-tools)
- High code quality: ruff, mypy, pytest, git hooks (`make install-hooks`), GitHub Actions CI (non-negotiable)
- Testing philosophy: no mocks/stubs/patches — favor functional and behavioral tests

## Component Architecture

| Component | Location | Purpose |
|-----------|----------|---------|
| MiniPong Environment | `src/envs/minipong.py` | Custom Gymnasium env with deterministic physics |
| DQN Agent | `src/agents/dqn_agent.py`, `src/rl/` | Classic DQN with replay, target net, epsilon-greedy |
| Training Pipeline | `src/train/train_dqn.py` | Orchestrates training, eval, checkpointing |
| Evaluation | `src/train/evaluate.py` | Fixed-seed policy evaluation |
| Video Recording | `src/train/record_video.py` | Evaluation video capture |
| Learning Verification | `src/train/verify_learning.py` | Statistical proof that learning occurred |
| Dashboard | `src/dashboard/app.py` | Streamlit app for observability |
| Montage | `src/train/make_montage.py` | Video progression compilation |

## Makefile Targets (must implement)

make deps, make lint, make typecheck, make test, make docker-build, make docker-smoke, make env-smoke, make train-smoke, make eval-smoke, make verify-learning, make dashboard, make validate (lint + typecheck + test + docker-build + docker-smoke + env-smoke)

## Docker

- `Dockerfile.train` — CUDA default, allow python:3.12-slim fallback
- `Dockerfile.demo` — python:3.12-slim

## CI

GitHub Actions — install deps, ruff, mypy, pytest, docker build, docker smoke. Must not require GPU.
