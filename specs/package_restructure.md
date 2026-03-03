# Spec: Isolate PR Review Pack & Dark Factory as Reusable Packages

## Override: Infrastructure Restructuring Permissions

**This spec is an infrastructure restructuring task, NOT a product code fix.**

The following overrides apply to the constraints in `factory_fix.md` for THIS ITERATION ONLY:

- You MUST create new directories under `packages/`
- You MUST move files from `scripts/`, `.claude/skills/`, `.github/`, `docs/` INTO `packages/`
- You MUST update `CLAUDE.md`, `Makefile`, `pyproject.toml`, `.github/workflows/ci.yaml` with new paths
- You MUST create symlinks (use Python `os.symlink()` or shell `ln -s`)
- You MUST delete the old copies of moved files
- You MUST update `factory_fix.md` itself (the protected-files list needs new paths)

All other constraints remain in effect: anti-gaming rules, quality checklist, `make lint && make typecheck`.

**Primary task:** Execute this entire spec. Read it top to bottom. Every section is actionable.

**IMPORTANT:** The other specs in `/specs/` (`system.md`, `env.md`, `rl.md`, `training.md`, `dashboard.md`, `proof.md`, `pong_interfaces.md`, `full_training.md`) are BACKLOG product specs — they describe the MiniPong RL product, NOT this restructuring task. Do NOT modify product code (`src/`, `tests/`, `configs/`) unless a path reference update from this spec requires it. Your ONLY task is the infrastructure restructuring described in THIS spec.

---

## Goal

Restructure into a monorepo with two extractable packages (`packages/pr-review-pack/` and `packages/dark-factory/`) plus a shared `packages/review-prompts/` directory. The monorepo continues working with direct path references (no backward-compatibility symlinks). Only platform-required symlinks are created.

---

## Target Structure (Full Repo Tree After Restructuring)

```
building_ai_w_ai/
+-- .claude/
|   +-- skills/
|   |   +-- pr-review-pack -> ../../packages/pr-review-pack           # symlink
|   |   +-- factory-orchestrate -> ../../packages/dark-factory         # symlink
|   +-- zone-registry.yaml          # stays here (product-specific)
|   +-- settings.local.json
|   +-- launch.json
|
+-- packages/
|   +-- review-prompts/                        # SHARED by both packages
|   |   +-- code_health_review.md
|   |   +-- security_review.md
|   |   +-- test_integrity_review.md
|   |   +-- adversarial_review.md
|   |
|   +-- pr-review-pack/                        # subtree-extractable
|   |   +-- SKILL.md
|   |   +-- assets/
|   |   |   +-- template.html
|   |   +-- scripts/
|   |   |   +-- generate_diff_data.py
|   |   |   +-- render_review_pack.py
|   |   |   +-- scaffold_review_pack_data.py
|   |   +-- references/
|   |   |   +-- build-spec.md
|   |   |   +-- data-schema.md
|   |   |   +-- section-guide.md
|   |   |   +-- css-design-system.md
|   |   |   +-- validation-checklist.md
|   |   +-- review-prompts -> ../review-prompts  # symlink to shared
|   |   +-- examples/
|   |       +-- zone-registry.example.yaml
|   |
|   +-- dark-factory/                          # subtree-extractable
|       +-- SKILL.md                           # factory-orchestrate entry point
|       +-- scripts/
|       |   +-- run_gate0.py
|       |   +-- nfr_checks.py
|       |   +-- check_test_quality.py
|       |   +-- run_scenarios.py
|       |   +-- compile_feedback.py
|       |   +-- strip_holdout.py
|       |   +-- restore_holdout.py
|       |   +-- persist_decisions.py
|       +-- prompts/
|       |   +-- factory_fix.md
|       +-- workflows/
|       |   +-- factory.yaml
|       +-- review-prompts -> ../review-prompts  # symlink to shared
|       +-- docs/
|           +-- dark_factory.md
|           +-- code_quality_standards.md
|
+-- .github/
|   +-- workflows/
|   |   +-- ci.yaml                            # product CI (paths updated)
|   |   +-- factory.yaml -> ../../packages/dark-factory/workflows/factory.yaml  # symlink
|   +-- codex/prompts/                         # EMPTIED (factory_fix.md moved to packages/)
|
+-- src/                    # product code (UNCHANGED)
+-- tests/                  # product tests (2 files get path updates)
+-- configs/                # product configs (UNCHANGED)
+-- specs/                  # product specs (UNCHANGED)
+-- scenarios/              # holdout scenarios (UNCHANGED)
+-- scripts/                # product-only scripts (factory scripts REMOVED)
|   +-- acquire_whitepapers.py
|   +-- verify_whitepapers.py
|   +-- package_artifacts.py
|   +-- create_postmerge_issues.py
+-- docs/                   # product docs (factory docs REMOVED from here)
|   +-- decisions/decision_log.json
|   +-- factory_validation_strategy.md
|   +-- [other product docs stay]
+-- agents/                 # reference only (UNCHANGED)
+-- infra/                  # Docker + SkyPilot (UNCHANGED)
+-- CLAUDE.md               # UPDATED paths
+-- Makefile                # UPDATED paths
+-- ProjectLeadAsks.md      # UPDATED paths
+-- pyproject.toml          # UPDATED paths
+-- LICENSE                 # Apache 2.0 (REPLACED from MIT)
+-- NOTICE                  # NEW
```

