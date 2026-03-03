# Scenario: Environment Reward Structure

## Category
environment

## Preconditions
- MiniPong environment is importable
- Environment can run episodes to completion

## Behavioral Expectation
The environment produces rewards of +1 (agent scores) and -1 (agent misses) during gameplay. A complete episode accumulates non-zero total reward. The agent_score and opponent_score in info track cumulative scoring correctly.

## Evaluation Method
```bash
python -c "
from src.envs.minipong import MiniPongEnv

env = MiniPongEnv()
obs, info = env.reset(seed=42)
total_reward = 0.0
rewards_seen = set()
steps = 0
done = False
while not done and steps < 2000:
    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
    total_reward += reward
    if reward != 0:
        rewards_seen.add(reward)
    done = terminated or truncated
    steps += 1

assert 1.0 in rewards_seen or -1.0 in rewards_seen, f'Expected +1 or -1 rewards, saw: {rewards_seen}'
assert info.get('agent_score', None) is not None, 'Missing agent_score in info'
assert info.get('opponent_score', None) is not None, 'Missing opponent_score in info'
score_sum = info['agent_score'] - info['opponent_score']
print(f'PASS: rewards correct. Total={total_reward}, scores={info[\"agent_score\"]}-{info[\"opponent_score\"]}, steps={steps}')
"
```

## Pass Criteria
Script exits with code 0. At least one of +1 or -1 rewards observed during a random-action episode.

## Evidence Required
- stdout showing total reward and score breakdown
