# Gate 0 Tier 2 — Test Integrity Review

**Reviewer:** test-integrity-reviewer
**Scope:** Package restructuring crank — test changes in `tests/test_factory_run_scenarios.py` and `tests/test_factory_compile_feedback.py`
**Paradigm:** Test quality, coverage intent, vacuity detection

---

## Tier 1 Context

The Tier 1 AST scanner (`gate0_results.json`) found:
- **test_quality:** 1 WARNING — `test_imports` in `tests/test_imports.py` has no assertions (may pass vacuously). This is a pre-existing issue, not introduced by this diff.
- **code_quality:** 2 WARNINGs (RET504 in minipong.py, C901 complexity in play_minipong.py). Not test files — out of scope.
- 3 checks skipped (bandit, vulture, radon not installed).

## Findings

```
FINDING: New function `_get_repo_root()` added to 3 scripts with no test coverage
SEVERITY: WARNING
FILE: packages/dark-factory/scripts/run_scenarios.py, compile_feedback.py, nfr_checks.py
LINE: ~lines 27-34 in each file (new block)
EVIDENCE: The diff introduces an identical `_get_repo_root()` function in run_scenarios.py, compile_feedback.py, and nfr_checks.py. This function walks up from __file__ to find a `.git` directory. It replaces the previous `Path(__file__).resolve().parent.parent` pattern with a more robust traversal. However, no test in the repo exercises `_get_repo_root()` — neither the happy path nor the RuntimeError branch (no .git found). The tests import the modules via `sys.path.insert` and call functions like `parse_scenario()`, `run_scenario()`, `compile_feedback()` etc. directly — none of them test repo root discovery.
IMPACT: If the repo root detection logic breaks (e.g., in a worktree where .git is a file not a directory, or in a CI context with a shallow clone), the scripts fail at import time with RuntimeError. This is undetected by any test. Since the function is called at module scope (REPO_ROOT = _get_repo_root()), a failure would cause ImportError in every consumer.
FIX: Add a test for `_get_repo_root()` — at minimum verify it returns a Path containing a `.git` entry when called from the repo. Optionally test the RuntimeError branch by running in a tmp_path with no .git ancestor. Note: since the function is duplicated 3x, consider extracting to a shared utility, but that is a code health concern, not test integrity.
```

```
FINDING: `_get_repo_root()` checks for `.git` as directory only — breaks in worktrees
SEVERITY: WARNING
FILE: packages/dark-factory/scripts/run_scenarios.py (and compile_feedback.py, nfr_checks.py)
LINE: ~line 30 in each file
EVIDENCE: The function checks `if (parent / ".git").is_dir()`. In a git worktree, `.git` is a file (containing `gitdir: /path/to/main/.git/worktrees/name`), not a directory. The test files themselves run from within a worktree context (the current working tree is `.claude/worktrees/factory-restructure`). This means `_get_repo_root()` would fail with RuntimeError when these scripts are invoked from a worktree.
IMPACT: All factory scripts (`run_scenarios.py`, `compile_feedback.py`, `nfr_checks.py`) would fail to start when invoked from a worktree — which is exactly the development context described in MEMORY.md and the current session. The tests don't catch this because they never invoke `_get_repo_root()` directly, and the existing test imports rely on `sys.path.insert` to find the modules (bypassing the module-level REPO_ROOT computation in a context where .git IS a directory — the tests are run from the main repo or a context with a real .git dir).
FIX: Change `(parent / ".git").is_dir()` to `(parent / ".git").exists()` (both file and directory). Add a test that exercises this in a simulated worktree layout (create a tmp_path with a `.git` file instead of a directory). This is a real bug that tests should catch.
```

