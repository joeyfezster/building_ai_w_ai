from __future__ import annotations

from random import Random


def select_action(q_values: list[float], epsilon: float, rng: Random, n_actions: int) -> int:
    if rng.random() < epsilon:
        return rng.randrange(n_actions)
    best = 0
    best_v = q_values[0]
    for i, v in enumerate(q_values):
        if v > best_v:
            best = i
            best_v = v
    return best


def td_loss(*args, **kwargs) -> float:
    return 0.0
