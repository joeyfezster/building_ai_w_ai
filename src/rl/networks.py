from __future__ import annotations

import torch
from torch import nn


class QNetwork(nn.Module):
    def __init__(self, obs_shape: tuple[int, int, int], num_actions: int) -> None:
        super().__init__()
        c = obs_shape[2]
        self.net = nn.Sequential(
            nn.Conv2d(c, 16, kernel_size=8, stride=4),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=4, stride=2),
            nn.ReLU(),
            nn.Flatten(),
            nn.LazyLinear(256),
            nn.ReLU(),
            nn.Linear(256, num_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.float() / 255.0
        x = x.permute(0, 3, 1, 2)
        return self.net(x)
