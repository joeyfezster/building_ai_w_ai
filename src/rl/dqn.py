from __future__ import annotations

import random

import numpy as np
import torch


def select_action(
    q_values: torch.Tensor, epsilon: float, rng: random.Random, n_actions: int
) -> int:
    if rng.random() < epsilon:
        return rng.randrange(n_actions)
    return int(torch.argmax(q_values, dim=1).item())


def td_loss(
    q_net: torch.nn.Module,
    target_net: torch.nn.Module,
    batch: tuple[np.ndarray, ...],
    gamma: float,
    device: torch.device,
) -> torch.Tensor:
    obs, actions, rewards, next_obs, dones = batch
    obs_t = torch.tensor(obs, device=device)
    act_t = torch.tensor(actions, device=device, dtype=torch.long)
    rew_t = torch.tensor(rewards, device=device)
    next_obs_t = torch.tensor(next_obs, device=device)
    done_t = torch.tensor(dones, device=device)

    q = q_net(obs_t).gather(1, act_t.unsqueeze(1)).squeeze(1)
    with torch.no_grad():
        next_max = target_net(next_obs_t).max(dim=1).values
        target = rew_t + gamma * (1 - done_t) * next_max
    return torch.nn.functional.mse_loss(q, target)
