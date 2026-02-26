---
name: pr-review-pack
description: This skill should be used when the user asks to "generate a review pack", "create a PR review pack", "build a review pack for this PR", "make a review report", or when a PR is ready for review and needs a review pack artifact. Generates a self-contained interactive HTML review pack following the three-pass pipeline.
user-invocable: true
argument-hint: "[PR-url-or-number]"
---

# PR Review Pack Generator

Generate a self-contained interactive HTML review pack for a pull request. Joey reviews the report, not the code. The review pack is the artifact that tells him whether to merge, what the risks are, and what to watch post-merge.

## Naming Convention

Every review pack produces multiple artifacts. All artifacts for a single PR share the same prefix so they are associated and differentiated from other review packs.

**Prefix:** `pr{N}_` where N is the PR number.

| Artifact | Filename | Location |
|----------|----------|----------|
| Review pack HTML | `pr{N}_review_pack.html` | `docs/` |
| Diff data JSON | `pr{N}_diff_data.json` | `docs/` |
| ReviewPackData JSON | `pr{N}_review_pack_data.json` | `/tmp/` (intermediate, not committed) |

Example for PR #6: `docs/pr6_review_pack.html`, `docs/pr6_diff_data.json`.

## Prerequisites

Before generating a review pack, verify all PR readiness criteria are met. **All three gates must be green. If any gate fails, stop and fix it before proceeding.** Never present a review pack with a failed prerequisite.

**CRITICAL: Prerequisites must be checked in order. Gate 2 (comments) CANNOT be checked until Gate 1 (CI) is fully complete.** Bot reviewers (Copilot, Codex connector) post their comments AFTER CI finishes. Checking comments before CI completes will produce a stale "0 comments" result that becomes false minutes later. This has happened before — don't repeat it.

### Gate 1: CI checks GREEN on HEAD

```bash
gh pr checks <N>
```

Wait until ALL checks complete (not just start). CI typically takes 4-6 minutes. If a bot pushed the HEAD commit (GITHUB_TOKEN), CI may not have re-triggered — push a human-authored commit to fix.

### Gate 2: All review comments resolved

**Run this AFTER Gate 1 is fully green.** Bot reviewers post comments after CI completes.

```bash
# Get unresolved thread count via GraphQL
gh api graphql -f query='
{
  repository(owner: "{owner}", name: "{repo}") {
    pullRequest(number: {N}) {
      reviewThreads(first: 100) {
        nodes { isResolved }
      }
    }
  }
}' --jq '{
  total: (.data.repository.pullRequest.reviewThreads.nodes | length),
  unresolved: ([.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length)
}'
```

If `unresolved > 0`: resolve or address every comment before proceeding. Both human and AI reviewer comments (Copilot, Codex bot) count.

**Pass the comment counts to Pass 2** so they appear in the header status badges.

### Gate 3: The review pack itself

This is what this skill produces. It is always the last gate.

If any gate is unmet, state what is blocking and resolve it before proceeding.

## Three-Pass Pipeline

The review pack is produced by a deterministic pipeline -- not written from the main agent's context. Three passes, each with a clear trust boundary.

### Pass 1: Diff Analysis (Deterministic, No LLM)

Extract the raw diff and map every changed file to its architecture zone(s).

1. Run the diff data extraction script from the project repo root:
   ```
   python3 .claude/skills/pr-review-pack/scripts/generate_diff_data.py \
     --base main --head HEAD --output docs/pr{N}_diff_data.json
   ```
   This produces per-file diffs, raw content, additions/deletions, and file status.

2. Load the project's zone registry (see "Zone Registry Setup" below). Match each file path against zone path patterns to produce the `{file -> zone[]}` mapping. This is pure glob/regex matching -- zero LLM involvement.

3. Aggregate stats: total files, additions, deletions, files per zone, zone file counts.

**Output:** `docs/pr{N}_diff_data.json` with file list, zone mappings, and aggregate stats.

**Trust level:** Deterministic. Zero hallucination risk. Code diffs are ground truth.

### Pass 2: Semantic Analysis (Delegated Agent Team)

Spawn a dedicated agent team (not the main thread) to analyze the diff. The team reads the diff output from Pass 1 and the zone registry. It produces:

- **What Changed summaries** -- two-layer (Infrastructure / Product), plus per-zone detail blocks
- **Key Decisions** -- each with title, rationale, zone associations, and affected file list
- **Adversarial findings** -- per-file grade (A/B/C/F), zone tag, and finding detail
- **Post-merge items** -- priority tag, code snippets with file/line references, failure and success scenarios
- **Convergence result** -- gate-by-gate status, satisfaction score
- **CI performance data** -- from `gh pr checks` output with timing
- **Header status badges** -- the following badges are **mandatory** (the template enforces visual affordances):
  - `CI X/Y` — type `pass` if all green, `fail` otherwise
  - `X/Y Scenarios` — type `pass` if all pass, `warn` or `fail` otherwise
  - `X/Y comments resolved` — type `pass` if all resolved (or 0 total), `warn` if unresolved exist. Comment counts come from the prerequisite Gate 2 check — the orchestrating agent must pass these to the Pass 2 team.

