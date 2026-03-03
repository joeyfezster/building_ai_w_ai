# Scenario: Right-Side Agent Receives Flipped Observation

## Category
environment

## Preconditions
- `src/play/play_minipong.py` is importable
- Play module exposes a function to prepare observations for the agent

## Behavioral Expectation
When the agent controls the RIGHT side, the observation must be horizontally flipped so the agent always "sees" itself on the left side (matching the training perspective where the agent is always the left paddle).

## Evaluation Method
```bash
python -c "
import numpy as np
from src.envs.minipong import MiniPongEnv
from src.play.play_minipong import prepare_agent_obs

env = MiniPongEnv(render_mode='rgb_array')
obs, _ = env.reset(seed=42)

# For left side, observation should be unchanged
obs_left = prepare_agent_obs(obs, side='left')
assert np.array_equal(obs, obs_left), 'Left-side obs should be unmodified'

# For right side, observation should be horizontally flipped
obs_right = prepare_agent_obs(obs, side='right')
expected_flip = np.flip(obs, axis=1)
assert np.array_equal(obs_right, expected_flip), 'Right-side obs should be horizontally flipped'

# Verify they are actually different (non-symmetric frame)
# Step a few times to get an asymmetric frame
for _ in range(10):
    obs, _, _, _, _ = env.step(0)
obs_left = prepare_agent_obs(obs, side='left')
obs_right = prepare_agent_obs(obs, side='right')
assert not np.array_equal(obs_left, obs_right), 'Left and right obs should differ for asymmetric frames'

print('PASS: right-side agent receives correctly flipped observation')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