---

## Symlinks (Platform-Required Only -- 5 Total)

| # | Symlink Path | Target | Reason |
|---|-------------|--------|--------|
| 1 | `.claude/skills/pr-review-pack` | `../../packages/pr-review-pack` | Claude Code discovers skills at `.claude/skills/` |
| 2 | `.claude/skills/factory-orchestrate` | `../../packages/dark-factory` | Claude Code discovers skills at `.claude/skills/` |
| 3 | `.github/workflows/factory.yaml` | `../../packages/dark-factory/workflows/factory.yaml` | GitHub Actions discovers workflows at `.github/workflows/` |
| 4 | `packages/pr-review-pack/review-prompts` | `../review-prompts` | Shared review prompts |
| 5 | `packages/dark-factory/review-prompts` | `../review-prompts` | Shared review prompts |

To create symlinks in Python:
```python
import os
os.symlink("../../packages/pr-review-pack", ".claude/skills/pr-review-pack")
```

Or in shell: `ln -s ../../packages/pr-review-pack .claude/skills/pr-review-pack`

**IMPORTANT:** Before creating symlinks 1 and 2, you must first remove the existing directories at `.claude/skills/pr-review-pack/` and `.claude/skills/factory-orchestrate/` (they contain real files that are being moved to `packages/`). The old directories must be gone before the symlinks can be created.

---

## Step 1: Create Package Directories

```bash
mkdir -p packages/review-prompts
mkdir -p packages/pr-review-pack/{assets,scripts,references,examples}
mkdir -p packages/dark-factory/{scripts,prompts,workflows,docs}
```

---

## Step 2: Move Files

### Review prompts to shared location

Move these 4 files from `.claude/skills/factory-orchestrate/review-prompts/` to `packages/review-prompts/`:
- `code_health_review.md`
- `security_review.md`
- `test_integrity_review.md`
- `adversarial_review.md`

### PR Review Pack files

Move from `.claude/skills/pr-review-pack/` to `packages/pr-review-pack/`:
- `SKILL.md` -> `packages/pr-review-pack/SKILL.md`
- `assets/template.html` -> `packages/pr-review-pack/assets/template.html`
- `scripts/generate_diff_data.py` -> `packages/pr-review-pack/scripts/generate_diff_data.py`
- `scripts/render_review_pack.py` -> `packages/pr-review-pack/scripts/render_review_pack.py`
- `scripts/scaffold_review_pack_data.py` -> `packages/pr-review-pack/scripts/scaffold_review_pack_data.py`
- `references/build-spec.md` -> `packages/pr-review-pack/references/build-spec.md`
- `references/data-schema.md` -> `packages/pr-review-pack/references/data-schema.md`
- `references/section-guide.md` -> `packages/pr-review-pack/references/section-guide.md`
- `references/css-design-system.md` -> `packages/pr-review-pack/references/css-design-system.md`
- `references/validation-checklist.md` -> `packages/pr-review-pack/references/validation-checklist.md`

### Dark Factory files

