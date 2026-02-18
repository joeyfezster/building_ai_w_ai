import numpy as np

from src.rl.replay import ReplayBuffer, Transition


def test_replay_add_and_sample() -> None:
    rb = ReplayBuffer(capacity=8, obs_shape=(84, 84, 4))
    obs = np.zeros((84, 84, 4), dtype=np.uint8)
    for i in range(6):
        rb.add(
            Transition(obs=obs + i, action=i % 3, reward=float(i), next_obs=obs + i + 1, done=False)
        )
    assert rb.size == 6
    batch = rb.sample(4, np.random.default_rng(0))
    assert batch[0].shape[0] == 4
