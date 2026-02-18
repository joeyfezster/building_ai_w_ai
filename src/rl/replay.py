from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class Transition:
    obs: list[list[list[int]]]
    action: int
    reward: float
    next_obs: list[list[list[int]]]
    done: bool


class ReplayBuffer:
    def __init__(self, capacity: int, obs_shape: tuple[int, ...]) -> None:
        self.capacity = capacity
        self.storage: list[Transition] = []
        self.ptr = 0

    @property
    def size(self) -> int:
        return len(self.storage)

    def add(self, transition: Transition) -> None:
        if len(self.storage) < self.capacity:
            self.storage.append(transition)
        else:
            self.storage[self.ptr] = transition
        self.ptr = (self.ptr + 1) % self.capacity

    def sample(self, batch_size: int, rng: Random) -> tuple[list, list, list, list, list]:
        picks = [self.storage[rng.randrange(len(self.storage))] for _ in range(batch_size)]
        return (
            [p.obs for p in picks],
            [p.action for p in picks],
            [p.reward for p in picks],
            [p.next_obs for p in picks],
            [1.0 if p.done else 0.0 for p in picks],
        )
