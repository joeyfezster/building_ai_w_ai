from __future__ import annotations

from src.envs.minipong import MiniPongEnv


def test_deterministic_reset_and_step() -> None:
    env1 = MiniPongEnv()
    env2 = MiniPongEnv()
    o1, _ = env1.reset(seed=42)
    o2, _ = env2.reset(seed=42)
    assert (o1 == o2).all()
    for a in [2, 0, 1, 2, 2]:
        n1, r1, t1, tr1, _ = env1.step(a)
        n2, r2, t2, tr2, _ = env2.step(a)
        assert (n1 == n2).all()
        assert r1 == r2
        assert t1 == t2
        assert tr1 == tr2
