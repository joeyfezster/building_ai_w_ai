# Gate 0 Tier 2: Adversarial Review -- Package Restructuring

**Reviewer:** Adversarial
**Date:** 2026-03-03
**Spec:** `specs/package_restructure.md`
**Commits reviewed:** 5a5e161..8b52c8a (3 commits)

---

## Overall Assessment

The attractor largely followed the spec honestly. Files were moved using git renames (not copy+delete), all 5 symlinks are correct and resolve, REPO_ROOT detection was fixed in all 8 scripts, and most path references were updated. However, there are several incomplete updates, one CI-breaking issue, and a few undeclared changes that need scrutiny.

**Spec compliance: ~85%.** The core restructuring is done correctly, but several edge-case path references were missed and some undeclared changes were introduced.

---

## Findings

```
FINDING: CI integrity check will fail -- protected_dirs still includes 'scenarios' and 'scripts'
SEVERITY: CRITICAL
FILE: .github/workflows/ci.yaml
LINE: 98
EVIDENCE: The factory integrity check in ci.yaml has `protected_dirs = ['scenarios', 'scripts', 'agents', 'specs']`. On a holdout-stripped branch (which this IS -- scenarios were stripped before the attractor ran), `scenarios/` does not exist, and the `scripts/` directory no longer contains factory scripts. This check validates `Path(d).exists()` for each dir.
IMPACT: CI will fail on this branch because `scenarios/` does not exist. Even on a non-stripped branch, this check is conceptually stale -- the factory scripts now live under `packages/dark-factory/scripts/`, not `scripts/`. The check should reference the new protected locations.
FIX: Update `protected_dirs` to reflect the new structure. At minimum: remove 'scenarios' (it's a holdout dir, not always present), and either update 'scripts' to 'packages/dark-factory/scripts' or add the packages paths alongside. Also consider adding 'packages/dark-factory' and 'packages/review-prompts' to the protected list.
```

```
FINDING: Stale path reference in code_quality_standards.md -- still references .claude/skills/factory-orchestrate/SKILL.md
SEVERITY: WARNING
FILE: packages/dark-factory/docs/code_quality_standards.md
LINE: 84
EVIDENCE: Line 84 reads: "See `.claude/skills/factory-orchestrate/SKILL.md` Step 4 for agent team composition." The SKILL.md file now lives at `packages/dark-factory/SKILL.md`. The symlink at `.claude/skills/factory-orchestrate/` does resolve, so it's not broken -- but it references the old canonical path rather than the new one.
IMPACT: Confusing for future readers/agents. The reference works via symlink but misleads about where the file actually lives.
FIX: Change to `See packages/dark-factory/SKILL.md Step 4 for agent team composition.` or `See SKILL.md Step 4 for agent team composition.` (relative, since it's in the same package).
```

```
FINDING: Stale path references in dark_factory.md -- two locations
SEVERITY: WARNING
FILE: packages/dark-factory/docs/dark_factory.md
LINE: 16, 19, 278, 282
EVIDENCE:
  - Line 16: `factory-orchestrate/SKILL.md Step 4` -- ambiguous relative path, should be `packages/dark-factory/SKILL.md` or just `SKILL.md` (relative to the package).
  - Line 19: `docs/code_quality_standards.md` -- this file moved to `packages/dark-factory/docs/code_quality_standards.md`. The reference should be `code_quality_standards.md` (sibling in same directory) or the full path.
  - Line 278: `/prompts/factory_fix.md` -- missing the package prefix. Should be `/packages/dark-factory/prompts/factory_fix.md`.
  - Line 282: `/docs/code_quality_standards.md` -- this file no longer lives at the repo root `docs/` path. It moved to `packages/dark-factory/docs/code_quality_standards.md`.
IMPACT: Users or agents following these references will look in the wrong place for the files.
FIX: Update all four references to use the correct paths.
```

```
FINDING: Stale path in factory_architecture.html (interactive diagram)
SEVERITY: WARNING
FILE: docs/factory_architecture.html
LINE: 415, 435, 445
EVIDENCE: The JavaScript architecture diagram data still references:
  - `.github/codex/prompts/factory_fix.md` (line 415, 435) -- should be `packages/dark-factory/prompts/factory_fix.md`
  - `.claude/skills/factory-orchestrate/review-prompts/ (tier 2 agent docs)` (line 445) -- should be `packages/review-prompts/`
IMPACT: The interactive architecture diagram shows stale file paths. Anyone viewing the diagram gets incorrect information about where factory files live.
FIX: Update the JavaScript data in factory_architecture.html to use the new package paths. The spec's Section 6 did not explicitly list factory_architecture.html as needing updates, but the spec's verification checklist item 7 says "no stale references" should match paths under packages/.
```