```
FINDING: sys.path.insert import pattern is fragile but unchanged — acceptable for restructuring
SEVERITY: NIT
FILE: tests/test_factory_run_scenarios.py, tests/test_factory_compile_feedback.py
LINE: lines 17-19 in both files
EVIDENCE: Both test files use `sys.path.insert(0, str(SCRIPTS_DIR))` to import non-package modules. The path was updated from `ROOT / "scripts"` to `ROOT / "packages" / "dark-factory" / "scripts"`. This correctly points to the new location and the imports resolve (the scripts exist at the new path). The import targets (`run_scenarios`, `compile_feedback`) are the same module names.
IMPACT: If the package structure changes again, these paths break silently at import time. However, this pattern was pre-existing and merely updated for the new path — the restructuring did not introduce new fragility.
FIX: No immediate fix needed. Long-term: consider making the scripts proper packages with `__init__.py` so they can be imported normally. This is a design choice, not a test integrity issue.
```

```
FINDING: Tests exercise real code paths through the restructured modules — imports resolve correctly
SEVERITY: NIT (positive observation)
FILE: tests/test_factory_run_scenarios.py, tests/test_factory_compile_feedback.py
LINE: lines 20-26 (run_scenarios), lines 20-27 (compile_feedback)
EVIDENCE: Both test files import real functions from the relocated scripts: `parse_scenario`, `run_scenario`, `Scenario`, `ScenarioReport`, `ScenarioResult` (run_scenarios); `compile_feedback`, `get_iteration_count`, `get_previous_feedback`, `infer_causes`, `load_ci_log`, `load_scenario_results` (compile_feedback). Tests construct real dataclass instances, write real files to tmp_path, invoke real functions, and assert meaningful properties of the outputs. No mocking of the SUT is present. The deletion test passes: replacing `parse_scenario` with `pass` would fail `test_parses_name_from_h1`; replacing `run_scenario` with `pass` would fail `test_passing_scenario_returns_passed_true`, etc.
IMPACT: N/A — this is a positive finding confirming the tests are non-vacuous.
FIX: None needed.
```

```
FINDING: Pre-existing Tier 1 finding confirmed — test_imports has no assertions
SEVERITY: WARNING (pre-existing, not introduced by this diff)
FILE: tests/test_imports.py
LINE: 4-9
EVIDENCE: Tier 1 scanner correctly identified this. The test imports 5 `src.*` modules but asserts nothing. It passes if imports succeed (no exception), which is a "doesn't crash" test. If any module's `__init__.py` were replaced with `pass`, the test would still pass.
IMPACT: Import-only test provides minimal value — it verifies module presence but not functionality. However, this is pre-existing and not part of the restructuring diff.
FIX: Add at least one assertion per module (e.g., `assert hasattr(src.agents, 'DQNAgent')`) to verify the modules export their expected public API. Or accept this as intentional smoke-level coverage.
```

---

## Summary

| Severity | Count | Details |
|----------|-------|---------|
| CRITICAL | 0 | — |
| WARNING  | 3 | `_get_repo_root()` untested (1), `.is_dir()` worktree bug (1), pre-existing test_imports vacuity (1) |
| NIT      | 2 | sys.path fragility (1), positive confirmation (1) |

## Overall Assessment

**The test changes in this diff are minimal and correct.** The two test files had their `sys.path.insert` paths updated from `ROOT / "scripts"` to `ROOT / "packages" / "dark-factory" / "scripts"`, which correctly tracks the script relocation. The tests themselves are well-structured — they exercise real code paths, use real file I/O with `tmp_path`, and assert meaningful behavioral properties. No mocking abuse, no vacuity, no gaming.

**The primary concern is a coverage gap, not a test quality issue.** The new `_get_repo_root()` function (duplicated in 3 scripts) introduces non-trivial logic (filesystem traversal + error handling) that is completely untested. More importantly, the `.is_dir()` check is a real bug in worktree contexts — it should be `.exists()`. This affects factory script execution in the exact context this development happens in (git worktrees). This is a WARNING, not CRITICAL, because the existing tests still exercise the core logic of both scripts through direct function calls — they just don't cover the new repo root discovery path.

**No merge-blocking findings.** All findings are WARNING or NIT level.
