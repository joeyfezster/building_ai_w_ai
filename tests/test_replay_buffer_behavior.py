from random import Random

from src.rl.replay import ReplayBuffer, Transition


def test_replay_add_and_sample() -> None:
    rb = ReplayBuffer(capacity=8, obs_shape=(84, 84, 4))
    obs = [[[0, 0, 0, 0] for _ in range(84)] for _ in range(84)]
    for i in range(6):
        rb.add(Transition(obs=obs, action=i % 3, reward=float(i), next_obs=obs, done=False))
    assert rb.size == 6
    batch = rb.sample(4, Random(0))
    assert len(batch[0]) == 4
