# Dark Factory — Operating Manual

## What Is This

The dark factory is a convergence loop that turns a one-shot AI code generation into working software through automated validation and feedback. Code is never reviewed by humans — correctness is inferred from externally observable behavior.

The pattern: **Seed → Agent → Validate → Feedback → Repeat until satisfied.**

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  HUMAN (Joey)                    │
│  Authors specs (/specs/) and scenarios           │
│  Sets satisfaction threshold                     │
│  Triggers factory via workflow_dispatch           │
│  Escalates when factory stalls                   │
└────────────┬──────────────────┬──────────────────┘
             │ specs            │ scenarios (holdout)
             ▼                  ▼
┌────────────────────────────────────────────────┐
│            FACTORY ORCHESTRATOR                 │
│        .github/workflows/factory.yaml           │
│                                                 │
│  for each iteration:                            │
│    1. Layer 1: make lint, typecheck, test        │
│    2. Layer 2: run_scenarios.py                  │
│    3. Check satisfaction threshold               │
│    4. compile_feedback.py                        │
│    5. Invoke Codex with specs + feedback         │
│    6. Codex commits fixes                        │
│    7. Loop                                       │
└────────────────────────────────────────────────┘
             │                  ▲
             │ code changes     │ feedback
             ▼                  │
┌────────────────────────────────────────────────┐
│              CODEX (Attractor)                  │
│  Reads: /specs/, feedback_iter_N.md             │
│  Writes: src/, tests/, configs/, Makefile       │
│  NEVER sees: /scenarios/                        │
│  NEVER touches: factory infrastructure          │
└────────────────────────────────────────────────┘
```

## Validation Layers

### Gate 1: Deterministic CI
- `make lint` — ruff check
- `make typecheck` — mypy
- `make test` — pytest

If any fail, subsequent gates are skipped. The agent gets the CI errors directly.

### Gate 2: Structural Quality (planned)
- `vulture` — dead code detection
- `radon` — cyclomatic complexity thresholds
- `pytest --cov` — test coverage
- `bandit` — security vulnerability patterns

Non-blocking but tracked in the feedback report. Gives visibility into NFRs (maintainability, security, complexity) without violating the validation constraint.

### Gate 3: Behavioral Scenarios
- `scripts/run_scenarios.py` executes holdout scenarios from `/scenarios/`
- Each scenario runs an evaluation command and checks pass criteria
- Results produce a satisfaction score: `passed / total`

### Gate 4: LLM-as-Judge (optional, not implemented yet)
- For subjective scenarios (video quality, dashboard usability)
- Enriches feedback with smarter root cause analysis
- Pluggable via `--llm-judge` flag on run_scenarios.py
- Not a hard dependency — factory works without it

## Scenario Isolation (Filesystem Shuffle)

The factory hides `/scenarios/` from Codex using a filesystem shuffle:

1. Before running scenarios: restore from `/tmp/factory_scenarios`
2. After running scenarios: move to `/tmp/factory_scenarios`
3. Codex runs with scenarios physically absent from the workspace
4. After Codex: restore scenarios for the next iteration

This is a hard gate — Codex literally cannot read files that don't exist in the filesystem.

Why not `.codexignore`? It doesn't exist as a shipped feature (as of Feb 2026, despite being the #1 community request).

## How to Trigger the Factory

### GitHub Actions (production)
```
# Via GitHub UI: Actions → Dark Factory → Run workflow
# Or via CLI:
gh workflow run factory.yaml -f max_iterations=5 -f satisfaction_threshold=0.80
```

### Local (testing the plumbing)
```bash
make factory-local    # One iteration: validate → scenarios → feedback (no Codex)
make factory-status   # Show current iteration and satisfaction score
```

### Individual components
```bash
make run-scenarios        # Just run scenarios
make compile-feedback     # Just compile feedback from latest results
```

## How to Write a New Scenario

Create a markdown file in `/scenarios/` with this structure:

```markdown
# Scenario: [descriptive name]

## Category
[environment | training | pipeline | dashboard | integration]

## Preconditions
- [what must be true before evaluation]

## Behavioral Expectation
[what the system should do, from observer perspective]

## Evaluation Method
\```bash
[command that tests the behavior]
\```

## Pass Criteria
[specific condition for passing]

## Evidence Required
- [what to capture as proof]
```

The evaluation method is a bash command that exits 0 on pass, non-zero on fail. Keep commands self-contained — they run in the repo root with PYTHONPATH set.

## How to Read Feedback

Feedback files are at `artifacts/factory/feedback_iter_N.md`. Each contains:
- **Summary** — satisfaction score and pass/fail counts
- **Convergence trajectory** — how scores changed across iterations
- **Likely root causes** — pattern-matched from error types
- **Full error details** — every failed scenario with complete stdout/stderr
- **Instructions** — prioritized fix guidance for the coding agent

## When to Escalate

Escalate to interactive debugging (Claude Code) when:
- The factory has stalled for 3+ iterations with no score improvement
- The same scenario keeps failing with the same error pattern
- Layer 1 failures persist (the code doesn't even pass lint/typecheck)
- A scenario requires architectural changes the agent can't figure out from error messages alone

## Factory State

```
artifacts/factory/
├── scenario_results.json    # Latest run results (gitignored)
├── ci_output.log            # Latest CI output (gitignored)
├── iteration_count.txt      # Current iteration number (committed)
└── feedback_iter_*.md       # All feedback files (committed — Codex reads these)
```

## Key Files

| File | Owner | Purpose |
|------|-------|---------|
| `/specs/*.md` | Human | What the system should do |
| `/scenarios/*.md` | Human | How to evaluate (holdout) |
| `/scripts/run_scenarios.py` | Factory | Scenario evaluation engine |
| `/scripts/compile_feedback.py` | Factory | Feedback generation |
| `/.github/workflows/factory.yaml` | Factory | Orchestrator |
| `/.github/codex/prompts/factory_fix.md` | Factory | Codex instruction template |
| `/CLAUDE.md` | Factory | Repo-level context for Claude Code |
| `/artifacts/factory/feedback_iter_*.md` | Factory | Iteration feedback (Codex reads) |
