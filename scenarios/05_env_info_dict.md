# Scenario: Environment Info Dict Completeness

## Category
environment

## Preconditions
- MiniPong environment is importable

## Behavioral Expectation
The info dict returned by reset() and step() contains all required keys: rally_length, hits, misses, agent_score, opponent_score, episode_reason. These are needed by the dashboard and learning verification pipeline.

## Evaluation Method
```bash
python -c "
from src.envs.minipong import MiniPongEnv

env = MiniPongEnv()
required_keys = ['rally_length', 'hits', 'misses', 'agent_score', 'opponent_score', 'episode_reason']

obs, info = env.reset(seed=0)
for key in required_keys:
    assert key in info, f'Missing key \"{key}\" in reset info dict. Got: {list(info.keys())}'

obs, r, d, t, info = env.step(0)
for key in required_keys:
    assert key in info, f'Missing key \"{key}\" in step info dict. Got: {list(info.keys())}'

print(f'PASS: info dict contains all required keys: {required_keys}')
"
```

## Pass Criteria
Script exits with code 0. All required keys present in both reset and step info dicts.

## Evidence Required
- stdout confirming key presence
