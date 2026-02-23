# Scenario: Training Produces Required Artifacts

## Category
training

## Preconditions
- Training pipeline is runnable via `python -m src.train.train_dqn`
- Config file exists at `configs/dqn_minipong.yaml`

## Behavioral Expectation
A short training smoke run produces all required artifact types: TensorBoard logs, JSONL training log, at least one checkpoint, and at least one evaluation metrics file. These artifacts are the raw material for learning proof and dashboard.

## Evaluation Method
```bash
python -m src.train.train_dqn --config configs/dqn_minipong.yaml --run-id scenario_test 2>&1 && \
python -c "
import os, glob

run_dir = 'artifacts/scenario_test'
assert os.path.isdir(run_dir), f'Run directory not created: {run_dir}'

# TensorBoard
tb_files = glob.glob(f'{run_dir}/tensorboard/events.*')
assert len(tb_files) > 0, 'No TensorBoard event files'

# JSONL log
assert os.path.isfile(f'{run_dir}/logs.jsonl'), 'No logs.jsonl'

# Checkpoints
ckpts = glob.glob(f'{run_dir}/checkpoints/*.pt')
assert len(ckpts) > 0, f'No checkpoints saved'

# Eval metrics
evals = glob.glob(f'{run_dir}/eval/metrics_*.json')
assert len(evals) > 0, f'No evaluation metrics files'

print(f'PASS: all artifact types present. TB={len(tb_files)}, ckpts={len(ckpts)}, evals={len(evals)}')
"
```

## Pass Criteria
Training completes without error. All four artifact types (TensorBoard, JSONL, checkpoints, eval metrics) are present in the run directory.

## Evidence Required
- Training stdout/stderr
- Artifact counts
