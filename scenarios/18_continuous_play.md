# Scenario: Continuous Play (Multi-Rally)

## Category
environment

## Preconditions
- MiniPong environment and play module are importable

## Behavioral Expectation
The game does NOT end after a single point. After a score, the ball resets to center and play continues. The game tracks cumulative scores for both sides. An episode ends when a configurable score limit is reached (default 11).

## Evaluation Method
```bash
python -c "
from src.envs.minipong import MiniPongEnv, MiniPongConfig

# Use a multi-point config — game should not end after 1 point
config = MiniPongConfig(max_steps=5000, score_limit=11)
env = MiniPongEnv(config=config)
obs, info = env.reset(seed=42)

total_steps = 0
points_scored = 0
max_score_seen = 0

for _ in range(3000):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    total_steps += 1
    if reward != 0:
        points_scored += 1
    current_max = max(info.get('agent_score', 0), info.get('opponent_score', 0))
    max_score_seen = max(max_score_seen, current_max)
    if terminated or truncated:
        break

# Must have scored multiple points in a single episode
assert points_scored > 1, f'Expected multiple points in one episode, got {points_scored}'
assert max_score_seen > 1, f'Expected cumulative score > 1, got {max_score_seen}'
print(f'PASS: continuous play works — {points_scored} points scored, max score {max_score_seen} in {total_steps} steps')
"
```

## Pass Criteria
Script exits with code 0. Multiple points scored in a single episode without premature termination.

## Evidence Required
- stdout showing points scored and max score achieved
