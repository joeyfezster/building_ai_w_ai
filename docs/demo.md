# Demo Reproduction

```bash
make deps
make train-smoke
python -m src.train.record_video --output artifacts/smoke_run/videos/random.mp4
python -m src.train.record_video --checkpoint artifacts/smoke_run/checkpoints/step_500.pt --output artifacts/smoke_run/videos/early.mp4
python -m src.train.record_video --checkpoint artifacts/smoke_run/checkpoints/step_1000.pt --output artifacts/smoke_run/videos/mid.mp4
python -m src.train.record_video --checkpoint artifacts/smoke_run/checkpoints/step_2000.pt --output artifacts/smoke_run/videos/late.mp4
python -m src.train.make_montage --run_id smoke_run
make verify-learning
make dashboard
```
