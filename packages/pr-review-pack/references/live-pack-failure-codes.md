# Live-Pack Validation Failure Codes

This file is the source of truth for every diagnostic code emitted by
`e2e/live-pack-validation.spec.ts`. Every `LIVE_PACK_FAIL` line in the spec
MUST have a matching row in the table below. CI greps the spec for
`"code":"<value>"` literals and rejects mismatches.

The orchestrator (Phase 4 Step 2b in `SKILL.md`) consumes failure codes
emitted on stderr in the form:

```
LIVE_PACK_FAIL {"code":"<code>","details":{...}}
```

For each unique code on a failed run, the orchestrator dispatches the
handler in the **Handler** column. Codes flagged `BLOCK` are not
auto-correctable — the loop halts and the banner stays.

## Code Registry

| Code | Trigger | Auto-correctable? | Handler |
|---|---|---|---|
| `finding-location-mismatch` | A finding's `locations[*].file` (or its legacy `file` field) does not normalize to a path present in `diff_data.files`. The detail includes a Levenshtein closest-match suggestion. | YES | Resume the **owning reviewer agent** (Pattern A). The agent is identified by `details.examples[i].agent`. Prompt: re-emit a corrected `ConceptUpdate` with the right `locations[*].file`, or use the suggested path. |
| `finding-zone-unresolved` | A finding's `zones` field references a zone ID not in `architecture.zones[*].id`. | YES | Resume the **owning reviewer agent** (Pattern A). Pass the list of valid zone IDs (`details.knownZones`) so it can pick the right one. |
| `concept-id-missing` | A rendered finding's title (carried as `notable`) has no matching `ReviewConcept.title` in the source `.jsonl` for that agent — i.e., the rendered pack references a concept the source doesn't contain. | YES | Resume the **owning reviewer agent** (Pattern A). Append the missing `ReviewConcept` line. |
| `source-jsonl-missing-concept-id` | The source `.jsonl` for an agent contains a line with a non-empty `title` but missing or empty `concept_id`. The source schema is malformed; the rendered pack itself may still be coherent. Distinguished from `concept-id-missing` so the orchestrator dispatches at the source defect, not the rendered pack. | YES | Resume the **owning reviewer agent** (Pattern A). The agent must emit a properly-formed `ReviewConcept` line (concept_id + title required) or a `ConceptUpdate` repairing the existing line. |
| `file-coverage-gap` | A diff file has no row in the `fileCoverage` table, OR the source `.jsonl` directory could not be located, OR a coverage row references a file not in the diff, OR a file appears more than once in coverage. | YES | If source `.jsonl` was found: resume each affected reviewer agent (Pattern A) to append a missing `FileReviewOutcome`. If source `.jsonl` is missing: this is a pipeline error — re-run the assembler step (`scripts/assemble_review_pack.py`). If extras/duplicates: re-run the assembler — the file-coverage builder is the responsible component. |
| `grade-without-outcome` | A file-coverage row shows a per-agent grade, but no `FileReviewOutcome` for that file from that agent exists in the source `.jsonl`. | YES | Resume the **specific reviewer agent** named in `details.examples[i].agent` (Pattern A). Have it append a corrected `FileReviewOutcome` for `details.examples[i].file`. |
| `rendered-undefined-or-null` | The visible body text (excluding `<script>`, `<style>`, and the file-modal diff view) contains the literal token `undefined` or standalone `null`. Indicates the renderer dropped a missing field into a label or value. | YES | Re-run the assembler/renderer pipeline. The assembler should populate any missing fields with documented defaults; the renderer should never serialize `undefined`/`null` into visible text. If the assembler step doesn't fix it, this becomes `renderer-template-gap`. |
| `glob-row-leak` | The pack's visible body text contains a `(N files)` row, an artifact of the multi-file glob notation produced by `transform_concept_to_finding` in the assembler. | YES | Resume the **owning reviewer agent** to split the multi-file `ConceptLocation` into per-file findings. The assembler then emits one row per file rather than the glob. (Alternatively, fix `assemble_review_pack.py` to flatten multi-file concepts, but agent-level correction matches the per-finding correction model.) |
| `inject-marker-leak` | The body HTML (outside `<script>`) still contains an `<!-- INJECT: ... -->` marker — the renderer failed to substitute it. | NO — **BLOCK** | Renderer/template gap. The renderer template (`assets/template_v2.html`) declares an injection point that `scripts/render_review_pack.py` does not handle. Banner stays; the orchestrator surfaces the raw marker name and points at the renderer. |
| `empty-detail-summary` | A `.kf-detail-summary` element is in the DOM but has no text and no HTML children. Indicates the rendered finding lost its `detail`/`detail_html`. | YES | Resume the **owning reviewer agent** (Pattern A). The agent must append a `ReviewConcept` with non-empty `detail_html` for the offending concept_id, or a `ConceptUpdate` filling the field. |
| `interaction-no-detail` | Clicking a `.kf-row` did not reveal a `.kf-detail-summary`, or the revealed detail was empty. | NO — **BLOCK** | Renderer JS gap. `toggleKFDetail` or the row/detail-row pairing is broken. Points at `scripts/render_review_pack.py::render_key_findings` and `assets/template_v2.html`. Banner stays. |
| `interaction-filter-broken` | Clicking an agent filter pill (`.kf-agent-pill`) did not change the visible-row count when other rows existed for other agents, or *increased* the visible count. | NO — **BLOCK** | Renderer JS gap. `filterKFByAgent` is broken or the agent classification on the rows is wrong. Points at `scripts/render_review_pack.py::render_key_findings` and the inline JS in `assets/template_v2.html`. Banner stays. |
| `interaction-gate-empty` | Clicking a `.gate-review-card` did not reveal a `.gate-detail` body, or the body was empty. | YES | Re-run the assembler — `convergence.gates[*].detail` (HTML) is the source. If the source data has the field, this is a renderer gap; flag as `renderer-template-gap` instead. |
| `architecture-assessment-schema` | The rendered `architectureAssessment` object is missing a required field, has an invalid `overallHealth`, or its values disagree with the source `.jsonl` `_type: "architecture_assessment"` line. | YES | Resume the **architecture reviewer agent** (Pattern A). Append a corrected `architecture_assessment` line. If the schema mismatch is in fields the assembler computes, re-run the assembler. |
| `renderer-template-gap` | Catch-all for "the data is correct but the rendered HTML element is missing." Banner-strip emits this when serial-mode would have skipped it but a flag check caught a regression. | NO — **BLOCK** | Renderer/template gap. Banner stays; orchestrator points at `scripts/render_review_pack.py` (and `assets/template_v2.html` if templating). |
| `diff-data-missing` | The pack HTML does not contain a parseable `const DIFF_DATA_INLINE = {...};` block. The renderer inserts this block; its absence indicates a renderer or pipeline failure. Without it the spec cannot validate finding-location-mismatch or file-coverage-gap, so it must fail loud rather than silently passing. | YES | Re-run the renderer (`scripts/render_review_pack.py --diff-data ...`) ensuring `--diff-data` points at the assembler-produced diff data JSON. If the renderer is correctly invoked but still omits the block, this becomes `renderer-template-gap`. |

