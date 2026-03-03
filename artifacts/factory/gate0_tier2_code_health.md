# Gate 0 Tier 2 — Code Health Review

## Diff Context
Package restructuring crank: factory scripts and skills moved from `scripts/` and `.claude/skills/` into `packages/dark-factory/` and `packages/pr-review-pack/`. Includes file moves, path reference updates, REPO_ROOT detection fixes, symlink creation, license changes, and new files.

## Tier 1 Context
Tier 1 had 3 checks skipped (bandit, vulture, radon not installed), 2 passed (code_quality, test_quality) with 3 warnings total. No critical findings.

---

## Findings

### Stale Cross-References (Incomplete Path Migration)

```
FINDING: dark_factory.md cross-reference table has inconsistent path styles
SEVERITY: WARNING
FILE: packages/dark-factory/docs/dark_factory.md
LINE: 16, 19
EVIDENCE: Line 16 uses relative path "factory-orchestrate/SKILL.md Step 4" while line 15 uses full "packages/dark-factory/SKILL.md". Line 19 uses "docs/code_quality_standards.md" but the file was moved to "packages/dark-factory/docs/code_quality_standards.md".
IMPACT: The cross-reference table is the navigation index for the operating manual. An agent or human following line 16's reference "factory-orchestrate/SKILL.md" will not find the file — it does not exist at that relative path from the doc's new location. Line 19 references a file at a path that no longer exists (moved in this diff).
FIX: Line 16: change to "packages/dark-factory/SKILL.md Step 4" (or just "SKILL.md" since it is adjacent). Line 19: change to "packages/dark-factory/docs/code_quality_standards.md" (or "docs/code_quality_standards.md" relative to package root, matching what adjacent docs use).
```

```
FINDING: code_quality_standards.md references old SKILL.md path
SEVERITY: WARNING
FILE: packages/dark-factory/docs/code_quality_standards.md
LINE: 84
EVIDENCE: "See `.claude/skills/factory-orchestrate/SKILL.md` Step 4 for agent team composition." — this path no longer exists as a real file (it is now a symlink to packages/dark-factory).
IMPACT: While the symlink makes this technically resolvable, the reference is misleading. It points to the symlink rather than the canonical location, contradicting the restructuring's goal of making packages/ the source of truth.
FIX: Change to "See `packages/dark-factory/SKILL.md` Step 4" or the relative "SKILL.md" since both files are in the same package.
```

```
FINDING: dark_factory.md file inventory table uses bare "/prompts/factory_fix.md" path
SEVERITY: WARNING
FILE: packages/dark-factory/docs/dark_factory.md
LINE: 278
EVIDENCE: The file inventory table lists `/prompts/factory_fix.md` as the path for the Codex instruction template. The actual file is at `packages/dark-factory/prompts/factory_fix.md`.
IMPACT: The bare `/prompts/factory_fix.md` path is ambiguous — it looks like an absolute path from repo root, but no such file exists there. An agent or script following this reference will fail.
FIX: Change to `/packages/dark-factory/prompts/factory_fix.md` to match the convention used in the rest of the table.
```

```
FINDING: ProjectLeadAsks.md has stale reference to old skills path
SEVERITY: NIT
FILE: ProjectLeadAsks.md
LINE: 60
EVIDENCE: "6. Factory orchestration skill created (`.claude/skills/factory-orchestrate/SKILL.md`)" — this is now a symlink, canonical location is packages/dark-factory/SKILL.md.
IMPACT: Low — this is in the "resolved" section of the project lead asks, so it is historical. But it is inconsistent with the other path updates in the same file (lines 56-57 were updated).
FIX: Update to `packages/dark-factory/SKILL.md` for consistency, or leave as-is since it is a historical record.
```

```
FINDING: Multiple review prompt files reference "docs/code_quality_standards.md" at old path
SEVERITY: WARNING
FILE: packages/review-prompts/code_health_review.md, packages/review-prompts/security_review.md, packages/review-prompts/test_integrity_review.md
LINE: 97, 116, 108 and 19 (respectively)
EVIDENCE: All three review prompt files reference "docs/code_quality_standards.md" and the test integrity review also references it at line 19. The file has been moved to "packages/dark-factory/docs/code_quality_standards.md".
IMPACT: When these review prompts are used by Gate 0 Tier 2 agents (as they are right now), the agents are instructed to read "docs/code_quality_standards.md" which no longer exists at that path. The agents may fail to find the quality standards, reducing review quality.
FIX: Update all references in the review prompt files to "packages/dark-factory/docs/code_quality_standards.md".
```

```
FINDING: SKILL.md (factory-orchestrate) references "docs/code_quality_standards.md" at old path
SEVERITY: WARNING
FILE: packages/dark-factory/SKILL.md
LINE: 106, 323
EVIDENCE: Line 106: "Each agent also receives: ... + `docs/code_quality_standards.md` + the diff." Line 323: "**Code quality standards**: `docs/code_quality_standards.md`"
IMPACT: The skill instructs the orchestrator to pass "docs/code_quality_standards.md" to review agents. This file no longer exists at that path — it moved to "packages/dark-factory/docs/code_quality_standards.md". The factory orchestrator following this skill will either fail to find the file or give agents the wrong path.
FIX: Update both references to "packages/dark-factory/docs/code_quality_standards.md".
```

