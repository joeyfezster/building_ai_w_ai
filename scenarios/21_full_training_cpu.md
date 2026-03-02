# Scenario: Full Training Config Runs on CPU

## Category
training

## Preconditions
- Full training config exists at `configs/dqn_minipong_full.yaml`
- Training script accepts `--device cpu` flag

## Behavioral Expectation
The full training config can execute on CPU with `--device cpu`. Training prints the selected device, produces progress output, and completes with a summary block. We use `--total-steps 500` to keep the test short while verifying the full pipeline wiring.

## Evaluation Method
```bash
python -m src.train.train_dqn --config configs/dqn_minipong_full.yaml --run-id scenario_cpu_train --device cpu --total-steps 500 2>&1 | tee /tmp/cpu_train_output.txt && \
python -c "
import os

output = open('/tmp/cpu_train_output.txt').read()

# Must print device selection
assert 'cpu' in output.lower(), 'Device selection not printed'
assert 'Training on device:' in output or 'device:' in output.lower(), 'No device announcement'

# Must have progress lines
assert '[Step' in output, 'No progress lines printed'

# Must have completion summary
assert 'Training complete' in output, 'No training completion summary'

# Artifacts must exist
run_dir = 'artifacts/scenario_cpu_train'
assert os.path.isdir(run_dir), f'Run directory not created: {run_dir}'
assert os.path.isdir(f'{run_dir}/checkpoints'), 'No checkpoints directory'

print('PASS: CPU training with full config works end-to-end')
"
```

## Pass Criteria
Training completes on CPU without error. Device is printed. Progress lines and completion summary appear in output. Artifacts directory created.

## Evidence Required
- Training stdout showing device selection and progress
- Completion summary block
- Artifact directory listing
