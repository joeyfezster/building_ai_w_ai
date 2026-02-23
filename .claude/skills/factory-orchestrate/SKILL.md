---
name: factory-orchestrate
description: Run the dark factory convergence loop. Use when the user says "run a factory crank", "start the factory", "orchestrate a crank", or similar. Orchestrates Codex via browser, manages holdout isolation, runs validation gates, and performs LLM-as-judge evaluation.
allowed-tools: Bash, Read, Write, Glob, Grep, Edit
---

# Dark Factory Orchestration — Claude Code as Orchestrator

You are the factory orchestrator. You run the convergence loop that turns specs into working software through iterative AI coding + validation.

## Prerequisites

- Chrome is logged into Codex (ChatGPT Plus account)
- Repository: `joeyfezster/building_ai_w_ai`
- Branch to base work on: confirm with user or default to `factory/v1`
- Satisfaction threshold: confirm with user or default to 80%
- Max iterations: confirm with user or default to 5

## The Loop

For each iteration:

### Step 1: Create Factory Branch
```bash
# First crank — create from base branch
git checkout -b df-crank-v01-{descriptor} {base_branch}
git push -u origin df-crank-v01-{descriptor}
```

Branch naming: `df-crank-vXX-{descriptor}` where XX is the crank version.

### Step 2: Strip Holdout
```bash
python scripts/strip_holdout.py
git push
```

This deterministically removes `/scenarios/` and comments out scenario Makefile targets. Codex literally cannot see evaluation criteria.

Verify: `ls scenarios/` should fail (directory gone).

### Step 3: Invoke Codex via Browser

Open the Codex UI in Chrome. Provide:
- **Repository**: `joeyfezster/building_ai_w_ai`
- **Base branch**: `df-crank-vXX-{descriptor}` (the stripped branch)
- **Prompt**: Contents of `.github/codex/prompts/factory_fix.md` + the latest feedback file (`artifacts/factory/feedback_iter_N.md`)
- **Versions**: 1

Codex will create its own branch (named `codex-...`). Wait for it to finish.

### Step 4: Gate 0 — Adversarial Code Review

Before merging Codex's changes, review them adversarially:

1. Fetch Codex's branch: `git fetch origin`
2. Read the diff: `git diff df-crank-vXX...origin/codex-{branch}`
3. Review using the checklist in `.github/codex/prompts/adversarial_review.md`:
   - Stam tests (mocking subject, stub assertions, tautologies)
   - Gaming (hardcoded lookups, overfitted implementations, test-detection)
   - Architectural dishonesty (import redirection, dependency skipping)
   - Spec violations (check against `/specs/`)
   - Integration gaps

**If CRITICAL findings**: Do NOT merge. Compile findings as feedback and loop back to Step 3 with specific remediation instructions.

**If clean or WARNING-only**: Proceed to Step 5.

### Step 5: Merge Codex Changes
```bash
git merge origin/codex-{branch} --no-ff -m "factory: merge codex iteration N"
```

### Step 6: Restore Holdout
```bash
python scripts/restore_holdout.py
git add scenarios/ Makefile
git commit -m "factory: restore holdout scenarios for evaluation"
```

### Step 7: Gate 1 — Deterministic Validation
```bash
make lint && make typecheck && make test
```

"test" = the FULL pytest suite, including any tests Codex wrote (already reviewed in Gate 0).

**If fail**: Compile feedback (`python scripts/compile_feedback.py --iteration N`), loop to Step 3.

### Step 8: Gate 2 — Non-Functional Requirements
```bash
make nfr-check
```

This runs all implemented NFR checks (code quality, complexity, dead code, security).

Gate 2 is **non-blocking** but findings are tracked and feed into:
- The feedback for the next Codex iteration
- Your LLM-as-judge evaluation in Step 10

### Step 9: Gate 3 — Behavioral Scenarios
```bash
python scripts/run_scenarios.py --timeout 180
```

Produces `artifacts/factory/scenario_results.json` with satisfaction score.

### Step 10: LLM-as-Judge — Holistic Evaluation

You ARE the judge. Don't just check `satisfaction_score >= threshold`. Reason through:

1. **Satisfaction trajectory**: Is the score improving across iterations? Plateaued? Regressing?
2. **Failure patterns**: Are the same scenarios failing repeatedly? Different ones each time?
3. **Fix quality**: Do Codex's changes look like real solutions or gaming attempts? (Gate 0 caught the obvious ones, but look for subtle patterns across iterations)
4. **Gate 2 NFR findings**: Even though non-blocking, are there concerning patterns? Growing complexity? Dropping coverage?
5. **Systemic issues**: Is there something the score doesn't capture? An architectural problem that will cause future failures?

**If satisfied**: Proceed to Step 11.
**If not satisfied**: Compile feedback with your holistic assessment, loop to Step 3.

### Step 11: Create PR (Accept/Merge Gate)
```bash
gh pr create \
  --title "[Factory] df-crank-vXX converged at {score}%" \
  --body "$(cat <<'EOF'
## Dark Factory — Converged

**Satisfaction score: {score}%**
**Iterations: {N}**
**Gate 2 NFR status: {summary}**

### Accept/Merge Gate
This PR was produced by the dark factory convergence loop, orchestrated by Claude Code.

**Before merging, verify:**
- [ ] Satisfaction score meets your quality bar
- [ ] Review latest feedback for residual warnings
- [ ] Gate 2 NFR findings are acceptable
- [ ] No unexpected files or dependencies introduced

**To merge:** Approve and merge. The factory branch can then be deleted.
**To reject:** Close this PR and either adjust scenarios/specs or trigger another crank.
EOF
)" \
  --label factory-converged --label accept-merge-gate
```

### Stall Protocol

If after 3+ iterations:
- Same scenario fails with same error → the spec or scenario may need adjustment. Escalate to the project lead.
- Score oscillates without converging → architectural issue. Escalate.
- Gate 0 keeps finding critical issues → attractor needs stronger constraints. Update `factory_fix.md`.

## Reference Files

- **Attractor prompt**: `.github/codex/prompts/factory_fix.md`
- **Adversarial review**: `.github/codex/prompts/adversarial_review.md`
- **Code quality standards**: `docs/code_quality_standards.md`
- **Specs**: `specs/*.md`
- **Factory docs**: `docs/dark_factory.md`
