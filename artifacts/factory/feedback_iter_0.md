# Factory Feedback — Iteration 0 (Initial Seed)

## Summary

This is the first factory iteration for the **Pong Interfaces** feature. There are no previous failures — this is a greenfield implementation.

## What Needs to Be Built

Read `specs/pong_interfaces.md` for the full specification. Key deliverables:

### 1. Interactive Play Module (`src/play/play_minipong.py`)
- pygame-based interactive window rendering MiniPong at 6x scale (504x504)
- Two-player same-keyboard controls: Q/A (left), P/L (right)
- Agent takeover toggle: Shift+A (left), Shift+L (right)
- Player status tags showing who controls each paddle
- Debug mode (`--debug`) showing policy names
- 30 FPS game loop

### 2. Multi-Rally Environment Support
- Add `score_limit` to `MiniPongConfig` (default=1 for backward compat)
- When `score_limit > 1`, ball resets to center after a point instead of terminating
- Episode ends when either side reaches `score_limit`
- New `episode_reason`: `"score_limit"`

### 3. Testable Game Logic
The spec requires these to be testable WITHOUT a pygame display:
- `get_action_from_keys(side, pressed)` — maps key names to actions
- `GameController` class with `toggle_agent()`, `get_controller()`, `get_status_tag()`, `restart()`
- `prepare_agent_obs(obs, side)` — flips observation for right-side agent

### 4. Makefile Targets
- `make play` → `python -m src.play.play_minipong`
- `make play-debug` → `python -m src.play.play_minipong --debug`
- `make play-agent-vs-agent` → launch with both sides agent-controlled

### 5. Dependencies
- Add `pygame` to `requirements.in`

## Priority Order

1. `pygame` in `requirements.in`
2. `score_limit` in `MiniPongConfig` + multi-rally logic in `MiniPongEnv`
3. `src/play/__init__.py` + `src/play/play_minipong.py` with testable components
4. Makefile targets
5. Run `make lint && make typecheck` to verify

## Hard Constraints
- Existing tests must still pass (backward compatibility via `score_limit=1` default)
- No mocks, no stubs — real implementations only
- pygame window must NOT open on module import
