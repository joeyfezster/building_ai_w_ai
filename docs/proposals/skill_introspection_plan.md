# Lessons from Anthropic Skill Introspection → Apply to PR Review Pack

**Date:** 2026-03-14
**Source:** Deep analysis of 4 Anthropic-authored skills/plugins: `code-review`, `skill-creator`, `feature-dev`, `plugin-dev`

---

## Key Findings Across All 4 Skills

### 1. Progressive Contexting is a Deliberate 3-Tier Architecture

Every complex Anthropic skill follows the same pattern:

| Tier | What | When Loaded | Context Cost |
|------|------|-------------|-------------|
| 1 | Frontmatter (name + description) | Always | ~100 words |
| 2 | SKILL.md body | On invocation | 500 lines max (skill-creator's own recommendation) |
| 3 | references/, agents/, examples/, scripts/ | On-demand per phase | Unlimited |

**Our problem:** Our SKILL.md is ~430 lines and growing. It contains the full workflow specification, agent spawn templates, validation loop pseudocode, schema summaries, and reference tables. This is all Tier 2 — loaded on every invocation regardless of phase.

**Their approach:** `plugin-dev` assigns specific skills to specific numbered phases. Phase 2 loads `plugin-structure` and stops there. Phase 5 loads only the skill for the current component. The command file is a conductor, not a textbook.

**Scripts execute without consuming context.** `skill-creator` runs 9 Python scripts via `python -m scripts.foo`. The orchestrator never reads the script source — it just calls it. This is zero-cost context usage for complex logic.

### 2. Agent Definition Files Are First-Class Citizens

All 4 skills define agents in separate `.md` files under `agents/`, not inline in the command/SKILL.md.

**`plugin-dev` agent frontmatter example:**
```yaml
name: plugin-validator
description: Validates plugin structure...
model: inherit
color: yellow
tools: ["Read", "Grep", "Glob", "Bash"]
```

**`feature-dev` agent frontmatter example:**
```yaml
name: code-reviewer
model: sonnet
color: red
tools: [Glob, Grep, LS, Read, NotebookRead, WebFetch, TodoWrite, WebSearch, KillShell, BashOutput]
```

**What this gives them:**
- **Explicit tool scoping per agent** — validators get `Read + Grep + Glob + Bash`, reviewers get `Read + Grep + Glob`, creators get `Write + Read`. Least privilege by design.
- **Model pinning per agent** — some pin to `sonnet`, others `inherit` from parent.
- **The `tools` field in agent frontmatter is the mechanism for granting subagent permissions.** This is the answer to our write-permission problem — not `mode: "acceptEdits"` on the spawn call, but a `tools:` field in the agent definition file.

**Our problem:** We define agents inline in SKILL.md's spawn template. Agents have no persistent identity, no tool declarations, no frontmatter. We rely on `mode: "acceptEdits"` as a blunt hammer.

### 3. No Skill Uses Structured JSON Contracts Between Agents

This is the most surprising finding. **None of the 4 skills enforce structured output schemas between agents and orchestrator.** All agent communication is natural language.

- `code-review`: Agents return "lists of issues" — prose, not JSON.
- `feature-dev`: Agents return analysis plus "a list of 5-10 key files."
- `skill-creator`: Graders write `grading.json` to disk, but the orchestrator reads the file, it doesn't parse agent return values.
- `plugin-dev`: Agents return prose; orchestrator synthesizes.

**Our approach is MORE rigorous** — we have agents write structured JSONL to disk with pydantic-validated schemas. This is architecturally stronger but creates the write-permission problem that Anthropic avoids by keeping agent output as prose return values.

### 4. Validation is Agent-as-Validator, Not Schema-as-Validator

- `code-review`: For each finding, spawns a separate validation subagent to confirm/reject it.
- `feature-dev`: The `code-reviewer` agent has a confidence score (0-100) with a hard cutoff at 80.
- `skill-creator`: Grader agent critiques not just outputs but the eval assertions themselves.
- `plugin-dev`: `plugin-validator` agent runs shell scripts + reads files, returns structured pass/fail.

**None of them run a deterministic validation script as a chokepoint.** Our assembler-as-chokepoint pattern is unique and stronger — but it depends on agents producing structured output, which depends on agents having write permissions, which is where we keep failing.

### 5. Broad `allowed-tools` in Frontmatter, Not Granular

- `code-review`: Only `gh` subcommands — tightly scoped because it's a pure GitHub operation.
- `feature-dev`: **No `allowed-tools` at all** — inherits everything from the session.
- `plugin-dev`: `["Read", "Write", "Grep", "Glob", "Bash", "TodoWrite", "AskUserQuestion", "Skill", "Task"]` — maximal.
- `skill-creator`: **No `allowed-tools` at all.**

**Our problem:** We kept listing individual `git` subcommands and missing some, causing permission prompts. The Anthropic pattern is either "list nothing and inherit everything" or "list broad categories." Our latest fix (`Bash(git *)`) is aligned with this.

### 6. TodoWrite for Progress Tracking

`plugin-dev` mandates `TodoWrite` at every phase: "Use TodoWrite to track progress at every phase." This creates visible progress tracking and recovery state if the session interrupts.

**We don't use TodoWrite at all.** This would solve the "I can't tell what phase the agent is in" observability problem.

### 7. Human-in-the-Loop Gates

`feature-dev` has explicit pause points: "CRITICAL: DO NOT SKIP Phase 3" and "DO NOT START WITHOUT USER APPROVAL." These are not just warnings — they're the primary enforcement mechanism for phase transitions.

**Our Phase 4 was treated as optional by every session.** The `feature-dev` approach of `CRITICAL: DO NOT SKIP` in all-caps at specific gates is the same pattern we just applied.

---

## Specific Changes to Apply to PR Review Pack

### Change 1: Create Agent Definition Files

**Current:** Agents defined inline in SKILL.md spawn templates.
**Proposed:** Create `agents/` directory with one `.md` file per reviewer.

```
agents/
├── code-health-reviewer.md
├── security-reviewer.md
├── test-integrity-reviewer.md
├── adversarial-reviewer.md
├── architecture-reviewer.md
└── synthesis-reviewer.md
```

Each file gets frontmatter with:
```yaml
---
name: code-health-reviewer
description: Reviews PR code changes for code quality, complexity, dead code, naming, and maintainability
model: opus
tools: [Read, Write, Glob, Grep]
---
```

**Impact:** Solves the write-permission problem structurally. Agents declared with `tools: [Write]` in their frontmatter get Write access without needing `mode: "acceptEdits"`.

### Change 2: Slim Down SKILL.md — Move Agent Templates to Agent Files

**Current:** SKILL.md contains full spawn templates with schema references, output format instructions, and validation loop pseudocode (~100 lines of Phase 2 content).
**Proposed:** SKILL.md Phase 2 becomes a conductor — "spawn these 5 agents, then run validation loop." The HOW lives in the agent files.

Each agent `.md` file contains its own:
- Paradigm prompt reference (read the paradigm prompt at `${CLAUDE_SKILL_DIR}/review-prompts/{agent}.md`)
- Output format specification (JSONL hybrid, schemas)
- Context files to read (diff data, zone registry, quality standards)
- Output file path pattern

SKILL.md Phase 2 shrinks to ~30 lines: agent list table + validation loop + synthesis spawn.

### Change 3: Add TodoWrite Phase Tracking

Add to the Pipeline Overview section:

```
**Progress tracking:** Use TodoWrite at the start of each phase to create a visible progress marker:
- Phase 1: "Setup: running review_pack_setup.py"
- Phase 2: "Review: spawning 5 reviewer agents"
- Phase 2b: "Validation: running feedback loop for {agent}"
- Phase 3: "Assembly: running assemble_review_pack.py"
- Phase 4: "Delivery: running Playwright validation"
```

**Impact:** Gives the user (and any observer) real-time visibility into which phase the orchestrator is in.

### Change 4: Scripts Stay as Scripts (Already Correct)

Our pattern of running Python scripts via Bash (`python3 "$SKILL_DIR/scripts/..."`) is exactly what Anthropic does. `skill-creator` runs 9 scripts the same way. This is zero-cost context usage. No change needed.

### Change 5: Consider Prose Agent Returns as Alternative Architecture

This is a bigger architectural question. The Anthropic pattern is:
1. Agents return prose to orchestrator
2. Orchestrator writes files / posts comments

Our pattern is:
1. Agents write JSONL files directly
2. Assembler script validates the files

**Our pattern is stronger for trust guarantees** but creates the write-permission failure mode. The Anthropic pattern avoids the permission problem entirely but has no deterministic validation.

**Hybrid approach:** Keep our JSONL-on-disk pattern but add a fallback — if an agent returns prose instead of writing a file, the orchestrator writes the file from the agent's return value AND flags this in the validation report as "orchestrator-written, not agent-written." This preserves the trust signal while handling the permission failure gracefully.

### Change 6: `allowed-tools` Should Include `Task` and `TodoWrite`

`plugin-dev` explicitly lists `Task` and `TodoWrite` in its allowed-tools. We should add these for agent spawning and progress tracking.

---

## Implementation Priority

| # | Change | Effort | Impact |
|---|--------|--------|--------|
| 1 | Agent definition files | Medium | Fixes write permissions structurally |
| 2 | Slim SKILL.md | Medium | Reduces context pressure, cleaner separation |
| 3 | TodoWrite tracking | Low | Observability for user |
| 4 | Scripts stay as-is | None | Already correct |
| 5 | Prose fallback architecture | High | Resilience, but complex |
| 6 | Add Task/TodoWrite to allowed-tools | Trivial | Enables 1 and 3 |

**Recommended order:** 6 → 1 → 2 → 3 → 5

---

## Appendix: Detailed Skill Profiles

### A. `code-review` (anthropics/claude-code/plugins/code-review)

- **Structure:** Single file (`code-review.md`), ~80 lines. No agents/, no scripts/.
- **Agents:** 8+ inline agents (haiku for triage, sonnet for summary/compliance, opus for bugs/logic).
- **Validation:** Agent-as-validator — each finding gets a confirmation subagent. No schema enforcement.
- **Model tiering:** Haiku → Sonnet → Opus pipeline. Cheapest model for cheapest task.
- **Notable:** The "no context outside the diff" constraint on bug agents is intentional false-positive suppression.

### B. `skill-creator` (anthropics/skills/skill-creator)

- **Structure:** SKILL.md + 3 agents/ + 1 references/ + 9 scripts/ + eval-viewer/.
- **Agents:** Grader, Comparator, Analyzer. Grader critiques the eval assertions themselves.
- **Validation:** Python scripts for schema validation. Grader agent for semantic validation.
- **Progressive contexting:** Textbook 3-tier. SKILL.md ~500 lines (at its own recommended limit). Scripts execute without loading into context.
- **Notable:** Train/test split for description optimization. Zero-dependency eval viewer (Python stdlib only). Platform-adaptive (Claude.ai vs Cowork vs Claude Code).

### C. `feature-dev` (anthropics/claude-code/plugins/feature-dev)

- **Structure:** 1 command + 3 agents. No scripts.
- **Agents:** code-explorer (parallel, 2-3x), code-architect (parallel, 2-3x, opinionated), code-reviewer (parallel, 3x, confidence-gated).
- **Validation:** Human gates. Reviewer confidence score ≥80 threshold.
- **Progressive contexting:** Orchestrator re-reads files after agents return (explicit workaround for context isolation).
- **Notable:** Architect agents give ONE recommendation each; optionality reconstructed by running 3 architects with different stances.

### D. `plugin-dev` (anthropics/claude-code/plugins/plugin-dev)

- **Structure:** 1 command + 3 agents + 7 skills (each with references/ + examples/ + scripts/).
- **Agents:** agent-creator (Write+Read, sonnet), plugin-validator (Read+Grep+Glob+Bash, inherit), skill-reviewer (Read+Grep+Glob, inherit). Least privilege per agent.
- **Validation:** `plugin-validator` runs shell scripts. `skill-reviewer` does prose analysis.
- **Progressive contexting:** Phase-gated skill loading. The command assigns specific skills to specific phases. This is the most sophisticated context management of all 4.
- **Notable:** Self-referential design. TodoWrite mandatory. Description-as-router architecture.
