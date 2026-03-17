# Proposed Changes: Applying Anthropic Skill Patterns to PR Review Pack

**Date:** 2026-03-14
**Source:** [Anthropic Skill Architecture Research](../research/anthropic_skill_architecture.md)
**Target:** `packages/pr-review-pack/`

---

## Current State

Our SKILL.md is ~430 lines and growing. It contains:
- Full workflow specification (4 phases)
- Inline agent spawn templates with schema references
- Validation loop pseudocode
- Output format instructions per agent
- Schema summary tables
- Reference file tables
- Grade scale definitions

All of this is **Tier 2** — loaded on every invocation regardless of phase. The orchestrator reads the entire playbook before doing anything.

In 3 rounds of fork validation (12 sessions total), we've observed:
- Subagent write permission failures (11 of 20 reviewer files ghost-written in round 2)
- Validation feedback loop never firing (all 12 sessions)
- Phase 4 (Playwright) skipped universally (all 12 sessions)
- Files with zero agent coverage passing through to the final pack
- Permission prompt fatigue from granular allowed-tools

---

## Change 1: Create Agent Definition Files

**Pattern source:** plugin-dev, feature-dev, pr-review-toolkit

**Current:** Agents defined inline in SKILL.md spawn templates. No persistent identity, no tool declarations, no frontmatter.

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

Each file gets frontmatter following the Anthropic pattern:
```yaml
---
name: code-health-reviewer
description: Reviews PR code changes for code quality, complexity, dead code, naming, and maintainability
model: opus
tools: [Read, Write, Glob, Grep]
---
```

The body contains everything the agent needs:
- Paradigm prompt reference path
- Context files to read (diff data, zone registry, quality standards)
- Output file path pattern
- Output format specification (hybrid JSONL)
- Correction protocol (append-only ConceptUpdate lines)

**Impact:**
- Solves write-permission problem structurally via `tools: [Write]` in frontmatter
- Removes ~100 lines from SKILL.md (spawn templates, output format specs)
- Each agent has a persistent identity the orchestrator can reference by name
- Follows Anthropic's least-privilege pattern (no Bash, no Edit for reviewers)

**Effort:** Medium
**Status:** Agent files created in monorepo, SKILL.md not yet updated to reference them

---

## Change 2: Slim Down SKILL.md — Orchestrator as Conductor

**Pattern source:** plugin-dev (the gold standard), skill-creator ("keep SKILL.md under 500 lines")

**Current:** SKILL.md Phase 2 contains:
- Agent spawn template (~30 lines)
- Output format specification (~20 lines)
- Schema summary table (~10 lines)
- Grade scale (~10 lines)
- Validation feedback loop (~30 lines)
- Ghost-writing prohibition (~5 lines)
- Total: ~105 lines of Phase 2 content

**Proposed:** SKILL.md Phase 2 becomes a conductor:

```markdown
## Phase 2: Review (Agent Team)

Spawn 6 review agents. Each agent's instructions, output format, and context
requirements are defined in its agent file under `${CLAUDE_SKILL_DIR}/agents/`.

### Step 1: Spawn 5 Review Agents (Parallel)

| Agent | File |
|-------|------|
| code-health | `${CLAUDE_SKILL_DIR}/agents/code-health-reviewer.md` |
| security | `${CLAUDE_SKILL_DIR}/agents/security-reviewer.md` |
| test-integrity | `${CLAUDE_SKILL_DIR}/agents/test-integrity-reviewer.md` |
| adversarial | `${CLAUDE_SKILL_DIR}/agents/adversarial-reviewer.md` |
| architecture | `${CLAUDE_SKILL_DIR}/agents/architecture-reviewer.md` |

Spawn parameters: `model: "opus"`, `mode: "acceptEdits"`

### Step 1b: Validation Feedback Loop
[validation loop stays — it's orchestrator logic, not agent logic]

### Step 2: Spawn Synthesis Agent
Read agent file: `${CLAUDE_SKILL_DIR}/agents/synthesis-reviewer.md`
```

Phase 2 shrinks from ~105 lines to ~40 lines. The HOW lives in the agent files. The WHEN and WHY stays in the conductor.

**What stays in SKILL.md:**
- Phase structure and gates
- Validation feedback loop (orchestrator logic)
- Ghost-writing prohibition (orchestrator constraint)
- Phase 4 hard gate (orchestrator enforcement)

**What moves to agent files:**
- Paradigm prompt paths
- Output format specifications
- Schema references
- Context file lists
- Correction protocol

**What moves to reference files (already done):**
- Schema definitions → `references/schemas/`
- Example .jsonl files → `references/examples/`

**Impact:** SKILL.md drops from ~430 lines to ~300 lines. Closer to the 500-line ceiling. More importantly, agents get their full instructions without polluting the orchestrator's context.

**Effort:** Medium

---

## Change 3: Add TodoWrite Phase Tracking

**Pattern source:** plugin-dev ("Use TodoWrite to track progress at every phase"), feature-dev ("Create todo list with all phases"), skill-creator ("Please add steps to your TodoList")

**Current:** No progress tracking. The user cannot tell what phase the orchestrator is in. If the session interrupts, there's no recovery state.

**Proposed:** Add to Pipeline Overview:

```markdown
**Progress tracking:** Use TodoWrite at the start of each phase:
- Phase 1: "Setup: running review_pack_setup.py"
- Phase 2: "Review: spawning 5 reviewer agents"
- Phase 2b: "Validation: running feedback loop for {agent}"
- Phase 3: "Assembly: running assemble_review_pack.py"
- Phase 4: "Delivery: running Playwright validation"
```