### Code Duplication

```
FINDING: _get_repo_root() function duplicated verbatim across 8 scripts
SEVERITY: NIT
FILE: packages/dark-factory/scripts/{run_gate0,nfr_checks,check_test_quality,run_scenarios,compile_feedback,strip_holdout,restore_holdout,persist_decisions}.py
LINE: varies (all near top of file)
EVIDENCE: The identical 6-line _get_repo_root() function is copy-pasted into all 8 factory scripts. Same logic, same docstring, same error message.
IMPACT: Low immediate risk — the function is simple and correct. However, 8 identical copies means 8 places to update if the logic ever changes (e.g., to handle git worktrees where `.git` is a file not a directory). This is the kind of duplication that creates maintenance drift over time.
FIX: Extract to a shared module (e.g., `packages/dark-factory/scripts/_common.py`) and import. Or accept the duplication as intentional — these scripts are designed to work standalone without inter-script imports, which is a valid design choice for extractable packages.
```

### Structural Health

```
FINDING: _get_repo_root() uses .is_dir() check which fails in git worktrees
SEVERITY: WARNING
FILE: packages/dark-factory/scripts/run_gate0.py (and all 7 other scripts)
LINE: 41
EVIDENCE: `if (parent / ".git").is_dir()` — in git worktrees, `.git` is a file (containing `gitdir: /path/to/main/.git/worktrees/name`), not a directory. The `.is_dir()` check will fail to find the repo root when running from a worktree.
IMPACT: This is a real runtime failure scenario. The factory is currently being reviewed from within a git worktree (`.claude/worktrees/factory-restructure`). If any factory script is run from a worktree, `_get_repo_root()` will raise RuntimeError because it will walk all the way up to `/` without finding a `.git` directory.
FIX: Change `.is_dir()` to `.exists()` — this handles both regular repos (`.git` is a directory) and worktrees (`.git` is a file). The `.exists()` check is the standard pattern used by `git rev-parse --show-toplevel`.
```

### Makefile Consistency

```
FINDING: Makefile run-scenarios and compile-feedback targets are commented out with holdout-stripped markers
SEVERITY: NIT
FILE: Makefile
LINE: 101-112
EVIDENCE: The `run-scenarios` and `compile-feedback` targets are wrapped in `[factory:holdout-stripped]` comment blocks with the new `packages/dark-factory/scripts/` paths. This is correct — the strip_holdout.py script comments these out. However, the diff shows these are ALREADY commented out on the branch, meaning the diff was generated from a stripped branch state.
IMPACT: If this branch is merged to main in its current state, `make run-scenarios` and `make compile-feedback` will not be available because they are commented out. The restore_holdout.py script should uncomment them on merge, but the diff should be reviewed from the restored state, not the stripped state.
FIX: Verify that restore_holdout.py will correctly restore these targets with the new paths. If the branch is to be merged, ensure scenarios are restored first.
```

### CI Workflow Consistency

```
FINDING: ci.yaml protected_dirs list still includes bare 'scripts' directory
SEVERITY: WARNING
FILE: .github/workflows/ci.yaml
LINE: 96
EVIDENCE: `protected_dirs = ['scenarios', 'scripts', 'agents', 'specs']` — the `scripts` directory is listed as protected, but factory scripts have been moved out of `scripts/` to `packages/dark-factory/scripts/`. The remaining `scripts/` directory contains only product scripts (acquire_whitepapers.py, etc.) which should NOT be protected from Codex.
IMPACT: The CI protection check will flag changes to product scripts that are not factory-protected, creating false positive CI failures. Meanwhile, changes to the actual factory scripts in `packages/dark-factory/scripts/` are NOT protected by this check.
FIX: Replace `'scripts'` with `'packages/dark-factory/scripts'` in the protected_dirs list. Consider also adding `'packages/review-prompts'` and `'packages/pr-review-pack'` if those should also be Codex-protected.
```

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| WARNING | 7 |
| NIT | 3 |

**Overall Assessment:** The restructuring is mechanically sound — files are moved correctly, symlinks resolve, REPO_ROOT detection is added to all scripts, and the main code references in CLAUDE.md, Makefile, and SKILL.md are updated. However, there is a **long tail of stale path references** in secondary documentation files (dark_factory.md cross-references, code_quality_standards.md, review prompt files, SKILL.md agent instructions, ci.yaml protection list). These are all WARNING-level — they do not break the build, but they will cause confusion for agents and humans following these references. The most impactful issue is the `.is_dir()` worktree bug in `_get_repo_root()` which can cause runtime failures in the current worktree-based workflow.

No CRITICAL findings. No blocking issues. Recommend fixing the WARNING-level path references before merge to avoid agent confusion in subsequent factory cranks.