Move to `packages/dark-factory/`:
- `.claude/skills/factory-orchestrate/SKILL.md` -> `packages/dark-factory/SKILL.md`
- `scripts/run_gate0.py` -> `packages/dark-factory/scripts/run_gate0.py`
- `scripts/nfr_checks.py` -> `packages/dark-factory/scripts/nfr_checks.py`
- `scripts/check_test_quality.py` -> `packages/dark-factory/scripts/check_test_quality.py`
- `scripts/run_scenarios.py` -> `packages/dark-factory/scripts/run_scenarios.py`
- `scripts/compile_feedback.py` -> `packages/dark-factory/scripts/compile_feedback.py`
- `scripts/strip_holdout.py` -> `packages/dark-factory/scripts/strip_holdout.py`
- `scripts/restore_holdout.py` -> `packages/dark-factory/scripts/restore_holdout.py`
- `scripts/persist_decisions.py` -> `packages/dark-factory/scripts/persist_decisions.py`
- `.github/codex/prompts/factory_fix.md` -> `packages/dark-factory/prompts/factory_fix.md`
- `.github/workflows/factory.yaml` -> `packages/dark-factory/workflows/factory.yaml`
- `docs/dark_factory.md` -> `packages/dark-factory/docs/dark_factory.md`
- `docs/code_quality_standards.md` -> `packages/dark-factory/docs/code_quality_standards.md`

### Delete superseded file

Delete `.github/codex/prompts/adversarial_review.md` (superseded by `packages/review-prompts/adversarial_review.md`).

### DO NOT move (product-specific, stays in place)

- `scripts/acquire_whitepapers.py`
- `scripts/verify_whitepapers.py`
- `scripts/package_artifacts.py`
- `scripts/create_postmerge_issues.py`
- `.github/workflows/ci.yaml`

---

## Step 3: Create Symlinks

After all files are moved and old directories are removed, create the 5 symlinks listed in the table above.

---

## Step 4: Fix REPO_ROOT Detection in All Factory Scripts

8 factory scripts use `Path(__file__).resolve().parent.parent` to find the repo root. This breaks at the new depth (`packages/dark-factory/scripts/` is 4 levels deep, not 2).

**Replace** the `REPO_ROOT = Path(__file__).resolve().parent.parent` pattern in each file with:

```python
def _get_repo_root() -> Path:
    """Walk up from this file to find the git repo root."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError("Repo root not found -- no .git directory in any parent")

REPO_ROOT = _get_repo_root()
```

Files requiring this fix (search for `Path(__file__).resolve().parent.parent` and replace):
1. `packages/dark-factory/scripts/run_gate0.py` (was line 36)
2. `packages/dark-factory/scripts/nfr_checks.py` (was line 410)
3. `packages/dark-factory/scripts/check_test_quality.py` (was line 215)
4. `packages/dark-factory/scripts/run_scenarios.py` (was line 237)
5. `packages/dark-factory/scripts/compile_feedback.py` (was line 300)
6. `packages/dark-factory/scripts/strip_holdout.py` (was line 201)
7. `packages/dark-factory/scripts/restore_holdout.py` (was line 177)
8. `packages/dark-factory/scripts/persist_decisions.py` (was line 22)

**DO NOT change** these (they stay at their current depth or use a different pattern):
- `scripts/create_postmerge_issues.py` -- product script, stays at `scripts/`, depth unchanged
- `docs/generate_diff_data.py` -- product script
- `packages/pr-review-pack/scripts/render_review_pack.py` -- uses `Path(__file__).parent.parent / "assets"` which resolves correctly since the template moves WITH the script

---

## Step 5: Fix Subprocess Calls in run_gate0.py

`run_gate0.py` invokes `nfr_checks.py` and `check_test_quality.py` via subprocess. After the move, all three are siblings in the same directory. Use `__file__`-relative paths:

**Change** the CHECKS list entries from:
```python
[sys.executable, "scripts/nfr_checks.py", "--check", "code_quality", "--json"]
```
To:
```python
SCRIPT_DIR = Path(__file__).resolve().parent
# ...
[sys.executable, str(SCRIPT_DIR / "nfr_checks.py"), "--check", "code_quality", "--json"]
```

Apply to ALL 5 entries in the CHECKS list (4 nfr_checks.py calls + 1 check_test_quality.py call).

Keep `cwd=str(REPO_ROOT)` -- the tools still need repo root to find source files.

---

## Step 6: Update All Path References

Every file referencing a moved path must be updated. No symlinks for backward compatibility -- direct path updates only.

### 6.1 Makefile

