"""Seeding helpers."""

from __future__ import annotations

import random
from typing import Any

import numpy as np
import torch


def set_global_seeds(seed: int) -> None:
    """Seed Python, NumPy, and Torch RNGs."""

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def seed_env(env: Any, seed: int) -> None:
    """Seed a Gymnasium environment."""

    env.reset(seed=seed)
    if hasattr(env.action_space, "seed"):
        env.action_space.seed(seed)
