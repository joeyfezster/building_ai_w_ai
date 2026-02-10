"""Replay buffer implementation."""

from __future__ import annotations

from dataclasses import dataclass
import random
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
        self._position = 0

    def add(self, transition: Transition) -> None:
        """Add a transition to the buffer."""

        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if len(self._storage) < self.capacity:
            self._storage.append(transition)
        else:
            self._storage[self._position] = transition
        self._position = (self._position + 1) % self.capacity

    def sample(self, batch_size: int) -> Iterable[Transition]:
        """Sample a batch of transitions."""

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if batch_size > len(self._storage):
            raise ValueError("batch_size exceeds buffer size")
        return random.sample(self._storage, batch_size)

    def __len__(self) -> int:
        return len(self._storage)
