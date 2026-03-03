# Scenario: Rally Length Grows With Training

## Category
training

## Preconditions
- `train_dqn.py` logs `eval/mean_rally_length` and `eval/hit_ratio` metrics
- `evaluate.py` returns `mean_rally_length` and `hit_ratio` in results dict
- Training configs exist for short and long runs

## Behavioral Expectation
Training an agent for 100k steps produces measurably longer rallies (more paddle contacts per point) than a 100-step agent, demonstrating that the agent learns to sustain play rather than just miss the ball.

## Evaluation Method
```bash
# Train a short agent (100 steps) and a longer agent (100k steps) on CPU
python -m src.train.train_dqn --config configs/dqn_minipong_full.yaml --run-id scenario_rally_100 --device cpu --total-steps 100
python -m src.train.train_dqn --config configs/dqn_minipong_full.yaml --run-id scenario_rally_100k --device cpu --total-steps 100000

# Evaluate both with the evaluate module
python -m src.train.evaluate --run-id scenario_rally_100 --episodes 10 --seeds 0 1 2 3 4 --frame-stack 4 --max-steps 800
python -m src.train.evaluate --run-id scenario_rally_100k --checkpoint "$(ls -t artifacts/scenario_rally_100k/checkpoints/step_*.pt | head -1)" --episodes 10 --seeds 0 1 2 3 4 --frame-stack 4 --max-steps 800

# Compare rally lengths
python -c "
import json
from pathlib import Path

short_dir = Path('artifacts/scenario_rally_100/eval')
long_dir = Path('artifacts/scenario_rally_100k/eval')

short_files = sorted(short_dir.glob('metrics_*.json'))
long_files = sorted(long_dir.glob('metrics_*.json'))

short_data = json.loads(short_files[-1].read_text()) if short_files else {}
long_data = json.loads(long_files[-1].read_text()) if long_files else {}

short_rally = short_data.get('mean_rally_length', 0)
long_rally = long_data.get('mean_rally_length', 0)
short_ratio = short_data.get('hit_ratio', 0)
long_ratio = long_data.get('hit_ratio', 0)

print(f'100-step agent: rally_length={short_rally:.2f}, hit_ratio={short_ratio:.3f}')
print(f'100k-step agent: rally_length={long_rally:.2f}, hit_ratio={long_ratio:.3f}')
print(f'Rally improvement: {long_rally - short_rally:.2f}')
print(f'Hit ratio improvement: {long_ratio - short_ratio:.3f}')

# Rally length must improve by at least 0.5
assert long_rally > short_rally + 0.5, f'FAIL: rally improvement {long_rally - short_rally:.2f} < 0.5'
# Hit ratio must also improve
assert long_ratio > short_ratio, f'FAIL: hit ratio did not improve ({long_ratio:.3f} <= {short_ratio:.3f})'
print('PASS: Rally length and hit ratio both grew with training')
"
```

## Pass Criteria
The 100k-step agent's `mean_rally_length` exceeds the 100-step agent's by at least 0.5, and `hit_ratio` improves. This demonstrates the agent learns to sustain competitive play.

## Evidence Required
- `mean_rally_length` for both agents
- `hit_ratio` for both agents
- Numerical improvement delta
