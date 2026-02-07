"""DQN agent stub."""

from __future__ import annotations

from typing import Any


class DQNAgent:
    """Placeholder DQN agent implementation."""

    def __init__(self, num_actions: int) -> None:
        self.num_actions = num_actions

    def act(self, observation: Any) -> int:
        """Select an action given an observation."""

        raise NotImplementedError("Action selection not implemented yet.")

    def observe(self, transition: Any) -> None:
        """Record a transition for learning."""

        raise NotImplementedError("Observation handling not implemented yet.")

    def update(self) -> None:
        """Run a learning update step."""

        raise NotImplementedError("Update step not implemented yet.")
