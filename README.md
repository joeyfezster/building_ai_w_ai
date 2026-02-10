# Retro RL Milestones

Recreating classic AI milestones by training play-agents on 80s-style games from pixels + controls. Play-agents live in `src/`, while dev-team agents (LLM prompt roles) live under `agents/` and define how PRs are produced and validated.

## Quickstart

### Install

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

### Whitepapers

```bash
python scripts/acquire_whitepapers.py
python scripts/verify_whitepapers.py
```

### Emulator smoke test

```bash
python scripts/emulator_smoke.py
```

### Random rollout + record MP4

```bash
python -m src.train.record_video --config configs/random_pong.yaml
```

### DQN smoke training + TensorBoard

```bash
python -m src.train.train_dqn --config configs/dqn_pong_smoke.yaml
tensorboard --logdir outputs/dqn_pong_smoke/runs
```

### Evaluate a checkpoint

```bash
python -m src.train.evaluate --config configs/dqn_pong_smoke.yaml
```

## Outputs

All generated artifacts (videos, runs, logs, checkpoints) are written to the `outputs/` directory and are gitignored by default.

## Validation (Makefile targets)

```bash
make lint
make typecheck
make test
make docker-build
make docker-smoke
make emulator-smoke
make whitepapers-acquire
make whitepapers-verify
make validate
```

## Validation Checklist

1) **Intention validation**: Repo installs, runs smoke training, records videos, and evaluates checkpoints using the commands above.
2) **Sanity checks**: `make validate` passes locally.
3) **Emulator validation**: `make emulator-smoke` reports frames stepped and observation shape.
4) **Whitepapers validation**: `make whitepapers-acquire` downloads PDFs; `make whitepapers-verify` confirms hashes + titles.
5) **Packaging validation**: `make docker-build` and `make docker-smoke` succeed for both Dockerfiles.
6) **CI validation**: CI workflow mirrors `make validate` steps.
7) **Edge cases**: invalid config paths and unwritable output dirs return friendly CLI errors; video can be disabled via config.
8) **Non-functional**: outputs are gitignored; all paths are OS-agnostic via `pathlib`; logging is JSONL + console readable.

## Docs

- Milestones: `docs/milestones.md`
- Agents operating model: `docs/agents.md`
- Demo guide: `docs/demo.md`
- Compute notes: `docs/compute.md`
- Roadmap: `docs/roadmap.md`
- Whitepapers index: `docs/whitepapers.md`
