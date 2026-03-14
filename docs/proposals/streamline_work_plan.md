# PR Review Pack Streamlining — Work Plan

**Owner**: Claude (overnight execution)
**Proposal**: `docs/proposals/streamline_review_pack.md` (read this first after compaction)
**Status**: IN PROGRESS
**Last updated**: 2026-03-14

## Recovery Instructions (read after context compaction)

If you've context-compacted, do this:
1. Read THIS file first
2. Read `docs/proposals/streamline_review_pack.md` for full proposal context
3. Load the `/skill-creator` skill for SKILL.md writing context (read `/Users/joey/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/SKILL.md`)
4. Check the progress checkboxes below to find where you left off
5. Resume from the first unchecked item

## Key Files

| File | Purpose |
|------|---------|
| `docs/proposals/streamline_review_pack.md` | The approved proposal — source of truth for all design decisions |
| `packages/pr-review-pack/SKILL.md` | The skill entry point — WS4 rewrites this |
| `packages/pr-review-pack/scripts/` | Pipeline scripts — WS2 and WS3 add new ones here |
| `packages/pr-review-pack/references/` | Reference docs (schemas, specs) |
| `packages/pr-review-pack/e2e/` | Playwright tests |
| `packages/pr-review-pack/tests/` | Python unit tests |
| `packages/review-prompts/` | 5 paradigm prompts — WS1 updates these |
| `zone-registry.yaml` | Architecture zone registry (repo root) |
| `packages/dark-factory/docs/code_quality_standards.md` | Factory quality standards |

## Critical Design Decisions (don't re-litigate these)

- Agents spawned with Read + Write ONLY (no Bash)
- Agent identity derived from filename, NOT a field in the schema
- Zones normalized to `string[]` everywhere, must match zone-registry.yaml keys
- Synthesis agent runs AFTER 5 reviewers (not parallel), uses highest-reasoning model, WILL see peer outputs
- .jsonl files are git-tracked in `docs/reviews/pr{N}/`, excluded from recursive review packs
- Valid grades: A, B+, B, C, F (NO N/A)
- Quality standards: discover copilot-instructions.md, CLAUDE.md, factory standards — reviewers treat with scrutiny, not as gospel
- Pydantic validation COUPLED with Anthropic structured outputs (not either/or)
- Orchestrator still spawns agents and handles errors/retries; it no longer reads diffs, constructs prompts, or parses JSON
- ReviewConcept → AgenticFinding transform: start with script, escalate to agent if needed
- Both factory and non-factory artifact cases must work and be tested

---

## Phase 1: Research & Schema (WS1)

### 1.1 Structured Outputs Investigation
- [ ] Test whether Claude Code's Agent tool supports `output_config` / structured output constraints
- [ ] Adversarially test: intentionally malformed prompts, edge cases, schema constraint violations
- [ ] Document findings in `packages/pr-review-pack/references/structured-outputs-findings.md`
- [ ] Determine the recommended enforcement path: Agent tool native or pydantic-only fallback
- [ ] NOTE: No API key available — direct API wrapper approach is OUT OF SCOPE. Testing is limited to what Claude Code's Agent tool exposes natively.

### 1.2 ReviewConcept Schema
- [ ] Define `ReviewConcept` pydantic model in `packages/pr-review-pack/scripts/models.py` (or similar)
  - Fields: concept_id, title, grade (A/B+/B/C/F), category, summary, detail_html, locations[]
  - locations[]: file, lines, zones (string[], validated against zone-registry), comment
  - NO agent field
  - Single-location concepts explicitly valid
  - Zone ID validator: must match zone-registry.yaml keys, lowercase-kebab-case
- [ ] Define `SemanticOutput` pydantic model (typed union: what_changed, decision, post_merge_item, factory_event)
- [ ] Generate JSON schema files (`.schema.json`) from pydantic models
- [ ] Create 2-3 example `.jsonl` files as reference in `packages/pr-review-pack/references/examples/`

