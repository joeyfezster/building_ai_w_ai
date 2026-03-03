# Scenario: Environment Observation Space

## Category
environment

## Preconditions
- MiniPong environment is importable

## Behavioral Expectation
The environment returns uint8 pixel observations with the correct shape. The observation space matches what the agent will receive — no privileged information leaks into observations.

## Evaluation Method
```bash
python -c "
from src.envs.minipong import MiniPongEnv
import numpy as np

env = MiniPongEnv()
obs, info = env.reset(seed=0)
assert obs.dtype == np.uint8, f'Expected uint8, got {obs.dtype}'
assert len(obs.shape) == 3, f'Expected 3D array (H, W, C), got shape {obs.shape}'
assert obs.shape[0] == 84 and obs.shape[1] == 84, f'Expected 84x84, got {obs.shape}'
assert obs.min() >= 0 and obs.max() <= 255, f'Pixel values out of range'
obs2, _, _, _, _ = env.step(0)
assert obs2.dtype == np.uint8, f'Step observation wrong dtype'
assert obs2.shape == obs.shape, f'Step observation shape changed'
print(f'PASS: observations are uint8 {obs.shape}')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
- Observation shape reported
