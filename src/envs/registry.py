"""Environment registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.envs.minipong import MiniPongConfig, MiniPongEnv

EnvFactory = Callable[..., Any]


@dataclass
class EnvRegistry:
    factories: dict[str, EnvFactory] = field(default_factory=dict)

    def register(self, name: str, factory: EnvFactory) -> None:
        self.factories[name] = factory

    def create(self, name: str, **kwargs: Any) -> Any:
        if name not in self.factories:
            raise KeyError(f"Unknown environment: {name}")
        return self.factories[name](**kwargs)


def default_registry() -> EnvRegistry:
    reg = EnvRegistry()
    reg.register("MiniPong-v0", lambda **kwargs: MiniPongEnv(config=MiniPongConfig(), **kwargs))
    return reg
