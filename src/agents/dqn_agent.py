"""DQN agent implementation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F
from torch import optim

from src.rl.networks import create_q_network
from src.rl.replay import ReplayBuffer, Transition


@dataclass
class DQNConfig:
    gamma: float = 0.99
    lr: float = 1e-3
    batch_size: int = 32
    flip_augment: bool = False


class DQNAgent:
    def __init__(
        self,
        obs_shape: tuple[int, int, int],
        num_actions: int,
        replay: ReplayBuffer,
        config: DQNConfig,
        device: torch.device | None = None,
    ) -> None:
        self.num_actions = num_actions
        self.replay = replay
        self.config = config
        if device is not None:
            self.device = device
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.online = create_q_network(obs_shape, num_actions).to(self.device)
        self.target = create_q_network(obs_shape, num_actions).to(self.device)
        self.target.load_state_dict(self.online.state_dict())
        self.optimizer = optim.Adam(self.online.parameters(), lr=config.lr)

    def act(self, observation: np.ndarray, epsilon: float) -> int:
        if np.random.rand() < epsilon:
            return int(np.random.randint(self.num_actions))
        with torch.no_grad():
            obs = torch.tensor(observation[None], dtype=torch.float32, device=self.device)
            q = self.online(obs)
            # Symmetric Q: average both orientations so Q(s) == Q(flip(s)) always.
            if self.config.flip_augment:
                q = (q + self.online(obs.flip(dims=[2]))) / 2
            return int(torch.argmax(q, dim=1).item())

    def observe(self, transition: Transition) -> None:
        self.replay.add(transition)

    def update(self) -> float:
        batch = self.replay.sample(self.config.batch_size)
        obs = torch.tensor(
            np.stack([t.obs for t in batch]), dtype=torch.float32, device=self.device
        )
        actions = torch.tensor([t.action for t in batch], dtype=torch.int64, device=self.device)
        rewards = torch.tensor([t.reward for t in batch], dtype=torch.float32, device=self.device)
        next_obs = torch.tensor(
            np.stack([t.next_obs for t in batch]), dtype=torch.float32, device=self.device
        )
        dones = torch.tensor([t.done for t in batch], dtype=torch.float32, device=self.device)

        # Symmetric Q-averaging: average Q-values from both orientations BEFORE
        # computing TD loss.  Q_sym(s) = (Q(s) + Q(flip(s))) / 2 is symmetric
        # by construction: Q_sym(s) == Q_sym(flip(s)) always.
        # Actions (up/down/stay) are vertical-only, unaffected by horizontal flip.
        if self.config.flip_augment:
            obs_flip = obs.flip(dims=[2])
            next_obs_flip = next_obs.flip(dims=[2])
            q_sym = (self.online(obs) + self.online(obs_flip)) / 2
            q = q_sym.gather(1, actions.unsqueeze(1)).squeeze(1)
            with torch.no_grad():
                q_next_sym = (self.target(next_obs) + self.target(next_obs_flip)) / 2
                q_next = q_next_sym.max(dim=1).values
                target = rewards + self.config.gamma * (1 - dones) * q_next
        else:
            q = self.online(obs).gather(1, actions.unsqueeze(1)).squeeze(1)
            with torch.no_grad():
                q_next = self.target(next_obs).max(dim=1).values
                target = rewards + self.config.gamma * (1 - dones) * q_next
        loss = F.mse_loss(q, target)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return float(loss.item())

    def sync_target(self) -> None:
        self.target.load_state_dict(self.online.state_dict())
