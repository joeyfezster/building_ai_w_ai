# PR Review Pack — Streamlining Proposal

## Part 1: Current State Spec (As-Built)

### What It Is
A self-contained interactive HTML "Mission Control" report for PR review. Joey reviews the report, not the code. One read tells him whether to merge, what the risks are, and what to watch post-merge.

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR (Main Agent)                     │
│  Reads SKILL.md → drives the 3-pass pipeline → handles errors       │
│  Runs in Claude Code interactive session                             │
└──────────┬──────────────┬──────────────────┬────────────────────────┘
           │              │                  │
     ┌─────▼─────┐  ┌────▼──────────┐  ┌───▼──────┐
     │  PASS 1   │  │    PASS 2     │  │  PASS 3  │
     │ Diff Data │  │  Scaffold +   │  │ Renderer │
     │ (script)  │  │  Enrichment   │  │ (script) │
     └───────────┘  └───────────────┘  └──────────┘
```

### Pass 1: Diff Analysis (Deterministic)
- **Script:** `generate_diff_data.py`
- **Input:** `--base main --head HEAD`
- **Output:** `docs/pr{N}_diff_data.json` (current; proposed: `docs/reviews/pr{N}/pr{N}_diff_data_{base8}-{head8}.json`)
- **What it does:** Git diff extraction, per-file diffs, raw content, base content, additions/deletions, file status
- **LLM involvement:** None
- **Permission risk:** Low (single python3 command)

### Pass 2a: Deterministic Scaffold (No LLM)
- **Script:** `scaffold_review_pack_data.py`
- **Input:** `--pr N --diff-data ... --output ...`
- **Output:** `/tmp/pr{N}_review_pack_data.json`
- **What it does:** Populates header, status badges, architecture zones, specs, scenarios, CI performance, convergence, code diffs, status model, commit scope from git/GitHub API/factory artifacts
- **LLM involvement:** None
- **Permission risk:** Low (single python3 command)

### Pass 2b: Semantic Enrichment (6 Agents, LLM-Heavy)

**This is where most of the time, tokens, and permission problems live.**

#### Workstream A: Agentic Review (5 agents in parallel)

| Agent | Abbrev | Focus | Output |
|-------|--------|-------|--------|
| code-health-reviewer | CH | Quality, complexity, dead code | `AgenticFinding[]` |
| security-reviewer | SE | Vulnerabilities | `AgenticFinding[]` |
| test-integrity-reviewer | TI | Test quality | `AgenticFinding[]` |
| adversarial-reviewer | AD | Gaming, spec violations | `AgenticFinding[]` |
| architecture-reviewer | AR | Zone coverage, coupling, structure | `AgenticFinding[]` + `ArchitectureAssessment` |

Each agent receives: diff data JSON, zone registry YAML, paradigm prompt MD, code quality standards MD, and (for some) additional context (specs, file tree, scaffold architecture).

Each agent must output raw JSON in a prescribed schema. Common failures:
- Markdown code fences wrapping JSON
- `zones` as array instead of space-separated string
- `codeSnippets` (plural) instead of `codeSnippet` (singular)
- Missing `agent` abbreviation field → findings render with "?" badge
- Missing `gradeSortOrder`
- HTML in `notable` (should be plain text)

#### Workstream B: Synthesis Agent (1 agent, highest-reasoning model)

Produces: `whatChanged`, `decisions`, `postMergeItems`, `factoryHistory`

This agent should use the highest-reasoning model available. It requires access to the full codebase, the code diff, AND the review team's outputs to produce coherent cross-cutting summaries. It runs AFTER the 5 reviewers complete, not in parallel.

Common failures:
- `infrastructure`/`product` as arrays instead of HTML strings
- `zones` format inconsistency (space-separated in decisions, array in postMergeItems)
- Missing `body` in decisions (only `rationale`)
- `codeSnippet` plural

#### Post-Agent Merge (Orchestrator)

The orchestrator:
1. Collects all agent outputs
2. Parses JSON (strips markdown fences if needed)
3. Validates structure
4. Auto-fixes common mistakes
5. Merges into scaffold JSON
6. Runs verification checks (file paths exist in diff, zones exist in registry, etc.)
7. Writes updated `/tmp/pr{N}_review_pack_data.json`

### Pass 3: Rendering (Deterministic)
- **Script:** `render_review_pack.py`
- **Input:** `--data ... --output ... --diff-data ... --template v2`
- **Output:** `docs/pr{N}_review_pack.html`
- **What it does:** Injects JSON into HTML template, embeds diff data inline, calculates SVG viewBox, validates no unreplaced markers
- **LLM involvement:** None
- **Permission risk:** Low (single python3 command)

### Post-Render: Playwright Validation
- **Baseline suite:** `e2e/review-pack-v2.spec.ts` (structural correctness)
- **Per-PR expansion:** Copy template → customize → run
- **Visual banner:** Removed when all tests pass

### Current Artifact Inventory

| Artifact | Type | Location |
|----------|------|----------|
| SKILL.md | Skill entry point | `packages/pr-review-pack/SKILL.md` |
| generate_diff_data.py | Script (Pass 1) | `packages/pr-review-pack/scripts/` |
| scaffold_review_pack_data.py | Script (Pass 2a) | `packages/pr-review-pack/scripts/` |
| render_review_pack.py | Script (Pass 3) | `packages/pr-review-pack/scripts/` |
| review_pack_cli.py | CLI tool (status/refresh/merge) | `packages/pr-review-pack/scripts/` |
| template_v2.html | HTML template | `packages/pr-review-pack/assets/` |
| build-spec.md | Authoritative spec | `packages/pr-review-pack/references/` |
| data-schema.md | TypeScript-style schema | `packages/pr-review-pack/references/` |
| section-guide.md | Section-by-section reference | `packages/pr-review-pack/references/` |
| css-design-system.md | CSS design tokens | `packages/pr-review-pack/references/` |
| validation-checklist.md | Pre-delivery checks | `packages/pr-review-pack/references/` |
| prerequisites.md | Gate-checking procedure | `packages/pr-review-pack/references/` |
| pass2b-invocation.md | Agent spawn spec | `packages/pr-review-pack/references/` |
| pass2b-output-schema.md | JSON output shapes | `packages/pr-review-pack/references/` |
| review-pack-v2.spec.ts | Playwright baseline | `packages/pr-review-pack/e2e/` |
| pr-validation.template.ts | Playwright PR template | `packages/pr-review-pack/e2e/` |
| 5 review prompt MDs | Paradigm prompts | `packages/review-prompts/` |
| code_quality_standards.md | Quality standards | `packages/dark-factory/docs/` |
| zone-registry.yaml | Architecture zones | Repo root (`zone-registry.yaml`) — **repo-owned artifact**, not a skill file. The architect agent helps create and maintain it. Must be adopted by any repo using the review pack skill. |
| 11 Python unit tests | Test suite | `packages/pr-review-pack/tests/` |

### Data Schema Summary

`ReviewPackData` has 15+ top-level fields, 20+ nested interfaces, and several organic inconsistencies (e.g., `zones` is a space-separated string in `decisions` and `findings`, but an array in `postMergeItems`). These will be normalized to `string[]` everywhere as part of the streamlining.

**Zones content guidance**: `string[]` is the type normalization. Additionally, zone IDs must: (1) match keys defined in `zone-registry.yaml`, (2) use lowercase-kebab-case formatting, (3) be validated by the assembler — unknown zone IDs are rejected except when the architecture reviewer flags "unzoned" files as a drift finding. The pydantic model should include a validator that enforces this.

---

## Part 2: Process Flow — Current State

```
User: "/pr-review-pack {N}"
        │
        ▼
