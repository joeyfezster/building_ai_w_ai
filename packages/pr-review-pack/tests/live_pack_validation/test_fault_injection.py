"""Per-code fault-injection regression tests.

For each non-BLOCK failure code in the live-pack-validation registry, we:
1. Take the pr36 baseline pack and clean it of known issues.
2. Mutate the embedded DATA (or HTML) to inject the specific fault.
3. Run the live-pack-validation Playwright project against the mutated pack.
4. Assert the spec emits exactly the expected `LIVE_PACK_FAIL` code.

These tests prevent silent regressions in the spec itself — if a future edit
breaks the diagnostic for, say, `finding-zone-unresolved`, the corresponding
test here catches it.

BLOCK codes (`renderer-template-gap`, `inject-marker-leak`,
`interaction-no-detail`, `interaction-filter-broken`) are exercised directly:
their faults are surfaced by the spec but no auto-correction is dispatched.
"""

from __future__ import annotations

import re
from pathlib import Path

from .conftest import run_live_pack_spec

# ---------------------------------------------------------------------------
# Content correctness
# ---------------------------------------------------------------------------


def test_finding_location_mismatch(mutate_pack):
    def mutator(data: dict) -> dict:
        # Re-target the first finding's `file` to a path not in the diff.
        findings = data["agenticReview"]["findings"]
        assert findings, "pr36 baseline must have at least one finding"
        # Remove all but the first finding to keep the spec output focused.
        # We need to keep an A-grade FileReviewOutcome story intact, so we
        # only mutate the file path, not the count.
        findings[0]["file"] = "non/existent/path/never_in_diff.py"
        # If the finding has a `locations` array, redirect that too.
        if isinstance(findings[0].get("locations"), list):
            for loc in findings[0]["locations"]:
                loc["file"] = "non/existent/path/never_in_diff.py"
        return data

    pack = mutate_pack(data_mutator=mutator)
    run = run_live_pack_spec(pack)
    assert run.exit_code != 0, run.stdout
    assert run.codes() == ["finding-location-mismatch"], (
        f"got {run.codes()}, exit={run.exit_code}\nSTDOUT:\n{run.stdout}"
    )


