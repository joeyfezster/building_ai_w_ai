---
type: plan
status: wip
created: 2026-03-14
updated: 2026-03-14
supersedes: streamline_work_plan.md
---

# PR Review Pack v3 — Work Plan

**Owner**: Joey + Claude
**Predecessor**: `docs/proposals/streamline_work_plan.md` (complete)
**Last updated**: 2026-03-14

This plan addresses 7 issues identified during fork validation of the streamlined review pack skill on LangChain PR #35788 and FastAPI PR #15067. All fixes are repo-agnostic and core to the skill pipeline.

---

## Design Decisions (settled, don't re-litigate)

- **Key Findings card**: Proposal B "Corroboration Lens" — compact table with severity heatbar, agent filter pills, corroboration badges. Findings sorted severity-first (F before C before B, regardless of corroboration count). A-grade findings collapsed by default.
- **Dual paradigm**: Key Findings (concept-first, "so what?") + Code Review (per-file, "did we miss anything?"). Both cards remain; Key Findings sits between Arch Assessment and Code Review. Code Review card renamed to "File Coverage".
- **Review gates**: 4 universal gates (CI, Deterministic, Agentic, Comments). Factory-specific gates only appear when factory artifacts exist.
- **Hybrid reviewer output**: Per-file objects first (exhaustive coverage), then concept objects (notable findings). Both in the same .jsonl. Validated deterministically.
- **Zone registry location**: Root (`zone-registry.yaml`) is primary. `.claude/zone-registry.yaml` is fallback. Rationale: not all repos use Claude workflows.
- **Reviewer model**: `opus` (opus-latest) for all 5 reviewers + synthesis. Not sonnet.
- **Validation loop**: `assemble_review_pack.py --validate-only` is the chokepoint. No valid JSONL = no assembly = no HTML = no review pack. The assembler is a script, not agent discretion. Failing to activate this loop leads to poor quality outputs and loss of trust in the artifact.
- **ConceptUpdate merging**: updated fields override the previous object's fields (matched by concept_id). The .jsonl is append-only; the assembler resolves updates at read time.

---

## Phase 1: Schema & Model Updates

### 1.1 FileReviewOutcome Model
- [ ] Add `FileReviewOutcome` pydantic model to `packages/pr-review-pack/scripts/models.py`
  - Fields: `_type: "file_review"` (literal discriminator), `file` (str, required), `grade` (Grade), `summary` (str, 1-2 sentences), `reviewed` (bool, default true)
  - Purpose: exhaustive per-file coverage — one per diff file per reviewer
- [ ] Add `ConceptUpdate` pydantic model to `models.py`
  - Fields: `_type: "concept_update"` (literal discriminator), `concept_id` (str, required), plus all optional ReviewConcept fields
  - Semantics: provided fields override the previous object's (matched by concept_id) fields. Missing fields are preserved from the original.
- [ ] Generate updated JSON schemas from pydantic models
- [ ] Update example .jsonl files in `references/examples/` to show the new hybrid format:
  - File review outcomes first, then concepts, then (optionally) concept updates
- [ ] Add unit tests for new models (validation, edge cases, update merging)

### 1.2 Assembler Updates for Hybrid Output
- [ ] Update `read_and_validate_jsonl()` to handle 4 line types via `_type` discriminator:
  - `"file_review"` → FileReviewOutcome
  - (no `_type` or absent) → ReviewConcept (backward compatible)
  - `"concept_update"` → ConceptUpdate
  - `"architecture_assessment"` → ArchitectureAssessmentOutput (existing)
- [ ] Add concept update merging logic: when reading JSONL, ConceptUpdate lines overwrite fields on the previously-seen ReviewConcept with the same concept_id. If no matching concept_id exists, log as error.
- [ ] Add `transform_file_outcomes_to_code_review()` — maps FileReviewOutcome objects to the per-file Code Review card data (per-file, per-agent grid)

### 1.3 Validation Chokepoint: `assemble_review_pack.py --validate-only`
**This is the enforcement mechanism. The assembler is the only script that can produce the review pack data JSON. It refuses to assemble if validation fails.**

- [ ] Add `--validate-only` flag to `assemble_review_pack.py`
  - Runs all validation checks (schema, cascading, coverage)
  - Outputs structured error report as JSON to stdout
  - Exit code 0 = valid, exit code 1 = errors found
  - Does NOT produce `_review_pack_data.json` — validation only
