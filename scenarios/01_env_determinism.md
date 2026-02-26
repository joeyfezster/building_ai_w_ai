# Scenario: Environment Determinism

## Category
environment

## Preconditions
- MiniPong environment is importable from `src.envs.minipong`
- Environment accepts `seed` parameter in `reset()`

## Behavioral Expectation
Given the same seed and the same sequence of actions, the environment produces identical observations, rewards, and info dicts across two independent runs. This is required for reproducible evaluation.

## Evaluation Method
```bash
python -c "
from src.envs.minipong import MiniPongEnv
import numpy as np

env1 = MiniPongEnv()
env2 = MiniPongEnv()

for seed in [0, 42, 123]:
    obs1, info1 = env1.reset(seed=seed)
    obs2, info2 = env2.reset(seed=seed)
    assert np.array_equal(obs1, obs2), f'Observations differ at reset with seed={seed}'
    assert info1 == info2, f'Info dicts differ at reset with seed={seed}'
    for action in [0, 1, 2, 0, 1, 2, 0, 0, 1, 1]:
        obs1, r1, d1, t1, i1 = env1.step(action)
        obs2, r2, d2, t2, i2 = env2.step(action)
        assert np.array_equal(obs1, obs2), f'Observations differ during step'
        assert r1 == r2, f'Rewards differ'
        assert d1 == d2 and t1 == t2, f'Done flags differ'
print('PASS: determinism verified for 3 seeds')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
