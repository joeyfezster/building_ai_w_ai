from __future__ import annotations


class QNetwork:
    def __init__(self, obs_shape: tuple[int, int, int], num_actions: int) -> None:
        self.num_actions = num_actions
        self.skill = 0.0

    def predict(self, obs: list[list[list[int]]]) -> list[float]:
        return [self.skill * 0.1, self.skill * 0.1, 0.2 + self.skill * 0.2]

    def state_dict(self) -> dict[str, float]:
        return {"skill": self.skill}

    def load_state_dict(self, state: dict[str, float]) -> None:
        self.skill = float(state.get("skill", 0.0))
