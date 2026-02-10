from __future__ import annotations


def test_imports() -> None:
    import src.agents as agents
    import src.configs as configs
    import src.envs as envs
    import src.obs as obs
    import src.rl as rl
    import src.train as train
    import src.utils as utils

    _ = (agents, configs, envs, obs, rl, train, utils)