| Old | New |
|-----|-----|
| `python scripts/run_scenarios.py` | `python packages/dark-factory/scripts/run_scenarios.py` |
| `python scripts/compile_feedback.py` | `python packages/dark-factory/scripts/compile_feedback.py` |
| `python scripts/nfr_checks.py --output artifacts/factory/nfr_results.json` | `python packages/dark-factory/scripts/nfr_checks.py --output artifacts/factory/nfr_results.json` |
| `python scripts/nfr_checks.py` (second call, no flags) | `python packages/dark-factory/scripts/nfr_checks.py` |
| `python scripts/run_scenarios.py --timeout 180` | `python packages/dark-factory/scripts/run_scenarios.py --timeout 180` |
| `python scripts/compile_feedback.py` (in factory-local) | `python packages/dark-factory/scripts/compile_feedback.py` |
| `python scripts/persist_decisions.py --pr $(PR)` | `python packages/dark-factory/scripts/persist_decisions.py --pr $(PR)` |

### 6.2 .github/workflows/ci.yaml

| Old | New |
|-----|-----|
| `ruff check scripts/run_scenarios.py scripts/compile_feedback.py` | `ruff check packages/dark-factory/scripts/run_scenarios.py packages/dark-factory/scripts/compile_feedback.py` |
| `mypy scripts/run_scenarios.py scripts/compile_feedback.py --ignore-missing-imports` | `mypy packages/dark-factory/scripts/run_scenarios.py packages/dark-factory/scripts/compile_feedback.py --ignore-missing-imports` |
| `'.github/codex/prompts/factory_fix.md'` (in protected_files list, inline Python) | `'packages/dark-factory/prompts/factory_fix.md'` |
| `python scripts/check_test_quality.py` | `python packages/dark-factory/scripts/check_test_quality.py` |

### 6.3 packages/dark-factory/workflows/factory.yaml (the workflow file itself, after move)

| Old | New |
|-----|-----|
| `python scripts/run_scenarios.py --timeout 180` (appears twice) | `python packages/dark-factory/scripts/run_scenarios.py --timeout 180` |
| `python scripts/compile_feedback.py --iteration $ITER` | `python packages/dark-factory/scripts/compile_feedback.py --iteration $ITER` |
| `Read .github/codex/prompts/factory_fix.md` | `Read packages/dark-factory/prompts/factory_fix.md` |

### 6.4 packages/dark-factory/scripts/strip_holdout.py (after move)

| Old | New |
|-----|-----|
| `"Restore with: python scripts/restore_holdout.py"` | `"Restore with: python packages/dark-factory/scripts/restore_holdout.py"` |

### 6.5 packages/pr-review-pack/scripts/scaffold_review_pack_data.py (after move)

| Old | New |
|-----|-----|
| `"Run: python scripts/run_gate0.py"` (user-facing error message) | `"Run: python packages/dark-factory/scripts/run_gate0.py"` |

### 6.6 pyproject.toml

| Old | New |
|-----|-----|
| `"scripts/run_scenarios.py" = []` (ruff per-file-ignores) | `"packages/dark-factory/scripts/run_scenarios.py" = []` |
| `"scripts/compile_feedback.py" = []` | `"packages/dark-factory/scripts/compile_feedback.py" = []` |

### 6.7 tests/test_factory_run_scenarios.py

| Old | New |
|-----|-----|
| `sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))` | `sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "dark-factory" / "scripts"))` |

### 6.8 tests/test_factory_compile_feedback.py

Same change as 6.7.

### 6.9 scripts/create_postmerge_issues.py

| Old | New |
|-----|-----|
| `"code_refs": ["scripts/nfr_checks.py:187"]` | `"code_refs": ["packages/dark-factory/scripts/nfr_checks.py:187"]` |

### 6.10 CLAUDE.md (extensive updates)

Update the Factory-Protected Files list. Every path starting with `/scripts/` that refers to a factory script changes to `/packages/dark-factory/scripts/`. Specific changes:

| Old | New |
|-----|-----|
| `/scripts/run_scenarios.py` | `/packages/dark-factory/scripts/run_scenarios.py` |
| `/scripts/compile_feedback.py` | `/packages/dark-factory/scripts/compile_feedback.py` |
| `/.github/workflows/factory.yaml` | stays (symlink still at this path) |
| `/.github/codex/prompts/factory_fix.md` | `/packages/dark-factory/prompts/factory_fix.md` |
| `/scripts/strip_holdout.py` | `/packages/dark-factory/scripts/strip_holdout.py` |
| `/scripts/restore_holdout.py` | `/packages/dark-factory/scripts/restore_holdout.py` |
| `/scripts/nfr_checks.py` | `/packages/dark-factory/scripts/nfr_checks.py` |
| `/scripts/check_test_quality.py` | `/packages/dark-factory/scripts/check_test_quality.py` |
| `/.claude/skills/factory-orchestrate/review-prompts/` | `/packages/review-prompts/` |
| `/docs/code_quality_standards.md` | `/packages/dark-factory/docs/code_quality_standards.md` |
| `/scripts/persist_decisions.py` | `/packages/dark-factory/scripts/persist_decisions.py` |
| `docs/code_quality_standards.md` (in Code Quality Standards section) | `packages/dark-factory/docs/code_quality_standards.md` |
| `.github/codex/prompts/adversarial_review.md` | REMOVE this line (file deleted) |

