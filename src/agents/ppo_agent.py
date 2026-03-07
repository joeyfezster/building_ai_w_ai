"""PPO agent implementation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import optim
from torch.distributions import Categorical

from src.rl.networks import ActorCriticNetwork, create_actor_critic


@dataclass
class PPOConfig:
    clip_epsilon: float = 0.1
    entropy_coef: float = 0.02
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    n_epochs: int = 4
    n_minibatches: int = 4
    adam_epsilon: float = 1e-5
    lr: float = 2.5e-4
    lr_anneal_total_steps: int = 0


class PPOAgent:
    def __init__(
        self,
        obs_shape: tuple[int, ...],
        num_actions: int,
        config: PPOConfig,
        device: torch.device | None = None,
    ) -> None:
        self.config = config
        self.num_actions = num_actions
        if device is not None:
            self.device = device
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.network: ActorCriticNetwork = create_actor_critic(obs_shape, num_actions).to(
            self.device
        )
        self.optimizer = optim.Adam(
            self.network.parameters(), lr=config.lr, eps=config.adam_epsilon
        )

    def act(self, obs: np.ndarray) -> tuple[int, float, float]:
        """Sample action from policy. Returns (action, log_prob, value)."""
        with torch.no_grad():
            obs_t = torch.tensor(obs[None], dtype=torch.float32, device=self.device)
            logits, value = self.network(obs_t)
            dist = Categorical(logits=logits)
            action = dist.sample()
            log_prob = dist.log_prob(action)
        return int(action.item()), float(log_prob.item()), float(value.item())

    def act_deterministic(self, obs: np.ndarray) -> int:
        """Greedy action (argmax logits) for evaluation."""
        with torch.no_grad():
            obs_t = torch.tensor(obs[None], dtype=torch.float32, device=self.device)
            logits, _ = self.network(obs_t)
            return int(torch.argmax(logits, dim=1).item())

    def get_value(self, obs: np.ndarray) -> float:
        """Get critic value for bootstrapping."""
        with torch.no_grad():
            obs_t = torch.tensor(obs[None], dtype=torch.float32, device=self.device)
            _, value = self.network(obs_t)
            return float(value.item())

    def update(
        self, minibatches: list[dict[str, torch.Tensor]], global_step: int
    ) -> dict[str, float]:
        """Run PPO update on minibatches. Returns loss dict."""
        # LR annealing
        if self.config.lr_anneal_total_steps > 0:
            frac = 1.0 - global_step / self.config.lr_anneal_total_steps
            frac = max(frac, 0.0)
            lr = self.config.lr * frac
            for pg in self.optimizer.param_groups:
                pg["lr"] = lr

        total_pg_loss = 0.0
        total_vf_loss = 0.0
        total_entropy = 0.0
        total_clipfrac = 0.0
        n_updates = 0

        for batch in minibatches:
            logits, values = self.network(batch["obs"])
            dist = Categorical(logits=logits)
            new_log_probs = dist.log_prob(batch["actions"])
            entropy = dist.entropy().mean()

            # Clipped surrogate objective
            ratio = torch.exp(new_log_probs - batch["log_probs"])
            pg_loss1 = -batch["advantages"] * ratio
            pg_loss2 = -batch["advantages"] * torch.clamp(
                ratio, 1.0 - self.config.clip_epsilon, 1.0 + self.config.clip_epsilon
            )
            pg_loss = torch.max(pg_loss1, pg_loss2).mean()

            # Value loss
            vf_loss = 0.5 * ((values - batch["returns"]) ** 2).mean()

            # Combined loss
            loss = pg_loss + self.config.vf_coef * vf_loss - self.config.entropy_coef * entropy

            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.network.parameters(), self.config.max_grad_norm)
            self.optimizer.step()

            with torch.no_grad():
                clipfrac = ((ratio - 1.0).abs() > self.config.clip_epsilon).float().mean()

            total_pg_loss += pg_loss.item()
            total_vf_loss += vf_loss.item()
            total_entropy += entropy.item()
            total_clipfrac += clipfrac.item()
            n_updates += 1

        return {
            "pg_loss": total_pg_loss / n_updates,
            "vf_loss": total_vf_loss / n_updates,
            "entropy": total_entropy / n_updates,
            "clipfrac": total_clipfrac / n_updates,
        }
