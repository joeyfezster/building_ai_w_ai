# Retro RL Milestones: MiniPong + DQN

This repo provides a complete open-source proof that a reinforcement learning agent can learn a Pong-like game using only pixels and discrete controls.

## Quickstart

```bash
make deps
make train-smoke
make eval-smoke
make verify-learning
make dashboard
```

## Artifacts

Training and evaluation artifacts are written to:

- `artifacts/<run_id>/logs.jsonl`
- `artifacts/<run_id>/tensorboard/`
- `artifacts/<run_id>/checkpoints/`
- `artifacts/<run_id>/eval/`
- `artifacts/<run_id>/videos/`
- `artifacts/<run_id>/demo/index.html`

## Validation

**Intention:** prove that MiniPong learning happens from pixels-only observations and controls, with quantitative and qualitative artifacts.

**Sanity checks (no GPU required):**
- `make validate`
- `make train-smoke`
- `make eval-smoke`

**Emulator correctness:**
- `make env-smoke`
- deterministic physics tests in `tests/test_env_minipong_determinism.py`

**Whitepapers integrity:**
- `make whitepapers-acquire`
- `make whitepapers-verify`

**Packaging:**
- `make docker-build`
- `make docker-smoke`

**Learning proof:**
- `make verify-learning`
- progression videos: `artifacts/<run_id>/videos/`
- montage/index: `artifacts/<run_id>/demo/index.html`
- dashboard data source: `artifacts/<run_id>/logs.jsonl` and `artifacts/<run_id>/eval/*.json`
