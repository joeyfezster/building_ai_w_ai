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

### Step 4: Gate 0 — Adversarial Code Review (Agent Team)

Before merging Codex's changes, run a **full adversarial review via agent teams**. This is the first line of defense — there is no point sending code to CI or later gates if Gate 0 finds critical issues.

1. Fetch Codex's branch: `git fetch origin`
2. Get the diff: `git diff df-crank-vXX...origin/codex-{branch}`

3. **Spawn the Gate 0 agent team.** Create a team and launch these agents in parallel:

   **Tool agents** (deterministic, Bash-capable — run ALL simultaneously):
   | Agent | What It Runs | What It Catches |
   |-------|-------------|-----------------|
   | `ruff-agent` | `python scripts/nfr_checks.py --check code_quality` | Lint violations, style, import issues |
   | `radon-agent` | `python scripts/nfr_checks.py --check complexity` | Cyclomatic complexity > threshold |
   | `vulture-agent` | `python scripts/nfr_checks.py --check dead_code` | Unreachable code, unused functions |
   | `bandit-agent` | `python scripts/nfr_checks.py --check security` | Security vulnerabilities |
   | `test-quality-agent` | `python scripts/check_test_quality.py` | Vacuous tests, stub assertions, mock abuse |

   **Semantic reviewer** (LLM-based, runs in parallel with tool agents):
   | Agent | What It Reads | What It Catches |
   |-------|--------------|-----------------|
   | `adversarial-reviewer` | The diff + `.github/codex/prompts/adversarial_review.md` + `docs/code_quality_standards.md` + `/specs/*.md` | Gaming, architectural dishonesty, spec violations, integration gaps, subtle patterns the tools miss |

4. **Aggregate findings.** Collect all agent outputs. Each finding has a severity: CRITICAL, WARNING, or NIT.

5. **Fail-fast rule:** If **any agent** reports a CRITICAL finding, Gate 0 fails. Do NOT proceed to later gates (1-3). However, **DO merge Codex's changes onto the factory branch** so that iteration N+1 is incremental — Codex iterates on its own code with feedback, rather than rebuilding from scratch. Compile all findings (from all agents) as feedback and loop back to Step 3 with specific remediation instructions.

   **Gate 0 failure workflow:**
   ```bash
   # 1. Merge Codex's code (keep it for incremental iteration)
   git merge origin/codex-{branch} --no-ff -m "factory: merge codex iteration N (Gate 0 blocked — iterating)"
   # 2. Delete Codex's remote branch (consumed by merge, prevent branch pollution)
   git push origin --delete codex-{branch}
   # 3. Commit feedback file
   git add artifacts/factory/feedback_iter_N.md
   git commit -m "factory: Gate 0 feedback for iteration N"
   # 4. Push — Codex's next run sees its own code + feedback
   git push
   # 5. Loop back to Step 3 (invoke Codex again)
   ```

   **NEVER revert Codex's merge on Gate 0 failure.** Reverting forces Codex to rebuild from zero, wasting an iteration. The feedback is specific enough to guide incremental fixes. The code is "wrong but close" — keep it and steer.

**If clean or WARNING-only across all agents**: Proceed to Step 5. WARNING findings are tracked — they feed into the LLM-as-judge evaluation in Step 10.

**Why agent teams, not a single reviewer:** The tool agents catch cheap, obvious violations in seconds (dead code, complexity, security). The semantic reviewer catches subtle gaming and architectural dishonesty. Running them in parallel means Gate 0 is both fast AND thorough. A single reviewer doing everything sequentially is slower and more likely to miss things.

### Step 5: Merge Codex Changes
```bash
git merge origin/codex-{branch} --no-ff -m "factory: merge codex iteration N"
```

### Step 5a: Delete Codex's Remote Branch

**Immediately after merging**, delete Codex's branch from origin. The factory is branch-heavy — stale Codex branches pollute the namespace and create confusion about which branch is current. The code is preserved in the merge commit on the factory branch.

```bash
git push origin --delete codex-{branch}
```

This applies to EVERY merge — whether Gate 0 passes or fails. The Codex branch is consumed by the merge; it has no further purpose.

### Step 5b: Check CI Results

