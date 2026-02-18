from src.envs.minipong import MiniPongEnv


def test_env_smoke() -> None:
    env = MiniPongEnv()
    obs, info = env.reset(seed=123)
    assert len(obs) == 84
    assert len(obs[0]) == 84
    assert len(obs[0][0]) == 1
    assert "hits" in info
