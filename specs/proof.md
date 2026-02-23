# Learning Proof & Video Proof Spec

## Learning Proof

### Baseline

Create a random policy evaluation FIRST and store its metrics. This is the control — the agent before any learning.

### Verification Criteria

Learning verification passes when ALL of:
1. Mean episode return improves over random baseline
2. Hit rate improves over random baseline
3. Improvement is observed for at least 2 distinct seeds

### Runnable Command

`make verify-learning` — returns non-zero exit code on failure.

Implemented via: `python -m src.train.verify_learning --run-id <run_id> --min-return-gain <threshold> --min-hits-gain <threshold>`

### Metrics

Comparison between random baseline and trained policy:
- Mean episode return (higher is better)
- Hit rate: hits / (hits + misses) (higher is better)
- Per-seed breakdown to ensure consistency

## Video Proof

### Recording Points

Record evaluation videos at:
1. Random baseline (step 0, untrained policy)
2. Early checkpoint (~10% of training)
3. Mid checkpoint (~50% of training)
4. Late checkpoint (~100% of training)

### Montage

Create either:
- A montage video combining all checkpoint videos, OR
- A folder with HTML index showing video progression side-by-side

Implemented via: `src/train/make_montage.py`

### Evidence

Videos must visually demonstrate:
- Random policy: ball passes paddle, no tracking behavior
- Trained policy: paddle tracks ball, returns volleys, rallies extend

### Artifact Locations

- Individual videos: `artifacts/<run_id>/videos/eval_step_<k>.mp4`
- Montage: `artifacts/<run_id>/videos/montage/` or `artifacts/<run_id>/videos/montage.mp4`
