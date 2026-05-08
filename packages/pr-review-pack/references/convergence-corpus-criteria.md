# Convergence Corpus Selection Criteria

**Audience:** any contributor (human or AI) modifying the live-pack-validation
spec, the assembler, or the renderer.

**Purpose:** the convergence corpus is how we validate that changes to the
spec/assembler/renderer survive contact with diverse real-world packs. A
corpus that misses a dimension of variety leaves a defect class undetectable
until production. **One such miss already shipped a real bug to PR #42:** the
asymmetric `normalizePath` in the spec was never exercised by the corpus
because none of the 4 OSS PRs we tested had renamed files. Don't repeat this.

## Hard rule

When you change anything in the spec / assembler / renderer code path that
processes pack data, the convergence corpus you run **must collectively cover
every dimension below**. A run that hits 4 PRs but misses 2 dimensions has not
demonstrated convergence — it has demonstrated convergence on the dimensions
it covered.

## Required dimensions

Every corpus run MUST include at least one PR that exercises each:

| Dimension | What to look for | Why it matters |
|---|---|---|
| **Renamed files** | git diff with `{old => new}` or `R100` rename status | catches asymmetric path normalization, glob-row leaks on renames, file-coverage matchers |
| **Multi-file findings** | concept whose `locations[]` spans 3+ files | catches glob-row notation generation, multi-loc rendering, location-table layouts |
| **Cross-zone references** | location pointing at a file outside the diff (zone-registry, CLAUDE.md, etc.) | catches the spec's tolerance for context refs vs strict in-diff matching |
| **Large diff (1000+ lines, 10+ files)** | broad refactor or feature PR | catches scaling issues in the assembler, renderer, and live-pack table widgets |
| **Tiny diff (1-2 files, < 50 lines)** | hotfix-shaped PRs | catches off-by-one assumptions in the file-coverage matcher and zero-or-near-zero finding handling |
| **A-grade-only finding** | every finding is grade A | catches the kf-a-toggle collapse logic (kf-row click test must pre-expand) |
| **No-finding pack** | reviewers all return clean | catches "skip if zero rows" branches and ensures the spec doesn't crash on empty `findings[]` |
| **Self-referential pack** | the PR being reviewed contains the spec/assembler/renderer source | catches the `const DATA = ` collision, similar marker-text overlap |
| **Schema-defective source jsonl** | a `ReviewConcept` with title but no concept_id, or oversized `summary` | catches the source-jsonl-missing-concept-id distinction and the assembler's merge re-validation |
| **Headless `claude -p` run** | at least one corpus PR run via `claude --dangerously-skip-permissions -p "/pr-review-pack <N>"` | catches the non-interactive shutdown-protocol bug (members must send `shutdown_response`, not just `idle_notification`, before TeamDelete — see SKILL.md Phase 2) |

## Recommended canonical corpus

These local clones cover the dimensions and are pre-staged at `/Users/joey/tmp/`:

| Repo / PR | Dimensions covered |
|---|---|
| django/django#20948 | small diff, no renames, baseline |
| microsoft/TypeScript#63108 | medium diff, A-grade-only paths, compiler binder |
| tiangolo/fastapi#15040 | tutorial/test files, multi-file findings |
| scikit-learn#33611 | medium diff, glob-row leak surface, ML/scientific code |
| **THE PR YOU ARE WORKING ON** | self-referential, often has renames; this is your true dogfood |

**This list does not satisfy the hard rule by itself.** None of the 4 OSS PRs above have renamed files. When the next contributor changes the spec, they must add a PR with renames to the corpus, OR confirm via `git diff --find-renames` on each PR that no renames are present and document the dimension as untested.

## Suggested high-coverage additions

Find these by running `gh pr list --search "in:title rename OR refactor" --state closed` against any active OSS repo:

- A PR that moves a directory tree (many renames + path prefix change)
- A PR with `git mv` operations followed by edits (rename-with-changes)
- A bot-submitted PR (single-file, no findings, terse) — exercises low-content paths
- A PR against a monorepo where files cross workspace boundaries — exercises zone-registry matching

## Non-negotiable: dogfood

Every change to the live-pack-validation spec MUST be dogfooded by running
`/pr-review-pack` against the PR introducing the change. The dogfood is the
single most valuable test. Self-reference often reveals defects the corpus
cannot. PR #42 itself caught the rename-notation asymmetry that the 4-PR
corpus missed.

## Definition of "convergence"

For each PR in the corpus, after Phase 4 runs:
- All 14 live-pack assertions pass, OR
- The failures are all true positives (named in `live-pack-failure-codes.md`)
  pointing at a specific upstream defect, AND the orchestrator's iterate-to-
  green correction loop reaches a stable state (banner stays, with named
  codes documented in the final summary).

A pack that fails because the spec itself is buggy (e.g., asymmetric path
normalization, missing collapsed-group expansion) is **not** a converged run.
Fix the spec, re-run, then declare convergence.
