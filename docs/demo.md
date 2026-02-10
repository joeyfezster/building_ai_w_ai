# Demo Guide

## Side-by-side evaluation videos

To compare two checkpoints, generate two evaluation MP4s and then stitch or display them side-by-side.

### Option A: Stitch with FFmpeg

```bash
ffmpeg -i outputs/eval_run_a/videos/eval_001.mp4 \
  -i outputs/eval_run_b/videos/eval_001.mp4 \
  -filter_complex hstack \
  outputs/side_by_side.mp4
```

### Option B: Display two MP4s

If you are presenting live, open both MP4s side-by-side in a player or a browser and synchronize the start.

## Recommended flow

1) Run `python -m src.train.evaluate --config configs/dqn_pong_smoke.yaml` for each checkpoint.
2) Confirm `metrics.json` and `videos/` outputs are present.
3) Stitch with FFmpeg or display them side-by-side.
