# Scenario: Evaluation Produces Videos

## Category
training

## Preconditions
- Training pipeline is runnable
- Video recording dependencies available (imageio, imageio-ffmpeg or opencv)

## Behavioral Expectation
The evaluation pipeline produces MP4 video files showing the agent playing MiniPong. Videos must be non-empty files that can be read by standard video tools.

## Evaluation Method
```bash
python -m src.train.train_dqn --config configs/dqn_minipong.yaml --run-id scenario_video_test 2>&1 && \
python -c "
import os, glob

run_dir = 'artifacts/scenario_video_test'
videos = glob.glob(f'{run_dir}/videos/*.mp4')
assert len(videos) > 0, f'No video files produced in {run_dir}/videos/'

for v in videos:
    size = os.path.getsize(v)
    assert size > 1000, f'Video {v} is too small ({size} bytes) — likely corrupt'

print(f'PASS: {len(videos)} evaluation video(s) produced, all non-trivial size')
"
```

## Pass Criteria
At least one MP4 video file exists and is larger than 1KB.

## Evidence Required
- Video file paths and sizes
