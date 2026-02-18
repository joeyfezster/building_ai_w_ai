# MiniPong RL Proof System

Public, end-to-end, reproducible system showing a DQN agent can learn an 80s-style Pong-like game from **pixels + discrete controls** only.

## What is included
- Open-source MiniPong environment (no proprietary ROMs) in `src/envs/minipong.py`.
- DQN training pipeline with replay buffer, target network, epsilon-greedy policy, frame stacking, checkpointing, and periodic evaluation.
- Observability: TensorBoard, JSONL logs, evaluation summaries, and saved videos.
- Learning verification gate with baseline-vs-trained checks.
- Streamlit dashboard for learning curves, outcomes, and strategy proxies.
- Docker + SkyPilot + CI integration.

## Quickstart
```bash
make deps
make train-smoke
make eval-smoke
make verify-learning
python -m src.train.make_montage --run_id demo_cpu
make dashboard
```

## Artifacts
Training/evaluation artifacts are stored in:
`artifacts/<run_id>/`
- `tensorboard/`
- `logs.jsonl`
- `checkpoints/*.pt`
- `eval/metrics_*.json`
- `videos/*.mp4`
- `demo/index.html`

## Validation
- **Intention:** success means the agent learns MiniPong from pixels only, and proof artifacts (metrics + videos + dashboard data) confirm it.

- **Sanity checks (no GPU required):**
  - `make validate`
  - `make train-smoke`
  - `make eval-smoke`

- **Emulator correctness:**
  - `make env-smoke`
  - deterministic physics checks are in tests.

- **Whitepapers integrity:**
  - `make whitepapers-acquire`
  - `make whitepapers-verify`

- **Packaging:**
  - `make docker-build`
  - `make docker-smoke`

- **Learning proof:**
  - `make verify-learning`
  - montage output: `artifacts/<run_id>/demo/index.html`
  - dashboard data: `artifacts/<run_id>/logs.jsonl` and `artifacts/<run_id>/eval/*.json`
