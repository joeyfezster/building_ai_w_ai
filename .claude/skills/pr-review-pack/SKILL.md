---
name: pr-review-pack
description: This skill should be used when the user asks to "generate a review pack", "create a PR review pack", "build a review pack for this PR", "make a review report", or when a PR is ready for review and needs a review pack artifact. Generates a self-contained interactive HTML review pack following the three-pass pipeline.
user-invocable: true
argument-hint: "[PR-url-or-number]"
---

# PR Review Pack Generator

Generate a self-contained interactive HTML review pack for a pull request. Joey reviews the report, not the code. The review pack is the artifact that tells him whether to merge, what the risks are, and what to watch post-merge.

## Prerequisites

Before generating a review pack, verify all PR readiness criteria are met. If any criterion fails, stop and fix it first. Never present a review pack until all three are green.

1. **CI checks are GREEN on HEAD.** Run `gh pr checks <N>` and verify all checks pass on the most recent commit. If a bot pushed the HEAD commit (GITHUB_TOKEN), CI may not have re-triggered -- push a human-authored commit to fix.
2. **All comments are resolved.** Run `gh api repos/{owner}/{repo}/pulls/{N}/comments` and `gh api repos/{owner}/{repo}/pulls/{N}/reviews` to verify. Both human and AI reviewer comments (Copilot, Codex bot) count.
3. **The review pack itself** -- that is what this skill produces.

If any criterion is unmet, state what is blocking and resolve it before proceeding.

## Three-Pass Pipeline

The review pack is produced by a deterministic pipeline -- not written from the main agent's context. Three passes, each with a clear trust boundary.

### Pass 1: Diff Analysis (Deterministic, No LLM)

Extract the raw diff and map every changed file to its architecture zone(s).

1. Run the diff data extraction script from the project repo root:
   ```
   python3 .claude/skills/pr-review-pack/scripts/generate_diff_data.py --base main --head HEAD --output /tmp/pr_diff_data.json
   ```
   This produces per-file diffs, raw content, additions/deletions, and file status.

2. Load the project's zone registry (see "Zone Registry Setup" below). Match each file path against zone path patterns to produce the `{file -> zone[]}` mapping. This is pure glob/regex matching -- zero LLM involvement.

3. Aggregate stats: total files, additions, deletions, files per zone, zone file counts.

**Output:** `diff_data.json` with file list, zone mappings, and aggregate stats.

**Trust level:** Deterministic. Zero hallucination risk. Code diffs are ground truth.

### Pass 2: Semantic Analysis (Delegated Agent Team)

Spawn a dedicated agent team (not the main thread) to analyze the diff. The team reads the diff output from Pass 1 and the zone registry. It produces:

- **What Changed summaries** -- two-layer (Infrastructure / Product), plus per-zone detail blocks
- **Key Decisions** -- each with title, rationale, zone associations, and affected file list
- **Adversarial findings** -- per-file grade (A/B/C/F), zone tag, and finding detail
- **Post-merge items** -- priority tag, code snippets with file/line references, failure and success scenarios
- **Convergence result** -- gate-by-gate status, satisfaction score
- **CI performance data** -- from `gh pr checks` output with timing

Every claim the semantic team makes is verifiable:
- Decision-to-zone claims must have at least one file in the diff touching that zone's paths. If not, flag as "unverified."
- Code snippet line references must exist in the actual diff.
- File paths must appear in the diff file list.

**Output:** Structured JSON matching the `ReviewPackData` schema (see `references/data-schema.md`).

**Trust level:** LLM-produced but verifiable. Every claim checked against Pass 1 output.

### Pass 3: Rendering (Deterministic, No LLM)

Inject the verified JSON into the HTML template. The template is a pure renderer with zero intelligence.

1. Copy `assets/template.html` to the output location.
2. Replace the `const DATA = {};` placeholder with the actual JSON data block.
3. Place the `pr_diff_data.json` alongside the HTML (the template fetches it for the file modal).

**Output:** Self-contained HTML file. Open in any browser.

**Trust level:** Deterministic. The renderer renders what the data says, nothing more.

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
     --base main --head HEAD --output docs/pr_diff_data.json
   ```

3. **Load zone registry.** Read the project's zone registry file. If it does not exist, create one based on the diff file list and project structure.

4. **Run Pass 2.** Spawn the semantic analysis team. Provide them:
   - The diff data JSON from Pass 1
   - The zone registry
   - The file-to-zone mapping
   - PR metadata from `gh pr view <N> --json title,number,headRefName,baseRefName,url,commits`
   - CI check data from `gh pr checks <N>`

   The team produces the `ReviewPackData` JSON.

5. **Verify Pass 2 output.** For each decision-to-zone claim, confirm at least one file in the diff touches that zone. Flag unverified claims. Confirm code snippet line references exist in the diff.

6. **Run Pass 3.** Copy the template, inject the data, place alongside the diff data JSON.

7. **Deliver.** The HTML file is the review pack. Open it in a browser to verify rendering before delivering to Joey.

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
| `assets/template.html` | HTML template skeleton with DATA placeholder (Pass 3) |