- [ ] Cascading validation checks (run in `--validate-only` AND in normal assembly mode):
  1. **Schema validation**: every JSONL line parses against its pydantic model (existing)
  2. **File coverage**: every file in diff_data has a FileReviewOutcome from every reviewer agent. Missing = error, reported per-file per-agent.
  3. **Concept backing**: every non-A-grade FileReviewOutcome must be represented in at least one ReviewConcept (matched by file path). A file graded B with no concept explaining why = error.
  4. **Concept ID uniqueness**: no duplicate concept_ids within an agent (existing)
  5. **Zone validity**: zone IDs exist in registry (existing)
  6. **File path validity**: referenced files exist in diff data (existing)
- [ ] Normal assembly mode (no `--validate-only`): runs the same checks first. If any errors: prints structured report, exits 1, does NOT produce output JSON.
- [ ] The SKILL.md Phase 2 orchestration loop:
  1. Reviewer writes .jsonl
  2. Orchestrator runs `python3 assemble_review_pack.py --validate-only --pr {N}`
  3. If exit 0 → proceed to next reviewer or assembly
  4. If exit 1 → feed error report to reviewer, reviewer appends corrections, re-validate
  5. Max 2 correction iterations (3 total attempts)
  6. If still failing → swap banner to "review output validation iterations did not converge", proceed with partial output, do NOT apply Phase 4 (banner remains visible)
- [ ] Add unit tests: validation pass, validation fail (missing file coverage), validation fail (concept backing gap), partial output assembly

---

## Phase 2: SKILL.md Rewrite

### 2.1 Grand Purpose
- [ ] Add "Reverse Compilation" framing to top of SKILL.md:
  - AI coding tools serve as **compilers** that translate from natural language (the semantic layer) into code (the code layer)
  - The volume of generated code becomes unsustainable for humans to review at the speed of generation
  - This skill performs **reverse compilation**: given a pull request — which is fundamentally in the code layer — it translates back to a semantic layer where a human reviewer can reason about changes, decisions, and impact, and make next-steps decisions
  - The entire skill pipeline is designed to achieve this reverse compilation effectively, transparently, and with deep commitment to creating trust in the review pack as an artifact for decision-making
- [ ] Add trust mandate: every phase exists to build trust in the artifact. Skipping any phase degrades trust. The review pack is only as trustworthy as the weakest phase that produced it.

### 2.2 Phase Enforcement
- [ ] Add explicit warnings to each phase about what happens when skipped:
  - Phase 1 skipped: no diff data, nothing to review
  - Phase 2 skipped: no findings, empty review pack
  - Phase 3 skipped: no validated output, raw agent claims unverified
  - Phase 4 skipped: self-review banner remains, trust degraded, no quality gate

### 2.3 Validation Loop
- [ ] Document the reviewer correction loop in Phase 2:
  1. Spawn 5 reviewers (opus model)
  2. After each reviewer completes, run `assemble_review_pack.py --validate-only --pr {N}`
  3. If validation fails: construct error report, re-spawn reviewer with errors + original context + instruction to append corrections
  4. Max 2 correction iterations per reviewer (3 total attempts)
  5. If still failing after 3 attempts: swap banner text to "review output validation iterations did not converge", proceed with partial output, do NOT apply Phase 4 so the banner remains visible as a trust signal
- [ ] Document FileReviewOutcome requirement: reviewers emit per-file objects FIRST, then concepts
- [ ] Document ConceptUpdate mechanism for append-only corrections
- [ ] Make clear: failing to activate this loop leads to poor quality outputs and loss of trust. The loop is not optional — it is the mechanism by which the skill guarantees output quality.

### 2.4 Zone Registry
- [ ] Change lookup order: root first (`zone-registry.yaml`), then `.claude/zone-registry.yaml`
- [ ] Add rationale: not all repos use Claude workflows; the skill's soft requirement shouldn't impose Claude-specific file structure

### 2.5 Reviewer Model
- [ ] Change agent spawn template to specify `model: "opus"` for all 5 reviewers
- [ ] Change synthesis agent to specify `model: "opus"` (already was, confirm)

