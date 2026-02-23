"""Replay buffer."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Transition:
    obs: np.ndarray
    action: int
    reward: float
    next_obs: np.ndarray
    done: bool


class ReplayBuffer:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._storage: list[Transition] = []
        self._index = 0

    def __len__(self) -> int:
        return len(self._storage)

    def add(self, transition: Transition) -> None:
        if len(self._storage) < self.capacity:
            self._storage.append(transition)
        else:
            self._storage[self._index] = transition
        self._index = (self._index + 1) % self.capacity

    def sample(self, batch_size: int) -> list[Transition]:
        idx = np.random.randint(0, len(self._storage), size=batch_size)
        return [self._storage[i] for i in idx]
