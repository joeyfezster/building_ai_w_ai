# Project Lead Asks

Items requiring the project lead's input or decision.

## Open

### 1. OpenAI API Key for Codex in GitHub Actions
**Status:** Blocking for production factory runs (not blocking for local testing)
**Priority:** Pre-first-crank

ChatGPT Plus ($20/mo) **does include Codex** — CLI, web, IDE, cloud tasks. Plus subscribers also get **$5 in free API credits** for 30 days.

For the factory's GitHub Action (CI automation), usage is billed at standard API rates via `platform.openai.com`. The $5 free credits will cover several factory iterations (~$1-5 each depending on context size). After that, API billing is pay-as-you-go.

**Action needed:**
1. Sign in to Codex CLI with your ChatGPT account (this auto-generates an API key)
2. Or generate one manually at platform.openai.com/api-keys
3. Store it: `gh secret set OPENAI_API_KEY --repo joeyfezster/building_ai_w_ai`

### 2. Satisfaction Threshold
**Status:** Decision needed before first factory crank
**Priority:** Pre-first-crank

**Default:** 80% (10/12 scenarios passing to declare convergence)

Is 80% the right starting point? Can be adjusted per workflow_dispatch run. Lower thresholds converge faster but accept more broken scenarios.

### 3. Scenario Isolation Architecture
**Status:** Design decision needed
**Priority:** Pre-first-crank (awareness), post-first-crank (fix)

**Problem:** The current filesystem shuffle (`mv scenarios /tmp/`) does NOT provide real holdout isolation. Codex runs in the same job and can read `/tmp/factory_scenarios/`. The shuffle is a **prompt-level control only** — Codex is instructed not to look, but there's no enforcement.

**Why this matters:** The factory's entire anti-gaming architecture assumes Codex cannot see its own evaluation criteria. If it can, it could overfit to specific scenarios without implementing general behavior. The holdout is not a holdout.

**Options (in order of isolation strength):**
1. **Separate evaluation job** — Run Codex in job A, then run scenario evaluation in job B on a clean checkout. Scenarios are never on the same filesystem as Codex. (Recommended)
2. **Private scenario repo** — Store scenarios in a separate private repo. Evaluation job fetches them; Codex job never has access.
3. **Container isolation** — Run Codex in a Docker container with a mount that excludes `/tmp/factory_scenarios/`.
4. **Current approach** (prompt-only) — Rely on the instruction in factory_fix.md. Effective against non-adversarial models; no enforcement against determined optimization.

**Current mitigation:** The prompt explicitly tells Codex `/scenarios/` should not exist in its workspace. The `--sandbox workspace-write` flag limits writes. But reads are unrestricted.

**For the first crank:** Accept the prompt-level control. The attractor is unlikely to proactively search `/tmp/` unless it's been specifically fine-tuned to game evaluations. After the first crank, implement option 1.

### 4. Token Budget
**Status:** Non-blocking (current defaults are reasonable)
**Priority:** Post-first-crank optimization

Codex context window determines how much the agent can read per iteration. Long feedback files + all specs could get expensive. Consider:
- Capping feedback to last 2 iterations
- Summarizing older feedback more aggressively

### 4. Model Control Plane
**Status:** Design phase
**Priority:** Post-first-crank

The factory has multiple LLM-powered components (current and planned):

| Component | Current Model | Role |
|-----------|--------------|------|
| Attractor (Codex) | codex-mini-latest | Code writing/fixing |
| LLM-as-judge (planned) | TBD | Subjective scenario evaluation |
| Feedback compiler (planned upgrade) | TBD | Root cause analysis enrichment |
| Orchestrator | N/A (bash/yaml) | Loop control (non-LLM today) |

**Desired capabilities:**
- Dashboard showing all LLM-powered workers with current model assignments
- Token consumption per worker, per iteration, per time window (day/week)
- Ability for the human operator to swap models per worker (e.g., switch attractor from codex-mini to gpt-5)
- Cost tracking and budget alerts
- Latency metrics per worker per iteration

**Implementation options:**
1. **Streamlit page** — extend the existing dashboard with a "Control Plane" tab
2. **Config file** — `configs/factory_models.yaml` mapping worker → model, read by all LLM components
3. **Environment variables** — lighter touch, less visibility

**Decision needed:** When to build, and how much observability is worth the infrastructure cost.

## Roadmap

### Pre-First-Crank (do before triggering the factory)
1. ✅ factory/v1 branch created and pushed (factory infra + Codex code merged)
2. ✅ Validation guidelines consolidated into attractor prompt
3. ✅ agents/dev_team collected as factory-side reference assets
4. 🔧 Satisfaction dashboard — visibility into scenario pass rates and convergence trajectory
5. 🔧 Accept/merge gate — human interaction point for promoting factory output
6. ⏳ API key stored as GitHub secret (#1 above)
7. ⏳ Satisfaction threshold confirmed (#2 above)

### Post-First-Crank (improve after first successful iteration)
1. Gate 2: Structural quality (vulture, radon, pytest --cov, bandit) — factory's own code health
2. LLM-as-judge (Gate 4) — smarter scenario evaluation for subjective criteria
3. Factory extraction to separate repo/package (see Phase 2 below)
4. Token budget optimization (#3 above)
5. Factory capability table — NFR testing, dead code detection, import graph analysis
6. Model control plane — see #4 below

### Phase 2: Factory Extraction
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

**Decision point:** After the first successful convergence, evaluate whether to extract immediately or after a second project validates the pattern.

## Resolved

### ✅ Codex Branch Strategy
**Resolved:** factory/v1 branch created from main, merged with Codex branch. Factory runs on `factory/*` branches.

### ✅ Codex Billing
**Resolved:** ChatGPT Plus includes Codex + $5 free API credits. Factory CI uses standard API rates. No separate subscription needed.

### ✅ Validation Guidelines in Attractor
**Resolved:** DoD, hard constraints, and quality checklist from agents/dev_team consolidated into `.github/codex/prompts/factory_fix.md`. Reduces iterations by giving Codex upfront quality expectations.
