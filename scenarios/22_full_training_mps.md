# Scenario: Full Training Config Runs on MPS (Apple GPU)

## Category
training

## Preconditions
- Full training config exists at `configs/dqn_minipong_full.yaml`
- Training script accepts `--device mps` flag
- Running on Apple Silicon Mac with MPS support

## Behavioral Expectation
The full training config can execute on Apple GPU via MPS with `--device mps`. Training prints the selected device as MPS, produces progress output, and completes with a summary block. We use `--total-steps 500` to keep the test short.

On machines without MPS (Linux CI), the script must exit with a clear error message rather than crashing.

## Evaluation Method
```bash
python -c "
import torch
if not torch.backends.mps.is_available():
    print('SKIP: MPS not available on this machine')
    exit(0)
print('MPS available, proceeding with test')
" && \
python -m src.train.train_dqn --config configs/dqn_minipong_full.yaml --run-id scenario_mps_train --device mps --total-steps 500 2>&1 | tee /tmp/mps_train_output.txt && \
python -c "
import os

output = open('/tmp/mps_train_output.txt').read()

# Must print MPS device
assert 'mps' in output.lower(), 'MPS device not shown in output'

# Must have progress lines
assert '[Step' in output, 'No progress lines printed'

# Must have completion summary
assert 'Training complete' in output, 'No training completion summary'

# Artifacts must exist
run_dir = 'artifacts/scenario_mps_train'
assert os.path.isdir(run_dir), f'Run directory not created'

print('PASS: MPS training with full config works end-to-end')
"
```

## Pass Criteria
On MPS-capable machines: training completes on MPS without error, device is printed as MPS, progress lines and completion summary appear. On non-MPS machines: test is skipped (not failed).

## Evidence Required
- Training stdout showing MPS device selection
- Completion summary block
- Or SKIP message on non-MPS hardware
