# Factory Feedback — Iteration 1 (Pong Interfaces Crank)

## Summary

**Gate 0 BLOCKED — 5 CRITICAL findings.** Validation gates (1-3) not reached.

Codex produced a solid first implementation across 7 files (+353/-9 lines). The core logic is correct — multi-rally `score_limit`, `GameController`, `get_action_from_keys`, `prepare_agent_obs`, Makefile targets, and pygame dependency are all present and structurally sound.

However, the `GameController` public API does not match the expected interface. Fix these and the implementation will likely pass.

## CRITICAL Fixes Required (Must fix ALL before next submission)

### 1. `GameController.__init__` must accept `debug` and `checkpoint_path` kwargs

**Current:**
```python
@dataclass
class GameController:
    left_agent_enabled: bool = False
    right_agent_enabled: bool = False
```

**Required:** The constructor must accept:
- `GameController()` — no args, both sides human, no debug
- `GameController(debug=False)` — explicit debug flag
- `GameController(debug=True, checkpoint_path='checkpoint_50000.pt')` — debug mode with checkpoint path

Store `debug` and `checkpoint_path` as instance attributes. `checkpoint_path` defaults to `""` or `None`.

### 2. `get_status_tag(side)` must work with ONE argument

**Current:** `get_status_tag(self, side, debug, policy_name)` — requires 3 args

**Required:** `get_status_tag(self, side)` — uses stored `self.debug` and derives policy name from `self.checkpoint_path`. Returns:
- Human left: `"Keyboard: Up:Q, Down:A"`
- Human right: `"Keyboard: Up:P, Down:L"`
- Agent (not debug): `"AI Agent"`
- Agent (debug, with checkpoint): `"Policy: checkpoint_50000.pt"` (just the filename from checkpoint_path)
- Agent (debug, no checkpoint): `"Policy: random"`

### 3. `restart()` must work with ZERO arguments

**Current:** `restart(self, env, seed)` — requires env

**Required:** `restart(self)` — resets only GameController's own internal state (if any), while preserving agent toggle state. The controller should NOT call env.reset(). The caller handles env.reset() separately.

### 4. `_manual_opponent_action` must be cleared in `reset()`

In `MiniPongEnv.reset()`, add:
```python
self._manual_opponent_action = None
```

This prevents state leaking between episodes.

### 5. `torch.load()` must use `weights_only=True`

In `AgentPolicy.__init__`, change line 78 to:
```python
data = torch.load(checkpoint_path, map_location=self.device, weights_only=True)
```

## WARNING Fixes (Should fix, non-blocking)

### 6. Add test coverage for `set_opponent_action()`
Verify that `set_opponent_action(0)` moves opponent up and `set_opponent_action(None)` restores AI.

### 7. Update `run_game()` call sites
After fixing `get_status_tag` and `restart` signatures, update all call sites in `run_game()`.

### 8. Add missing right-side STAY test
```python
assert get_action_from_keys("right", set()) == 2
```

## Priority Order

1. Fix `GameController.__init__` (CRITICAL #1)
2. Fix `get_status_tag` signature (CRITICAL #2)
3. Fix `restart()` signature (CRITICAL #3)
4. Fix `_manual_opponent_action` reset (CRITICAL #4)
5. Fix `torch.load` security (CRITICAL #5)
6. Update `run_game()` call sites
7. Add tests (WARNINGs)
8. Run `make lint && make typecheck` before finishing

## What NOT to Change
- `get_action_from_keys()` — correct as-is
- `prepare_agent_obs()` — correct as-is
- `MiniPongConfig.score_limit` — correct as-is
- `_finish_point()` multi-rally logic — correct as-is
- Makefile targets — correct as-is
- `requirements.in` pygame entry — correct as-is