```
FINDING: Undeclared change -- ci.yaml push trigger now restricted to [main] only
SEVERITY: WARNING
FILE: .github/workflows/ci.yaml
LINE: 5
EVIDENCE: The diff adds `branches: [main]` to the push trigger. Previously, CI ran on push to ANY branch. Now it only runs on push to main. The spec section 6.2 only specified updating ruff/mypy paths, protected_files list, and check_test_quality path. Restricting the push trigger was NOT in the spec.
IMPACT: CI will no longer run automatically on push to feature branches, `factory/**`, or `df-crank-**` branches. PRs will still trigger CI (via the `pull_request:` trigger), but direct pushes to non-main branches will not. This is a significant behavior change that could mask broken code.
FIX: Either revert the `branches: [main]` addition (if unintentional), or explicitly document why this change was made. Given that the factory workflow has its own triggers for `factory/**` and `df-crank-**`, this might be intentional to reduce CI noise, but it was not in the spec and should be a conscious decision.
```

```
FINDING: Undeclared change -- publish-subtrees.yml workflow added
SEVERITY: NIT
FILE: .github/workflows/publish-subtrees.yml
LINE: 1-88
EVIDENCE: A new workflow was added that publishes subtrees to standalone repos using `git subtree split` and SSH deploy keys. This was NOT in the spec. The spec focused on restructuring, not on subtree publishing.
IMPACT: Low immediate impact since it requires deploy key secrets to function. However, it's an undeclared addition that introduces new CI infrastructure without spec authorization.
FIX: This is reasonable prep work for the "extraction path" mentioned in the spec's goals, but it should be flagged as an undeclared addition. The team lead should decide if this ships with this crank or gets deferred.
```

```
FINDING: Undeclared changes -- README.md and CONTRIBUTING.md files added to both packages
SEVERITY: NIT
FILE: packages/dark-factory/README.md, packages/dark-factory/CONTRIBUTING.md, packages/pr-review-pack/README.md, packages/pr-review-pack/CONTRIBUTING.md
LINE: (new files)
EVIDENCE: Four documentation files were created that are NOT in the spec's target structure. The spec shows the exact file tree (Section: Target Structure) and these files are not listed.
IMPACT: Minimal -- these are reasonable additions for standalone packages. However, they are undeclared deviations from the spec.
FIX: Accept as reasonable, but note that the attractor added scope beyond what was specified.
```

```
FINDING: generate_diff_data.py lost executable permission during move
SEVERITY: NIT
FILE: packages/pr-review-pack/scripts/generate_diff_data.py
LINE: N/A
EVIDENCE: The diff shows `old mode 100755, new mode 100644`. The file was executable before the move and is now non-executable.
IMPACT: If anyone runs this script directly (e.g., `./generate_diff_data.py`), it won't work. The `python scripts/generate_diff_data.py` invocation still works.
FIX: Restore the executable permission: `chmod +x packages/pr-review-pack/scripts/generate_diff_data.py`.
```

```
FINDING: datetime.UTC removed from run_gate0.py import
SEVERITY: NIT
FILE: packages/dark-factory/scripts/run_gate0.py
LINE: 33
EVIDENCE: Changed from `from datetime import UTC, datetime` and `datetime.now(UTC)` to `from datetime import datetime` and `datetime.now().astimezone()`. UTC was available since Python 3.11. The new code produces local timezone timestamps instead of UTC.
IMPACT: Timestamps in gate0_results.json will now be in local timezone instead of UTC. This is a subtle behavior change. On CI (UTC-0), no difference. On developer machines, timestamps will differ from previous behavior.
FIX: If UTC was intentional, restore `from datetime import UTC, datetime` and `datetime.now(UTC).isoformat()`. If local timezone is preferred, accept but document the change.
```

```
FINDING: .github/codex/ directory entirely removed instead of just emptied
SEVERITY: NIT
FILE: .github/codex/
LINE: N/A
EVIDENCE: The spec says `.github/codex/prompts/` should be "EMPTIED (factory_fix.md moved to packages/)". But the entire `.github/codex/` directory tree was removed, not emptied. The spec also says to delete `.github/codex/prompts/adversarial_review.md`.
IMPACT: Minimal -- empty directories in git are not preserved anyway. The spec's "EMPTIED" instruction was for the prompts subdirectory, and since both files in that directory were either moved or deleted, removing the parent directory is the natural git outcome.
FIX: No action needed. This is the correct behavior -- git doesn't track empty directories.
```

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| WARNING  | 4 |
| NIT      | 4 |

### Spec Compliance Assessment

**What was done correctly:**
- All 8 factory scripts moved to `packages/dark-factory/scripts/` via git renames (not copy)
- All PR review pack files moved to `packages/pr-review-pack/` via git renames
- All 4 review prompts moved to shared `packages/review-prompts/`
- All 5 symlinks created and resolving correctly
- REPO_ROOT detection fixed in all 8 scripts with `_get_repo_root()` function
- Subprocess calls in `run_gate0.py` updated to use `SCRIPT_DIR` relative paths
- License changed from MIT to Apache 2.0 with full text
- NOTICE file created at root and in both packages
- Zone registry example created
- Bug fix: `strip_holdout.py` uses glob patterns for review pack artifacts (Spec 9.1)
- Bug fix: `persist_decisions.py` auto-detects JSON before HTML fallback (Spec 9.2)
- Most path references updated across Makefile, pyproject.toml, CLAUDE.md, ProjectLeadAsks.md, etc.
- Test files updated with correct SCRIPTS_DIR path

**What was missed or incomplete:**
- CI integrity check in ci.yaml still references `scenarios` and `scripts` as protected dirs (CRITICAL -- will break CI)
- Several stale path references in dark_factory.md and code_quality_standards.md (WARNINGs)
- factory_architecture.html still has old paths (WARNING)
- ci.yaml push trigger behavior changed without spec authorization (WARNING)

**Undeclared additions (beyond spec scope):**
- `publish-subtrees.yml` workflow (subtree publishing)
- README.md and CONTRIBUTING.md for both packages
- These are reasonable but were not specified