## CI Enforcement

The spec must not emit a `LIVE_PACK_FAIL` code that is not in this file.
The skill repo's CI runs the following grep-check:

```bash
# Extract every code literal from the spec. Matches single-quoted,
# double-quoted, and backtick-quoted code arguments so a quote-style
# switch cannot bypass parity enforcement.
SPEC_CODES=$(grep -oE "liveFail\(\s*['\"\`][a-z][a-z0-9-]*['\"\`]" \
  packages/pr-review-pack/e2e/live-pack-validation.spec.ts \
  | sed -E "s/.*['\"\`]([a-z0-9-]+)['\"\`].*/\1/" | sort -u)

# Sanity guard: empty extraction means the regex broke and the parity
# check would silently pass. Fail loud if either side is empty.
[ -n "$SPEC_CODES" ] || { echo "spec_codes empty"; exit 1; }

# Extract every registered code from this file.
REGISTRY_CODES=$(grep -E "^\| \`[a-z][a-z0-9-]*\` \|" \
  packages/pr-review-pack/references/live-pack-failure-codes.md \
  | sed -E 's/^\| `([a-z0-9-]+)`.*/\1/' | sort -u)
[ -n "$REGISTRY_CODES" ] || { echo "reg_codes empty"; exit 1; }

# Every spec code must be in the registry; every registry code must be in the spec.
diff <(echo "$SPEC_CODES") <(echo "$REGISTRY_CODES")
```

A non-empty diff fails the CI job. See
`.github/workflows/ci.yaml::pr-review-pack-skill-check` for the live job.

## Adding a New Code

1. Add a row to the table above with the four columns filled in.
2. Use the new code in the spec via `liveFail('your-new-code', { ... })`.
3. If the code is auto-correctable, name a specific reviewer agent or
   pipeline step that handles it.
4. If the code is `BLOCK`, explain why no auto-correction is possible.
5. Add a fault-injection regression test in
   `tests/live-pack-validation/` that synthesizes a fault and asserts the
   spec emits exactly your new code.
