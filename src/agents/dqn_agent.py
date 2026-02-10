"""Minimal DQN agent implementation."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch import nn

from src.rl.losses import dqn_loss
from src.rl.networks import create_q_network
from src.rl.replay import ReplayBuffer, Transition


@dataclass
class DQNHyperparams:
    """Hyperparameters for DQN."""

    gamma: float
    batch_size: int
    buffer_capacity: int
    learning_rate: float
    target_update_interval: int
    train_interval: int
    max_grad_norm: float


class DQNAgent:
    """Minimal DQN agent implementation."""

    def __init__(
        self,
        obs_shape: Sequence[int],
        num_actions: int,
        hyperparams: DQNHyperparams,
        device: torch.device,
    ) -> None:
        self.num_actions = num_actions
        self.device = device
        self.hyperparams = hyperparams
        self.q_network = create_q_network(obs_shape, num_actions).to(self.device)
        self.target_network = create_q_network(obs_shape, num_actions).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.optimizer = torch.optim.Adam(
            self.q_network.parameters(),
            lr=self.hyperparams.learning_rate,
        )
        self.replay = ReplayBuffer(self.hyperparams.buffer_capacity)
        self.epsilon = 0.0
        self._learn_step = 0

    def act(self, observation: Any, explore: bool) -> int:
        """Select an action given an observation."""

        if explore and random.random() < self.epsilon:
            return random.randrange(self.num_actions)
        obs_tensor = self._obs_to_tensor(observation)
        with torch.no_grad():
            q_values = self.q_network(obs_tensor).squeeze(0)
        return int(torch.argmax(q_values).item())

    def observe(self, transition: Any) -> None:
        """Record a transition for learning."""

        if not isinstance(transition, Transition):
            raise TypeError("transition must be a Transition")
        self.replay.add(transition)

    def learn(self) -> Mapping[str, float]:
        """Run a learning update step."""

        self._learn_step += 1
        if self._learn_step % self.hyperparams.train_interval != 0:
            return {}
        if len(self.replay) < self.hyperparams.batch_size:
            return {}
        transitions = list(self.replay.sample(self.hyperparams.batch_size))
        obs_batch = np.stack([t.obs for t in transitions], axis=0)
        next_obs_batch = np.stack([t.next_obs for t in transitions], axis=0)
        actions = torch.tensor([t.action for t in transitions], device=self.device)
        rewards = torch.tensor([t.reward for t in transitions], device=self.device)
        dones = torch.tensor([t.done for t in transitions], device=self.device)
        obs_tensor = self._batch_to_tensor(obs_batch)
        next_obs_tensor = self._batch_to_tensor(next_obs_batch)
        q_values = self.q_network(obs_tensor).gather(
            1,
            actions.view(-1, 1),
        ).squeeze(1)
        with torch.no_grad():
            next_q_values = self.target_network(next_obs_tensor).max(1).values
            targets = rewards + (1.0 - dones.float()) * (
                self.hyperparams.gamma * next_q_values
            )
        loss = dqn_loss(q_values, targets)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(
            self.q_network.parameters(),
            max_norm=self.hyperparams.max_grad_norm,
        )
        self.optimizer.step()
        if self._learn_step % self.hyperparams.target_update_interval == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())
        return {"loss": float(loss.item())}

    def save(self, path: str) -> None:
        """Save model weights to disk."""

        payload = {
            "q_network": self.q_network.state_dict(),
            "target_network": self.target_network.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "learn_step": self._learn_step,
        }
        torch.save(payload, path)

    def load(self, path: str) -> None:
        """Load model weights from disk."""

        payload = torch.load(path, map_location=self.device)
        self.q_network.load_state_dict(payload["q_network"])
        self.target_network.load_state_dict(payload["target_network"])
        self.optimizer.load_state_dict(payload["optimizer"])
        self._learn_step = int(payload.get("learn_step", 0))

    def _obs_to_tensor(self, observation: Any) -> torch.Tensor:
        obs_array = np.asarray(observation, dtype=np.float32)
        if obs_array.ndim == 3:
            obs_array = np.expand_dims(obs_array, axis=0)
        return torch.tensor(obs_array, device=self.device)

    def _batch_to_tensor(self, batch: np.ndarray) -> torch.Tensor:
        return torch.tensor(batch, dtype=torch.float32, device=self.device)