**Impact:** User can see real-time phase progress. Session interruptions leave a visible recovery marker.

**Effort:** Low

---

## Change 4: Broaden `allowed-tools` with Orchestration Tools

**Pattern source:** plugin-dev (`["Read", "Write", "Grep", "Glob", "Bash", "TodoWrite", "AskUserQuestion", "Skill", "Task"]`)

**Current:**
```yaml
allowed-tools: Bash(python3 *), Bash(npx playwright *), Bash(npm *), Bash(gh *),
  Bash(git *), Bash(ls *), Bash(sleep *), Bash(which *), Bash(mkdir *),
  Bash(open *), Bash(cat *), Read, Edit, Write, Glob, Grep
```

**Proposed:** Add orchestration tools:
```yaml
allowed-tools: Bash(python3 *), Bash(npx playwright *), Bash(npm *), Bash(gh *),
  Bash(git *), Bash(ls *), Bash(sleep *), Bash(which *), Bash(mkdir *),
  Bash(open *), Bash(cat *), Bash(wc *), Bash(cd *),
  Read, Edit, Write, Glob, Grep, Task, TodoWrite
```

Added: `Task` (for agent spawning), `TodoWrite` (for progress tracking), `Bash(wc *)`, `Bash(cd *)` (observed permission prompts in round 3).

**Impact:** Enables Changes 3 (TodoWrite) and proper agent dispatch. Eliminates `wc` and `cd` permission prompts.

**Effort:** Trivial

---

## Change 5: Scripts Stay as Scripts (Already Correct)

**Pattern source:** skill-creator (9 scripts), webapp-testing ("treat as black boxes"), mcp-builder (eval harness)

Our pattern of running Python scripts via Bash (`python3 "${CLAUDE_SKILL_DIR}/scripts/..."`) is exactly what Anthropic does. Zero-cost context usage for complex logic. No change needed.

---

## Change 6: Rethink Enforcement Language

**Pattern source:** skill-creator's writing philosophy

skill-creator explicitly warns:
> "If you find yourself writing ALWAYS or NEVER in all caps, or using super rigid structures, that's a yellow flag — reframe and explain the reasoning so that the model understands why the thing you're asking for is important."

Our SKILL.md currently has:
- "**HARD GATE — Phase 4 is not optional. You MUST execute it.**"
- "**CRITICAL: The main agent must NEVER write .jsonl content itself.**"
- "**This loop is non-negotiable.**"

These were added as desperate fixes after 12 sessions of non-compliance. The Anthropic philosophy suggests a different approach: explain WHY, not just WHAT.

**Proposed:** Keep the gates but reframe with reasoning:

Before:
> **HARD GATE — Phase 4 is not optional. You MUST execute it.**

After:
> **Phase 4 validates the rendered HTML.** The self-review banner signals to the reader that the pack was never machine-validated. In 8 test runs where this phase was skipped, the banner remained visible — the reader had no way to know whether the content was trustworthy. Run Playwright to validate, then remove the banner.

This is a longer-term change. The current MUST/NEVER language may still be necessary for now — we should test whether the reasoning-based approach actually improves compliance before removing the caps-lock enforcement.

**Effort:** Low
**Risk:** Compliance may regress. Test with 1 round before committing.

---

## Change 7: Consider Prose Agent Returns as Fallback

**Pattern source:** All 12+ Anthropic skills — none enforce structured JSON between agents and orchestrator

**Current:** Our agents write JSONL files directly. The assembler validates them. This is architecturally stronger for trust guarantees but creates the write-permission failure mode.

**The Anthropic pattern:**
1. Agents return prose to orchestrator
2. Orchestrator writes files / posts comments

**Hybrid approach:** Keep JSONL-on-disk as primary. Add a fallback:
- If an agent returns prose instead of writing a file, the orchestrator writes the file from the agent's return value
- Flag this in the validation report as "orchestrator-written, not agent-written"
- This preserves the trust signal while handling permission failure gracefully

**Impact:** Resilience against permission failures. The pack still gets produced even when Write permissions aren't granted to subagents.

**Effort:** High (requires changes to assembler + validation + trust reporting)
**Priority:** After Changes 1-4 prove whether the permission problem is solved structurally

---

## Implementation Priority

| # | Change | Effort | Impact | Status |
|---|--------|--------|--------|--------|
| 4 | Add Task/TodoWrite/wc/cd to allowed-tools | Trivial | Unblocks 1 and 3 | Not started |
| 1 | Agent definition files | Medium | Fixes permissions structurally | Agent files created, SKILL.md not updated |
| 2 | Slim SKILL.md | Medium | Context pressure, cleaner separation | Not started |
| 3 | TodoWrite tracking | Low | Observability | Not started |
| 5 | Scripts stay as-is | None | Already correct | Done |
| 6 | Rethink enforcement language | Low | Compliance (test first) | Not started |
| 7 | Prose fallback architecture | High | Resilience | Not started, deprioritized |

**Recommended order:** 4 → 1 → 2 → 3 → 6 → 7

---

## Round 3 Analysis Template

After analyzing the round 3 exports, add findings here:

| Session | Write Permissions | Validation Loop | Phase 4 | Files Covered | Ghost-Written |
|---------|------------------|-----------------|---------|---------------|---------------|
| langchain-35603 | ? | ? | ? | ? | ? |
| langchain-35542 | ? | ? | ? | ? | ? |
| fastapi-14978 | ? | ? | ? | ? | ? |
| fastapi-14962 | ? | ? | ? | ? | ? |