Also fix the stale Gate 0 description. Replace:
> "Gate 0 MUST use agent teams. Use TeamCreate to spawn all 6 Gate 0 agents (5 tool agents + 1 adversarial reviewer)"

With:
> "Gate 0 has two tiers. Tier 1: run `packages/dark-factory/scripts/run_gate0.py` (5 deterministic tool checks in parallel). Tier 2: spawn 4 LLM review agents via Agent Teams (Code Health, Security, Test Integrity, Adversarial) -- each runs in its own context window."

Update the skill paths near the bottom:
| Old | New |
|-----|-----|
| `skill: /factory-orchestrate` | stays |
| `.claude/skills/pr-review-pack/` | `packages/pr-review-pack/` (accessible via `.claude/skills/pr-review-pack` symlink) |

### 6.11 packages/dark-factory/SKILL.md (factory-orchestrate, after move)

All script references should use paths relative to the SKILL.md location. Add a "Script Discovery" section near the top:

```markdown
## Script Discovery

All scripts referenced in this skill are in the `scripts/` directory adjacent to this SKILL.md.
From the monorepo root, these resolve to `packages/dark-factory/scripts/`.

Review prompts are in the `review-prompts/` directory adjacent to this SKILL.md (symlink to shared prompts).
```

Then update all `scripts/X.py` references to specify they are in `scripts/` relative to this file. For commands run from repo root, use full paths: `python packages/dark-factory/scripts/run_gate0.py`.

Update:
- Review-prompts reference: `review-prompts/` (adjacent via symlink)
- `.github/codex/prompts/factory_fix.md` -> `prompts/factory_fix.md` (adjacent)
- `docs/code_quality_standards.md` -> `docs/code_quality_standards.md` (adjacent)

### 6.12 packages/dark-factory/prompts/factory_fix.md (after move)

Update the protected-files list inside the file:
| Old | New |
|-----|-----|
| `/scripts/run_scenarios.py` | `/packages/dark-factory/scripts/run_scenarios.py` |
| `/scripts/compile_feedback.py` | `/packages/dark-factory/scripts/compile_feedback.py` |
| `/.github/workflows/factory.yaml` | stays (symlink) |
| `/.github/codex/prompts/factory_fix.md (this file)` | `/packages/dark-factory/prompts/factory_fix.md (this file)` |
| `/scripts/strip_holdout.py` | `/packages/dark-factory/scripts/strip_holdout.py` |
| `/scripts/restore_holdout.py` | `/packages/dark-factory/scripts/restore_holdout.py` |
| `/scripts/nfr_checks.py` | `/packages/dark-factory/scripts/nfr_checks.py` |
| `/scripts/check_test_quality.py` | `/packages/dark-factory/scripts/check_test_quality.py` |
| `/scripts/persist_decisions.py` | `/packages/dark-factory/scripts/persist_decisions.py` |

Also update the "Read the component specifications" section to include `specs/package_restructure.md`.

### 6.13 docs/dark_factory.md (stays in place but references updated after factory docs move)

Wait -- this file MOVES to `packages/dark-factory/docs/dark_factory.md`. Update its internal references:
- All `scripts/X.py` -> `packages/dark-factory/scripts/X.py` (or relative: `../scripts/X.py`)
- `.claude/skills/factory-orchestrate/review-prompts/` -> `packages/review-prompts/`
- `.claude/skills/factory-orchestrate/` -> `packages/dark-factory/`
- `.claude/skills/pr-review-pack/` -> `packages/pr-review-pack/`

### 6.14 docs/factory_validation_strategy.md (stays in docs/)

Update all script paths and skill paths:
- All `scripts/X.py` -> `packages/dark-factory/scripts/X.py`
- `factory-orchestrate/SKILL.md` -> `packages/dark-factory/SKILL.md`
- `review-prompts/adversarial_review.md` -> `packages/review-prompts/adversarial_review.md`

