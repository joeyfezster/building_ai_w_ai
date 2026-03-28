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


def _layer_init(
    layer: nn.Conv2d | nn.Linear, std: float, bias_const: float = 0.0
) -> nn.Conv2d | nn.Linear:
    """Orthogonal weight initialization (PPO standard)."""
    nn.init.orthogonal_(layer.weight, std)
    assert layer.bias is not None
    nn.init.constant_(layer.bias, bias_const)
    return layer


class ActorCriticNetwork(nn.Module):
    """Nature-CNN backbone with separate actor/critic heads for PPO."""

    def __init__(self, obs_shape: Sequence[int], num_actions: int) -> None:
        super().__init__()
        c = obs_shape[2]
        gain = 2**0.5
        self.features = nn.Sequential(
            _layer_init(nn.Conv2d(c, 32, kernel_size=8, stride=4), gain),
            nn.ReLU(),
            _layer_init(nn.Conv2d(32, 64, kernel_size=4, stride=2), gain),
            nn.ReLU(),
            _layer_init(nn.Conv2d(64, 64, kernel_size=3, stride=1), gain),
            nn.ReLU(),
            nn.Flatten(),
        )
        with torch.no_grad():
            dummy = torch.zeros(1, c, obs_shape[0], obs_shape[1])
            n_flat = self.features(dummy).shape[1]
        self.actor = nn.Sequential(
            _layer_init(nn.Linear(n_flat, 512), gain),
            nn.ReLU(),
            _layer_init(nn.Linear(512, num_actions), 0.01),
        )
        self.critic = nn.Sequential(
            _layer_init(nn.Linear(n_flat, 512), gain),
            nn.ReLU(),
            _layer_init(nn.Linear(512, 1), 1.0),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = x / 255.0
        x = x.permute(0, 3, 1, 2)
        features = self.features(x)
        logits = self.actor(features)
        value = self.critic(features).squeeze(-1)
        return logits, value


def create_actor_critic(obs_shape: Sequence[int], num_actions: int) -> ActorCriticNetwork:
    return ActorCriticNetwork(obs_shape, num_actions)
