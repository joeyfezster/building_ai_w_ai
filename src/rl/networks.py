"""Q-network definitions."""

from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import nn


class ConvQNetwork(nn.Module):
    def __init__(self, obs_shape: Sequence[int], num_actions: int) -> None:
        super().__init__()
        c = obs_shape[2]
        self.features = nn.Sequential(
            nn.Conv2d(c, 16, kernel_size=8, stride=4),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=4, stride=2),
            nn.ReLU(),
            nn.Flatten(),
        )
        with torch.no_grad():
            dummy = torch.zeros(1, c, obs_shape[0], obs_shape[1])
            n_flat = self.features(dummy).shape[1]
        self.head = nn.Sequential(nn.Linear(n_flat, 128), nn.ReLU(), nn.Linear(128, num_actions))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x / 255.0
        x = x.permute(0, 3, 1, 2)
        return self.head(self.features(x))


def create_q_network(obs_shape: Sequence[int], num_actions: int) -> nn.Module:
    return ConvQNetwork(obs_shape, num_actions)
