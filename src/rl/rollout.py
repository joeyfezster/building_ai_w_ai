"""Rollout buffer for on-policy algorithms (PPO)."""

from __future__ import annotations

import numpy as np
import torch


class RolloutBuffer:
    """Fixed-size buffer that collects n_steps of experience, then computes GAE."""

    def __init__(self, n_steps: int, obs_shape: tuple[int, ...], device: torch.device) -> None:
        self.n_steps = n_steps
        self.device = device
        self.pos = 0

        self.obs = np.zeros((n_steps, *obs_shape), dtype=np.uint8)
        self.actions = np.zeros(n_steps, dtype=np.int64)
        self.rewards = np.zeros(n_steps, dtype=np.float32)
        self.dones = np.zeros(n_steps, dtype=np.float32)
        self.values = np.zeros(n_steps, dtype=np.float32)
        self.log_probs = np.zeros(n_steps, dtype=np.float32)

        self.advantages: np.ndarray | None = None
        self.returns: np.ndarray | None = None

    def add(
        self,
        obs: np.ndarray,
        action: int,
        reward: float,
        done: bool,
        value: float,
        log_prob: float,
    ) -> None:
        self.obs[self.pos] = obs
        self.actions[self.pos] = action
        self.rewards[self.pos] = reward
        self.dones[self.pos] = float(done)
        self.values[self.pos] = value
        self.log_probs[self.pos] = log_prob
        self.pos += 1

    def compute_advantages(
        self,
        last_value: float,
        last_done: bool,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
    ) -> None:
        """Compute GAE-Lambda advantages (Schulman 2016)."""
        advantages = np.zeros(self.n_steps, dtype=np.float32)
        last_gae = 0.0
        for t in reversed(range(self.n_steps)):
            if t == self.n_steps - 1:
                next_non_terminal = 1.0 - float(last_done)
                next_value = last_value
            else:
                next_non_terminal = 1.0 - self.dones[t + 1]
                next_value = self.values[t + 1]
            delta = self.rewards[t] + gamma * next_value * next_non_terminal - self.values[t]
            last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae
            advantages[t] = last_gae
        self.advantages = advantages
        self.returns = advantages + self.values

    def get_minibatches(
        self, n_minibatches: int
    ) -> list[dict[str, torch.Tensor]]:
        """Shuffle and split into minibatches with per-batch advantage normalization."""
        assert self.advantages is not None and self.returns is not None, (
            "Call compute_advantages first"
        )
        indices = np.random.permutation(self.n_steps)
        batch_size = self.n_steps // n_minibatches
        batches = []
        for start in range(0, self.n_steps, batch_size):
            idx = indices[start : start + batch_size]
            adv = torch.tensor(self.advantages[idx], dtype=torch.float32, device=self.device)
            if len(adv) > 1:
                adv = (adv - adv.mean()) / (adv.std() + 1e-8)
            batches.append(
                {
                    "obs": torch.tensor(self.obs[idx], dtype=torch.float32, device=self.device),
                    "actions": torch.tensor(
                        self.actions[idx], dtype=torch.int64, device=self.device
                    ),
                    "log_probs": torch.tensor(
                        self.log_probs[idx], dtype=torch.float32, device=self.device
                    ),
                    "advantages": adv,
                    "returns": torch.tensor(
                        self.returns[idx], dtype=torch.float32, device=self.device
                    ),
                }
            )
        return batches

    def reset(self) -> None:
        self.pos = 0
        self.advantages = None
        self.returns = None