### 1.3 Synthesis Agent Design
- [ ] Determine: 6th paradigm prompt or different kind of agent?
- [ ] Design the prompt: highest-reasoning model, reads codebase + diff + all 5 reviewer .jsonl outputs
- [ ] Define what it produces: whatChanged (infrastructure/product), decisions, postMergeItems, factoryHistory (optional)
- [ ] Write the prompt/paradigm doc

### 1.4 Update Paradigm Prompts
- [ ] Update 5 existing paradigm prompts to output ReviewConcept .jsonl format
- [ ] Add: "Write .jsonl to {output_path}" instruction (output path is passed by orchestrator)
- [ ] Add: "Use Read tool for all file access, never Bash"
- [ ] Add: quality standards discovery (copilot-instructions.md, CLAUDE.md) with scrutiny guidance
- [ ] Add: zone ID validation guidance (must match zone-registry.yaml)
- [ ] Add: grade guidance (A/B+/B/C/F only, explain if can't assess, no N/A)
- [ ] Verify prompts work for both factory and non-factory contexts (orchestrator controls output path)

---

## Phase 2: Scripts (WS2 + WS3)

### 2.1 Setup Script (`review_pack_setup.py`)
- [ ] Create `packages/pr-review-pack/scripts/review_pack_setup.py`
- [ ] Consolidate: prerequisites (gates 1-2) + Pass 1 (generate_diff_data) + Pass 2a (scaffold)
- [ ] Output diff data to `docs/reviews/pr{N}/pr{N}_diff_data_{base8}-{head8}.json`
- [ ] Output scaffold JSON to `docs/reviews/pr{N}/`
- [ ] Include gate0 conversion if gate0_tier2 files exist (`convert_gate0_to_jsonl.py` logic)
- [ ] Single python3 invocation with clear arguments
- [ ] Test: runs cleanly on current monorepo

### 2.2 Assembly Script (`assemble_review_pack.py`)
- [ ] Create `packages/pr-review-pack/scripts/assemble_review_pack.py`
- [ ] Read all .jsonl files from `docs/reviews/pr{N}/`
- [ ] Validate each line against pydantic models (ReviewConcept, SemanticOutput)
- [ ] Produce structured error report for any validation failures
- [ ] Transform ReviewConcept → AgenticFinding (zones format, gradeSortOrder, etc.)
- [ ] Transform SemanticOutput → whatChanged/decisions/postMergeItems/factoryHistory
- [ ] Merge into scaffold JSON
- [ ] Run verification checks:
  - File path verification (must exist in diff data)
  - Zone verification (must exist in registry, except "unzoned" architect findings)
  - Decision-zone verification (must have ≥1 file in zone's paths)
  - Code snippet verification (line numbers exist in file content)
  - Grade validity (A/B+/B/C/F only)
  - Concept ID uniqueness per agent
  - Zone coverage gaps (flag files with no zone)
  - HTML sanitization (detail_html is valid HTML)
  - Coverage gaps (files in diff no agent mentioned)
  - Severity inflation detection
  - Cross-reference verification (referenced functions exist)
  - Contradiction detection between agents
- [ ] Compute status model
- [ ] Call render_review_pack.py
- [ ] Auto-generate Tier 1 Playwright test from review pack data
- [ ] Run baseline Playwright suite + PR-specific tests
- [ ] If tests fail: iteratively fix and re-run until passing (assembler is accountable)
- [ ] Report results including validation errors for recovery
- [ ] Test: runs cleanly with sample .jsonl data

### 2.3 Unit Tests for New Scripts
- [ ] Add unit tests for `review_pack_setup.py` to existing test suite
- [ ] Add unit tests for `assemble_review_pack.py`:
  - Validation logic
  - Transform logic (ReviewConcept → AgenticFinding)
  - Verification checks
  - Error reporting
- [ ] Verify all tests pass in CI

---

## Phase 3: SKILL.md Update (WS4)

- [ ] Load `/skill-creator` skill context before starting this phase
- [ ] Read current SKILL.md to understand what exists
- [ ] Rewrite to 4-phase flow: Setup → Review → Assemble → Deliver
- [ ] Remove all inline orchestration logic
- [ ] Point to scripts as tools (review_pack_setup.py, assemble_review_pack.py)
- [ ] Define agent spawn pattern: Read + Write only, no Bash
- [ ] Include quality standards discovery guidance (copilot-instructions.md, CLAUDE.md, factory standards — with scrutiny)
- [ ] Define synthesis agent sequencing (after 5 reviewers, highest-reasoning model)
- [ ] Keep under 500 lines per skill-creator guidance
- [ ] Use progressive disclosure: metadata → SKILL.md body → bundled resources

---

## Phase 4: Portability (WS5)

### 4.1 Zone Registry
- [ ] Verify zone-registry.yaml is at repo root in current monorepo (move if not)
- [ ] Create `zone-registry.example.yaml` to ship with the skill
- [ ] Document as the one required adoption artifact

### 4.2 Exclusion Patterns
- [ ] Verify `docs/reviews/*` pattern covers ALL file types created in the reviews directory
- [ ] Test with fnmatch against: .jsonl, .json, .html, .ts (Playwright tests)

### 4.3 Factory Optionality
- [ ] Test scaffold script with factory artifacts present (convergence, factory history, specs, scenarios)
- [ ] Test scaffold script WITHOUT factory artifacts — verify clean skip, no broken/empty JSON
- [ ] Test template rendering in both cases — verify graceful hiding, no broken cards
- [ ] Verify Playwright suite covers both cases (extend if not)

### 4.4 Onboarding Docs
- [ ] Update skill README
- [ ] Update SKILL.md "getting started" section for non-factory repos
- [ ] Update monorepo README if needed
- [ ] Minimum adoption path documented: (1) add zone-registry.yaml, (2) invoke /pr-review-pack {N}

---

## Phase 5: Integration Testing on Current Repo

- [ ] Run the full streamlined skill end-to-end on a real PR in the monorepo
- [ ] Verify: setup → review (5 agents + synthesis) → assemble → deliver
- [ ] Verify: .jsonl files created, validated, transformed correctly
- [ ] Verify: HTML review pack renders correctly
- [ ] Verify: Playwright tests pass
- [ ] Verify: permission count is 3-4 (not 16-36+)
- [ ] Flag any issues with the "agents produce clean schema, assembler translates" thesis

---

## Phase 6: Open Source Fork Validation

**This is the final validation step. Each fork must run in an independently-contexted agent session.**

### 6.1 LangChain Fork
- [ ] Fork `langchain-ai/langchain`
- [ ] Identify an open PR with 600+ lines of changes (AI-generated code preferred)
- [ ] Create `zone-registry.yaml` at fork root
- [ ] Run streamlined `/pr-review-pack` skill in a fresh, independent agent session
- [ ] Deliver the generated review pack for Joey's review
- [ ] Document: PR chosen, PR URL, why this PR showcases value

### 6.2 FastAPI Fork
- [ ] Fork `tiangolo/fastapi`
- [ ] Identify an open PR with 600+ lines of changes (AI-generated code preferred)
- [ ] Create `zone-registry.yaml` at fork root
- [ ] Run streamlined `/pr-review-pack` skill in a fresh, independent agent session
- [ ] Deliver the generated review pack for Joey's review
- [ ] Document: PR chosen, PR URL, why this PR showcases value

---

## Progress Log

Track significant milestones and issues here as work progresses:

| Timestamp | Phase | Status | Notes |
|-----------|-------|--------|-------|
| 2026-03-14 | Plan | COMPLETE | Plan created, proposal .md finalized |
| | | | |
