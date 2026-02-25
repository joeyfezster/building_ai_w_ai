"""Tests for the factory's own scenario runner (scripts/run_scenarios.py).

These test the factory's infrastructure, not the product code.
Every test exercises real code paths — no mocking of run_scenarios internals.
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

# Insert scripts/ into path so we can import the non-package modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from run_scenarios import (  # noqa: E402, I001
    Scenario,
    ScenarioReport,
    ScenarioResult,
    parse_scenario,
    run_scenario,
)


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture()
def scenario_dir(tmp_path: Path) -> Path:
    """Create a temporary scenarios directory with test scenarios."""
    d = tmp_path / "scenarios"
    d.mkdir()
    return d


def _write_scenario(
    d: Path,
    name: str,
    category: str,
    eval_command: str,
    pass_criteria: str = "Exits with code 0",
) -> Path:
    """Write a scenario markdown file with given parameters."""
    content = textwrap.dedent(f"""\
        # Scenario: {name}

        ## Category
        {category}

        ## Preconditions
        - None

        ## Behavioral Expectation
        Test expectation for {name}.

        ## Evaluation Method
        ```bash
        {eval_command}
        ```

        ## Pass Criteria
        {pass_criteria}

        ## Evidence Required
        - stdout
    """)
    path = d / f"{name.lower().replace(' ', '_')}.md"
    path.write_text(content)
    return path


# ── parse_scenario tests ─────────────────────────────────────


class TestParseScenario:
    """Tests for scenario markdown parsing."""

    def test_parses_name_from_h1(self, scenario_dir: Path) -> None:
        path = _write_scenario(scenario_dir, "Foo Bar Test", "environment", "echo hi")
        scenario = parse_scenario(path)
        assert scenario.name == "Foo Bar Test"

    def test_parses_category(self, scenario_dir: Path) -> None:
        path = _write_scenario(scenario_dir, "Cat Test", "training", "echo hi")
        scenario = parse_scenario(path)
        assert scenario.category == "training"

    def test_parses_evaluation_method_from_code_block(
        self, scenario_dir: Path
    ) -> None:
        path = _write_scenario(
            scenario_dir,
            "Eval Test",
            "environment",
            'python -c "print(42)"',
        )
        scenario = parse_scenario(path)
        assert 'python -c "print(42)"' in scenario.evaluation_method

    def test_parses_preconditions_as_list(self, scenario_dir: Path) -> None:
        content = textwrap.dedent("""\
            # Scenario: Multi Precond

            ## Category
            environment

            ## Preconditions
            - First condition
            - Second condition
            - Third condition

            ## Behavioral Expectation
            Something.

            ## Evaluation Method
            ```bash
            echo ok
            ```

            ## Pass Criteria
            Exits 0.

            ## Evidence Required
            - stdout
        """)
        path = scenario_dir / "multi_precond.md"
        path.write_text(content)
        scenario = parse_scenario(path)
        assert len(scenario.preconditions) == 3
        assert "First condition" in scenario.preconditions[0]

    def test_parses_pass_criteria(self, scenario_dir: Path) -> None:
        path = _write_scenario(
            scenario_dir, "PC Test", "integration", "echo ok", "Script exits with 0"
        )
        scenario = parse_scenario(path)
        assert "exits with 0" in scenario.pass_criteria.lower()

    def test_handles_missing_sections_gracefully(
        self, scenario_dir: Path
    ) -> None:
        """A minimal scenario file should parse without crashing."""
        content = "# Scenario: Minimal\n\n## Category\ntest\n"
        path = scenario_dir / "minimal.md"
        path.write_text(content)
        scenario = parse_scenario(path)
        assert scenario.name == "Minimal"
        assert scenario.category == "test"
        assert scenario.evaluation_method == ""

    def test_returns_scenario_dataclass(self, scenario_dir: Path) -> None:
        path = _write_scenario(scenario_dir, "Type Test", "environment", "echo 1")
        result = parse_scenario(path)
        assert isinstance(result, Scenario)
        assert result.file_path == str(path)


# ── run_scenario tests ───────────────────────────────────────


class TestRunScenario:
    """Tests for scenario execution.

    These run REAL bash commands — not mocked subprocess calls.
    """

    def test_passing_scenario_returns_passed_true(self, tmp_path: Path) -> None:
        scenario = Scenario(
            name="Passing",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method="exit 0",
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=10, repo_root=tmp_path)
        assert result.passed is True
        assert result.exit_code == 0

    def test_failing_scenario_returns_passed_false(self, tmp_path: Path) -> None:
        scenario = Scenario(
            name="Failing",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method="exit 1",
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=10, repo_root=tmp_path)
        assert result.passed is False
        assert result.exit_code == 1

    def test_timeout_scenario_returns_timeout_error(
        self, tmp_path: Path
    ) -> None:
        scenario = Scenario(
            name="Slow",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method="sleep 30",
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=1, repo_root=tmp_path)
        assert result.passed is False
        assert result.exit_code == -1
        assert "TIMEOUT" in result.stderr

    def test_captures_stdout(self, tmp_path: Path) -> None:
        scenario = Scenario(
            name="Output",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method='echo "hello factory"',
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=10, repo_root=tmp_path)
        assert "hello factory" in result.stdout

    def test_captures_stderr(self, tmp_path: Path) -> None:
        scenario = Scenario(
            name="Stderr",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method='echo "err msg" >&2; exit 1',
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=10, repo_root=tmp_path)
        assert "err msg" in result.stderr

    def test_error_summary_extracts_error_lines(
        self, tmp_path: Path
    ) -> None:
        scenario = Scenario(
            name="ErrorExtract",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method=(
                'echo "line 1" >&2; '
                'echo "AssertionError: bad value" >&2; '
                "exit 1"
            ),
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=10, repo_root=tmp_path)
        assert "AssertionError" in result.error_summary

    def test_duration_is_positive(self, tmp_path: Path) -> None:
        scenario = Scenario(
            name="Duration",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method="sleep 0.1",
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=10, repo_root=tmp_path)
        assert result.duration_seconds > 0

    def test_result_is_scenarioresult_dataclass(
        self, tmp_path: Path
    ) -> None:
        scenario = Scenario(
            name="Type",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method="exit 0",
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=10, repo_root=tmp_path)
        assert isinstance(result, ScenarioResult)

    def test_cwd_is_repo_root(self, tmp_path: Path) -> None:
        """The scenario runs in the repo root, not some temp dir."""
        scenario = Scenario(
            name="CWD",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method="pwd",
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=10, repo_root=tmp_path)
        # pwd output should match the repo root we passed in
        assert str(tmp_path) in result.stdout

    def test_pythonpath_is_set(self, tmp_path: Path) -> None:
        """PYTHONPATH should include repo root for imports."""
        scenario = Scenario(
            name="PythonPath",
            file_path="test.md",
            category="test",
            preconditions=[],
            behavioral_expectation="",
            evaluation_method="echo $PYTHONPATH",
            pass_criteria="",
            evidence_required=[],
        )
        result = run_scenario(scenario, timeout=10, repo_root=tmp_path)
        assert str(tmp_path) in result.stdout


# ── Dataclass tests ──────────────────────────────────────────


class TestDataclasses:
    """Verify that dataclasses serialize correctly for JSON output."""

    def test_scenario_report_serializes_to_json(self) -> None:
        from dataclasses import asdict

        report = ScenarioReport(
            timestamp="2026-02-22T00:00:00Z",
            total=2,
            passed=1,
            failed=1,
            skipped=0,
            satisfaction_score=0.5,
            results=[],
        )
        data = asdict(report)
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        assert parsed["satisfaction_score"] == 0.5
        assert parsed["total"] == 2

    def test_scenario_result_serializes_to_json(self) -> None:
        from dataclasses import asdict

        result = ScenarioResult(
            name="Test",
            file_path="test.md",
            category="test",
            passed=True,
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_seconds=1.5,
        )
        data = asdict(result)
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        assert parsed["passed"] is True
        assert parsed["duration_seconds"] == 1.5
