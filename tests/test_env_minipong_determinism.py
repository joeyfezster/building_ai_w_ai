from src.envs.minipong import MiniPongEnv


def test_deterministic_rollout_same_seed() -> None:
    env1 = MiniPongEnv()
    env2 = MiniPongEnv()
    obs1, _ = env1.reset(seed=7)
    obs2, _ = env2.reset(seed=7)
    assert (obs1 == obs2).all()

    actions = [0, 1, 2, 2, 0, 1, 1]
    for a in actions:
        o1, r1, t1, tr1, i1 = env1.step(a)
        o2, r2, t2, tr2, i2 = env2.step(a)
        assert (o1 == o2).all()
        assert r1 == r2
        assert t1 == t2
        assert tr1 == tr2
        assert i1["agent_score"] == i2["agent_score"]