Every claim the semantic team makes is verifiable:
- Decision-to-zone claims must have at least one file in the diff touching that zone's paths. If not, flag as "unverified."
- Code snippet line references must exist in the actual diff.
- File paths must appear in the diff file list.

**Output:** Structured JSON matching the `ReviewPackData` schema (see `references/data-schema.md`). Save to `/tmp/pr{N}_review_pack_data.json`.

**Trust level:** LLM-produced but verifiable. Every claim checked against Pass 1 output.

### Pass 3: Rendering (Deterministic, No LLM)

Run the renderer script to inject the verified JSON into the HTML template. The renderer replaces all `<!-- INJECT: ... -->` markers with generated HTML and injects the DATA JSON for JS interactivity.

```bash
python3 .claude/skills/pr-review-pack/scripts/render_review_pack.py \
  --data /tmp/pr{N}_review_pack_data.json \
  --output docs/pr{N}_review_pack.html \
  --diff-data docs/pr{N}_diff_data.json
```

The renderer:
1. Reads the template (`assets/template.html`) and the ReviewPackData JSON.
2. Generates HTML for every `<!-- INJECT: ... -->` marker (26 injection points across all sections).
3. Injects the full JSON into `const DATA = {...}` for JS interactivity (zone filtering, file modal, etc.).
4. **Embeds diff data inline** in a `<script>` block, making the pack truly self-contained. No companion JSON file needed, no CORS issues when opening via `file://` protocol.
5. Validates that no unreplaced markers remain (warns on stderr if any do).

**Self-contained guarantee:** The `--diff-data` flag embeds the Pass 1 output directly in the HTML. The diff data is raw `git diff`/`git show` output — deterministic, zero LLM — byte-equivalent to what GitHub displays for the same commit SHA. Always use `--diff-data` to embed it.

**Output:** `docs/pr{N}_review_pack.html` -- truly self-contained HTML file. Open in any browser, even via `file://`.

**Trust level:** Deterministic. The renderer renders what the data says, nothing more.

## Visual Validation

**This step is mandatory.** Never deliver a review pack without visual validation.

After rendering, validate that the pack renders correctly:

1. **Programmatic check (always run):**
   ```python
   python3 -c "
   html = open('docs/pr{N}_review_pack.html').read()
   checks = [
       ('No unreplaced markers', '<!-- INJECT:' not in html),
       ('DATA injected', 'const DATA = {};' not in html),
       ('PR title present', 'PR #{N}' in html),
       ('Scenario cards', html.count('scenario-card') >= 1),
       ('Adversarial rows', 'adv-row' in html),
       ('CI rows', 'expandable' in html),
       ('Decision cards', 'decision-card' in html),
       ('Convergence grid', 'conv-card' in html),
       ('Post-merge items', 'pm-item' in html),
       ('Diff data inline', 'DIFF_DATA_INLINE' in html),
       ('No external fetch', \"fetch('pr_diff_data.json')\" not in html),
       ('Stat labels', 'additions' in html and 'deletions' in html),
       ('Stat colors', 'stat green' in html and 'stat red' in html),
       ('Spec file links', html.count('file-path-link') >= 3),
       ('Comments badge', 'comments' in html.lower() and 'resolved' in html.lower()),
   ]
   for name, ok in checks:
       print(f'  [{\"PASS\" if ok else \"FAIL\"}] {name}')
   assert all(ok for _, ok in checks), 'Validation failed!'
   print(f'All {len(checks)} checks passed.')
   "
   ```

2. **Browser check (when possible):** Open the HTML file and verify:
   - All 9 sections render with content (not empty)
   - Architecture diagram shows zones with correct colors
   - Theme toggle works (light/dark/system)
   - Expandable sections toggle on click
   - File modal opens when clicking file paths (including spec file paths)
   - Stats show labeled additions (green) and deletions (red)
   - Factory History tab (if present) switches and shows content

3. **If browser viewing is unavailable** (e.g., headless environment, agent cannot see browser output): The programmatic check is the minimum bar. State clearly in the delivery message: "Programmatic validation passed. Browser visual validation was not performed due to [reason]. Please verify rendering before sharing."

## Zone Registry Setup

Every project needs a zone registry -- a YAML file mapping file path patterns to named architecture zones. This is the linchpin of deterministic correctness.

Look for the registry at these locations (in order):
1. `.claude/zone-registry.yaml` in the project repo
2. `docs/zone-registry.yaml` in the project repo
3. `CLAUDE.md` inline zone definitions (look for a zones section)

If no registry exists, create one. Format:

```yaml
zones:
  zone-name:
    paths: ["src/module/**", "tests/test_module*"]
    specs: ["docs/module_spec.md"]
    category: product  # product | factory | infra
    label: "Module Name"
    sublabel: "brief description"
  another-zone:
    paths: [".github/workflows/**"]
    specs: ["docs/ci.md"]
    category: infra
    label: "CI/CD"
    sublabel: "workflows, actions"
```

