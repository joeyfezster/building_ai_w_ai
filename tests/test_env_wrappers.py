from src.envs.registry import make_env


def test_frame_stack_shape() -> None:
    env = make_env(seed=0, frame_stack=4)
    obs, _ = env.reset(seed=0)
    assert len(obs) == 84
    assert len(obs[0]) == 84
    assert len(obs[0][0]) == 4