### 2.6 Review Gates Redesign
- [ ] Document the 4-gate model:
  - Gate 1: CI — repo's own CI checks pass (`gh pr checks`)
  - Gate 2: Deterministic Review — vulture, bandit, ruff (if config exists), mypy (if config exists), test quality scanner. Outputs visible on click-to-expand in the review gates card.
  - Gate 3: Agentic Review — 5 reviewers + synthesis complete. C-grade findings → yellow. F-grade → red.
  - Gate 4: PR Comments — all review threads resolved
- [ ] Document: factory gates (Gate 0 Two-Tier, scenarios) only appear when factory artifacts exist

---

## Phase 3: Review Prompt Updates

### 3.1 All 5 Reviewer Prompts
- [ ] Update all 5 paradigm prompts (`packages/review-prompts/*.md`) to instruct:
  1. **First**: emit one `FileReviewOutcome` per file in the diff (grade + 1-2 sentence summary). Every file must be covered.
  2. **Then**: emit `ReviewConcept` objects for notable findings (B or lower grade, or A-grade insights worth calling out)
  3. **Why**: explain the reverse compilation framing — the human reviewer is not likely to look at the code. The agent must work in conjunction with the rest of the skill artifacts to produce a trustworthy, next-steps-decision-enabling review pack.
  4. **Correction**: if the orchestrator feeds back validation errors, emit `ConceptUpdate` or corrected `FileReviewOutcome` objects as new lines (append-only)
- [ ] Use `/skill-creator` capabilities to craft prompts that communicate *what* we are trying to achieve (reverse compilation, trust-building) and *why* the output format matters (it feeds deterministic validation and rendering pipelines)
- [ ] Remove Tier 1 / Gate 0 references from prompts (these are factory-specific; the shared paradigm is reviewer-agnostic)
- [ ] Ensure prompts work for any repo (no factory assumptions)

### 3.2 Synthesis Prompt
- [ ] Update `synthesis_review.md` to read FileReviewOutcome data in addition to ReviewConcept
- [ ] Synthesis should identify corroborated findings (same file/issue flagged by multiple agents) and note corroboration in its output

---

## Phase 4: Review Gates Implementation

### 4.1 Extract Deterministic Tools
- [ ] Identify which Gate 0 tools from `packages/dark-factory/scripts/run_gate0.py` are universally applicable:
  - `vulture` (dead code) — universal
  - `bandit` (security) — universal
  - `ruff` (lint) — only if ruff config exists in target repo
  - `mypy` (type check) — only if mypy config exists in target repo
  - `check_test_quality.py` (test scanner) — universal
- [ ] Create `packages/pr-review-pack/scripts/run_deterministic_review.py` — runs applicable tools, outputs structured results
  - Auto-detect which tools are installed/configured in the target repo
  - Output format: JSON with per-tool pass/fail + findings (tool output visible in review gates card)
- [ ] Add unit tests for the deterministic review runner

### 4.2 Scaffold & Renderer Updates
- [ ] Update `scaffold_review_pack_data.py` `build_convergence()` to use 4-gate model
  - Gate 1: CI (from `gh pr checks` — already works)
  - Gate 2: Deterministic (from `run_deterministic_review.py` output)
  - Gate 3: Agentic (from assembler — reviewer completion + grade summary)
  - Gate 4: Comments (from prerequisite check — already works)
- [ ] Remove hardcoded factory gates (Gate 0 Two-Tier, Gate 3 Scenarios)
- [ ] Add factory gates conditionally when factory artifacts exist
- [ ] Update `render_review_gates_cards()` to render clickable gate sub-cards with detail content (tool outputs expandable)
- [ ] Add unit tests for the new gate model

---

## Phase 5: Key Findings Card

### 5.1 Template Updates
- [ ] Add `section-key-findings` section to `template_v2.html` between arch assessment and code review
- [ ] Add `<!-- INJECT: key findings section -->` marker
- [ ] Add CSS for: severity heatbar, agent filter pills, corroboration badges, finding rows, expanded detail
- [ ] Add dark mode CSS for all new elements
- [ ] Agent 2-letter codes have tooltip on hover: full agent name + short paradigm description

### 5.2 Renderer
- [ ] Add `render_key_findings()` function to `render_review_pack.py`
  - Input: `agenticReview.findings` (the concept-level findings)
  - Groups findings by severity (F → C → B → B+ → A)
  - Within same severity: sorted by corroboration count (descending)
  - Severity always trumps corroboration for sort order
  - A-grade findings collapsed behind toggle by default
  - Corroboration detection: finds findings with overlapping files + similar titles across agents
