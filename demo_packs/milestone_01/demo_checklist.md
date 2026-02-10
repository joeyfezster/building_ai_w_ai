# Demo Checklist

## Pre-demo validation
- Run `python -m src.train.train_dqn --config configs/dqn_pong_smoke.yaml`.
- Run `python -m src.train.evaluate --config configs/dqn_pong_smoke.yaml`.
- Confirm `outputs/dqn_pong_smoke/videos/` contains MP4s.
- Confirm `outputs/dqn_pong_smoke/metrics.json` is present.

## Recording
- Capture 10-15 seconds of gameplay from the evaluation video.
- Overlay metrics from `metrics.json`.

## Post-demo
- Upload the MP4 to the milestone pack.
- Update the demo pack checklist with actual metrics.
