"""Shared utilities for live-pack-validation fault-injection tests.

Each test in this directory:
1. Takes the locally-checked-in pr36 review pack as a clean baseline.
2. Mutates either its embedded `const DATA = {...};` JSON or its rendered HTML
   to inject a deliberate fault.
3. Runs the live-pack-validation Playwright project against the mutated pack.
4. Asserts the spec emits exactly the expected `LIVE_PACK_FAIL` code.

The baseline pack sits in the repo at
`docs/pr36_review_pack_<base>-<head>.html`. The .jsonl source files for it
live under `docs/reviews/pr36/` so the spec can validate against source of truth.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = PACKAGE_DIR.parent.parent

BASELINE_PACK = REPO_ROOT / "docs" / "pr36_review_pack_514497a0-3e1e11d3.html"

PLAYWRIGHT_AVAILABLE = (PACKAGE_DIR / "node_modules" / "@playwright" / "test").exists()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if PLAYWRIGHT_AVAILABLE:
        return
    skip_marker = pytest.mark.skip(
        reason=(
            "Playwright not installed in packages/pr-review-pack/node_modules. "
            "These tests run in the pr-review-pack-skill-check CI job, not the "
            "generic test job. Run `npm ci` in packages/pr-review-pack/ to enable."
        )
    )
    for item in items:
        item.add_marker(skip_marker)


def baseline_pack_exists() -> bool:
    return BASELINE_PACK.exists()


@dataclass
class PlaywrightRun:
    """Result of running the live-pack spec against a mutated pack."""

    exit_code: int
    stdout: str
    stderr: str

    def codes(self) -> list[str]:
        """Parse all unique LIVE_PACK_FAIL codes from stderr+stdout."""
        seen: list[str] = []
        # Playwright surfaces failure diagnostics on stdout (in the test
        # output formatter), not stderr. We scrape both.
        text = self.stdout + "\n" + self.stderr
        # Match: LIVE_PACK_FAIL {"code":"<code>",...}
        for m in re.finditer(r'LIVE_PACK_FAIL\s+(\{.*\})', text):
            try:
                payload = json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
            code = payload.get("code")
            if isinstance(code, str) and code not in seen:
                seen.append(code)
        return seen


def run_live_pack_spec(pack_path: Path, *, grep: str | None = None) -> PlaywrightRun:
    """Invoke `npx playwright test --project=live-pack-validation` against pack_path.

    Args:
        pack_path: absolute path to the (possibly mutated) review pack HTML.
        grep: optional Playwright -g filter to limit which tests run.

    Returns:
        PlaywrightRun with captured stdout/stderr and exit code.
    """
    env = os.environ.copy()
    env["PACK_PATH"] = str(pack_path)
    cmd = [
        "npx",
        "playwright",
        "test",
        "--project=live-pack-validation",
        "--reporter=list",
    ]
    if grep:
        cmd.extend(["-g", grep])
    proc = subprocess.run(
        cmd,
        cwd=PACKAGE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return PlaywrightRun(
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


# ---------------------------------------------------------------------------
# Pack mutation helpers
# ---------------------------------------------------------------------------


_DATA_PREFIX = "const DATA = "


def _find_object_end(html: str, start: int) -> int:
    """Given an index pointing at `{` in `html`, return the index AFTER the
    matching closing `}`. Tracks JS string literals (including escapes) so
    braces inside strings don't confuse the counter.
    """
    if html[start] != "{":
        raise RuntimeError("expected '{' at start of object")
    depth = 0
    i = start
    in_str: str | None = None
    while i < len(html):
        ch = html[i]
        if in_str is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_str = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise RuntimeError("unbalanced braces in embedded DATA object")


def read_embedded_data(html: str) -> tuple[dict, tuple[int, int]]:
    """Extract the `const DATA = {...};` JSON object and its byte span.

    The renderer emits multiple `const DATA = {};` placeholder strings; the
    last occurrence (located via rfind, mirroring the renderer's logic)
    is replaced with the real data object. We do the same: find the LAST
    `const DATA = ` prefix, brace-count to its matching `}`, and parse.

    Returns the parsed dict and the (start, end) span of the JSON object
    text (NOT including the prefix or trailing `;`).
    """
    last_idx = html.rfind(_DATA_PREFIX)
    if last_idx < 0:
        raise RuntimeError("could not find `const DATA = ` in pack HTML")
    obj_start = last_idx + len(_DATA_PREFIX)
    if obj_start >= len(html) or html[obj_start] != "{":
        raise RuntimeError("expected '{' after `const DATA = `")
    obj_end = _find_object_end(html, obj_start)
    raw = html[obj_start:obj_end]
    data = json.loads(raw)
    return data, (obj_start, obj_end)


def write_embedded_data(html: str, data: dict, span: tuple[int, int]) -> str:
    """Substitute the embedded DATA JSON with `data` at the given span."""
    new_json = json.dumps(data, indent=2)
    return html[: span[0]] + new_json + html[span[1] :]


def _strip_glob_row_findings(data: dict) -> dict:
    """Remove agenticReview.findings entries whose `file` uses glob notation.

    The pr36 baseline pack was generated by an older assembler that emitted
    multi-file concepts as a single finding with a `path/to/* (N files)`
    string. The live-pack spec correctly flags these as `glob-row-leak`.
    For fault-injection tests of LATER-running checks, we strip the glob
    findings from DATA. The HTML cleaning is handled separately by
    `_strip_glob_rows_from_html`.
    """
    findings = data.get("agenticReview", {}).get("findings", [])
    cleaned = [f for f in findings if not re.search(r"\(\d+ files?\)", str(f.get("file", "")))]
    data["agenticReview"]["findings"] = cleaned
    return data


def _strip_glob_rows_from_html(html: str) -> str:
    """Remove rendered (N files) glob rows from the static HTML body text.

    The pre-rendered pr36 HTML contains rows whose visible text includes
    `path/to/* (N files)`. Cleaning DATA does not retroactively unrender
    those rows. We strip any kf-row / cr-file-row whose visible text
    contains the glob pattern, so fault-injection tests of LATER-running
    checks can reach their target.
    """
    out = html
    out = re.sub(
        r'<tr class="kf-row"[^>]*>[\s\S]*?\(\d+ files?\)[\s\S]*?</tr>'
        r'\s*<tr class="kf-detail-row"[^>]*>[\s\S]*?</tr>',
        "",
        out,
    )
    out = re.sub(
        r'<tr class="cr-file-row"[^>]*>[\s\S]*?\(\d+ files?\)[\s\S]*?</tr>',
        "",
        out,
    )
    return out


@pytest.fixture()
def mutate_pack(tmp_path: Path):
    """Fixture that returns a callable for mutating a pack and yielding its path.

    Usage:
        def test_something(mutate_pack):
            def mutator(data: dict) -> dict:
                data['agenticReview']['findings'][0]['file'] = 'nonexistent.py'
                return data
            mutated_path = mutate_pack(mutator)
            run = run_live_pack_spec(mutated_path)
            assert run.codes() == ['finding-location-mismatch']

    The `clean_baseline=True` option (default) first strips known issues
    from the pr36 baseline (glob-row leaks) so injected faults are tested
    in isolation. Pass `clean_baseline=False` if you want to assert
    against pr36's existing faults (e.g., the glob-row-leak test itself).
    """
    if not baseline_pack_exists():
        # Fail loud, not skip. A skipped fault-injection suite reports green
        # while exercising zero failure codes — exactly the silent-vacuous
        # mode the F-grade adversarial finding on PR #42 called out. The
        # baseline pack is checked into the repo at the BASELINE_PACK path;
        # if it's missing, that's a regression in the repo state, not a
        # local-environment quirk to skip past.
        raise FileNotFoundError(
            f"Baseline pack not found at {BASELINE_PACK}. The pr36 baseline "
            "and its docs/reviews/pr36/ source jsonl files are tracked in "
            "git and required by the fault-injection regression suite. If "
            "they're missing, check git status and restore from origin."
        )

    def _mutate(
        data_mutator=None,
        html_mutator=None,
        jsonl_mutator=None,
        clean_baseline: bool = True,
    ) -> Path:
        """Apply mutations and return path to the mutated pack.

        jsonl_mutator: optional callable (target_dir: Path) -> None that
        runs after the source `.jsonl` files have been mirrored next to
        the mutated pack. Use it to inject malformed source lines for
        codes whose trigger lives in the source jsonl rather than the
        rendered pack.
        """
        if (
            data_mutator is None
            and html_mutator is None
            and jsonl_mutator is None
            and clean_baseline is False
        ):
            raise ValueError(
                "provide a data_mutator, html_mutator, jsonl_mutator, or clean_baseline"
            )
        html = BASELINE_PACK.read_text(encoding="utf-8")
        if clean_baseline or data_mutator is not None:
            data, span = read_embedded_data(html)
            if clean_baseline:
                data = _strip_glob_row_findings(data)
            if data_mutator is not None:
                data = data_mutator(data)
            html = write_embedded_data(html, data, span)
        if clean_baseline:
            html = _strip_glob_rows_from_html(html)
        if html_mutator is not None:
            html = html_mutator(html)
        out = tmp_path / "pr36_review_pack_mutated.html"
        out.write_text(html, encoding="utf-8")
        # Mirror the source jsonl directory next to the pack so the
        # spec's `loadSourceJsonl` walk finds it. Pack lives at
        # tmp_path/pr36_review_pack_mutated.html and the reviews at
        # tmp_path/docs/reviews/pr36/, matching the spec's first probe
        # `${dir}/docs/reviews/pr${pr}`.
        source_reviews = REPO_ROOT / "docs" / "reviews" / "pr36"
        target_docs = tmp_path / "docs" / "reviews" / "pr36"
        if source_reviews.exists():
            target_docs.parent.mkdir(parents=True, exist_ok=True)
            if not target_docs.exists():
                shutil.copytree(source_reviews, target_docs)
        if jsonl_mutator is not None:
            jsonl_mutator(target_docs)
        return out

    return _mutate