- [ ] Add `render_key_findings_nav()` for sidebar icon states:
  - Any F → `count-fail` with F-count
  - Worst C → `count-warn` with C+F count
  - Worst B/B+ → `count` with non-A count
  - All A → `pass` checkmark
- [ ] Wire injection into the render pipeline

### 5.3 JavaScript
- [ ] Add agent filter pill click handlers (filter table to selected agent)
- [ ] Add zone filtering integration (clicking zone chips filters Key Findings too)
- [ ] Add expand/collapse row handlers
- [ ] Add A-grade toggle handler

### 5.4 File Coverage Card (renamed from Code Review)
- [ ] Rename section from "Code Review" to "File Coverage"
- [ ] Populate from FileReviewOutcome data (per-file, per-agent grid)

---

## Phase 6: Architecture Assessment Graceful Degradation

- [ ] Update assembler: partial validation failure should retain validated fields, not discard entirely
  - If `overallHealth` and `summary` validate but `zoneChanges` fails: render with what validated
  - If entire assessment fails: show "Assessment produced but contained validation errors" with error details
- [ ] Add consistency check: if `overallHealth` is "needs-attention" or worse, summary must not start with positive language ("good shape", "healthy", etc.) — flag as warning
- [ ] Add unit tests for partial validation scenarios

---

## Phase 7: Playwright Tests

### 7.1 Key Findings Card Tests
- [ ] Every finding has all expected fields on collapsed row (grade, title, agent tag, zone tag, corroboration badge)
- [ ] Expansion shows: summary, corroborating agents (when applicable), file list
- [ ] Every finding expansion must have at least one file reference — Playwright fails if any finding has zero files (this was a bug in fork validation)
- [ ] All file references are clickable and open diff modal with file diff data visible in all 3 modes (unified, split, raw)
- [ ] Zone chip clicks filter findings
- [ ] Agent pill clicks filter findings
- [ ] Mouse hover over agent 2-letter codes shows tooltip with agent full name and short paradigm description
- [ ] Sidebar nav icon states sync with findings data:
  - Test with F-grade data → red icon
  - Test with C-grade worst → amber icon
  - Test with B-grade worst → blue icon
  - Test with all A → green check
- [ ] A-grade toggle shows/hides A findings
- [ ] Severity heatbar segments proportional to grade distribution
- [ ] Dark mode renders correctly for all new elements

### 7.2 Review Gates Tests
- [ ] 4 gates render with correct labels and status
- [ ] Gate chips in navbar are color-synced with gate state (green/yellow/red)
- [ ] Gate sub-cards are clickable and show detail (including deterministic tool outputs)
- [ ] Factory gates only appear when factory data exists
- [ ] Non-factory fixture shows only universal gates

### 7.3 File Coverage Card Tests
- [ ] Per-file, per-agent grid populated from FileReviewOutcome data
- [ ] Missing coverage flagged visually
- [ ] Modify existing code review tests to match new File Coverage card format (keep them, just update for rename and new data source)

### 7.4 Baseline Suite Updates
- [ ] Update `e2e/review-pack-v2.spec.ts` baseline tests for new card structure
- [ ] Add new fixture data files for Key Findings scenarios
- [ ] All existing tests pass or are updated (no silent breakage)

---

## Phase 8: End-to-End Validation

### 8.1 Monorepo Validation
- [ ] Run full `/pr-review-pack` on a real PR in this monorepo
- [ ] Verify: FileReviewOutcome + ReviewConcept both produced
- [ ] Verify: Key Findings card renders with corroboration
- [ ] Verify: File Coverage card shows per-file coverage from FileReviewOutcome
- [ ] Verify: Review gates show universal gates (no factory-specific)
- [ ] Verify: Playwright tests pass

### 8.2 Fork Validation (4 PRs)
- [ ] Identify 2 PRs from `langchain-ai/langchain` and 2 from `tiangolo/fastapi`
  - PRs should have: 5-20 files, meaningful code changes, CI checks run
  - PR candidates:
    - **LangChain #35603** — "fix: backport patch ReDoS vulnerability (CVE-2024-58340)" — 8 files, 66+/139-, security fix
    - **LangChain #35542** — "feat(fireworks,groq,openrouter): add standard model property" — 9 files, 31+/3-, cross-partner feature
    - **FastAPI #14978** — "Add strict_content_type checking for JSON requests" — 12 files, 411+/9-, new security feature
    - **FastAPI #14962** — "Serialize JSON response with Pydantic (in Rust)" — 10 files, 196+/74-, performance optimization
