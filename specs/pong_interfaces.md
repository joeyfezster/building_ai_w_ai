# Pong Interfaces Spec

## Overview

MiniPong must be playable interactively by humans via a pygame window, with support for two-player same-keyboard play and agent takeover of either side.

## Dependencies

Add `pygame` to `requirements.in`. The interactive player is a first-class module at `src/play/play_minipong.py`, runnable via `make play`.

## Human — Two Players

The packaged MiniPong game must be playable by 2 players on the same keyboard (or one player using two hands to play against himself).

### Controls

| Player | Up Key | Down Key | Side |
|--------|--------|----------|------|
| Left   | `Q`    | `A`      | Left paddle |
| Right  | `P`    | `L`      | Right paddle |

Keys were selected based on QWERTY key positions and natural left-right / up-down dynamics.

If no key is pressed for a given side, that paddle stays in place (STAY action).

### Rendering

- The game renders in a pygame window at a scaled resolution (minimum 6x the 84x84 game pixels = 504x504).
- White paddles and ball on black background, matching the existing `rgb_array` rendering.
- The window title must include "MiniPong".
- The game runs at 30 FPS (matching `render_fps` metadata).

### Scoring

- The game must NOT end after a single point. Episodes continue with the ball resetting to center after each score, tracking cumulative score for both sides.
- A HUD displays the current score for each side.
- The game ends when a player reaches a configurable score limit (default 11) or the player presses ESC/Q-key-combo to quit.

### Game Flow

- `ESC` quits the game.
- `R` restarts the game (resets scores to 0-0).
- After a point is scored, the ball resets to center and play continues automatically.

## Agent Takeover

While playing, a human may choose any side (left or right) to be taken over by a trained agent. This includes having two agents play each other.

### Takeover Controls

| Combination | Effect |
|-------------|--------|
| `Shift+A`   | Toggle agent control of the LEFT side |
| `Shift+L`   | Toggle agent control of the RIGHT side |

Pressing the same combination again toggles control back to human (for the respective side).

### Agent Policy

- The agent loads a trained DQN checkpoint. The checkpoint path is configurable via command-line argument (`--checkpoint`).
- If no checkpoint is provided, the agent falls back to a random policy.
- The agent receives the same 84x84 grayscale pixel observation that the training pipeline uses.
- For the RIGHT side agent, the observation must be horizontally flipped so the agent always "sees" itself on the left (matching training perspective).

## Player Status Tags

Each side (left and right) must display a status tag indicating who is currently controlling that paddle.

### Placement

- Left player tag: top-left corner of the screen, outside/above the playing area.
- Right player tag: top-right corner of the screen, outside/above the playing area.

### Content

When controlled by a human:
```
Keyboard: Up:Q, Down:A
```
(or `Up:P, Down:L` for the right side)

When controlled by an agent:
```
AI Agent
```

When in debug mode (activated via `--debug` flag):
```
Policy: <policy_name>
```
where `<policy_name>` is the checkpoint filename (e.g., `checkpoint_50000.pt`) or `random` if no checkpoint.

### Tag Accuracy

The tag must reflect the **true current state** of who is controlling each paddle at all times. Specifically:
- The tag must update immediately when a takeover toggle occurs (same frame).
- The tag must never show "AI Agent" when the human is controlling the paddle, or vice versa.
- The tag state must survive game restarts (R key) — if the agent was controlling the left side, it continues to do so after restart.

## Makefile Integration

| Target | Command |
|--------|---------|
| `make play` | `python -m src.play.play_minipong` |
| `make play-debug` | `python -m src.play.play_minipong --debug` |
| `make play-agent-vs-agent` | Launch with both sides set to agent (convenience target) |

## Module Structure

```
src/play/
    __init__.py
    play_minipong.py      # Main interactive game loop
```

The play module imports from `src.envs.minipong` for the game physics and from `src.rl.networks` / `src.agents.dqn_agent` for the trained policy.

## Non-Functional Requirements

- The game must run at 30 FPS on CPU without frame drops.
- pygame is the only additional dependency (already added to requirements.in).
- The play module must not break any existing imports or tests.
- All code must pass `ruff` and `mypy` checks.
