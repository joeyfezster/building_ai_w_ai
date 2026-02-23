# Project Lead Asks

Items requiring the project lead's input or decision.

## Open

### 1. OpenAI API Key for Codex in GitHub Actions
**Status:** Blocking for production factory runs (not blocking for local testing)

The factory workflow needs `OPENAI_API_KEY` as a GitHub Actions secret. ChatGPT Plus ($20/mo) subscription does NOT bridge to the API — they're separate billing systems.

**Action needed:**
- Check platform.openai.com for included API credits with your Plus account
- If none: add payment method on platform side (pay-as-you-go)
- Generate API key at platform.openai.com/api-keys
- Store it: `gh secret set OPENAI_API_KEY --repo joeyfezster/building_ai_w_ai`

**Cost estimate:** ~$1-5 per factory iteration depending on context size.

### 2. Satisfaction Threshold
**Default:** 80% (8/10 scenarios passing to declare convergence)

Is 80% the right starting point? Can be adjusted per workflow_dispatch run. Lower thresholds converge faster but accept more broken scenarios.

### 3. Codex Branch Strategy
**Current assumption:** Factory runs on `factory/*` branches created from the Codex seed branch.

To kick off the first factory run:
1. Merge the factory infrastructure into the Codex branch (or create a new branch combining both)
2. Push to `factory/v1`
3. Trigger the workflow

### 4. Token Budget
Codex context window determines how much the agent can read per iteration. Long feedback files + all specs could get expensive. Consider:
- Capping feedback to last 2 iterations
- Summarizing older feedback more aggressively

### 5. Factory Extraction — Phase 2
**Status:** Planned after first successful convergence run

The factory infrastructure is designed for extraction into its own repo (and eventually a reusable package). The separation is already native:

**Factory-generic code** (extractable as-is):
- `scripts/run_scenarios.py` — reads any `/scenarios/*.md`, zero project-specific logic
- `scripts/compile_feedback.py` — reads any `scenario_results.json`, zero project-specific logic
- `.github/workflows/factory.yaml` — parameterized via `workflow_dispatch` inputs
- `.github/codex/prompts/factory_fix.md` — generic fix template, refs `/specs/` and `/scenarios/`
- `docs/dark_factory.md` — generic operating manual

**Project-specific content** (stays in product repo):
- `/specs/*.md` — MiniPong-specific requirements
- `/scenarios/*.md` — MiniPong-specific holdout evaluations
- `CLAUDE.md` — MiniPong-specific context
- Makefile factory targets — thin wrappers calling scripts

**Extraction path (when ready):**
1. **Fork mode:** Move factory scripts + workflow to `joeyfezster/dark-factory`. Product repo's workflow calls factory repo via [reusable workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows) or checks it out as a step.
2. **Package mode:** Publish factory as a pip-installable CLI (`pip install dark-factory`). Product repo runs `dark-factory run-scenarios` instead of `python scripts/run_scenarios.py`. Workflow becomes a thin shell.

**What makes extraction easy today:**
- Scripts discover paths relative to repo root — no hardcoded project names
- Scenario format is a markdown convention, not code — any project can write them
- Feedback compiler is input-format-driven, not project-aware
- The workflow is already parameterized (max_iterations, satisfaction_threshold, target_branch)

**Decision point:** After the first successful convergence, evaluate whether to extract immediately or after a second project validates the pattern.

## Resolved

(none yet)
