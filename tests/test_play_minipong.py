from __future__ import annotations

import numpy as np

from src.play.play_minipong import GameController, get_action_from_keys, prepare_agent_obs


def test_get_action_from_keys() -> None:
    assert get_action_from_keys("left", {"q"}) == 0
    assert get_action_from_keys("left", {"a"}) == 1
    assert get_action_from_keys("left", set()) == 2
    assert get_action_from_keys("right", {"p"}) == 0
    assert get_action_from_keys("right", {"l"}) == 1
    assert get_action_from_keys("right", set()) == 2


def test_prepare_agent_obs_flips_right_side() -> None:
    obs = np.arange(12, dtype=np.uint8).reshape(2, 6, 1)
    right = prepare_agent_obs(obs, "right")
    left = prepare_agent_obs(obs, "left")

    assert np.array_equal(left, obs)
    assert np.array_equal(right[:, :, 0], np.fliplr(obs[:, :, 0]))


def test_game_controller_status_and_restart() -> None:
    controller = GameController(debug=True, checkpoint_path="models/checkpoint.pt")
    assert controller.get_controller("left") == "human"
    assert controller.get_status_tag("left") == "Keyboard: Up:Q, Down:A"

    controller.toggle_agent("left")
    assert controller.get_controller("left") == "agent"
    assert controller.get_status_tag("left") == "Policy: checkpoint.pt"

    nodebug = GameController(left_agent_enabled=True)
    assert nodebug.get_status_tag("left") == "AI Agent"


def test_game_controller_restart_preserves_toggles() -> None:
    controller = GameController(left_agent_enabled=True, right_agent_enabled=False)
    controller.restart()
    assert controller.get_controller("left") == "agent"
    assert controller.get_controller("right") == "human"


def test_game_controller_debug_random_policy_name() -> None:
    controller = GameController(left_agent_enabled=True, debug=True)
    assert controller.get_status_tag("left") == "Policy: random"