The registry enables:
- **File to Zone:** pure path matching (deterministic, no LLM)
- **Zone to Diagram position:** static lookup from registry category and order
- **Decision to Zone:** LLM-produced but verifiable -- must have at least one file in the diff touching that zone's paths
- **CI Job to Zone:** static mapping (which gates cover which zones)

## Quick Start

Minimal steps to generate a review pack for PR #N:

1. **Verify readiness.** Run `gh pr checks <N>` and check comments. All green? Proceed.

2. **Run Pass 1.** From the project repo root:
   ```bash
   python3 .claude/skills/pr-review-pack/scripts/generate_diff_data.py \
     --base main --head HEAD --output docs/pr{N}_diff_data.json
   ```

3. **Load zone registry.** Read the project's zone registry file. If it does not exist, create one based on the diff file list and project structure.

4. **Run Pass 2.** Spawn the semantic analysis team. Provide them:
   - The diff data JSON from Pass 1
   - The zone registry
   - The file-to-zone mapping
   - PR metadata from `gh pr view <N> --json title,number,headRefName,baseRefName,url,commits`
   - CI check data from `gh pr checks <N>`

   The team produces the `ReviewPackData` JSON. Save to `/tmp/pr{N}_review_pack_data.json`.

5. **Verify Pass 2 output.** For each decision-to-zone claim, confirm at least one file in the diff touches that zone. Flag unverified claims. Confirm code snippet line references exist in the diff.

6. **Run Pass 3.** Render the HTML with embedded diff data:
   ```bash
   python3 .claude/skills/pr-review-pack/scripts/render_review_pack.py \
     --data /tmp/pr{N}_review_pack_data.json \
     --output docs/pr{N}_review_pack.html \
     --diff-data docs/pr{N}_diff_data.json
   ```

7. **Validate.** Run the programmatic validation check. Open in browser if possible.

8. **Deliver.** The HTML file is the review pack. It is fully self-contained — diff data is embedded inline, no companion files needed.

## Architecture Diagram: Source of Truth (Open Design)

The architecture diagram in the review pack must have **continuity across PRs**. The "updated" diagram after PR N must become the "baseline" diagram before PR N+1. This is not about pixel-perfect positioning — it's about comparing consistent design changes over time.

**Current state:** The zone registry (`.claude/zone-registry.yaml`) defines zones (paths, labels, categories) but NOT diagram layout. The architecture diagram layout (SVG positions, zone relationships) is currently generated ad-hoc by the Pass 2 agent, which means it has no continuity between review packs.

**Rules for the Pass 2 agent:**
- **Never invent architecture diagram layout from scratch.** Read the zone registry for zone definitions, but get positions from the project's architecture source of truth.
- If the project has a canonical architecture layout (zone-registry.yaml with `position` fields, or a separate architecture data file), use it.
- If no layout exists yet, compute positions deterministically (by category row + sequential x placement) and persist them back to the registry so the next review pack inherits the layout.
- The zone-registry.yaml `position` field is the interim solution. A richer architecture model (multi-granularity, relationships, zoom levels) is a future design need.

**Future direction:** The architecture should evolve into a living project artifact (possibly in `docs/`) that the factory orchestrator maintains and the review pack consumes. The review pack should never be the generator of architecture — only the renderer.

## File Link Integrity Rule

Every `file-path-link` element in the review pack must resolve to a useful view when clicked. The template's `openFileModal()` handles two cases:

1. **File is in the diff data:** Shows the diff (side-by-side, unified, or raw). This is the normal case for changed files.
2. **File is NOT in the diff data:** Shows "This file was not modified in this PR" with a prominent "View on GitHub" link. This is the correct behavior for spec files, scenario files, and other reference files.

**Never make a file path clickable without verifying the click target resolves gracefully.** The template handles both cases, but if you add new file link patterns outside `openFileModal()`, you must handle the "not in diff" case yourself.

## Verification Rule

If a decision claims to affect zone X but no files in zone X's paths appear in the diff, that claim is flagged as "unverified" in the review pack. Unverified claims are rendered with a visual indicator -- never silently included.

## Ground Truth Hierarchy

1. Code diffs (Pass 1 output) -- primary source of truth
2. Main thread context -- secondary, used only when diff is ambiguous
3. If there is a conflict between diff and context, the diff wins

## Reference Files

Detailed specifications for each component of the review pack:

| Reference | What It Covers |
|-----------|---------------|
| `references/build-spec.md` | **Authoritative build specification** — full data schema, zone registry spec, section-by-section guide, pipeline delegation, CSS design system, validation checklist. The comprehensive "what and why." |
| `references/data-schema.md` | Quick-access: TypeScript-style data schema for ReviewPackData |
| `references/section-guide.md` | Quick-access: section-by-section build reference (all 9 sections + Factory History) |
| `references/css-design-system.md` | Quick-access: CSS tokens, dark mode, component patterns, layout |
| `references/validation-checklist.md` | Quick-access: pre-delivery validation checks |
| `scripts/generate_diff_data.py` | Git diff extraction script (Pass 1) |
| `scripts/render_review_pack.py` | HTML renderer script (Pass 3) — injects data into template |
| `assets/template.html` | HTML template skeleton with `<!-- INJECT: -->` markers and JS interactivity |
