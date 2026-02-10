"""Configuration loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


class ConfigError(ValueError):
    """Configuration error."""


def load_config(path: Path) -> dict[str, Any]:
    """Load a YAML config file into a dictionary."""

    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    if not path.is_file():
        raise ConfigError(f"Config path is not a file: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in config: {path}") from exc
    if not isinstance(data, Mapping):
        raise ConfigError("Config must be a YAML mapping")
    return dict(data)


def require_keys(config: Mapping[str, Any], keys: set[str]) -> None:
    missing = keys - config.keys()
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ConfigError(f"Missing required config keys: {missing_list}")
