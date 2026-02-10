# LinkedIn Post (Long)

Milestone 2 is live: a classic DQN agent learning Pong directly from pixels.

What shipped:
- A runnable random-policy rollout that records MP4s.
- A minimal DQN smoke training loop with TensorBoard metrics.
- Deterministic evaluation that writes metrics + videos to a consistent output structure.

Why it matters:
This establishes a walking skeleton for our retro-RL milestones. We can now iterate on stronger agents while keeping validation, demo packs, and reproducibility intact.

Next steps:
- Longer training runs
- Additional baselines (Double DQN, Dueling DQN)
- Expanded demos with side-by-side comparisons
