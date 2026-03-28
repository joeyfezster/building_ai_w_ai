"""Smoke tests for PPO agent components."""

from __future__ import annotations

import numpy as np
import torch

from src.agents.ppo_agent import PPOAgent, PPOConfig
from src.rl.networks import ActorCriticNetwork, create_actor_critic
from src.rl.rollout import RolloutBuffer


class TestActorCriticNetwork:
    def test_forward_shape(self) -> None:
        obs_shape = (84, 84, 4)
        net = ActorCriticNetwork(obs_shape, num_actions=3)
        x = torch.zeros(2, 84, 84, 4, dtype=torch.float32)
        logits, values = net(x)
        assert logits.shape == (2, 3)
        assert values.shape == (2,)

    def test_factory(self) -> None:
        net = create_actor_critic((84, 84, 4), 3)
        assert isinstance(net, ActorCriticNetwork)


class TestPPOAgent:
    def _make_agent(self) -> PPOAgent:
        return PPOAgent(
            obs_shape=(84, 84, 4),
            num_actions=3,
            config=PPOConfig(),
            device=torch.device("cpu"),
        )

    def test_act_returns_tuple(self) -> None:
        agent = self._make_agent()
        obs = np.zeros((84, 84, 4), dtype=np.uint8)
        action, log_prob, value = agent.act(obs)
        assert 0 <= action < 3
        assert isinstance(log_prob, float)
        assert isinstance(value, float)

    def test_act_deterministic(self) -> None:
        agent = self._make_agent()
        obs = np.zeros((84, 84, 4), dtype=np.uint8)
        a1 = agent.act_deterministic(obs)
        a2 = agent.act_deterministic(obs)
        assert a1 == a2  # deterministic = same result
        assert 0 <= a1 < 3

    def test_get_value(self) -> None:
        agent = self._make_agent()
        obs = np.zeros((84, 84, 4), dtype=np.uint8)
        v = agent.get_value(obs)
        assert isinstance(v, float)

    def test_update(self) -> None:
        agent = self._make_agent()
        # Create a fake minibatch
        batch = {
            "obs": torch.zeros(32, 84, 84, 4, dtype=torch.float32),
            "actions": torch.randint(0, 3, (32,)),
            "log_probs": torch.zeros(32),
            "advantages": torch.randn(32),
            "returns": torch.randn(32),
        }
        losses = agent.update([batch], global_step=100)
        assert "pg_loss" in losses
        assert "vf_loss" in losses
        assert "entropy" in losses
        assert "clipfrac" in losses


class TestRolloutBuffer:
    def test_add_and_compute(self) -> None:
        buf = RolloutBuffer(n_steps=8, obs_shape=(84, 84, 4), device=torch.device("cpu"))
        for i in range(8):
            buf.add(
                obs=np.zeros((84, 84, 4), dtype=np.uint8),
                action=i % 3,
                reward=0.1,
                done=False,
                value=0.5,
                log_prob=-0.3,
            )
        buf.compute_advantages(last_value=0.5, last_done=False)
        assert buf.advantages is not None
        assert buf.returns is not None
        assert len(buf.advantages) == 8

    def test_minibatches(self) -> None:
        buf = RolloutBuffer(n_steps=16, obs_shape=(84, 84, 4), device=torch.device("cpu"))
        for i in range(16):
            buf.add(
                obs=np.zeros((84, 84, 4), dtype=np.uint8),
                action=i % 3,
                reward=0.1,
                done=False,
                value=0.5,
                log_prob=-0.3,
            )
        buf.compute_advantages(last_value=0.5, last_done=False)
        batches = buf.get_minibatches(n_minibatches=4)
        assert len(batches) == 4
        assert batches[0]["obs"].shape[0] == 4

    def test_reset(self) -> None:
        buf = RolloutBuffer(n_steps=4, obs_shape=(84, 84, 4), device=torch.device("cpu"))
        for _ in range(4):
            buf.add(
                obs=np.zeros((84, 84, 4), dtype=np.uint8),
                action=0,
                reward=0.0,
                done=False,
                value=0.0,
                log_prob=0.0,
            )
        buf.compute_advantages(last_value=0.0, last_done=False)
        buf.reset()
        assert buf.pos == 0
        assert buf.advantages is None