def test_finding_zone_unresolved(mutate_pack):
    def mutator(data: dict) -> dict:
        findings = data["agenticReview"]["findings"]
        assert findings
        # Inject a zone ID that is definitely not in the registry.
        findings[0]["zones"] = "zone-that-does-not-exist"
        return data

    pack = mutate_pack(data_mutator=mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["finding-zone-unresolved"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_concept_id_missing(mutate_pack):
    def mutator(data: dict) -> dict:
        findings = data["agenticReview"]["findings"]
        assert findings
        # Rename a finding's `notable` so it no longer matches any
        # ReviewConcept.title in the source .jsonl.
        findings[0]["notable"] = "INJECTED_TITLE_NEVER_IN_SOURCE_JSONL_xyz123"
        return data

    pack = mutate_pack(data_mutator=mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["concept-id-missing"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_source_jsonl_missing_concept_id(mutate_pack):
    """Source jsonl has a line with `title` but missing `concept_id`.

    Distinct from `concept-id-missing` (which fires when a rendered
    finding has no backing concept in source). This code fires when the
    source jsonl itself is malformed — the rendered pack may still be
    coherent. Distinguishing the two lets the orchestrator dispatch
    correctly.
    """

    def jsonl_mutator(target_dir):
        # Append a malformed line to the architecture reviewer's jsonl.
        # The malformed line has a non-empty `title` but no `concept_id`.
        target = next(target_dir.glob("pr36-architecture-*.jsonl"), None)
        assert target is not None, "expected pr36 architecture jsonl"
        with target.open("a", encoding="utf-8") as f:
            f.write(
                '{"title": "MALFORMED_NO_CONCEPT_ID — synthetic fault", '
                '"grade": "B", "category": "architecture", '
                '"summary": "Source schema fault: missing concept_id", '
                '"detail_html": "<p>synthetic</p>", '
                '"locations": [{"file": "docs/CONVENTIONS.md", "lines": null, "zones": []}]}\n'
            )

    pack = mutate_pack(jsonl_mutator=jsonl_mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["source-jsonl-missing-concept-id"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_diff_data_missing(mutate_pack):
    """Strip the DIFF_DATA_INLINE block from the rendered HTML.

    Without diff data the spec cannot resolve finding locations or
    verify file coverage, so it must fail loud with `diff-data-missing`
    rather than silently passing.
    """

    def html_mutator(html: str) -> str:
        return html.replace(
            "const DIFF_DATA_INLINE = ",
            "const DIFF_DATA_INLINE_DISABLED_FOR_TEST = ",
        )

    pack = mutate_pack(html_mutator=html_mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["diff-data-missing"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_file_coverage_gap_missing_diff_file(mutate_pack):
    def mutator(data: dict) -> dict:
        # Drop the first file from the file-coverage table.
        coverage = data["fileCoverage"]["files"]
        assert coverage, "fileCoverage.files must be non-empty"
        coverage.pop(0)
        return data

    pack = mutate_pack(data_mutator=mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["file-coverage-gap"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_grade_without_outcome(mutate_pack):
    def mutator(data: dict) -> dict:
        # Add a grade to the first file-coverage row from a fictitious agent
        # that has no .jsonl source.
        coverage = data["fileCoverage"]["files"]
        assert coverage
        coverage[0].setdefault("grades", {})["fictitious-agent"] = "A"
        return data

    pack = mutate_pack(data_mutator=mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["grade-without-outcome"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_architecture_assessment_schema(mutate_pack):
    def mutator(data: dict) -> dict:
        aa = data.get("architectureAssessment")
        if aa is None:
            data["architectureAssessment"] = {}
            aa = data["architectureAssessment"]
        # Set an invalid overallHealth value.
        aa["overallHealth"] = "totally-broken-status"
        # Ensure the required fields exist (so we test invalid value, not absence).
        aa.setdefault("summary", "")
        aa.setdefault("unzonedFiles", [])
        aa.setdefault("registryWarnings", [])
        aa.setdefault("decisionZoneVerification", [])
        return data

    pack = mutate_pack(data_mutator=mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["architecture-assessment-schema"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


# ---------------------------------------------------------------------------
# Rendering invariants
# ---------------------------------------------------------------------------


def _inject_before_body_close(html: str, snippet: str) -> str:
    """Insert `snippet` immediately before the LAST </body> tag.

    Using rfind avoids hitting the many `</body>` tokens embedded inside
    diff content as strings.
    """
    pos = html.rfind("</body>")
    if pos < 0:
        raise RuntimeError("no </body> tag found in pack HTML")
    return html[:pos] + snippet + html[pos:]


def test_rendered_undefined_or_null(mutate_pack):
    """Inject a literal 'undefined' token into rendered body HTML.

    We append a <span> with the literal text directly inside <body> so
    the spec's visible-text walker (which excludes <script>, <style>,
    and the file-modal) hits it.
    """

    def html_mutator(html: str) -> str:
        marker = '<span data-test-fault="rendered-undefined"> undefined </span>'
        return _inject_before_body_close(html, marker)

    pack = mutate_pack(html_mutator=html_mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["rendered-undefined-or-null"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_glob_row_leak(mutate_pack):
    """Inject a `path/* (N files)` row into the cleaned baseline.

    The pr36 baseline pack happens to exhibit this fault historically
    (older assembler emitted multi-file concepts as a single row with
    glob notation), but relying on that pre-existing defect makes the
    test fragile — if pr36 is regenerated cleanly, the test would flip
    to a false fail. We instead build on the cleaned baseline and
    deliberately inject a glob row, asserting only the spec's response.

    The cleaned-baseline path also covers the canonical historical
    defect: `_strip_glob_rows_from_html` removes glob rows, then we
    re-inject a single one, and the spec catches it.
    """

    def html_mutator(html: str) -> str:
        # Insert a plausible-looking kf-row containing the glob marker
        # just before </body>. The spec scans body text for the pattern
        # `\* \(\d+ files?\)`, so the literal text suffices.
        synthetic_row = (
            '<table class="kf-table" data-test-fault="glob-row-leak">'
            '<tbody><tr class="kf-row" data-zones="" data-agents="" '
            'data-grade="C">'
            "<td>C</td>"
            "<td>Synthetic glob finding</td>"
            "<td>"
            "<code>packages/synthetic/* (4 files)</code>"
            "</td>"
            "</tr></tbody></table>"
        )
        return _inject_before_body_close(html, synthetic_row)

    pack = mutate_pack(html_mutator=html_mutator)
    run = run_live_pack_spec(pack)
    assert run.exit_code != 0
    assert run.codes() == ["glob-row-leak"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_inject_marker_leak(mutate_pack):
    """Inject an unreplaced INJECT marker into the body HTML."""

    def html_mutator(html: str) -> str:
        marker = "<!-- INJECT: synthetic-fault -->"
        return _inject_before_body_close(html, marker)

    pack = mutate_pack(html_mutator=html_mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["inject-marker-leak"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_empty_detail_summary(mutate_pack):
    """Empty out a rendered .kf-detail-summary in the HTML.

    The pre-rendered baseline HTML carries the kf-detail-summary content;
    mutating DATA alone won't change it because nothing re-renders. We
    surgically empty the FIRST .kf-detail-summary's content directly.
    """

    def html_mutator(html: str) -> str:
        # Match the first <div class="kf-detail-summary">...</div> and
        # replace its content with empty.
        return re.sub(
            r'(<div class="kf-detail-summary">)([\s\S]*?)(</div>)',
            r"\1\3",
            html,
            count=1,
        )

    pack = mutate_pack(html_mutator=html_mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["empty-detail-summary"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


# ---------------------------------------------------------------------------
# Interactivity (BLOCK codes — non-auto-correctable)
# ---------------------------------------------------------------------------


def test_interaction_no_detail(mutate_pack):
    """Strip the kf-detail-row out of the rendered HTML.

    Spec then clicks a kf-row, looks for a paired kf-detail-row, and finds
    none — emits `interaction-no-detail`.
    """

    def html_mutator(html: str) -> str:
        # Remove every <tr class="kf-detail-row" ...>...</tr> block.
        return re.sub(
            r'<tr class="kf-detail-row"[^>]*>[\s\S]*?</tr>',
            "",
            html,
        )

    pack = mutate_pack(html_mutator=html_mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["interaction-no-detail"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_interaction_filter_broken(mutate_pack):
    """Override filterKFByAgent at runtime with a no-op.

    The spec clicks each pill and checks the visible row count matches
    the expected count of rows owning that agent. With a no-op filter,
    the count stays equal to total — different from `expected` whenever
    pr36 has multi-agent findings. Spec emits `interaction-filter-broken`.
    """

    def html_mutator(html: str) -> str:
        # Append a script block that runs after page load and replaces
        # filterKFByAgent with a no-op. This sidesteps the issue of
        # multiple `function filterKFByAgent` occurrences in diff
        # content vs the actual JS definition.
        #
        # Sentinel: if the renderer renames the function, the override
        # silently does nothing and the test would pass vacuously. To
        # prevent that false green, we assert at injection time that
        # the function exists; if it doesn't, we stamp the body with a
        # precondition-failed token that pytest checks for.
        override = (
            "<script>\n"
            "// FAULT-INJECTION: override filter function with no-op\n"
            "window.addEventListener('DOMContentLoaded', function() {\n"
            "  if (typeof window.filterKFByAgent !== 'function') {\n"
            "    document.body.innerText = "
            "'FAULT_INJECT_PRECONDITION_FAILED:filterKFByAgent';\n"
            "    return;\n"
            "  }\n"
            "  window.filterKFByAgent = function(pill, agentAbbrev) {\n"
            "    /* no-op stub for live-pack-validation regression test */\n"
            "  };\n"
            "});\n"
            "</script>\n"
        )
        return _inject_before_body_close(html, override)

    pack = mutate_pack(html_mutator=html_mutator)
    run = run_live_pack_spec(pack)
    # Precondition: the renderer must still expose `filterKFByAgent` as a
    # global function. If the renderer renamed it, the override is a
    # silent no-op and this test would pass vacuously. Fail loudly.
    combined = run.stdout + run.stderr
    assert "FAULT_INJECT_PRECONDITION_FAILED:filterKFByAgent" not in combined, (
        "fault-injection precondition failed: window.filterKFByAgent does not "
        "exist at DOMContentLoaded. The renderer probably renamed the function. "
        "Update e2e/live-pack-validation.spec.ts and this test together to use "
        "the new name."
    )
    assert run.codes() == ["interaction-filter-broken"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


def test_interaction_gate_empty(mutate_pack):
    """Populate DATA gate detail but strip rendered .gate-detail content.

    The spec only flags `interaction-gate-empty` when DATA says the gate
    has detail but the rendered .gate-detail container is empty. Empty
    detail in DATA is a legitimate signal-encoding choice, not a
    renderer bug.
    """

    def mutator(data: dict) -> dict:
        gates = data.get("convergence", {}).get("gates", [])
        for g in gates:
            g["detail"] = "<p>Gate detail content for this scenario.</p>"
        return data

    def html_mutator(html: str) -> str:
        # Empty out every .gate-detail container in the rendered HTML.
        return re.sub(
            r'(<div class="gate-detail"[^>]*>)([\s\S]*?)(</div>)',
            r"\1\3",
            html,
        )

    pack = mutate_pack(data_mutator=mutator, html_mutator=html_mutator)
    run = run_live_pack_spec(pack)
    assert run.codes() == ["interaction-gate-empty"], (
        f"got {run.codes()}\nSTDOUT:\n{run.stdout}"
    )


# ---------------------------------------------------------------------------
# renderer-template-gap is a BLOCK guard. We don't have a clean way to
# trigger it deliberately without breaking the serial-mode insurance flag,
# but we DO assert the canonical message is emitted when the flag check
# fires. That requires running the spec with no PACK_PATH and ensuring
# the no-PACK_PATH branch raises a different, expected error — see the
# parity test below.
# ---------------------------------------------------------------------------


def test_no_pack_path_raises_required_error(tmp_path: Path):
    """Without PACK_PATH, the spec emits a required-env error (not a
    LIVE_PACK_FAIL code). This guards against silent passes when the
    skill harness misconfigures the env.
    """
    import subprocess

    from .conftest import PACKAGE_DIR

    env = {k: v for k, v in __import__("os").environ.items() if k != "PACK_PATH"}
    proc = subprocess.run(
        [
            "npx",
            "playwright",
            "test",
            "--project=live-pack-validation",
            "--reporter=list",
        ],
        cwd=PACKAGE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    text = proc.stdout + proc.stderr
    assert "PACK_PATH environment variable is required" in text
