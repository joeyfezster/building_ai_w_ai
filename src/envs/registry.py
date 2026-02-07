"""Environment registry stubs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict

EnvFactory = Callable[[], Any]


@dataclass
class EnvRegistry:
    """In-memory registry for environment factories."""

    factories: Dict[str, EnvFactory] = field(default_factory=dict)

    def register(self, name: str, factory: EnvFactory) -> None:
        """Register a factory by name."""

        self.factories[name] = factory

    def create(self, name: str) -> Any:
        """Create an environment instance from the registry."""

        if name not in self.factories:
            raise KeyError(f"Unknown environment: {name}")
        return self.factories[name]()


def register_env(registry: EnvRegistry, name: str, factory: EnvFactory) -> None:
    """Convenience helper to register an environment."""

    registry.register(name, factory)
