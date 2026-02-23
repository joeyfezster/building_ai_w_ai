# DQN Algorithm Spec

## Algorithm

Classic Deep Q-Network (DQN) with:
- Experience replay buffer
- Target network with periodic hard updates
- Epsilon-greedy exploration with linear decay schedule
- Optional frame stacking wrapper

## Network Architecture

CNN processing pixel observations:
- Input: stacked grayscale frames (e.g., 4 x 84 x 84)
- Conv layers extracting spatial features
- Fully connected layers producing Q-values for each action
- Output: Q-value per action (3 actions: UP, DOWN, STAY)

## Replay Buffer

- Capacity: configurable (default 20,000 transitions)
- Warmup: configurable number of random-action steps before training begins (default 200)
- Sampling: uniform random from buffer
- Storage: observations, actions, rewards, next observations, done flags

## Epsilon Schedule

Linear decay from `epsilon_start` to `epsilon_end` over `epsilon_decay_steps`:
- `epsilon_start`: 1.0 (fully random)
- `epsilon_end`: 0.05 (mostly greedy)
- `epsilon_decay_steps`: configurable (default 1,500)

## Target Network

- Separate target network for stable Q-value targets
- Hard update: copy weights from online network every `target_update_period` steps (default 100)

## Training Hyperparameters

All configurable via YAML config file (`configs/dqn_minipong.yaml`):
- `gamma`: 0.99 (discount factor)
- `lr`: 0.001 (learning rate)
- `batch_size`: 32
- `total_steps`: training step budget

## Loss

Standard DQN loss: MSE between predicted Q-values and target Q-values computed from the target network.

## Components

| Module | Location | Responsibility |
|--------|----------|---------------|
| Networks | `src/rl/networks.py` | CNN Q-network definition |
| Replay | `src/rl/replay.py` | Experience replay buffer |
| Schedules | `src/rl/schedules.py` | Epsilon decay schedule |
| Agent | `src/agents/dqn_agent.py` | Action selection, learning step |
