"""Tests for _utils.py shared utilities."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _utils import (
    _get_repo_slug,
    format_time,
    health_tag,
    match_file_to_zones,
    parse_ci_time,
    run_gh,
)


class TestImports:
    """Verify all exported functions are importable."""

    def test_all_functions_importable(self) -> None:
        assert callable(_get_repo_slug)
        assert callable(run_gh)
        assert callable(match_file_to_zones)
        assert callable(health_tag)
        assert callable(format_time)
        assert callable(parse_ci_time)


class TestHealthTag:
    def test_normal(self) -> None:
        assert health_tag(30) == "normal"

    def test_acceptable(self) -> None:
        assert health_tag(120) == "acceptable"

    def test_watch(self) -> None:
        assert health_tag(400) == "watch"

    def test_refactor(self) -> None:
        assert health_tag(700) == "refactor"

    def test_boundary_60(self) -> None:
        assert health_tag(60) == "acceptable"

    def test_boundary_300(self) -> None:
        assert health_tag(300) == "watch"

    def test_boundary_600(self) -> None:
        assert health_tag(600) == "refactor"


class TestFormatTime:
    def test_seconds_only(self) -> None:
        assert format_time(45) == "45s"

    def test_minutes_and_seconds(self) -> None:
        assert format_time(125) == "2m 5s"

    def test_zero(self) -> None:
        assert format_time(0) == "0s"


class TestParseCiTime:
    def test_valid_timestamps(self) -> None:
        result = parse_ci_time("2026-01-01T00:00:00Z", "2026-01-01T00:05:30Z")
        assert result == 330.0

    def test_invalid_timestamps(self) -> None:
        assert parse_ci_time("bad", "data") == 0

    def test_empty_strings(self) -> None:
        assert parse_ci_time("", "") == 0


class TestMatchFileToZones:
    def test_single_match(self) -> None:
        zones = {
            "infra": {"paths": [".github/**"]},
            "src": {"paths": ["src/**"]},
        }
        assert match_file_to_zones(".github/workflows/ci.yaml", zones) == ["infra"]

    def test_no_match(self) -> None:
        zones = {"infra": {"paths": [".github/**"]}}
        assert match_file_to_zones("README.md", zones) == []

    def test_multiple_zones(self) -> None:
        zones = {
            "zone-a": {"paths": ["packages/**"]},
            "zone-b": {"paths": ["packages/foo/**"]},
        }
        result = match_file_to_zones("packages/foo/bar.py", zones)
        assert "zone-a" in result
        assert "zone-b" in result


class TestGetRepoSlug:
    def test_override(self) -> None:
        assert _get_repo_slug("owner/repo") == "owner/repo"