- [ ] For each PR, spawn a **completely independent subagent** with:
  - Fresh context (no plan file knowledge)
  - Only the SKILL.md and the PR number
  - Zone registry created fresh (or use existing if repo has one)
  - Full 4-phase pipeline execution
- [ ] Verify each review pack:
  - Key Findings card populated with real findings
  - File Coverage card shows per-file coverage
  - Review gates show universal gates
  - No self-review banner (Phase 4 completed)
  - Architecture assessment renders (even if partial)
- [ ] Document: PR URL, wall-clock time, compaction count, issues found

---

## Progress Log

| Timestamp | Phase | Status | Notes |
|-----------|-------|--------|-------|
| 2026-03-14T~20:00 | Plan | COMPLETE | Plan created from Joey's feedback on fork validation results |
| 2026-03-14T~21:00 | Plan | UPDATE | Joey's inline feedback incorporated: validation chokepoint design, ConceptUpdate merge semantics, banner text for non-convergence, reverse compilation framing detail, deterministic tool output visibility, Playwright test specifics |
| 2026-03-14T14:36 | 1.1 | COMPLETE | Added FileReviewOutcome + ConceptUpdate models to models.py, updated export_json_schemas() |
| 2026-03-14T14:36 | 1.2 | COMPLETE | Rewrote read_and_validate_jsonl() for 4-type JSONL routing with ConceptUpdate merging |
| 2026-03-14T14:36 | 1.3 | COMPLETE | Added validate_file_coverage(), validate_concept_backing() cascading validation functions |
| 2026-03-14T14:36 | 1.4 | COMPLETE | Updated assemble() for 4-tuple return, cascading validation chokepoint (refuses on errors), transform_file_outcomes_to_coverage(), zone registry root-first |
| 2026-03-14T14:36 | 1.5 | COMPLETE | Added --validate-only flag to main() with explicit pass/fail exit codes |
| 2026-03-14T14:36 | 1.6 | COMPLETE | 12 new tests (TestHybridJSONL, TestCascadingValidation, TestFileCoverageTransform), 11 new model tests (TestFileReviewOutcome, TestConceptUpdate). All 465 tests pass. |
| 2026-03-14T14:36 | 1.7 | COMPLETE | Generated JSON schemas for all 5 model classes |
| 2026-03-14T15:10 | 2 | COMPLETE | SKILL.md rewritten: reverse compilation framing, 4-gate model, hybrid output docs, validation loop docs, zone registry root-first, opus model, phase enforcement warnings |
| 2026-03-14T15:25 | 3 | COMPLETE | All 6 reviewer prompts updated: removed Gate 0/factory references, added hybrid output (FileReviewOutcome+ReviewConcept), added ConceptUpdate correction protocol, reverse compilation framing, repo-agnostic |
| 2026-03-14T15:40 | 4.1 | COMPLETE | Created run_deterministic_review.py (vulture, bandit, ruff, mypy with auto-detection) |
| 2026-03-14T15:40 | 4.2 | COMPLETE | Updated build_convergence() to 4-gate model: Gate 1 CI, Gate 2 Deterministic, Gate 3 Agentic, Gate 4 Comments. Factory gates conditional. |
| 2026-03-14T16:00 | 5 | COMPLETE | Key Findings card (Proposal B): template CSS+HTML+JS, renderer (corroboration detection, heatbar, agent pills, severity sort), sidebar nav, File Coverage rename |
| 2026-03-14T16:15 | 6 | COMPLETE | Architecture assessment graceful degradation: partial validation retains overallHealth+summary, consistency check for positive language vs negative health. 5 new tests. |
| 2026-03-14T16:30 | 7 | COMPLETE | Playwright tests updated: section-code-review→section-file-coverage, 4-gate model tests, Key Findings card tests (7 tests), File Coverage tests (2 tests), Review Gates tests (3 tests) |
| 2026-03-14T16:45 | 8 | READY | Phases 1-7 complete. 470 Python tests pass. Phase 8 (E2E validation) requires running the full skill pipeline — separate session. Monorepo PR #17 available for 8.1. Fork PRs identified for 8.2. |
| | | | |
