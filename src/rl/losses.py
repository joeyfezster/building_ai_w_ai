"""Loss utilities."""

from __future__ import annotations

import torch
from torch import nn


def dqn_loss(predicted_q: torch.Tensor, target_q: torch.Tensor) -> torch.Tensor:
    """Compute the DQN loss."""

    return nn.functional.smooth_l1_loss(predicted_q, target_q)
