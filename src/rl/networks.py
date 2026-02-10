"""Network utilities for DQN."""

from __future__ import annotations

from typing import Sequence

import torch
from torch import nn


class AtariQNetwork(nn.Module):
    """Convolutional Q-network for Atari."""

    def __init__(self, obs_shape: Sequence[int], num_actions: int) -> None:
        super().__init__()
        channels, height, width = obs_shape
        self.features = nn.Sequential(
            nn.Conv2d(channels, 32, kernel_size=8, stride=4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ReLU(),
            nn.Flatten(),
        )
        with torch.no_grad():
            sample = torch.zeros(1, channels, height, width)
            feature_dim = int(self.features(sample).shape[1])
        self.head = nn.Sequential(
            nn.Linear(feature_dim, 512),
            nn.ReLU(),
            nn.Linear(512, num_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(x))


def create_q_network(obs_shape: Sequence[int], num_actions: int) -> nn.Module:
    """Create a Q-network for the given observation shape and action space."""

    if len(obs_shape) != 3:
        raise ValueError("obs_shape must be (channels, height, width)")
    return AtariQNetwork(obs_shape, num_actions)
