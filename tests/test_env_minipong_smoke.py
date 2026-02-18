from src.envs.minipong import MiniPongEnv


def test_env_smoke() -> None:
    env = MiniPongEnv()
    obs, info = env.reset(seed=123)
    assert obs.shape == (84, 84, 1)
    assert obs.dtype.name == "uint8"
    assert "hits" in info
