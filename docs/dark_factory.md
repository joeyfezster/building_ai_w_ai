# Dark Factory — Operating Manual

## What Is This

The dark factory is a convergence loop that turns a one-shot AI code generation into working software through automated validation and feedback. Code is never reviewed by humans — correctness is inferred from externally observable behavior.

The pattern: **Seed → Agent → Validate → Feedback → Repeat until satisfied.**

## Architecture

The factory supports two orchestration modes: **Claude Code orchestrated** (primary) and **CI-only** (fallback).

### Claude Code as Orchestrator (Primary)

Claude Code runs the convergence loop via the `/factory-orchestrate` skill, using browser automation to invoke Codex through the ChatGPT Plus UI.

```
┌─────────────────────────────────────────────────┐
│               HUMAN (Project Lead)               │
│  Authors specs (/specs/) and scenarios           │
│  Invokes /factory-orchestrate skill              │
│  Reviews PR at accept/merge gate                 │
└────────────┬─────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│         CLAUDE CODE (Orchestrator)               │
│         .claude/skills/factory-orchestrate        │
│                                                   │
│  for each iteration:                              │
│    1. Create df-crank-vXX branch                  │
│    2. strip_holdout.py → remove /scenarios/       │
│    3. Push stripped branch to origin               │
│    4. Invoke Codex via browser (Codex UI)          │
│       → Codex creates its own codex-... branch     │
│    5. Gate 0: Adversarial code review              │
│    6. Merge Codex changes onto factory branch      │
│    7. restore_holdout.py → restore /scenarios/     │
│    8. Gate 1: make lint && typecheck && test        │
│    9. Gate 2: NFR checks (non-blocking)            │
│   10. Gate 3: Behavioral scenarios                 │
│   11. LLM-as-judge: holistic evaluation            │
│   12. If satisfied → PR. If not → feedback → loop  │
└─────────────────────────────────────────────────┘
             │                  ▲
             │ stripped branch   │ codex-... branch
             ▼                  │
┌─────────────────────────────────────────────────┐
│              CODEX (Attractor)                    │
│  Reads: /specs/, feedback_iter_N.md               │
│  Writes: src/, tests/, configs/, Makefile         │
│  NEVER sees: /scenarios/ (stripped from branch)    │
│  NEVER touches: factory infrastructure             │
│  Creates own branch: codex-...                     │
└─────────────────────────────────────────────────┘
```

### CI-Only Mode (Fallback)

When an `OPENAI_API_KEY` secret is available, the GitHub Actions workflow can run the full loop autonomously. Without the key, CI runs validation-only on push (Gates 1-3 + feedback compilation).

```
┌─────────────────────────────────────────────────┐
│            CI VALIDATION                          │
│        .github/workflows/factory.yaml             │
│                                                   │
│  On push to factory/** or df-crank-** branches:   │
│    1. Gate 1: lint + typecheck + test              │
│    2. Gate 2: NFR checks                           │
│    3. Gate 3: Behavioral scenarios                 │
│    4. Compile feedback                             │
│  Claude Code reads CI results and decides next     │
└─────────────────────────────────────────────────┘
```

## Validation Gates

### Gate 0: Adversarial Code Review (Claude Code orchestrated)
- Claude Code reviews Codex's changes before merging to the factory branch
- Checks for: stam tests, gaming, architectural dishonesty, stub implementations
- Standards defined in `docs/code_quality_standards.md`
- CRITICAL findings → send back to Codex with feedback (no point running gates)
- Clean or WARNING-only → proceed to Gate 1

### Gate 1: Deterministic CI
- `make lint` — ruff check
- `make typecheck` — mypy
- `make test` — full pytest suite (including tests the attractor wrote, already reviewed by Gate 0)

If any fail, Gates 2-3 are skipped. The agent gets the CI errors directly.

### Gate 2: Non-Functional Requirements (NFRs)
- `make nfr-check` — extensible framework (`scripts/nfr_checks.py`)
- **Active checks:** code quality (ruff extended), complexity (radon), dead code (vulture), security (bandit)
- **Planned checks:** duplication, import hygiene, coverage, maintainability, reliability
- Non-blocking — findings feed into feedback and LLM-as-judge evaluation
- Adding a new check: write a function, register in `NFR_CHECKS` dict