After pushing, check CI results. CI runs Gates 1-3 on every push to factory/** branches. Use CI results as early signal before running gates locally.

```bash
# Wait for CI to complete (typically 2-5 minutes)
gh run list --branch df-crank-vXX --limit 3

# Check the PR's checks (if PR exists)
gh pr checks <PR_NUMBER>
```

**Known `gh pr checks` behavior:**
- `gh pr checks` shows checks associated with the PR's **merge ref**, not the branch HEAD directly
- If a bot (GITHUB_TOKEN) pushes a commit that becomes PR HEAD, GitHub does NOT re-trigger CI workflows (prevents infinite loops). The PR may show "0 checks" even though CI ran fine on the previous commit.
- Workaround: If you see stale/missing checks, use `gh run list --branch <branch>` instead — this shows actual workflow runs regardless of the merge ref.
- Commits pushed by workflows using `GITHUB_TOKEN` do not trigger other workflows. This is a GitHub safety measure.
- If CI results conflict with your local gate results, investigate — don't just ignore the discrepancy.

**If CI fails**: Use the github.com's copilot's 'explain errors' as initial reference, check logs to validate and make up your own mind, compile actionable feedback (yourself), and loop back to Step 3.

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

"test" = *should be* the FULL pytest suite, including any tests Codex wrote (already reviewed in Gate 0).

**If fail**: Compile feedback (use this script as aid, but make sure you intervene if the feedback doesn't make sense: `python scripts/compile_feedback.py --iteration N`), loop to Step 3.

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
6. **Documentation currency**: Did this iteration's changes affect documented behavior? Check: Are specs in `/specs/` still accurate? Does the README reflect current state? Are factory docs (`dark_factory.md`, `code_quality_standards.md`) still correct? Stale documentation is technical debt — flag it in feedback if needed.

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

### Step 12: Generate PR Review Pack

After creating the PR, invoke the `/pr-review-pack` skill to generate the interactive HTML review pack. This is how the human project lead reviews the factory's output — they review the report, not the code.

The review pack gives the project lead:
- Architecture diagram showing which zones were touched
- Adversarial findings (from Gate 0 agent team) graded by file
- CI performance with health classification
- Key decisions with zone-level traceability
- Convergence result (gate-by-gate status)
- Post-merge items with code snippets and failure/success scenarios
- Factory history (iteration timeline, gate findings per iteration)

```
/pr-review-pack {PR_NUMBER}
```

The review pack is the artifact that communicates factory status to the human. Without it, the accept/merge gate is a rubber stamp.

### Stall Protocol

If after 3+ iterations:
- Same scenario fails with same error → the spec or scenario may need adjustment. Escalate to the project lead.
- Score oscillates without converging → architectural issue. Escalate.
- Gate 0 keeps finding critical issues → attractor needs stronger constraints. Update `factory_fix.md`.

## Reference Files

- **Attractor prompt**: `.github/codex/prompts/factory_fix.md`
- **Adversarial review**: `.github/codex/prompts/adversarial_review.md`
- **Code quality standards**: `docs/code_quality_standards.md`
- **NFR checks script**: `scripts/nfr_checks.py` (Gate 0 tool agents + Gate 2)
- **Test quality scanner**: `scripts/check_test_quality.py` (Gate 0 tool agent)
- **PR review pack skill**: `.claude/skills/pr-review-pack/SKILL.md` (Step 12)
- **Specs**: `specs/*.md`
- **Factory docs**: `docs/dark_factory.md`
- **Factory architecture**: `docs/factory_architecture.html`

## Operational Knowledge

### Layered Defense Against Gaming
The factory's quality defense is layered — no single gate is sufficient:
1. **Gate 0 tool agents** (agent team, parallel) — deterministic checks via vulture, radon, bandit, ruff, and `check_test_quality.py`. Catches dead code, complexity, security issues, lint violations, and obvious vacuous test patterns. Fast, cheap, runs in seconds. Risk: regex/AST-level analysis can be fooled by sophisticated gaming.
2. **Gate 0 adversarial reviewer** (agent team, parallel with tool agents) — LLM-based judgment catches subtle gaming, architectural dishonesty, spec violations, and patterns the static tools miss. Reads the full diff against code quality standards and specs.
3. **Gate 3 holdout scenarios** — behavioral evaluation against criteria the attractor never sees (ground truth). If the code actually works, gaming doesn't matter.

The tool agents and semantic reviewer run in parallel at Gate 0 as an agent team. Any CRITICAL finding from any agent stops the pipeline before merge. No single layer is sufficient. Tool agents catch the cheap stuff fast, the adversarial reviewer catches the clever stuff, and holdout scenarios verify actual behavior.

### Iteration → Commit Model
Each factory iteration produces ONE commit from Codex (via merge). This provides a clean diff for adversarial review and clear rollback boundaries. The commit message must include the iteration number for traceability.

### CI vs. Orchestrator Roles
CI (factory.yaml) runs validation-only on every push — Gates 1, 2, 3 + feedback compilation. CI does NOT drive the convergence loop. Claude Code drives the loop via this skill. CI results are INPUT to orchestration decisions, not orchestration themselves.

**Current CI structure:**
- `factory-self-test (push)` — factory script validation
- `factory-self-test (PR)` — PR-specific factory validation
- `factory-loop` — fallback convergence via Codex API (only with OPENAI_API_KEY)
- `validate (push)` — product code validation
- `validate (PR)` — PR-specific product validation

**Future consolidation note:** Once the factory runs regularly, `factory-loop` and `validate` could be consolidated into a single workflow with better separation. Current overlap provides coverage redundancy during proof-of-concept.

### NFR Gate Architecture
Gate 2 runs deterministic tool-based checks. Each check follows the pattern:
1. Run external tool (ruff, radon, vulture, bandit)
2. Parse output (JSON preferred, text fallback)
3. Map findings to severity (CRITICAL/WARNING/NIT/INFO)
4. Return structured findings

Adding a new check: write `check_<name>(repo_root: Path) -> list[NFRFinding]`, register in `NFR_CHECKS` dict. The factory picks it up automatically.

**Important:** All JSON parsing must include fallback handling for decode errors. Silent `pass` on JSONDecodeError hides tool failures — always emit at least a WARNING finding.

### Gate 2 and LLM-Based Review
Gate 2 should stay deterministic (tool-based). LLM-based review belongs in Gate 0 (adversarial review) and Step 10 (LLM-as-judge). Mixing deterministic and non-deterministic findings in the same gate creates confusion about what's reliable vs. advisory. If LLM-based checks are added, label findings as "advisory" and never let them block convergence alone.

### Holdout Stripping Scope
`strip_holdout.py` removes `/scenarios/` and Makefile scenario targets. It also strips review pack artifacts (`docs/pr_review_pack.html`, `docs/pr_diff_data.json`) — the attractor has no business seeing adversarial review findings from previous iterations. The attractor's information boundary is: specs + feedback + its own code. Nothing else.

### Git Hooks vs. CI Enforcement
`.githooks/pre-commit` runs ruff + mypy on staged Python files — a local speed bump. It is NOT enforced on clean clone; developers must run `make install-hooks`. CI is the enforcement layer. The hook catches issues before they hit CI, saving iteration time. Both exist because they serve different failure modes.
