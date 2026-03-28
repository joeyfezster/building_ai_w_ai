"""Smoke tests for PPO self-play training loop."""

from __future__ import annotations

import torch

from src.train.train_ppo_selfplay import PPOSelfPlayOpponent, train_ppo_selfplay


class TestPPOSelfPlayOpponent:
    def test_act_returns_valid_action(self) -> None:
        import numpy as np

        obs_shape = (84, 84, 4)
        opp = PPOSelfPlayOpponent(obs_shape, 3, frame_stack=4, device=torch.device("cpu"))
        raw_obs = np.zeros((84, 84, 1), dtype=np.uint8)
        opp.reset(raw_obs)
        action = opp.act()
        assert 0 <= action < 3

    def test_load_weights(self) -> None:
        import numpy as np

        from src.rl.networks import create_actor_critic

        obs_shape = (84, 84, 4)
        net = create_actor_critic(obs_shape, 3)
        opp = PPOSelfPlayOpponent(obs_shape, 3, frame_stack=4, device=torch.device("cpu"))
        opp.load_weights(net.state_dict())
        raw_obs = np.zeros((84, 84, 1), dtype=np.uint8)
        opp.reset(raw_obs)
        action = opp.act()
        assert 0 <= action < 3


class TestTrainPPOSelfplay:
    def test_short_run(self) -> None:
        """Run 256 steps of PPO self-play to verify the loop works."""
        config = {
            "run_id": "ppo_smoke_test",
            "seed": 42,
            "frame_stack": 4,
            "total_steps": 256,
            "max_episode_steps": 200,
            "n_steps": 128,
            "n_minibatches": 2,
            "n_epochs": 2,
            "lr": 2.5e-4,
            "lr_anneal": False,
            "clip_epsilon": 0.1,
            "entropy_coef": 0.02,
            "vf_coef": 0.5,
            "max_grad_norm": 0.5,
            "gamma": 0.99,
            "gae_lambda": 0.95,
            "reward_shaping": True,
            "hit_reward": 0.1,
            "rally_bonus_per_step": 0.02,
            "opponent_update_period": 128,
            "checkpoint_pool_size": 3,
            "eval_every_steps": 256,
            "eval_episodes": 2,
            "eval_seeds": [11],
            "log_every_steps": 128,
        }
        run_id = train_ppo_selfplay(config, device=torch.device("cpu"))
        assert run_id == "ppo_smoke_test"
