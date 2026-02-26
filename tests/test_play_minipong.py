from __future__ import annotations

import numpy as np

from src.envs.minipong import MiniPongConfig, MiniPongEnv
from src.play.play_minipong import GameController, get_action_from_keys, prepare_agent_obs


def test_get_action_from_keys() -> None:
    assert get_action_from_keys("left", {"q"}) == 0
    assert get_action_from_keys("left", {"a"}) == 1
    assert get_action_from_keys("left", set()) == 2
    assert get_action_from_keys("right", {"p"}) == 0
    assert get_action_from_keys("right", {"l"}) == 1


def test_prepare_agent_obs_flips_right_side() -> None:
    obs = np.arange(12, dtype=np.uint8).reshape(2, 6, 1)
    right = prepare_agent_obs(obs, "right")
    left = prepare_agent_obs(obs, "left")

    assert np.array_equal(left, obs)
    assert np.array_equal(right[:, :, 0], np.fliplr(obs[:, :, 0]))


def test_game_controller_status_and_restart() -> None:
    controller = GameController()
    assert controller.get_controller("left") == "human"
    assert (
        controller.get_status_tag("left", debug=False, policy_name="random")
        == "Keyboard: Up:Q, Down:A"
    )

    controller.toggle_agent("left")
    assert controller.get_controller("left") == "agent"
    assert controller.get_status_tag("left", debug=False, policy_name="random") == "AI Agent"
    assert (
        controller.get_status_tag("left", debug=True, policy_name="checkpoint.pt")
        == "Policy: checkpoint.pt"
    )

    env = MiniPongEnv(config=MiniPongConfig(score_limit=3))
    env.reset(seed=1)
    env.agent_score = 2

    _, info = controller.restart(env, seed=2)
    assert info["agent_score"] == 0
    assert controller.get_controller("left") == "agent"