### Gate 3: Behavioral Scenarios
- `scripts/run_scenarios.py` executes holdout scenarios from `/scenarios/`
- Each scenario runs an evaluation command and checks pass criteria
- Results produce a satisfaction score: `passed / total`

### LLM-as-Judge (Claude Code orchestrated)
- Claude Code reasons holistically through ALL gate outputs
- Not just "score >= threshold" — considers trajectory, systemic issues, Gate 2 warnings
- Factors in: Are fixes real or is Codex gaming? Do patterns make sense?
- Holistic go/no-go decision for creating the PR

## Scenario Isolation (Branch Stripping)

The factory hides `/scenarios/` from Codex using **branch stripping** — scenarios are physically removed from the branch Codex works on.

### How it works
1. `scripts/strip_holdout.py` removes `/scenarios/` and comments out Makefile scenario targets
2. Commits with marker `[factory:holdout-stripped]`
3. Verifies no scenario files remain on the branch
4. Stripped branch is pushed to origin — Codex only ever sees this branch
5. After Codex finishes, `scripts/restore_holdout.py` restores from `origin/main`

### Why branch stripping (not filesystem shuffle)
The previous approach (`mv scenarios /tmp/`) was security theater — Codex runs in the same job and can read `/tmp/`. Branch stripping is a real gate: scenarios literally don't exist on the branch Codex sees. There's nothing to read, no path to guess, no hidden directory to discover.

### Scripts
- `scripts/strip_holdout.py` — deterministic removal, supports `--dry-run` and `--no-commit`
- `scripts/restore_holdout.py` — deterministic restoration from a git ref, supports `--ref` and `--dry-run`
- Both are factory-protected files (never modified by Codex)

## How to Trigger the Factory

### Claude Code Orchestrated (primary)
```
# Invoke the factory orchestration skill:
/factory-orchestrate
```
Claude Code handles the full loop: branch creation, holdout stripping, Codex invocation (via browser), adversarial review, validation, LLM judgment, and PR creation.

### GitHub Actions (CI validation on push)
```
# Automatic: push to factory/** or df-crank-** branches triggers CI validation
# Manual: Actions → Dark Factory → Run workflow
gh workflow run factory.yaml -f max_iterations=5 -f satisfaction_threshold=0.80
```
CI runs Gates 1-3 + feedback compilation. Claude Code reads the results.

### Local (testing the plumbing)
```bash
make factory-local    # One iteration: Gate 1 → Gate 2 → Gate 3 → feedback
make factory-status   # Show current iteration and satisfaction score
make nfr-check        # Just run Gate 2 NFR checks
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

## Accept/Merge Gate

The factory **never auto-merges** to main. When the convergence loop meets the satisfaction threshold, it creates (or updates) a PR with the `factory-converged` and `accept-merge-gate` labels. This is the single human decision point in the entire loop.

**What the project lead reviews:**
- Satisfaction score — does it meet your quality bar?
- Residual warnings in the latest feedback file
- Unexpected files or dependencies introduced by the attractor
- Optionally: run `make factory-local` locally for additional confidence

**To accept:** Approve and merge the PR. The factory branch can be deleted.
**To reject:** Close the PR and either adjust scenarios/specs or trigger another factory run.

The accept/merge gate exists because code produced by the factory was never reviewed by humans during production. The satisfaction score provides probabilistic confidence, but the merge decision is always human.

## When to Escalate

Escalate to interactive debugging (Claude Code) when:
- The factory has stalled for 3+ iterations with no score improvement
- The same scenario keeps failing with the same error pattern
- Gate 1 failures persist (the code doesn't even pass lint/typecheck)
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
| `/scripts/strip_holdout.py` | Factory | Holdout stripping (isolation gate) |
| `/scripts/restore_holdout.py` | Factory | Holdout restoration |
| `/scripts/nfr_checks.py` | Factory | Gate 2 NFR checker |
| `/.github/workflows/factory.yaml` | Factory | CI validation on push |
| `/.github/codex/prompts/factory_fix.md` | Factory | Codex instruction template |
| `/.claude/skills/factory-orchestrate/` | Factory | Claude Code orchestration skill |
| `/docs/code_quality_standards.md` | Factory | Universal code quality standards |
| `/CLAUDE.md` | Factory | Repo-level context for Claude Code |
| `/artifacts/factory/feedback_iter_*.md` | Factory | Iteration feedback (Codex reads) |
