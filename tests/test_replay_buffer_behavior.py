from __future__ import annotations

import numpy as np

from src.rl.replay import ReplayBuffer, Transition


def test_replay_capacity_and_sample() -> None:
    rb = ReplayBuffer(capacity=3)
    obs = np.zeros((2, 2, 1), dtype=np.uint8)
    for i in range(5):
        rb.add(Transition(obs=obs + i, action=0, reward=0.0, next_obs=obs + i, done=False))
    assert len(rb) == 3
    sample = rb.sample(2)
    assert len(sample) == 2
