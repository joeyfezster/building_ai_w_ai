# Scenario: Observable Learning Improvement Over Exponential Training Steps

## Category
training

## Preconditions
- Full training config exists at `configs/dqn_minipong_full.yaml`
- Training script accepts `--device`, `--total-steps` flags
- Evaluation produces mean_return and mean_hits metrics

## Behavioral Expectation
An agent trained for more steps should perform better than one trained for fewer steps. This scenario trains at exponential step counts (100, 1000, 10000, 100000) on CPU and verifies monotonic improvement in at least one key metric (mean_return or mean_hits) across the scale.

The agent at 100 steps is essentially random. By 100k steps, it should show clear improvement. We don't require strict monotonicity at every step count (RL is noisy), but the 100k agent must measurably outperform the 100-step agent.

On MPS-capable machines, we also verify the 100k MPS agent improves over the 100-step baseline, confirming that GPU training produces equivalent learning.

## Evaluation Method
```bash
# Train at exponential step counts on CPU
for STEPS in 100 1000 10000 100000; do
    python -m src.train.train_dqn \
        --config configs/dqn_minipong_full.yaml \
        --run-id scenario_learn_cpu_${STEPS} \
        --device cpu \
        --total-steps ${STEPS} 2>&1 | tail -5
done && \
python -c "
import json, glob, os, torch

def get_final_eval(run_id):
    \"\"\"Get eval metrics from the last checkpoint.\"\"\"
    eval_dir = f'artifacts/{run_id}/eval'
    evals = sorted(glob.glob(f'{eval_dir}/metrics_step_*.json'))
    if not evals:
        # No eval checkpoint yet (too few steps) — evaluate the last checkpoint directly
        from src.train.evaluate import evaluate_policy
        ckpts = sorted(glob.glob(f'artifacts/{run_id}/checkpoints/step_*.pt'))
        if not ckpts:
            return {'mean_return': -1.0, 'mean_hits': 0.0}
        metrics = evaluate_policy(ckpts[-1], episodes=5, seeds=[11,22,33,44,55], frame_stack=4, max_steps=800)
        return metrics
    with open(evals[-1]) as f:
        return json.load(f)

results = {}
for steps in [100, 1000, 10000, 100000]:
    run_id = f'scenario_learn_cpu_{steps}'
    m = get_final_eval(run_id)
    results[steps] = m
    print(f'CPU {steps:>6} steps: return={m[\"mean_return\"]:.3f}  hits={m[\"mean_hits\"]:.2f}')

# The 100k agent must outperform the 100-step agent
gain_return = results[100000]['mean_return'] - results[100]['mean_return']
gain_hits = results[100000]['mean_hits'] - results[100]['mean_hits']
print(f'Improvement 100→100k: return_gain={gain_return:.3f}  hits_gain={gain_hits:.2f}')
assert gain_return > 0.0 or gain_hits > 1.0, (
    f'100k agent did not improve over 100-step baseline! '
    f'return_gain={gain_return:.3f}, hits_gain={gain_hits:.2f}'
)

# MPS test (if available)
if torch.backends.mps.is_available():
    import subprocess
    for steps in [100, 100000]:
        subprocess.run([
            'python', '-m', 'src.train.train_dqn',
            '--config', 'configs/dqn_minipong_full.yaml',
            '--run-id', f'scenario_learn_mps_{steps}',
            '--device', 'mps',
            '--total-steps', str(steps),
        ], check=True, capture_output=True)
    m_100 = get_final_eval('scenario_learn_mps_100')
    m_100k = get_final_eval('scenario_learn_mps_100000')
    mps_gain_return = m_100k['mean_return'] - m_100['mean_return']
    mps_gain_hits = m_100k['mean_hits'] - m_100['mean_hits']
    print(f'MPS 100→100k: return_gain={mps_gain_return:.3f}  hits_gain={mps_gain_hits:.2f}')
    assert mps_gain_return > 0.0 or mps_gain_hits > 1.0, 'MPS 100k agent did not improve'
    print('PASS: MPS learning improvement verified')
else:
    print('SKIP: MPS not available, CPU-only test')

print('PASS: Learning improvement over exponential steps verified')
"
```

## Pass Criteria
The 100k-step CPU agent must measurably outperform the 100-step agent (return gain > 0.0 OR hits gain > 1.0). On MPS-capable machines, the same must hold for MPS training.

## Evidence Required
- Metrics at each step count (100, 1k, 10k, 100k)
- Computed improvement gains
- MPS results if applicable (or SKIP message)