### 6.15 ProjectLeadAsks.md

Update all script paths. Also move "Phase 2: Factory Extraction" to the Resolved section.

### 6.16 agents/README.md

| Old | New |
|-----|-----|
| `.github/codex/prompts/factory_fix.md` | `packages/dark-factory/prompts/factory_fix.md` |

### 6.17 packages/dark-factory/scripts/compile_feedback.py (after move)

| Old | New |
|-----|-----|
| `"or /.github/workflows/factory.yaml"` | `"or /packages/dark-factory/workflows/factory.yaml"` |

### 6.18 Self-referential docstrings in moved scripts

Update any `scripts/X.py` self-references in docstrings/usage comments in ALL 8 moved factory scripts. For example, `run_gate0.py`'s docstring says `Usage: python scripts/run_gate0.py` -- change to `Usage: python packages/dark-factory/scripts/run_gate0.py`.

---

## Step 7: License Change (MIT -> Apache 2.0)

### 7.1 Replace root LICENSE

Replace the entire content of `LICENSE` with the Apache License 2.0 full text. The Apache 2.0 full text starts with:

```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
```

### 7.2 Create root NOTICE

Create `NOTICE` with this content:

```
PR Review Pack & Dark Factory
Copyright 2026 Joel Baruch

Originally developed as part of the building_ai_w_ai project:
https://github.com/joeyfezster/building_ai_w_ai

Portions of this software were generated with AI coding agent assistance
(OpenAI Codex, Anthropic Claude). Human direction and acceptance decisions
were made by Joel Baruch.
```

### 7.3 Copy to packages

Copy `LICENSE` and `NOTICE` to:
- `packages/pr-review-pack/LICENSE` and `packages/pr-review-pack/NOTICE`
- `packages/dark-factory/LICENSE` and `packages/dark-factory/NOTICE`

---

## Step 8: Create Zone Registry Example

Create `packages/pr-review-pack/examples/zone-registry.example.yaml`:

```yaml
# Zone Registry Example
# Copy this to .claude/zone-registry.yaml and customize for your project.
# The review pack uses this to map files to architectural zones.

zones:
  source:
    paths: ["src/**"]
    specs: []
    category: product
    label: "Source"
    sublabel: "Application code"
  tests:
    paths: ["tests/**"]
    category: product
    label: "Tests"
    sublabel: "Test suite"
  config:
    paths: ["*.toml", "*.yaml", "Makefile", "requirements*"]
    category: infra
    label: "Config"
    sublabel: "Build and project configuration"
  docs:
    paths: ["docs/**", "*.md"]
    category: infra
    label: "Docs"
    sublabel: "Documentation"
  ci:
    paths: [".github/**"]
    category: infra
    label: "CI"
    sublabel: "Continuous integration"
```

---

## Step 9: Bug Fixes

### 9.1 strip_holdout.py -- Stale Filenames

In `packages/dark-factory/scripts/strip_holdout.py`, find any hardcoded reference to `docs/pr_review_pack.html` (without the `{N}` prefix) and replace with a glob pattern: `docs/pr*_review_pack.html`, `docs/pr*_diff_data.json`, `docs/pr*_review_pack.approval.json`.

### 9.2 persist_decisions.py -- Prefer JSON Input

In `packages/dark-factory/scripts/persist_decisions.py`, the script should auto-check for `/tmp/pr{N}_review_pack_data.json` (where N is the PR number) before falling back to HTML parsing. The `--data` flag already exists for JSON input -- make the auto-detection the default behavior.

---

## Verification Checklist

After all changes, verify:

1. `make lint` passes (ruff check)
2. `make typecheck` passes (mypy src)
3. `make test` passes (pytest)
4. All 5 symlinks resolve: `ls -la .claude/skills/pr-review-pack/SKILL.md`, etc.
5. `python packages/dark-factory/scripts/run_gate0.py --help` works
6. `python packages/dark-factory/scripts/run_scenarios.py --help` works
7. No stale references: `grep -r "scripts/run_scenarios\|scripts/compile_feedback\|scripts/nfr_checks\|scripts/check_test_quality\|scripts/run_gate0\|scripts/strip_holdout\|scripts/restore_holdout\|scripts/persist_decisions" --include='*.py' --include='*.yaml' --include='*.md' --include='Makefile' --include='*.toml' .` should only match paths under `packages/` or product-code references
8. LICENSE file contains "Apache License" text
9. NOTICE file exists