┌──────────────────────────┐
│ SKILL.md loaded into     │
│ orchestrator context     │
│ (~440 lines of prompt)   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ PREREQUISITES            │
│ ├─ Gate 1: gh pr checks  │  ◄── 1 bash command (may need permission)
│ ├─ Gate 2: GraphQL query │  ◄── 1 bash command (may need permission for gh api)
│ └─ Gate 2b: Route        │  ◄── Multiple bash commands if unresolved comments
│    unresolved comments   │      (read, fix, push, resolve — MANY permissions)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ PASS 1: Diff extraction  │  ◄── 1 bash command (python3)
│ generate_diff_data.py    │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ PASS 2a: Scaffold        │  ◄── 1 bash command (python3)
│ scaffold_review_pack_data│
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ PASS 2b: Semantic Enrichment                                     │
│                                                                   │
│  ┌─ Check for existing gate0_tier2 files ──┐                     │
│  │  If current SHA: convert & skip agent   │  ◄── File reads +   │
│  │  If stale/missing: spawn agent          │      bash commands   │
│  └─────────────────────────────────────────┘                     │
│                                                                   │
│  Workstream A (5 agents in parallel):                             │
│  ┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐             │
│  │  CH    ││  SE    ││  TI    ││  AD    ││  AR    │             │
│  │ agent  ││ agent  ││ agent  ││ agent  ││ agent  │             │
│  └───┬────┘└───┬────┘└───┬────┘└───┬────┘└───┬────┘             │
│      │         │         │         │         │                    │
│      └─────────┴────┬────┴─────────┴────┬────┘                    │
│                     │                    │                         │
│  Each agent:        │  Workstream B:     │                        │
│  • Reads diff JSON  │  ┌────────┐        │                        │
│  • Reads paradigm   │  │Semantic│        │                        │
│  • Reads zone reg   │  │Analysis│        │                        │
│  • Reads standards  │  │ agent  │        │                        │
│  • Outputs JSON     │  └───┬────┘        │                        │
│                     │      │             │                         │
│  PROBLEMS HERE:     │      │             │                         │
│  • Each agent may   │      │             │                         │
│    need file reads  │      │             │                         │
│  • Agents construct │      │             │                         │
│    bash commands    │      │             │                         │
│    with special     │      │             │                         │
│    chars (#, ', \)  │      │             │                         │
│  • JSON output      │      │             │                         │
│    schema errors    │      │             │                         │
│  • Retries add more │      │             │                         │
│    permission asks  │      │             │                         │
│                     │      │             │                         │
│  ┌──────────────────▼──────▼─────────────▼──────┐                │
│  │ MERGE + VALIDATE                              │                │
│  │ • Parse 6 JSON outputs                        │                │
│  │ • Auto-fix schema mistakes                    │                │
│  │ • Verify file paths vs diff                   │  ◄── Multiple  │
│  │ • Verify zones vs registry                    │      file      │
│  │ • Flag unverified claims                      │      reads +   │
│  │ • Write merged JSON                           │      writes    │
│  └──────────────────┬───────────────────────────┘                │
└──────────────────────┼───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────┐
│ PASS 3: Render HTML      │  ◄── 1 bash command (python3)
│ render_review_pack.py    │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ PLAYWRIGHT VALIDATION    │
│ ├─ Copy template         │  ◄── bash command (may need permission)
│ ├─ Edit PR-specific test │  ◄── file edit
│ ├─ npx playwright test   │  ◄── bash command (may need permission)
│ └─ Fix failures + retry  │  ◄── MULTIPLE permission asks
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ COMMIT + DELIVER         │
│ ├─ git add               │  ◄── bash command
│ ├─ git commit            │  ◄── bash command (may need permission)
│ └─ git push              │  ◄── bash command (may need permission)
└──────────────────────────┘
```

### Permission Pain Points (Current)

| Phase | Cause | Frequency |
|-------|-------|-----------|
| Prerequisites | `gh api graphql` with single-quoted JSON | Every run |
| Prerequisites | Comment routing → multiple `gh` + `git` commands | When unresolved comments exist |
| Pass 2b agents | Agents construct bash commands with `#`, `'`, `\` | High — agents are creative with shell |
| Pass 2b agents | Agents use `Read` on files (OK) but then sometimes `cat` or `grep` | Medium |
| Pass 2b merge | Orchestrator writes JSON with `Write` tool | Usually OK |
| Pass 2b merge | Orchestrator runs verification with bash | Sometimes |
| Playwright | `npx playwright test` with arguments | Every run |
| Playwright | Test failures → edit → re-run cycle | When tests fail |
| Git | commit + push | Every run |

**Estimated permission prompts per run: 8-20+**, depending on comment resolution needs and test failures.

### The Core Problem

The primary problem is **complexity**: the skill takes a long time to complete, outcomes are unpredictable, and the orchestrator sometimes forgets key operations or stages (e.g., skipping Playwright validation entirely after context compaction). Permission prompts are a secondary effect of this complexity — each bespoke inline step is an opportunity for the orchestrator to construct a command that triggers a permission prompt.

Root cause: the orchestrator does too much inline — agent invocation, JSON parsing, format fixing, verification, Playwright management. The fix is not fewer steps, but simpler steps: each step should be a single tool call to a well-defined script. A single `python3` command per phase is much better than having the orchestrator construct multiple custom commands on the fly.

Additionally, the orchestrator may benefit from subagents to help with assembly — separating the review team's work from the assembly of the final report.

---

## Part 3: Triage

### KEEP (Essential, Working Well)

| Item | Why |
|------|-----|
| Three-pass pipeline architecture | Sound separation of deterministic vs semantic. Core design is right. |
| Zone registry as collaboration interface | Deterministic file-to-zone mapping is the linchpin. No changes needed. |
| `generate_diff_data.py` (Pass 1) | Works, deterministic, no issues. |
| `scaffold_review_pack_data.py` (Pass 2a) | Works, deterministic, no issues. |
| `render_review_pack.py` (Pass 3) | Works, deterministic, template injection is solid. |
| `review_pack_cli.py` | Useful for status/refresh/merge workflows. |
| `template_v2.html` | "Mission Control" layout is mature and tested. |
| Data schema (ReviewPackData) | Complex but complete. Template depends on exact shapes. |
| 5 review paradigm prompts | Well-crafted, each focuses on a distinct concern. |
| Playwright baseline tests | Structural correctness validation works. |
| 11 Python unit tests | Good coverage of renderer, scaffold, CLI. These run in **CI on every push to the monorepo**, not during each review pack build. They validate the pipeline tools themselves, not individual review pack outputs. |
| Ground truth hierarchy | Code diffs > context > LLM claims. Core principle. |
| Verification checks | File paths, zones, decisions — all valuable. |

### SIMPLIFY (Keep Intent, Reduce Complexity)

| Item | Problem | Proposed Change |
|------|---------|-----------------|
| Pass 2b agent invocation | Orchestrator must: read paradigm, read standards, read diff, construct massive prompt, spawn agent, parse JSON, handle errors, retry — all with bespoke bash/tool calls | The orchestrator no longer reads diffs, constructs prompts, or parses JSON. It STILL spawns agent teams and handles errors/retries. Agents write `.jsonl` files with prescribed schemas; the assembler script reads, validates, and transforms them into the scaffold JSON for the template. |
| Zones data representation (DRY) | `zones` is a space-separated string in `AgenticFinding` and `decisions`, but a `string[]` array in `postMergeItems` — organic inconsistency, not intentional | Normalize to `string[]` (array of zone IDs) everywhere: ReviewPackData schema, reviewer output schema, template consumption. Zone registry YAML is the single source of truth. Every zone ID must exist in the registry (except architect findings that flag drift). No translation layer needed — the assembler passes zones through. One-time template update to consume arrays everywhere. |
| Field naming inconsistencies | `codeSnippet` vs `codeSnippets`; agents frequently use the wrong one | Standardize field names in the reviewer output JSON schema; validate with the assembler script |
| Agent output format enforcement | Agents produce wrong shapes → orchestrator fixes → sometimes re-spawns | Pydantic models as source of truth; assembler validates each .jsonl line; recovery loop (pass errors back or spawn recovery subagent); investigate Anthropic structured outputs for API-level enforcement |
| Error recovery (malformed JSON) | Orchestrator strips fences, retries — adds complexity and permissions | Agents are told to write to a file, not return in-context JSON |
| Playwright per-PR expansion | Copy template → edit → run is manual and error-prone | Auto-generate per-PR test from review pack data JSON |

### REMOVE (Overcomplicated or Redundant)

| Item | Why Remove |
|------|-----------|
| In-context JSON parsing by orchestrator | Agents should write files, not return JSON inline. Eliminates markdown-fence stripping, JSON extraction heuristics. |
| Manual gate0_tier2 → AgenticFinding conversion | Should be a script, not orchestrator logic. |
| Orchestrator-driven verification | Should be a script that reads the merged JSON and validates. |
| Bespoke bash commands by review agents | Agents currently have Bash available and sometimes reach for `cat`, `grep`, `find` instead of the Read tool — constructing commands with `#`, `'`, `\` that trigger permission prompts. Fix: (1) spawn review agents with only Read + Write tools — no Bash in their tool set, (2) update paradigm prompts to explicitly instruct agents to use the Read tool for all file access. The diff data JSON tells them which files changed; all files are in the repo at their normal paths. No workspace copying needed — the repo is the workspace. |
| Visual self-review banner logic | Currently already removed by running Playwright tests. Ensure this remains true post-streamlining — banner state should be purely a function of test pass/fail, not something the orchestrator manages. |

### GAPS (Missing, Needed)

| Gap | Why Needed |
|-----|-----------|
| **Standard reviewer output format (.jsonl)** | Currently agents return inline JSON of varying quality. Need prescribed file-based output. |
| **Merge/validate script** | Currently the orchestrator does this inline. Should be `merge_review_outputs.py` — deterministic, no LLM. |
| **Auto-generate Playwright tests** | Currently manual template copy + edit. Should generate from review pack data. |
| **Session observability** | No way to track permission prompts, agent failures, retry counts across runs. This is a **skill-developer need** (for improving the skill), not an end-user impact. |
| **Concept-level review model** | Current schema is file-level (`AgenticFinding.file`). Vision is concept-level (one concept may span multiple files). |
| **Assembler agent/script** | Currently the orchestrator IS the assembler. Need separation. |
| **Process flow diagram** | No visual of the skill's workflow exists. |
| **Portability layer** | Skill is somewhat coupled to this repo (factory artifacts, scenarios). Need clean separation of repo-specific vs universal. |

---

## Part 4: Proposed Process Flow (After Streamlining)

```
User: "/pr-review-pack {N}"
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 1: SETUP (Deterministic, Scripted)                         │
│                                                                   │
│  python3 scripts/review_pack_setup.py --pr {N}                   │
│  ├─ Gate 1: gh pr checks (fail fast)                             │
│  ├─ Gate 2: GraphQL comment count (fail fast)                    │
│  ├─ Pass 1: generate_diff_data.py                                │
│  │  → docs/reviews/pr{N}/pr{N}_diff_data_{base8}-{head8}.json   │
│  └─ Pass 2a: scaffold_review_pack_data.py → scaffold JSON       │
│                                                                   │
│  All inputs for Phase 2 are already in the repo:                 │
│  • Diff data: docs/reviews/pr{N}/pr{N}_diff_data_*.json         │
│  • Zone registry: zone-registry.yaml (repo root)                │
│  • Quality standards (any/all of):                               │
│    - packages/dark-factory/docs/ (factory option)                │
│    - copilot-instructions.md (GitHub Copilot compat)             │
│    - CLAUDE.md (repo's own Claude instructions)                  │
│    NOTE: Reviewers must scrutinize these files — do NOT treat    │
│    them as gospel. They may be poorly crafted, outdated, or      │
│    otherwise less-than-helpful.                                   │
│  • Paradigm prompts: packages/review-prompts/                   │
│  • Source files: at their normal repo paths                      │
│  No copying needed — the repo is the workspace.                  │
│                                                                   │
│  Permission cost: 1 bash command (python3)                        │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 2: REVIEW (Agent Team, Parallel)                           │
│                                                                   │
│  5 reviewers spawned in parallel, then synthesis agent:            │
│  • Spawned with Read + Write tools ONLY (no Bash)                │
│  • Reads diff data, zone registry, standards from repo paths     │
│  • Reads source files directly from the repo                     │
│  • Writes .jsonl output to docs/reviews/pr{N}/                   │
│                                                                   │
│  File naming: pr{N}-{agent}-{base8}-{head8}.jsonl                │
│  Example:     pr7-CH-a1b2c3d4-e5f6g7h8.jsonl                    │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ pr7-CH-* │ │ pr7-SE-* │ │ pr7-TI-* │ │ pr7-AD-* │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
│  ┌──────────┐ ┌──────────────────────┐                           │
│  │ pr7-AR-* │ │ pr7-semantic-*       │                            │
│  └──────────┘ └──────────────────────┘                           │
│                                                                   │
│  Each reviewer .jsonl line = one ReviewConcept:                   │
│  {                                                                │
│    "concept_id": "CH-001",                                       │
│    "title": "Frame buffer lifecycle",                            │
│    "grade": "B+",                                                │
│    "category": "code-quality",                                   │
│    "summary": "One-line plain text summary",                     │
│    "detail_html": "<p>Full explanation...</p>",                  │
│    "locations": [                                                 │
│      {                                                            │
│        "file": "src/envs/minipong.py",                           │
│        "lines": "45-52",                                         │
│        "zones": ["environment"],                                 │
│        "comment": "Expressive comment about this location"       │
│      }                                                            │
│    ]                                                              │
│  }                                                                │
│                                                                   │
│  Note: `agent` field is NOT in the schema — it's derived from    │
│  the filename (pr7-CH-*.jsonl → agent is CH). Single-location    │
│  concepts are fine (locations array with one entry).              │
│                                                                   │
│  Synthesis agent .jsonl lines = typed objects:                     │
│  {"type": "what_changed", "zone_id": "...", ...}                 │
│  {"type": "decision", "number": 1, ...}                          │
│  {"type": "post_merge_item", "priority": "medium", ...}          │
│  {"type": "factory_event", ...}                                  │
│                                                                   │
│  The synthesis agent WILL need to see peer agents' outputs        │
│  to produce coherent decisions and "what changed" summaries.      │
│  This agent runs AFTER the 5 reviewers complete, not in parallel. │
│  Uses highest-reasoning model available.                          │
│                                                                   │
│  Permission cost: 0 bash commands                                 │
│  (agents only have Read + Write tools — Bash not available)       │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 3: ASSEMBLE (Deterministic, Scripted)                      │
│                                                                   │
│  python3 scripts/assemble_review_pack.py \                       │
│    --pr {N} --output docs/reviews/pr{N}/pr{N}_review_pack.html   │
│                                                                   │
│  This script:                                                     │
│  1. Reads all .jsonl files from docs/reviews/pr{N}/              │
│  2. Validates each line against pydantic models                   │
│  3. Transforms ReviewConcepts → AgenticFindings                  │
│     (handles zones format, gradeSortOrder, etc.)                 │
│     Note: start with script; may need agent involvement if        │
│     transformation requires semantic understanding.               │
│  4. Transforms semantic objects → whatChanged, decisions, etc.    │
│     (handles all format inconsistencies the template expects)    │
│  5. Merges into scaffold.json                                    │
│  6. Runs verification checks                                     │
│  7. Computes status model                                        │
│  8. Renders HTML via render_review_pack.py                       │
│  9. Generates per-PR Playwright test from data (Tier 1)          │
│  10. Runs Playwright tests                                       │
│  11. If tests fail: iteratively fix and re-run until passing     │
│  12. Reports results (including any validation errors)            │
│                                                                   │
│  Permission cost: 1 bash command (python3)                        │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 4: DELIVER (User-Initiated)                                │
│                                                                   │
│  User reviews Playwright results + opens HTML                     │
│  If satisfied: git add + commit + push                           │
│                                                                   │
│  Permission cost: 2-3 bash commands (git)                         │
└──────────────────────────────────────────────────────────────────┘
```

### Permission Budget Comparison

| | Current | Proposed |
|---|---------|----------|
| Setup / Prerequisites | 2-5+ | 1 |
| Pass 1 + 2a | 2 | 0 (folded into setup) |
| Pass 2b (agents) | 5-15+ | 0 (Read/Write only) |
| Pass 2b (merge/validate) | 2-5 | 0 (folded into assemble) |
| Pass 3 (render) | 1 | 0 (folded into assemble) |
| Playwright | 2-5+ | 0 (folded into assemble) |
| Git | 2-3 | 2-3 |
| **Total** | **16-36+** | **3-4** |

### Key Design Changes

#### 1. Concept-Level Review Model (not file-level)

Current: Each `AgenticFinding` has a single `file` field. Reviewers think file-by-file.

Proposed: Each `ReviewConcept` has a `title` (the concept), `detail_html` (holistic explanation), and `locations[]` (list of file/line clusters that relate to this concept). A concept might touch 5 files across 3 zones.

The assembler script transforms `ReviewConcept` → `AgenticFinding[]` for template compatibility (one finding per location, all sharing the concept's detail).

#### 2. File-Based Agent Output (not in-context JSON)

Current: Agents return JSON in their response text. Orchestrator parses, strips fences, retries.

Proposed: Agents write `.jsonl` files to `docs/reviews/pr{N}/` in the repo. Each line is independently parseable. Partial output is recoverable. Agents spawned with Read + Write only — no Bash available.

The `.jsonl` files are **git-tracked as part of the review pack artifacts** — not first-class user-facing deliverables, but available for debugging and deep-diving when needed. They sit alongside the rendered HTML and diff data in `docs/reviews/pr{N}/`.

**Exclusion from recursive review packs**: All files in `docs/reviews/` must be excluded from subsequent PR review pack diff data to avoid recursive explosion. The `generate_diff_data.py` exclusion pattern `docs/reviews/*` already covers this (verified with fnmatch). Any new file types added to this directory must also be covered.

#### 3. All Format Translation in Scripts (not agents or orchestrator)

Current: Agents must produce exact schema (zones as space-separated strings, specific field names). They frequently get it wrong.

Proposed: Agents produce a simple, consistent schema (zones always as `string[]` arrays of zone IDs from the registry, `locations` instead of `file`). The assembler script handles translation to the template's current format. Long-term: normalize the template to match the clean schema so no translation is needed.

**Testing mandate**: The thesis that "agents produce clean schema, assembler translates" must be comprehensively tested during implementation. If the translation layer introduces its own bugs or the agent output is consistently wrong in ways the assembler can't fix, flag it immediately — don't silently work around it.

#### 4. Scripts as Tools for the Agent

The three passes and the assembly step are not just scripts the agent calls via bash — they should be thought of as **tools the agent can use**. A skill is not a workflow; it provides tools and guidance on how to achieve something. Packaging these scripts as clearly defined tools (with known inputs, known outputs, and predictable behavior) lets the orchestrator call them without constructing bespoke commands.

Current: Orchestrator runs 5+ individual commands, reads multiple files, constructs arguments.

Proposed: Two tool-like scripts:
- `review_pack_setup.py` — prerequisites + Pass 1 + Pass 2a
- `assemble_review_pack.py` — merge + validate + render + test

Each is a single `python3` invocation with clear arguments. The orchestrator calls them like tools, not like workflow steps it must reason about.

#### 5. Pydantic Validation + Recovery Loop

Current: Agents produce wrong JSON shapes → orchestrator fixes inline or re-spawns. No structured enforcement.

Proposed: Use **pydantic models** (or equivalent) for schema validation of ReviewConcept and SemanticOutput objects. The assembler script validates each .jsonl line against the pydantic model and produces a structured error report. If validation errors exist, the orchestrator can either:
- Pass the errors back to the original agent to fix and re-write the .jsonl file
- Spawn a lightweight recovery subagent that reads the errors and the malformed objects and produces corrected output

This is more robust than post-hoc script validation alone. The pydantic models serve as the single source of truth for what a valid ReviewConcept looks like — they're used in validation, in documentation, and potentially in the paradigm prompts as a reference.

**Structured outputs (mandatory investigation):** Anthropic now supports **structured outputs** on the Claude API (GA January 2026) — constrained decoding that physically prevents the model from generating tokens that violate the schema. The Python SDK supports `client.messages.parse()` with pydantic models directly. This MUST be coupled with the pydantic validation approach — they are complementary:
- **Structured outputs** prevent malformed output at generation time (API-level enforcement)
- **Pydantic validation** catches edge cases the schema can't express (semantic validation, zone ID existence, etc.)

**Key question**: How does a skill, an agent prompt, or an orchestrator invoking an agent team via Claude Code's Agent tool enforce structured output constraints? This is not just a research task — it requires **adversarial testing** until we learn how to use the feature in Claude Code, and the findings must be **documented** as a reference for the skill and for future skills.

**Scope constraint**: No API key is available for direct API calls. Testing is limited to what Claude Code's Agent tool exposes natively. If the Agent tool does not support structured output constraints, the fallback is pydantic validation + recovery loop (which remains valuable regardless).

#### 6. Auto-Generated Playwright Tests (Two Tiers)

Current: Manual copy of template → edit → run. Agent must construct npx command.

Proposed: Two tiers of Playwright testing:

**Tier 1 — Deterministic (auto-generated from metadata):** The assembler script generates tests based on review pack data: PR number, reviewed HEAD commit SHA, files reviewed, number of findings per agent, zones covered, section presence/absence. These tests verify structural correctness and data completeness. Zero agent involvement.

**Tier 2 — Agent-driven custom tests:** For unexpected findings that don't have existing UI primitives. Example: a previous review pack had an architectural finding that required a custom UI element created on the fly. We keep this tier open for these occurrences — the goal is not to eliminate agent-driven tests entirely, but to minimize them by maximizing deterministic coverage in Tier 1. Validate during implementation whether Tier 2 is needed; if the template handles all standard data shapes, it may not be.

**Baseline suite**: The existing comprehensive, case-agnostic Playwright suite must be maintained alongside the PR-specific enhancements. Both run every time.

#### 7. Ground Truth Hierarchy — Implementation

The principle "code diffs > context > LLM claims" must be enforceable, not just stated. Implementation:
- **File path verification:** Every file path in a finding must exist in the diff data JSON. The assembler script checks this.
- **Zone verification:** Every zone ID in a finding must exist in the zone registry YAML. Checked by the assembler. Exception: the architecture reviewer may flag files as "unzoned" — these render with the red "unzoned" chip in the HTML, indicating the zone registry needs updating.
- **Decision-zone verification:** Every decision-to-zone claim must have ≥1 file in the diff that touches that zone's paths. Unverified claims are flagged in the rendered HTML.
- **Code snippet verification:** Line numbers referenced in findings must exist in the actual file content from the diff data.

These checks are **implemented in the assembler script** as deterministic validation — no LLM involved. The agent does not need to think about verification; it's automatic.

#### 8. Verification Completeness

Current verification checks (file paths, zones, decision-zone claims) are necessary but may not be complete. Additional validations:

**Structural validations:**
- **Grade validity:** Grade must be one of A, B+, B, C, F. No N/A — if an agent can't assess a file, it must explain why in the finding body, not use a non-grade.
- **Concept ID uniqueness:** No duplicate concept IDs within a single agent's output
- **Zone registry coverage:** Flag if significant portions of the diff (by line count) fall in no zone
- **Mandatory fields:** All required fields present per the pydantic model
- **HTML sanitization:** `detail_html` should be valid HTML fragments, not raw text or markdown

**Hallucination detection:**
- **Coverage gaps:** Flag files in the diff that no agent mentioned — potential missed issues
- **Severity inflation:** Detect when agents grade everything as C/F without substantive evidence in the detail
- **Cross-reference verification:** Do referenced functions/classes actually exist in the diff content?
- **Contradiction detection:** Flag when two agents make contradictory claims about the same file/concept
- **Phantom file references:** References to files not in the diff or not in the repo

All verifications must be constructed so the assembler script runs them automatically. The agent never needs to reinvent validation methods or create tools/scripts on the fly.

---

## Part 5: Implementation Workstreams

### WS1: ReviewConcept Schema + Reviewer Output Format
- Define `ReviewConcept` pydantic model and JSON schema (`.schema.json`). Note: `agent` field is NOT in the schema — agent identity is derived from the filename (`pr7-CH-*.jsonl` → agent CH). Single-location concepts are explicitly valid.
- Define `SemanticOutput` pydantic model and JSON schema for the synthesis agent
- Create example `.jsonl` files as reference
- Update 5 paradigm prompts to output ReviewConcepts
- Design the **synthesis agent**: highest-reasoning model, access to codebase + diff + all 5 reviewer outputs. Produces decisions, "what changed" summaries, post-merge items, and factory events. Runs AFTER the 5 reviewers complete (not in parallel). Determine whether this is a 6th paradigm prompt or a different kind of agent.
- **Structured outputs research + adversarial testing**: Determine how to enforce structured output constraints through Claude Code's Agent tool. Test adversarially until the mechanism is understood. Document findings as a reference for the skill and for future skills. This is not optional research — it's a critical dependency for the validation pipeline.

### WS2: Setup Script (`review_pack_setup.py`)
- Consolidate prerequisites + Pass 1 + Pass 2a into one script
- Output diff data to `docs/reviews/pr{N}/pr{N}_diff_data_{base8}-{head8}.json`
- Output scaffold JSON to `docs/reviews/pr{N}/`

### WS3: Assembly Script (`assemble_review_pack.py`)
- Read `.jsonl` files from `docs/reviews/pr{N}/`
- Validate against pydantic models (ReviewConcept, SemanticOutput)
- Transform ReviewConcept → AgenticFinding (handle all format quirks)
- Transform SemanticOutput → whatChanged/decisions/postMergeItems/factoryHistory
- Merge into scaffold
- Run verification checks (file paths, zones, decision-zone claims, grade validity, HTML sanitization)
- Compute status
- Call render_review_pack.py
- Auto-generate Playwright test (Tier 1: deterministic from metadata)
- Run Playwright
- Report results (including any validation errors for recovery)
- **This script itself needs unit tests** — add to the existing test suite, run in CI

### WS4: Update SKILL.md
- Load the `/skill-creator` skill for context on skill anatomy, progressive disclosure, and writing patterns before making changes
- Simplify to 4-phase flow
- Remove all inline orchestration logic
- Point to scripts for everything
- Define agent spawn pattern (Read + Write only, no Bash)
- Include quality standards discovery: copilot-instructions.md, CLAUDE.md, and factory standards (with scrutiny guidance)

### WS5: Portability

What "portability layer" means in concrete terms:

1. **Zone registry location**: Ensure target repo has `zone-registry.yaml` at its root. For the current monorepo: move from `.claude/zone-registry.yaml` to repo root if not already done. Ship `zone-registry.example.yaml` with the skill. Document it as the one required adoption artifact. The architect agent helps create and maintain it.
2. **Review output directory convention**: Standardize on `docs/reviews/pr{N}/` with SHA-based filenames. Update `generate_diff_data.py` exclusion patterns to cover ALL files created in this directory (already done for base pattern `docs/reviews/*`; verify coverage for any new file types added during implementation).
3. **Scaffold script conditional sections**: The scaffold script already needs to gracefully skip factory-specific data (convergence, factory history) when artifacts don't exist. Verify this works cleanly and doesn't produce broken/empty JSON fields that confuse the template. **Both cases (with and without each factory artifact) must work and be tested.** The existing Playwright suite may already cover this — verify and extend if not.
4. **Template graceful hiding**: Factory-specific sections (Convergence Result, Factory History, Specs & Scenarios) already don't render when their backing data is absent. Verify this remains true as the schema evolves — no regressions where an empty array or null value causes a broken card to appear. Factory artifacts must remain optional but fully supported.
5. **Spec semantics**: Factory specs (detailed product specifications driving the convergence loop) are not the same as arbitrary spec files a non-factory repo might have. The skill should not auto-discover random `specs/` directories and treat them as factory specs. Factory spec integration activates only when the factory artifact structure is present.
6. **Paradigm prompts — universal, not factory-gated**: The adversarial reviewer's checks for gaming, vacuous tests, and spec violations are universal concerns — any repo with AI-written code can have gaming. These stay as-is. No factory-specific variant needed.
7. **Quality standards discovery**: Reviewers should discover and read quality standards from multiple sources: the repo's CLAUDE.md, copilot-instructions.md (GitHub Copilot compatibility), and factory-specific standards when present. **Crucially**: reviewers must treat these files with scrutiny — they may be poorly crafted, outdated, or less-than-helpful. Do NOT assume they are authoritative.
8. **README and onboarding docs**: Update skill README, SKILL.md, and repo README. Provide a "getting started" section for non-factory repos. Minimum adoption path: (1) add `zone-registry.yaml` to your repo root, (2) invoke `/pr-review-pack {N}`. Everything else is optional and activates automatically when detected.

### WS6: Session Observability (Research)
- Investigate transcript files for permission tracking
- Consider a lightweight hook that logs permission events
- Build a post-session analysis script

---

## Part 6: Decisions (Resolved) and Tracked Issues

### Resolved

1. **Concept-level findings in the HTML template**: Ultimately we want to modify the template for concept-level grouping, but that requires UI design work. **Deferred to a separate workstream.** For now, the assembler flattens ReviewConcepts to file-level AgenticFindings for template compatibility. **Tracked as high-importance issue.**

2. **Agent tool permissions**: This is a **user choice**, not a prescriptive decision. The skill should work in any permission mode. The design (agents use only Read + Write) makes it possible to be very permissive without risk.

3. **Review output location**: Confirmed: `docs/reviews/pr{N}/`. File naming: `pr{N}-{agent}-{base8}-{head8}.jsonl`, `pr{N}_diff_data_{base8}-{head8}.json`.

4. **Existing gate0_tier2 reuse**: Middle ground. Keep the harmless check in the orchestrator. Add a standalone `convert_gate0_to_jsonl.py` script that converts gate0 markdown findings into standard `.jsonl` format during Phase 1 (setup). The assembler only ever sees `.jsonl` — one input format, no special cases.

5. **Playwright auto-generation**: Two tiers. Tier 1 (deterministic, auto-generated from metadata) is the MVP. Tier 2 (agent-driven custom tests) stays open for unexpected findings that don't have existing UI primitives — not eliminated, but minimized by maximizing Tier 1 coverage. The existing baseline suite runs alongside PR-specific tests every time.

6. **Timeline**: WS1–WS5 are the MVP. WS6 (session observability) is tracked as a separate issue — it's a skill-developer need, not end-user impacting.

### Tracked Issues

- **Template concept-level grouping**: High importance. Separate workstream from this proposal. Requires UI design work to render concept-level findings natively instead of flattening to file-level.
- **Session observability**: Skill-developer tooling for tracking permission events, agent failures, retry counts. Research task.
- **Tier 2 Playwright tests**: Keep open for unexpected findings (e.g., architectural finding without a UI primitive). Minimize by maximizing Tier 1. Track whether any concrete examples emerge during implementation.
- **Structured outputs in Claude Code**: Critical dependency. How does a skill/agent prompt/orchestrator enforce structured output constraints via the Agent tool? Requires adversarial testing and documented findings (not just research).

### Final Validation: Open Source Fork Testing

After all development work is complete, validate the streamlined skill on real open source repos:

1. **Fork LangChain** (`langchain-ai/langchain`, 129k stars) — on brand, the repo our audience builds with. "We brought order to LangChain's chaos" is the adoption story.
2. **Fork FastAPI** (`tiangolo/fastapi`, ~80k stars) — clean architecture, well-known, good comparison point.
3. For each fork:
   - Identify an open PR with **600+ lines of changes** (the more the better). AI-generated code PRs preferred.
   - Create a `zone-registry.yaml` at the repo root
   - Run the streamlined `/pr-review-pack` skill against the PR
   - **Each fork must be tested by an independently-contexted agent** (separate Claude Code sessions) — the skill drains context and will context-compact multiple times
   - Choose PRs that showcase the skill's power and value — these review packs will be used to drive adoption
4. Deliver the generated review packs for Joey's review

### Factory Impact: Shared Paradigm Prompts

The 5 review paradigm prompts are shared between the review pack skill and the dark factory's Gate 0 Tier 2. Updating these prompts to output `.jsonl` files impacts the factory as well. Key considerations:

- **The orchestrator tells agents where to write**, not the prompts. The prompts define *what* to write (ReviewConcept schema); the orchestrator passes the output path as a parameter. For the review pack skill: `docs/reviews/pr{N}/`. For the factory: wherever Gate 0 expects output.
- **Minimal factory-side fix**: Update the factory orchestrator to pass the output path to agents (same pattern as the review pack skill). The factory's `run_gate0.py` needs to accept `.jsonl` output instead of the current markdown format — or the `convert_gate0_to_jsonl.py` script handles backward compatibility.
- **Prompt changes are shared**: Any changes to the paradigm prompts (e.g., adding ReviewConcept schema reference, instructing agents to use Read tool only) apply to both contexts. This is by design — the review quality should be identical regardless of who triggers it.
