# Post-Merge Feedback — PR #9 (Pong Interfaces)

Items synthesized from bot reviewer comments. Must be included in the next factory crank's seed feedback.

## From: chatgpt-codex-connector (P2) — max_steps enforcement on scored points

**File:** `src/envs/minipong.py`, line 105 (`_finish_point` early return path)
**What was flagged:** When `score_limit > 1`, the `_finish_point()` method's "continue playing" return path (`return self._obs(), reward, False, False, self._info()`) does not check `self.steps >= self.config.max_steps`. A point scored on the exact step that hits max_steps is reported as `terminated=False, truncated=False`, allowing the episode to run past its configured time limit.
**Orchestrator assessment:** Valid. Minor edge case — does not affect any current scenarios (score_limit=11 with max_steps=5000 makes collision extremely unlikely), but it's a real correctness gap. The "continue playing" branch in `_finish_point` should check max_steps and set `truncated=True` + `episode_reason="max_steps"` when applicable.
**Severity:** P2 (correctness edge case, no scenario impact)
