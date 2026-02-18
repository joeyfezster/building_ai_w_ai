from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class Transition:
    obs: npt.NDArray[np.uint8]
    action: int
    reward: float
    next_obs: npt.NDArray[np.uint8]
    done: bool


class ReplayBuffer:
    def __init__(self, capacity: int, obs_shape: tuple[int, ...]) -> None:
        self.capacity = capacity
        self.obs = np.zeros((capacity, *obs_shape), dtype=np.uint8)
        self.next_obs = np.zeros((capacity, *obs_shape), dtype=np.uint8)
        self.actions = np.zeros((capacity,), dtype=np.int64)
        self.rewards = np.zeros((capacity,), dtype=np.float32)
        self.dones = np.zeros((capacity,), dtype=np.float32)
        self.size = 0
        self.ptr = 0

    def add(self, transition: Transition) -> None:
        idx = self.ptr
        self.obs[idx] = transition.obs
        self.actions[idx] = transition.action
        self.rewards[idx] = transition.reward
        self.next_obs[idx] = transition.next_obs
        self.dones[idx] = 1.0 if transition.done else 0.0

        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int, rng: np.random.Generator) -> tuple[np.ndarray, ...]:
        idxs = rng.integers(0, self.size, size=batch_size)
        return (
            self.obs[idxs],
            self.actions[idxs],
            self.rewards[idxs],
            self.next_obs[idxs],
            self.dones[idxs],
        )
