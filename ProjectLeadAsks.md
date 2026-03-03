# Project Lead Asks

Items requiring the project lead's input or decision.

## Open

### 1. Satisfaction Threshold
**Status:** Decision needed before first factory crank
**Priority:** Pre-first-crank

**Default:** 80% (10/12 scenarios passing to declare convergence)

Is 80% the right starting point? Can be adjusted per workflow_dispatch run. Lower thresholds converge faster but accept more broken scenarios.

### 2. Token Budget
**Status:** Non-blocking (current defaults are reasonable)
**Priority:** Post-first-crank optimization

Codex context window determines how much the agent can read per iteration. Long feedback files + all specs could get expensive. Consider:
- Capping feedback to last 2 iterations
- Summarizing older feedback more aggressively

### 3. Factory Control Plane
**Status:** Design phase
**Priority:** Post-first-crank

The factory has multiple dimensions requiring centralized control:

| Dimension | Examples | Current State |
|-----------|----------|---------------|
| Models | Attractor model (codex-mini-latest), LLM-as-judge model | Hardcoded |
| Gate configs | Satisfaction threshold, NFR severity levels, timeout limits | Scattered in scripts |
| Iteration limits | Max iterations per crank, stall detection threshold | In workflow yaml |
| Branch policies | Naming conventions, auto-cleanup rules | In skill docs |
| Cost tracking | Token consumption per worker, per iteration | Not implemented |

**Desired capabilities:**
- Dashboard showing all factory dimensions with current settings
- Token consumption per worker, per iteration, per time window (day/week)
- Ability for the human operator to swap models per worker (e.g., switch attractor from codex-mini to gpt-5)
- Gate configuration tuning without code changes
- Cost tracking and budget alerts
- Latency metrics per worker per iteration

**Implementation options:**
1. **Streamlit page** — extend the existing dashboard with a "Control Plane" tab
2. **Config file** — `configs/factory_control.yaml` mapping all dimensions, read by all components
3. **Hybrid** — config file for settings, dashboard for visibility and tuning

**Decision needed:** When to build, and how much observability is worth the infrastructure cost.

## Roadmap

### Pre-First-Crank (do before triggering the factory)
1. ✅ factory/v1 branch created and pushed (factory infra + Codex code merged)
2. ✅ Validation guidelines consolidated into attractor prompt
3. ✅ agents/dev_team collected as factory-side reference assets
4. ✅ Holdout isolation via branch stripping (`packages/dark-factory/scripts/strip_holdout.py`, `packages/dark-factory/scripts/restore_holdout.py`)
5. ✅ Gate 2 NFR framework implemented (`packages/dark-factory/scripts/nfr_checks.py` — code quality, complexity, dead code, security)
6. ✅ Factory orchestration skill created (`.claude/skills/factory-orchestrate/SKILL.md`)
7. ✅ Code quality standards codified (`docs/code_quality_standards.md`, linked from CLAUDE.md)
8. ✅ Claude Code as orchestrator — replaces CI-only loop, browser automation for Codex
9. 🔧 Satisfaction dashboard — visibility into scenario pass rates and convergence trajectory
10. 🔧 Accept/merge gate — human interaction point for promoting factory output
11. ⏳ Satisfaction threshold confirmed (#1 above)

### Post-First-Crank (improve after first successful iteration)
1. LLM-as-judge — holistic evaluation beyond satisfaction score (built into orchestration skill)
2. Factory extraction to separate repo/package (see Phase 2 below)
3. Token budget optimization (#2 above)
4. Additional NFR checks — duplication, import hygiene, coverage, maintainability, reliability
5. Factory control plane — see #3 above

### Resolved: Phase 2: Factory Extraction
**Status:** Planned after first successful convergence run

The factory infrastructure is designed for extraction into its own repo (and eventually a reusable package). The separation is already native:

**Factory-generic code** (extractable as-is):
- `packages/dark-factory/scripts/run_scenarios.py` — reads any `/scenarios/*.md`, zero project-specific logic
- `packages/dark-factory/scripts/compile_feedback.py` — reads any `scenario_results.json`, zero project-specific logic
- `.github/workflows/factory.yaml` — parameterized via `workflow_dispatch` inputs
- `packages/dark-factory/prompts/factory_fix.md` — generic fix template, refs `/specs/` and `/scenarios/`
- `packages/dark-factory/docs/dark_factory.md` — generic operating manual

**Project-specific content** (stays in product repo):
- `/specs/*.md` — MiniPong-specific requirements
- `/scenarios/*.md` — MiniPong-specific holdout evaluations
- `CLAUDE.md` — MiniPong-specific context
- Makefile factory targets — thin wrappers calling scripts

**Extraction path (when ready):**
1. **Fork mode:** Move factory scripts + workflow to `joeyfezster/dark-factory`. Product repo's workflow calls factory repo via [reusable workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows) or checks it out as a step.
2. **Package mode:** Publish factory as a pip-installable CLI (`pip install dark-factory`). Product repo runs `dark-factory run-scenarios` instead of `python packages/dark-factory/scripts/run_scenarios.py`. Workflow becomes a thin shell.

**Decision point:** After the first successful convergence, evaluate whether to extract immediately or after a second project validates the pattern.

## Resolved

### ✅ Codex Branch Strategy
**Resolved:** factory/v1 branch created from main, merged with Codex branch. Factory runs on `factory/*` and `df-crank-**` branches.

### ✅ Codex Billing / API Key
**Resolved:** No separate API key needed. Claude Code orchestrates via browser automation using Joey's existing ChatGPT Plus login (Chrome already authenticated). The billing "hack" is isolated in the orchestration skill's Codex invocation step — all other factory infrastructure (stripping, validation, feedback, PR creation) works identically regardless of how Codex is invoked. If/when an API key becomes available, only that one step changes.

### ✅ Scenario Isolation Architecture
**Resolved:** Branch stripping replaces the `/tmp/` filesystem shuffle. Deterministic scripts (`packages/dark-factory/scripts/strip_holdout.py` and `packages/dark-factory/scripts/restore_holdout.py`) remove and restore `/scenarios/` from the branch Codex works on. Scenarios literally don't exist on the attractor's branch — not hidden, not shuffled, physically absent. The strip script commits with marker `[factory:holdout-stripped]` and verifies no scenario files remain.

### ✅ Validation Guidelines in Attractor
**Resolved:** DoD, hard constraints, and quality checklist from agents/dev_team consolidated into `packages/dark-factory/prompts/factory_fix.md`. Reduces iterations by giving Codex upfront quality expectations.
