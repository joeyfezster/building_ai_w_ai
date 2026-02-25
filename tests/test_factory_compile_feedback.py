"""Tests for the factory's own feedback compiler (scripts/compile_feedback.py).

These test the factory's infrastructure, not the product code.
Every test exercises real code paths — no mocking of compile_feedback internals.
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

# Insert scripts/ into path so we can import the non-package modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from compile_feedback import (  # noqa: E402, I001
    compile_feedback,
    get_iteration_count,
    get_previous_feedback,
    infer_causes,
    load_ci_log,
    load_scenario_results,
)


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture()
def factory_dir(tmp_path: Path) -> Path:
    """Create a temporary factory artifacts directory."""
    d = tmp_path / "factory"
    d.mkdir()
    return d


def _make_results(
    factory_dir: Path,
    passed: int = 5,
    failed: int = 7,
    results: list[dict] | None = None,
) -> Path:
    """Write a scenario_results.json to the factory dir."""
    total = passed + failed
    score = passed / total if total > 0 else 0.0
    if results is None:
        results = []
        for i in range(passed):
            results.append({
                "name": f"passing_{i}",
                "category": "test",
                "passed": True,
                "exit_code": 0,
                "stdout": "ok",
                "stderr": "",
                "duration_seconds": 0.5,
            })
        for i in range(failed):
            results.append({
                "name": f"failing_{i}",
                "category": "test",
                "passed": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": "ModuleNotFoundError: No module named 'foo'"
                if i % 2 == 0
                else "AssertionError: expected True",
                "duration_seconds": 1.0,
                "error_summary": "ModuleNotFoundError"
                if i % 2 == 0
                else "AssertionError",
            })
    data = {
        "timestamp": "2026-02-22T00:00:00Z",
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": 0,
        "satisfaction_score": round(score, 4),
        "results": results,
    }
    path = factory_dir / "scenario_results.json"
    path.write_text(json.dumps(data, indent=2))
    return path


def _make_feedback(factory_dir: Path, iteration: int, score: float) -> Path:
    """Write a feedback file for trajectory testing."""
    content = textwrap.dedent(f"""\
        # Factory Feedback — Iteration {iteration}

        ## Summary
        - **Satisfaction score: {score:.0%}** (x/y scenarios passed)
        - Passed: x | Failed: y | Total: z

        ## Likely Root Causes
        1. Some cause.
    """)
    path = factory_dir / f"feedback_iter_{iteration}.md"
    path.write_text(content)
    return path


# ── load_scenario_results tests ──────────────────────────────


class TestLoadScenarioResults:
    """Tests for loading scenario results JSON."""

    def test_returns_none_when_file_missing(
        self, factory_dir: Path
    ) -> None:
        result = load_scenario_results(factory_dir / "nonexistent.json")
        assert result is None

    def test_loads_valid_json(self, factory_dir: Path) -> None:
        _make_results(factory_dir, passed=3, failed=2)
        result = load_scenario_results(
            factory_dir / "scenario_results.json"
        )
        assert result is not None
        assert result["total"] == 5
        assert result["passed"] == 3
        assert result["failed"] == 2

    def test_preserves_satisfaction_score(
        self, factory_dir: Path
    ) -> None:
        _make_results(factory_dir, passed=8, failed=4)
        result = load_scenario_results(
            factory_dir / "scenario_results.json"
        )
        assert result is not None
        # 8/12 = 0.6667
        assert 0.66 < result["satisfaction_score"] < 0.67


# ── load_ci_log tests ────────────────────────────────────────


class TestLoadCiLog:
    """Tests for loading CI output logs."""

    def test_returns_placeholder_when_missing(
        self, factory_dir: Path
    ) -> None:
        result = load_ci_log(factory_dir / "ci_output.log")
        assert "no ci log" in result.lower()

    def test_loads_full_log(self, factory_dir: Path) -> None:
        log_path = factory_dir / "ci_output.log"
        log_path.write_text("line1\nline2\nline3")
        result = load_ci_log(log_path)
        assert "line1" in result
        assert "line3" in result

    def test_truncates_long_logs(self, factory_dir: Path) -> None:
        log_path = factory_dir / "ci_output.log"
        # Write a log longer than 10000 chars
        log_path.write_text("A" * 5000 + "MIDDLE" + "Z" * 5001)
        result = load_ci_log(log_path)
        assert "truncated" in result.lower()
        # Should preserve start and end
        assert result.startswith("A")
        assert result.rstrip().endswith("Z")


# ── get_iteration_count tests ────────────────────────────────


class TestGetIterationCount:
    """Tests for reading iteration count."""

    def test_returns_zero_when_no_file(self, factory_dir: Path) -> None:
        count = get_iteration_count(factory_dir)
        assert count == 0

    def test_reads_integer_from_file(self, factory_dir: Path) -> None:
        (factory_dir / "iteration_count.txt").write_text("5\n")
        count = get_iteration_count(factory_dir)
        assert count == 5

    def test_handles_invalid_content(self, factory_dir: Path) -> None:
        (factory_dir / "iteration_count.txt").write_text("not a number\n")
        count = get_iteration_count(factory_dir)
        assert count == 0


# ── get_previous_feedback tests ──────────────────────────────


class TestGetPreviousFeedback:
    """Tests for loading feedback history."""

    def test_returns_empty_when_no_feedback(
        self, factory_dir: Path
    ) -> None:
        result = get_previous_feedback(factory_dir)
        assert result == []

    def test_loads_ordered_feedback(self, factory_dir: Path) -> None:
        _make_feedback(factory_dir, 1, 0.25)
        _make_feedback(factory_dir, 2, 0.50)
        _make_feedback(factory_dir, 3, 0.75)
        result = get_previous_feedback(factory_dir)
        assert len(result) == 3
        assert result[0][0] == 1  # iteration number
        assert result[2][0] == 3

    def test_extracts_summary_section(self, factory_dir: Path) -> None:
        _make_feedback(factory_dir, 1, 0.42)
        result = get_previous_feedback(factory_dir)
        assert len(result) == 1
        # Summary should contain the satisfaction score
        assert "42%" in result[0][1]


# ── infer_causes tests ───────────────────────────────────────


class TestInferCauses:
    """Tests for root cause inference from error patterns."""

    def test_detects_import_errors(self) -> None:
        results = {
            "results": [
                {
                    "name": "broken",
                    "passed": False,
                    "stderr": "ModuleNotFoundError: No module named 'foo'",
                    "stdout": "",
                }
            ]
        }
        causes = infer_causes(results)
        assert any("import" in c.lower() for c in causes)

    def test_detects_assertion_errors(self) -> None:
        results = {
            "results": [
                {
                    "name": "assertion_fail",
                    "passed": False,
                    "stderr": "AssertionError: expected True",
                    "stdout": "",
                }
            ]
        }
        causes = infer_causes(results)
        assert any("assertion" in c.lower() for c in causes)

    def test_detects_timeouts(self) -> None:
        results = {
            "results": [
                {
                    "name": "slow",
                    "passed": False,
                    "stderr": "TIMEOUT: exceeded 60s",
                    "stdout": "",
                }
            ]
        }
        causes = infer_causes(results)
        assert any("timeout" in c.lower() for c in causes)

    def test_detects_file_not_found(self) -> None:
        results = {
            "results": [
                {
                    "name": "missing",
                    "passed": False,
                    "stderr": "FileNotFoundError: [Errno 2] No such file",
                    "stdout": "",
                }
            ]
        }
        causes = infer_causes(results)
        assert any("missing file" in c.lower() for c in causes)

    def test_returns_fallback_for_unknown_patterns(self) -> None:
        results = {
            "results": [
                {
                    "name": "weird",
                    "passed": False,
                    "stderr": "SegmentationFault: core dumped",
                    "stdout": "",
                }
            ]
        }
        causes = infer_causes(results)
        assert any("no clear pattern" in c.lower() for c in causes)

    def test_ignores_passing_scenarios(self) -> None:
        results = {
            "results": [
                {
                    "name": "good",
                    "passed": True,
                    "stderr": "ModuleNotFoundError in warning",
                    "stdout": "",
                }
            ]
        }
        causes = infer_causes(results)
        # Should not flag the passing scenario
        assert not any("good" in c for c in causes)

    def test_multiple_error_types(self) -> None:
        results = {
            "results": [
                {
                    "name": "import_fail",
                    "passed": False,
                    "stderr": "ModuleNotFoundError: no module 'x'",
                    "stdout": "",
                },
                {
                    "name": "assert_fail",
                    "passed": False,
                    "stderr": "AssertionError: bad",
                    "stdout": "",
                },
            ]
        }
        causes = infer_causes(results)
        # Should detect both patterns
        assert any("import" in c.lower() for c in causes)
        assert any("assertion" in c.lower() for c in causes)


# ── compile_feedback tests ───────────────────────────────────


class TestCompileFeedback:
    """Tests for the main feedback compilation function."""

    def test_produces_markdown_with_header(self) -> None:
        feedback = compile_feedback(
            results=None,
            ci_log="",
            iteration=1,
            previous_feedback=[],
        )
        assert "# Factory Feedback — Iteration 1" in feedback

    def test_includes_satisfaction_score(self) -> None:
        results = {
            "total": 10,
            "passed": 7,
            "failed": 3,
            "satisfaction_score": 0.7,
            "results": [],
        }
        feedback = compile_feedback(
            results=results,
            ci_log="",
            iteration=1,
            previous_feedback=[],
        )
        assert "70%" in feedback
        assert "7/10" in feedback

    def test_includes_convergence_trajectory(self) -> None:
        previous = [
            (1, "Score: 25%"),
            (2, "Score: 50%"),
        ]
        feedback = compile_feedback(
            results=None,
            ci_log="",
            iteration=3,
            previous_feedback=previous,
        )
        assert "Convergence Trajectory" in feedback
        assert "Score: 25%" in feedback
        assert "Score: 50%" in feedback

    def test_includes_ci_log_when_present(self) -> None:
        feedback = compile_feedback(
            results=None,
            ci_log="ruff check failed with 5 errors",
            iteration=1,
            previous_feedback=[],
        )
        assert "ruff check failed" in feedback

    def test_excludes_ci_log_placeholder(self) -> None:
        feedback = compile_feedback(
            results=None,
            ci_log="(no CI log available)",
            iteration=1,
            previous_feedback=[],
        )
        assert "CI Log Output" not in feedback

    def test_includes_failed_scenario_details(self) -> None:
        results = {
            "total": 2,
            "passed": 1,
            "failed": 1,
            "satisfaction_score": 0.5,
            "results": [
                {
                    "name": "good_one",
                    "category": "test",
                    "passed": True,
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "duration_seconds": 0.1,
                },
                {
                    "name": "bad_one",
                    "category": "test",
                    "passed": False,
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "ImportError: no module named 'x'",
                    "duration_seconds": 0.2,
                    "error_summary": "ImportError",
                },
            ],
        }
        feedback = compile_feedback(
            results=results,
            ci_log="",
            iteration=1,
            previous_feedback=[],
        )
        # Should include failed scenario details
        assert "bad_one" in feedback
        assert "ImportError" in feedback
        # Should NOT list passing scenarios in failure details
        assert feedback.count("good_one") == 0 or "Failed" not in feedback.split("good_one")[0]

    def test_includes_instructions_section(self) -> None:
        feedback = compile_feedback(
            results=None,
            ci_log="",
            iteration=1,
            previous_feedback=[],
        )
        assert "Instructions for Coding Agent" in feedback
        assert "Import errors" in feedback

    def test_handles_none_results_gracefully(self) -> None:
        feedback = compile_feedback(
            results=None,
            ci_log="",
            iteration=1,
            previous_feedback=[],
        )
        assert "No scenario results available" in feedback

    def test_output_is_valid_markdown(self) -> None:
        """Basic structural check — headings use ## format."""
        results = {
            "total": 1,
            "passed": 0,
            "failed": 1,
            "satisfaction_score": 0.0,
            "results": [
                {
                    "name": "fail",
                    "category": "test",
                    "passed": False,
                    "exit_code": 1,
                    "stdout": "out",
                    "stderr": "err",
                    "duration_seconds": 1.0,
                    "error_summary": "err",
                },
            ],
        }
        feedback = compile_feedback(
            results=results,
            ci_log="some log",
            iteration=3,
            previous_feedback=[(1, "iter 1"), (2, "iter 2")],
        )
        # Should have proper heading structure
        assert feedback.startswith("# Factory Feedback")
        assert "## Summary" in feedback
        assert "## Likely Root Causes" in feedback
        assert "## Failed Scenarios" in feedback


# ── Integration test ─────────────────────────────────────────


class TestCompileFeedbackIntegration:
    """End-to-end test of the feedback compilation pipeline."""

    def test_full_pipeline(self, factory_dir: Path) -> None:
        """Write results + feedback files, compile, verify output."""
        # Set up iteration 1
        _make_results(factory_dir, passed=3, failed=9)
        _make_feedback(factory_dir, 1, 0.25)

        # Load inputs (real function calls, not mocks)
        results = load_scenario_results(
            factory_dir / "scenario_results.json"
        )
        ci_log = load_ci_log(factory_dir / "ci_output.log")
        previous = get_previous_feedback(factory_dir)

        # Compile
        feedback = compile_feedback(
            results=results,
            ci_log=ci_log,
            iteration=2,
            previous_feedback=previous,
        )

        # Verify all sections are present
        assert "Iteration 2" in feedback
        assert "25%" in feedback  # satisfaction score from results
        assert "Convergence Trajectory" in feedback
        assert "Likely Root Causes" in feedback
        assert "Instructions for Coding Agent" in feedback

        # Verify the output can be written and re-read
        output_path = factory_dir / "feedback_iter_2.md"
        output_path.write_text(feedback)
        reloaded = output_path.read_text()
        assert reloaded == feedback
