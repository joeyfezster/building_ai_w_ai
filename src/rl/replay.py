"""Replay buffer stubs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List


@dataclass(frozen=True)
class Transition:
    """Single transition in the replay buffer."""

    obs: Any
    action: int
    reward: float
    next_obs: Any
    done: bool


class ReplayBuffer:
    """Placeholder replay buffer."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._storage: List[Transition] = []

    def add(self, transition: Transition) -> None:
        """Add a transition to the buffer."""

        raise NotImplementedError("Replay buffer add not implemented yet.")

    def sample(self, batch_size: int) -> Iterable[Transition]:
        """Sample a batch of transitions."""

        raise NotImplementedError("Replay buffer sampling not implemented yet.")
