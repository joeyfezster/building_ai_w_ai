# From Pong to Go: A Deep Dive into Reinforcement Learning and Game-Playing AI

*An individualized course of study — from first principles to AlphaGo and beyond.*

---

## Course Map

This course builds in layers. Each module assumes you've internalized the previous ones. The MiniPong DQN agent we built is a running example — it illustrates the simplest instance of each concept before we scale to Go.

| Module | Topic | Key Question |
|--------|-------|-------------|
| 1 | Foundations: MDPs | What is the mathematical framework for sequential decision-making? |
| 2 | Value-Based RL: Q-Learning to DQN | How does an agent learn from trial and error, and why do we need neural nets? |
| 3 | Policy Gradients and Actor-Critic | What if we directly learn *what to do* instead of *how good things are*? |
| 4 | Game Trees and MCTS | How do you plan ahead in a game, and why does brute force fail for Go? |
| 5 | AlphaGo | How did DeepMind combine neural nets + search + RL to beat the world champion? |
| 6 | AlphaGo Zero and AlphaZero | What happens when you remove all human knowledge and let the system teach itself? |
| 7 | MuZero | What if the agent doesn't even know the rules of the game? |
| 8 | Hardware and Scale | What hardware makes this possible, and how does it constrain what we can learn? |
| 9 | The Mathematics | What are the theoretical guarantees, and where do they break down? |
| 10 | Software Engineering at Scale | How do you build the infrastructure for self-play at planetary scale? |

---

## Module 1: Foundations — Markov Decision Processes

### 1.1 The Problem

An agent interacts with an environment over time. At each timestep:
1. The agent observes a **state** *s*
2. The agent takes an **action** *a*
3. The environment transitions to a new state *s'* and emits a **reward** *r*
4. Repeat

The agent's goal: maximize the **cumulative discounted reward** over time.

**In MiniPong**: the state is 4 stacked 84x84 grayscale frames (giving motion information). The actions are {up, down, stay}. The reward is +1 (score a point), -1 (opponent scores), 0 (otherwise).

### 1.2 The Markov Property

A process is **Markov** if the future depends only on the present state, not on the history. Formally:

> P(s_{t+1} | s_t, a_t, s_{t-1}, a_{t-1}, ...) = P(s_{t+1} | s_t, a_t)

This is why we stack 4 frames in MiniPong — a single frame doesn't contain velocity information (which direction is the ball moving?). By stacking frames, we encode enough history into the state to make it approximately Markov.

**Key insight**: The Markov property is an *assumption*, not a fact. In complex environments, it's an approximation. The quality of your state representation determines how well the Markov assumption holds.

### 1.3 Formal Definition: MDP

A Markov Decision Process is a tuple (S, A, P, R, gamma):

- **S**: State space (all possible states)
- **A**: Action space (all possible actions)
- **P(s'|s, a)**: Transition function — probability of reaching state s' from state s after action a
- **R(s, a, s')**: Reward function — immediate reward for a transition
- **gamma** (0 < gamma <= 1): Discount factor — how much we value future vs. immediate reward

**gamma is crucial.** With gamma = 0.99 (our MiniPong config), a reward 100 steps in the future is worth 0.99^100 = 0.366 of its face value. With gamma = 0.9, it's 0.9^100 = 0.0000266 — nearly worthless. The discount factor encodes the agent's "time horizon."

**Why discount at all?** Three reasons:
1. Mathematical: ensures infinite sums converge
2. Practical: rewards far in the future are uncertain
3. Behavioral: encodes a preference for sooner rewards (like humans)

### 1.4 Policies and Value Functions

A **policy** pi(a|s) is a mapping from states to actions (possibly probabilistic). It's the agent's "strategy."

The **state-value function** V^pi(s) answers: "If I'm in state s and follow policy pi forever, what's my expected cumulative discounted reward?"

V^pi(s) = E[r_t + gamma * r_{t+1} + gamma^2 * r_{t+2} + ... | s_t = s, pi]

The **action-value function** Q^pi(s, a) answers: "If I'm in state s, take action a, and then follow policy pi forever, what's my expected return?"

Q^pi(s, a) = E[r_t + gamma * r_{t+1} + gamma^2 * r_{t+2} + ... | s_t = s, a_t = a, pi]

**The relationship**: V^pi(s) = sum over a of pi(a|s) * Q^pi(s, a). The state value is the average of action values weighted by the policy.

### 1.5 The Bellman Equations

The key recursive insight. The value of a state can be decomposed into:
- The immediate reward, plus
- The discounted value of the next state

**Bellman Expectation Equation:**
> Q^pi(s, a) = E[r + gamma * Q^pi(s', a') | s, a, pi]

"The Q-value of taking action a in state s equals the expected immediate reward plus the discounted Q-value of wherever I end up, following my policy."

**Bellman Optimality Equation:**
> Q*(s, a) = E[r + gamma * max_{a'} Q*(s', a') | s, a]

"The *optimal* Q-value equals the expected immediate reward plus the discounted *best possible* Q-value from the next state."

If you could solve this equation for Q*, you'd have the perfect strategy: always pick argmax_a Q*(s, a).

**In MiniPong terms**: Q*(frame_stack, "move up") might be 0.7, meaning "if I move up now, and play optimally from here on, I expect to accumulate 0.7 reward on average." If Q*(frame_stack, "stay") = 0.3 and Q*(frame_stack, "move down") = -0.2, the optimal action is "move up."

### 1.6 Why Can't We Just Solve the Bellman Equation?

For small, discrete problems (like a 4x4 grid world), you can solve Bellman equations exactly using **dynamic programming** — iterating until convergence. This is called *value iteration* or *policy iteration*.

For MiniPong: the state space is 256^(84*84*4) — a number with ~67,000 digits. You can't store a table that big, let alone iterate over it. This is the **curse of dimensionality** — and it's why we need function approximation (neural networks).

For Go: the state space is approximately 2.1 x 10^170 legal board positions. The number of atoms in the observable universe is ~10^80. Go's state space is not just large — it's *incomprehensibly* large relative to any physical system we know of.

### 1.7 Connection to Control Theory

You correctly intuited that MiniPong can be solved with control theory. Here's the formal connection:

- An MDP with known dynamics (known P and R) is equivalent to an **optimal control problem**
- The Bellman equation is the discrete-time analog of the **Hamilton-Jacobi-Bellman (HJB) equation** in continuous control
- A PID controller for MiniPong is essentially hand-coding the policy using domain knowledge about the dynamics

RL is for when you *don't know* the dynamics (model-free), or when the dynamics are too complex to solve analytically (model-based RL). For MiniPong, RL is overkill. For Go, it's necessary.

### 1.8 Module 1 Summary

| Concept | What it means | MiniPong example |
|---------|--------------|------------------|
| State | What the agent observes | 4 stacked 84x84 frames |
| Action | What the agent can do | {up, down, stay} |
| Reward | Immediate feedback signal | +1 (score), -1 (scored on), 0 |
| Policy | Strategy: state → action mapping | The neural network's output |
| V(s) | Expected return from state s | "How good is this position?" |
| Q(s,a) | Expected return from state s, action a | "How good is moving up right now?" |
| gamma | Discount factor | 0.99 — care about next ~100 steps |
| Bellman equation | Recursive value decomposition | Q = reward + gamma * future Q |
| Curse of dimensionality | State space too large for tables | 256^28,224 possible states |

---

## Module 2: Value-Based RL — From Q-Tables to DQN

### 2.1 Q-Learning: The Foundation

Q-learning (Watkins, 1989) is the algorithm that directly estimates Q* — the optimal action-value function — without knowing the environment dynamics.

**Algorithm:**
1. Initialize Q(s, a) arbitrarily for all state-action pairs
2. Observe state s
3. Choose action a (using some exploration strategy)
4. Execute a, observe reward r and next state s'
5. Update: Q(s, a) <- Q(s, a) + alpha * [r + gamma * max_{a'} Q(s', a') - Q(s, a)]
6. Go to step 2

The update rule is intuitive:
- **Target**: r + gamma * max_{a'} Q(s', a') — "what actually happened, plus my best estimate of the future"
- **Prediction**: Q(s, a) — "what I thought would happen"
- **Error**: target - prediction — "how wrong I was"
- **Update**: nudge Q toward the target by alpha * error

**alpha** is the learning rate — how much to trust new experience vs. old estimates.

This converges to Q* with probability 1 — *if* you visit every state-action pair infinitely often and decay alpha appropriately. For a small grid world with 100 states and 4 actions, you'd maintain a 100x4 table and fill it in through experience. This is **tabular Q-learning**.

### 2.2 The Neural Network Approximation

For MiniPong with 84x84x4 input, a Q-table is impossible. Instead, we approximate Q with a neural network parameterized by weights theta:

> Q(s, a; theta) ≈ Q*(s, a)

The network takes a state (pixel frames) as input and outputs Q-values for *all actions simultaneously*. For MiniPong: input is (4, 84, 84), output is 3 values [Q(s, up), Q(s, down), Q(s, stay)].

**Architecture of our MiniPong network** (from `create_q_network` in `src/rl/networks.py`):
- Conv2d layers extract spatial features from the pixel input
- Fully connected layers combine features into Q-value estimates
- No activation on the output — Q-values can be any real number

The network learns to "see" the ball position, ball velocity (from frame differences), paddle position, and compute which action maximizes future reward.

### 2.3 Why Naive Neural Q-Learning Fails

Naively plugging a neural network into Q-learning breaks catastrophically. Two problems:

**Problem 1: Correlated samples.** Consecutive frames are nearly identical. Training on sequential experience means the network sees the same pattern thousands of times in a row, then something completely different. It overfits to recent experience and forgets everything else. This is like studying only Chapter 7 of a textbook for a week, then only Chapter 3.

**Problem 2: Moving target.** The target r + gamma * max Q(s', a'; theta) depends on the *same network* we're updating. Every weight update shifts both the prediction and the target. It's like trying to catch a ball that moves every time you reach for it.

These problems caused neural Q-learning to fail for decades. The DQN paper (Mnih et al., 2015) solved both.

### 2.4 DQN Innovation #1: Experience Replay

**Solution to correlated samples: store transitions, sample randomly.**

Instead of training on the most recent transition, we store all transitions (s, a, r, s', done) in a **replay buffer** — a fixed-size FIFO queue. During training, we sample random *mini-batches* from this buffer.

In our code (`src/rl/replay.py`): `ReplayBuffer(capacity=100000)` stores up to 100k transitions. Each training step samples `batch_size=32` random transitions.

**Why this works:**
- Breaks temporal correlation — a mini-batch contains transitions from many different episodes and time periods
- Data efficiency — each transition is used for multiple gradient updates, not just one
- Smooths the training distribution — the network sees a diverse mix of experiences

**The tradeoff:** The replay buffer stores transitions from an *older* policy (the policy at the time the transition was collected). As the policy improves, old transitions become "off-policy" — they were generated by a different strategy. This is acceptable for Q-learning (it's naturally off-policy), but it's a limitation we'll revisit when we discuss policy gradient methods.

### 2.5 DQN Innovation #2: Target Network

**Solution to the moving target: freeze a copy of the network.**

We maintain two copies of the network:
- **Online network** (theta): updated every training step, used to select actions
- **Target network** (theta^-): updated only every N steps (by copying from online), used to compute targets

The update rule becomes:
> target = r + gamma * max_{a'} Q(s', a'; theta^-)   [uses frozen target network]
> loss = (Q(s, a; theta) - target)^2                  [prediction from online network]
> theta <- theta - alpha * gradient(loss)              [update only online network]

Every `target_update_period` steps (1000 in our 1M config), we sync: theta^- <- theta.

**Why this works:** For 1000 steps at a time, the target is stationary. The online network can make genuine progress toward a fixed goal. Then the goal shifts (target network update), and the process repeats. It's like setting a series of milestones rather than chasing a moving target.

**In our MiniPong code** (`src/agents/dqn_agent.py`):
- `self.online` — the network that acts and gets updated
- `self.target` — the frozen copy for computing targets
- `sync_target()` — copies online weights to target

### 2.6 DQN Innovation #3: Frame Stacking

Raw pixels don't contain velocity information. A single frame of MiniPong shows where the ball *is*, but not where it's *going*. The same ball position could mean the ball is moving left or right — the optimal action is completely different.

**Solution:** Stack the last N frames (N=4 in our config) into a single observation. The network can compute velocity by comparing pixel differences across frames.

This is implemented in `src/envs/wrappers.py` as `FrameStackPixels` — a Gymnasium wrapper that maintains a deque of recent frames and concatenates them into the observation.

**Connection to the Markov property:** A single frame violates the Markov assumption (the ball's direction is missing). Four stacked frames approximately restore it — the state now contains enough information to predict the future without knowing the history.

### 2.7 Exploration vs. Exploitation: Epsilon-Greedy

The agent faces a dilemma:
- **Exploit**: Pick the action with the highest Q-value (use what you've learned)
- **Explore**: Pick a random action (discover new strategies)

Too much exploitation → the agent gets stuck in local optima, never discovering better strategies.
Too much exploration → the agent wastes time on random actions despite knowing better.

**Epsilon-greedy** is the simplest solution:
- With probability epsilon: take a random action
- With probability (1 - epsilon): take argmax_a Q(s, a)

We **anneal** epsilon over time — start high (explore a lot early) and decay to a small value (mostly exploit later).

**Our MiniPong schedule** (from `src/rl/schedules.py`):
- epsilon_start = 1.0 (100% random at the beginning)
- epsilon_end = 0.02 (2% random at the end)
- epsilon_decay_steps = 500,000 (linear decay over 500k steps)

### 2.8 The Complete DQN Training Loop

Putting it all together — this is exactly what `train_dqn.py` does:

```
Initialize online network Q(theta) with random weights
Initialize target network Q(theta^-) <- Q(theta)
Initialize replay buffer D (empty, capacity C)

For step = 1 to total_steps:
    1. Observe state s (4 stacked frames)
    2. Choose action:
       - With probability epsilon: random action
       - Otherwise: argmax_a Q(s, a; theta)
    3. Execute action, observe reward r, next state s', done flag
    4. Store (s, a, r, s', done) in replay buffer D
    5. If |D| > warmup_steps:
       a. Sample random mini-batch of 32 transitions from D
       b. For each (s, a, r, s', done) in batch:
          - If done: target = r
          - Else: target = r + gamma * max_{a'} Q(s', a'; theta^-)
       c. Compute loss = mean((Q(s, a; theta) - target)^2)
       d. Backpropagate and update theta
    6. Every target_update_period steps: theta^- <- theta
    7. Decay epsilon
```

### 2.9 What We Observed: The 1M Training Curve

Our 1M MPS training run showed a classic DQN phenomenon:

| Step | Hit Ratio | Rally Length | Interpretation |
|------|-----------|-------------|----------------|
| 100k | 0.725 | 5.8 | Early learning — epsilon still 0.82 |
| 200k | 0.877 | 11.6 | Rapid improvement phase |
| 300k | 0.943 | 18.0 | Agent becoming competent |
| 400k | 0.970 | 21.1 | Near-optimal play |
| 500k | 0.973 | 23.0 | Peak approaching, epsilon at 0.02 |
| **600k** | **1.000** | **24.0** | **Peak — perfect hit ratio** |
| 700k | 0.941 | 17.6 | Degradation begins |
| 800k | 0.905 | 14.7 | Continued collapse |
| 900k | 0.806 | 8.9 | Severe forgetting |
| 1M | 0.798 | 8.5 | Worse than 200k |

**What happened at 600k?** The agent achieved perfection — then lost it. This is **catastrophic forgetting** combined with **replay buffer drift**:

1. At low epsilon (0.02), the agent rarely explores. The replay buffer fills with near-optimal trajectories.
2. The buffer loses diversity — it no longer contains examples of recovery from mistakes.
3. When the agent makes a rare mistake (due to the 2% random actions), it doesn't know how to recover — it hasn't practiced recovery in hundreds of thousands of steps.
4. The network's predictions become overconfident and brittle.

**Fixes (not implemented in our simple DQN):**
- **Prioritized Experience Replay**: Sample surprising transitions more often (transitions with high prediction error)
- **Dueling DQN**: Separate the value of a state from the advantage of each action
- **Double DQN**: Use the online network to *select* the best action but the target network to *evaluate* it (reduces overestimation)
- **Higher epsilon floor**: Keep exploring more (e.g., 0.05 instead of 0.02)
- **Checkpoint selection**: Use the best checkpoint, not the final one (we'd use step 600k)

### 2.10 DQN's Limitations for Game-Playing

DQN works for MiniPong because:
- The action space is tiny (3 actions)
- The game is reactive (respond to the ball)
- No long-term planning is needed

DQN fails for Go because:
- The action space is huge (361 intersections on a 19x19 board)
- You need to plan 100+ moves ahead
- The reward is extremely sparse (only +1/-1 at the end of a 200+ move game)
- There's no "ball to react to" — you need strategic thinking

This is why the AlphaGo lineage needed fundamentally different approaches: **policy gradients** (Module 3) and **Monte Carlo Tree Search** (Module 4).

### 2.11 Module 2 Summary

| DQN Component | Problem it Solves | Our Implementation |
|---------------|------------------|-------------------|
| Neural network | Curse of dimensionality | Conv2d → FC layers, outputs 3 Q-values |
| Replay buffer | Correlated samples | ReplayBuffer(capacity=100k), batch=32 |
| Target network | Moving target | Frozen copy, synced every 1000 steps |
| Frame stacking | Non-Markov observations | 4 frames concatenated as channels |
| Epsilon-greedy | Exploration vs. exploitation | 1.0 → 0.02 over 500k steps |

**What DQN achieved:** Superhuman play on 49 Atari games from raw pixels (Mnih et al., 2015). This was the paper that launched the deep RL revolution.

**What DQN can't do:** Strategic planning, large action spaces, sparse rewards, multi-agent games with hidden information. For those, we need the tools in the next modules.

---

## Module 3: Beyond Value Functions — Policy Gradients and Actor-Critic

### 3.1 The Motivation

DQN learns Q(s, a) and derives a policy from it: always pick argmax_a Q(s, a). This is an **indirect** approach — we learn values, then extract actions.

What if we learned the policy **directly**? Instead of Q(s, a), we learn pi(a|s; theta) — a neural network that outputs a probability distribution over actions.

**Why bother?** Three reasons:

1. **Continuous actions.** DQN needs to compute max over all actions — impossible if actions are continuous (e.g., "apply 3.7 degrees of torque"). Policy networks naturally output continuous values.

2. **Stochastic policies.** Sometimes the optimal strategy is random (rock-paper-scissors). DQN always picks one action deterministically. A policy network can output "30% rock, 30% paper, 40% scissors."

3. **Large action spaces.** In Go, there are up to 361 possible moves. Computing Q for each and taking the max is expensive. A policy network can directly output "play at position (3, 4) with probability 0.12."

**For AlphaGo, this is essential.** The policy network is what makes MCTS tractable — instead of considering all 361 moves, it focuses search on the 10-20 most promising ones.

### 3.2 The Policy Gradient Theorem

How do you train a policy network? You can't use the Bellman equation (that's for value functions). Instead, you directly optimize the expected return.

**Objective:** J(theta) = E[total return | pi(theta)]

"Find the parameters theta that maximize the expected cumulative reward when following policy pi."

The **policy gradient theorem** (Sutton et al., 2000) gives us the gradient:

> gradient J(theta) = E[ gradient log pi(a|s; theta) * Q^pi(s, a) ]

In English: "Increase the probability of actions that led to high returns. Decrease the probability of actions that led to low returns." This is the **REINFORCE** algorithm (Williams, 1992).

### 3.3 REINFORCE: The Simplest Policy Gradient

```
For each episode:
    1. Run the policy, collecting (s_t, a_t, r_t) for every step
    2. Compute return G_t = sum of discounted future rewards from step t
    3. For each step t:
       - Compute gradient of log pi(a_t | s_t; theta)
       - Weight it by G_t
       - Accumulate gradient
    4. Update theta in the direction of accumulated gradient
```

**The problem:** REINFORCE has extremely high variance. G_t depends on all future rewards, which are random. The gradient estimate is noisy — sometimes a good action looks bad because of unlucky future events, and vice versa.

**Analogy:** Imagine evaluating a chess player by the outcome of the game. They make a brilliant move at step 10, but their opponent gets lucky at step 40 and wins. REINFORCE would *decrease* the probability of that brilliant move, because the game was lost.

### 3.4 Baselines and Advantage Functions

**The fix:** Instead of weighting by absolute return G_t, weight by the **advantage** — how much *better* this action was compared to the average.

> A^pi(s, a) = Q^pi(s, a) - V^pi(s)

"The advantage of action a in state s is the Q-value minus the state value." Positive advantage means "better than average," negative means "worse."

This dramatically reduces variance. We don't increase the probability of actions that happened in good states — only actions that were *better than expected* for that state.

### 3.5 Actor-Critic Methods

The next evolution: maintain **two networks simultaneously**:

- **Actor** (policy network): pi(a|s; theta) — decides what to do
- **Critic** (value network): V(s; w) — evaluates how good the current state is

The critic provides the baseline for the actor's gradient. The actor provides the policy for the critic to evaluate.

**Training loop:**
1. Actor takes action a in state s
2. Observe reward r and next state s'
3. Critic computes TD error: delta = r + gamma * V(s'; w) - V(s; w)
4. Update critic: w <- w + alpha_w * delta * gradient V(s; w)
5. Update actor: theta <- theta + alpha_theta * delta * gradient log pi(a|s; theta)

The TD error delta serves as the advantage estimate — it's positive when things went better than expected (the reward plus future value exceeded the predicted value).

### 3.6 A3C and A2C: Scaling with Parallelism

**A3C** (Asynchronous Advantage Actor-Critic, Mnih et al., 2016):
- Run multiple copies of the agent in parallel, each in its own environment
- Each agent computes gradients independently
- Gradients are asynchronously applied to a shared set of parameters
- The asynchrony provides natural exploration diversity (different agents see different states)

**A2C** (synchronous version): same idea, but agents synchronize their gradient updates. Simpler, often just as effective.

**Why this matters for AlphaGo:** Distributed training across many workers is the blueprint for the self-play training used in AlphaGo Zero. Instead of environments, the "workers" are self-play games.

### 3.7 PPO: The Industry Standard

**PPO** (Proximal Policy Optimization, Schulman et al., 2017) is currently the most widely used policy gradient algorithm. It addresses a critical problem: policy gradient updates can be too large, causing the policy to change drastically and "fall off a cliff."

PPO constrains updates so the new policy stays close to the old one:

> L(theta) = min(r_t * A_t, clip(r_t, 1-epsilon, 1+epsilon) * A_t)

Where r_t = pi_new(a|s) / pi_old(a|s) is the probability ratio. If the ratio gets too large (policy changed too much), the clipping kicks in and prevents further movement.

**PPO is what OpenAI uses for most of their RL work**, including RLHF for ChatGPT. It's stable, easy to tune, and parallelizes well.

### 3.8 Why AlphaGo Needs Both

AlphaGo uses **both** a policy network (Module 3) and a value network (Module 1/2):

- **Policy network**: "Which moves are worth considering?" → Guides the search tree
- **Value network**: "Who's winning in this position?" → Evaluates leaf nodes

Neither alone is sufficient:
- Policy alone can't look ahead (it just picks moves without planning)
- Value alone can't efficiently explore the game tree (it would need to evaluate every possible move)

Combined with Monte Carlo Tree Search (Module 4), they become greater than the sum of their parts.

### 3.9 Module 3 Summary

| Method | Key Idea | Advantage | Limitation |
|--------|----------|-----------|------------|
| REINFORCE | Directly optimize expected return | Handles continuous/large action spaces | High variance |
| Actor-Critic | Two networks: policy + value | Lower variance than REINFORCE | More complex, two networks to train |
| A3C/A2C | Parallel actors for diversity | Natural exploration, faster training | Requires parallel compute |
| PPO | Constrained policy updates | Stable, widely applicable | Slightly less sample-efficient |

**The progression:** Q-learning → DQN (add neural nets) → Policy gradients (learn policy directly) → Actor-Critic (combine both) → PPO (stabilize updates). Each step builds on the limitations of the previous.

---

## Module 4: Game Trees and Monte Carlo Tree Search

### 4.1 Games as Trees

A two-player game can be represented as a **game tree**:
- **Root**: starting position
- **Edges**: legal moves
- **Nodes**: board positions
- **Leaves**: terminal positions (win/loss/draw)

For tic-tac-toe, the full tree has ~255,000 nodes. For chess, ~10^120. For Go, ~10^360.

### 4.2 Minimax and Alpha-Beta Pruning

The classical approach to game-playing AI:

**Minimax**: Assume both players play optimally. At your turn, pick the move that maximizes your score. At the opponent's turn, assume they pick the move that minimizes your score. Recurse to the leaves.

**Alpha-beta pruning**: Skip branches that can't possibly affect the outcome. "If I already found a move that guarantees me +5, and this branch starts with -3 for me, I don't need to explore it further." Reduces the effective branching factor from b to roughly b^(1/2).

**For chess:** Alpha-beta + a handcrafted evaluation function + decades of opening/endgame databases = Stockfish-level play. This approach dominated chess AI for 50 years.

**For Go:** Alpha-beta fails completely. Why?

### 4.3 Why Go Breaks Classical Methods

Three reasons Go is fundamentally harder than chess:

1. **Branching factor.** Chess: ~35 legal moves per position. Go: ~250. Alpha-beta prunes this to ~6 effective moves in chess; in Go, it's still ~15-30. The tree explodes.

2. **No good evaluation function.** In chess, material count (sum of piece values) is a strong heuristic — a queen is worth ~9 pawns. In Go, there's no equivalent. A position's value depends on subtle interactions across the entire board. The best handcrafted Go evaluation functions were ~amateur-level.

3. **Game length.** Chess averages ~40 moves. Go averages ~200 moves. Combined with the branching factor, the search tree is incomprehensibly larger.

**The key insight that led to AlphaGo:** You don't need to search the entire tree. You need to search the *right parts* intelligently. This is Monte Carlo Tree Search.

### 4.4 Monte Carlo Tree Search (MCTS)

MCTS builds a search tree incrementally, guided by random simulations. Four phases, repeated thousands of times:

**1. Selection.** Start at the root. Descend through the tree by picking the child node that maximizes:

> UCT(node) = Q(node)/N(node) + c * sqrt(ln(N(parent)) / N(node))

The first term is the average reward (exploitation). The second term is an exploration bonus (less-visited nodes get higher bonus). c is a constant balancing the two.

**2. Expansion.** When you reach a leaf node that hasn't been fully explored, add one new child node.

**3. Simulation (rollout).** From the new node, play a random game to completion. Record the outcome.

**4. Backpropagation.** Walk back up the tree, updating N (visit count) and Q (total reward) for every node on the path.

After many iterations, the root's children have accurate value estimates. Pick the most-visited child as the move.

**Why MCTS works for Go:** It doesn't need a handcrafted evaluation function. Random rollouts provide a noisy but unbiased estimate of position value. The UCT formula balances exploring uncertain moves with exploiting known-good moves.

**Why MCTS alone isn't enough for professional Go:** Random rollouts are terrible at evaluating Go positions. A random game of Go is meaningless — it takes hundreds of thousands of simulations per move to get reasonable estimates. Professional players plan with far more sophistication than random play.

### 4.5 MCTS + Neural Networks: The AlphaGo Breakthrough

**The key innovation:** Replace random rollouts with neural network evaluations.

Instead of playing random games to estimate a position's value, ask a neural network: "Who's winning?" This gives a much better estimate with a single forward pass instead of hundreds of random simulations.

Instead of considering all legal moves equally during selection, ask a policy network: "Which moves are most promising?" This focuses the search on moves that a strong player would consider.

This is the core architecture of AlphaGo (detailed in Module 5).

### 4.6 Module 4 Summary

| Method | Branching Factor | Evaluation | Go Performance |
|--------|-----------------|------------|----------------|
| Minimax + alpha-beta | Chess: effective ~6 | Handcrafted | Fails completely |
| MCTS (pure) | ~250 → focused ~30 | Random rollouts | Weak amateur |
| MCTS + neural nets | ~250 → focused ~10 | Learned evaluation | Superhuman |

---

## Module 5: AlphaGo — Combining It All

### 5.1 The Training Pipeline

AlphaGo's training (Silver et al., 2016) was a four-stage pipeline — the first system to combine supervised learning, reinforcement learning, and tree search for a board game.

**Stage 1: Supervised Learning from Human Games**
- Trained a **policy network** (p_sigma) on ~30 million positions from the KGS Go Server
- Input: 19x19 board with 48 feature planes (stone positions, liberties, capture info, etc.)
- Network: **13 convolutional layers, 192 filters each**, 5x5 kernel on first layer, 3x3 on the rest
- The network predicts which move a human expert would play in each position
- Accuracy: **57.0%** top-1 prediction of expert moves (vs. 44.4% for previous state-of-the-art)
- Also trained a fast **rollout policy** (p_pi): a simpler linear model of 3x3 patterns (~24.2% accuracy but 1,000x faster — used for MCTS rollouts)

**Stage 2: Reinforcement Learning Self-Play**
- Starting from the SL policy, used **REINFORCE** (policy gradient) to fine-tune via self-play
- The RL policy (p_rho) played against randomly selected previous versions of itself (to prevent overfitting to the current opponent)
- **Result:** The RL policy won **80% of games** against the SL policy
- Crucially, RL improvement came from strategic insight, not just pattern matching — the RL policy found moves that humans wouldn't play but that win more often

**Stage 3: Value Network Training**
- Trained a separate **value network** (v_theta) to predict the game winner from any board position
- Architecture: identical to the policy network (13 conv layers, 192 filters) but with a single scalar output
- Training data: **30 million distinct positions**, each from a separate self-play game (one position per game to prevent overfitting to correlated positions)
- The value network achieves prediction accuracy approaching that of full MCTS rollouts — but with a single forward pass

**Stage 4: MCTS Integration**
During actual play, AlphaGo runs MCTS with neural network guidance:

1. **Selection:** At each node, pick the child that maximizes:
   > a_t = argmax_a (Q(s, a) + u(s, a))
   > u(s, a) = c_puct * P(s, a) * sqrt(N(s)) / (1 + N(s, a))

   Where P(s, a) comes from the policy network — **this is what makes the search tractable.** Instead of exploring all 250+ legal moves, the policy network focuses search on the ~10-20 most promising ones.

2. **Evaluation:** Leaf nodes are evaluated by **both** the value network and a rollout:
   > V(s_L) = (1 - lambda) * v_theta(s_L) + lambda * z_L

   Where v_theta is the value network prediction and z_L is the rollout outcome. Lambda=0.5 in the match against Lee Sedol — equal weight to both.

3. **Backup:** Update Q-values and visit counts back up the tree.

4. **Play:** Choose the most-visited root child as the move.

### 5.2 Architecture Details

**Policy network (SL and RL):**
- Input: 19x19 board with 48 feature planes
- 13 convolutional layers, 192 filters per layer
- First layer: 5x5 kernels, remaining layers: 3x3 kernels
- ReLU activations, no pooling (spatial information is critical in Go)
- Output: 19x19 = 361 move probabilities (softmax)
- ~5.3 million parameters

**Value network:**
- Same 13-layer CNN architecture as the policy network
- Additional fully connected layer (256 units)
- Output: single scalar in [-1, 1] via tanh activation (expected game outcome)
- Trained on 30M positions from 30M distinct self-play games

**Rollout policy:**
- Linear softmax over 3x3 pattern features + response/capture features
- ~2 microseconds per move (vs. ~3 milliseconds for the full policy network)
- 1,500x faster, enabling thousands of rollouts per MCTS simulation

### 5.3 The Lee Sedol Match (March 2016)

AlphaGo defeated Lee Sedol 4-1, one of the most significant milestones in AI history.

**Hardware during the match:**
- **1,202 CPUs** and **176 GPUs** for distributed MCTS
- **48 TPUs** (v1 — inference accelerators) for neural network evaluation
- Each move: **~10,000 MCTS simulations**, each requiring policy and value network forward passes
- Thinking time: ~60 seconds per move on average

**Key moments:**
- Lee Sedol was an 18-time world champion, widely considered one of the greatest Go players of all time
- **"Move 37" in Game 2** is legendary — AlphaGo played a shoulder hit on the fifth line that no human professional would consider. Commentators called it a mistake. It turned out to be brilliant, contributing to AlphaGo's win.
- Game 4: Lee Sedol's "God Move" (Move 78) exploited a known weakness in MCTS (difficulty with ko threats), leading to AlphaGo's only loss
- The match was watched by over 200 million people worldwide

**What the hardware tells us:** The 1,202 CPUs ran the MCTS tree traversal. The 176 GPUs and 48 TPUs ran the neural networks. The bottleneck was neural network inference speed — each MCTS simulation requires at least one policy network call and one value network call.

---

## Module 6: AlphaGo Zero and AlphaZero — The Self-Play Revolution

### 6.1 What Changed

AlphaGo Zero (Silver et al., 2017) achieved a remarkable simplification:

**Removed:**
- All human game data (no supervised learning stage)
- The separate rollout policy
- Handcrafted features

**Added:**
- A single dual-headed ResNet (policy head + value head sharing a body)
- Pure self-play training from random initialization
- Simpler MCTS (no rollouts — value network only)

**Result:** AlphaGo Zero defeated the original AlphaGo 100-0. Starting from zero human knowledge, it surpassed 3,000 years of accumulated human Go expertise in 40 days of training.

### 6.2 The Self-Play Training Loop

```
Initialize neural network f(theta) with random weights
f outputs both policy p and value v: (p, v) = f(s; theta)

Repeat:
    1. SELF-PLAY: Use current network + MCTS to play games against itself
       - For each move, run MCTS with the current network guiding search
       - Store (state, MCTS policy, game outcome) for every position
    2. TRAINING: Update network on collected self-play data
       - Policy target: the MCTS visit distribution (not the raw network output)
       - Value target: the actual game outcome (+1 or -1)
       - Loss = (v - z)^2 - pi^T * log(p) + regularization
         (z = game outcome, pi = MCTS policy, p = network policy, v = network value)
    3. EVALUATION: Play the new network against the current best
       - If it wins >55% of games, it becomes the new best
       - Only the best network is used for self-play
```

**The key insight:** MCTS acts as a **policy improvement operator**. The raw network policy is good, but MCTS with that network is *better* (because it looks ahead). By training the network to match the MCTS output, we distill the search back into the network. The next round of MCTS with the improved network is even better. This creates a virtuous cycle.

### 6.3 The ResNet Architecture

AlphaGo Zero used a fundamentally different architecture from AlphaGo — a single deep residual network with two output heads:

**Input representation:**
- 19x19 board with **17 feature planes**: 8 planes for current player's stone history (last 8 moves), 8 planes for opponent's history, 1 plane for color to play
- Much simpler than AlphaGo's 48 hand-engineered features — the network learns what features matter

**Shared body — Residual Tower:**
- **20 residual blocks** (in the 20-block version) or **40 residual blocks** (in the stronger version)
- Each block: two 3x3 convolutional layers with **256 filters**, batch normalization, ReLU, skip connection
- Total: ~24 million parameters (40-block version)
- The skip connections are critical — without them, gradient signal degrades in deep networks (the "vanishing gradient" problem). With skip connections, the network can be much deeper while still training stably.

**Policy head:**
- 2 convolutional layers (1x1 kernels)
- Final layer: 362 outputs (361 board intersections + 1 pass move)
- Softmax activation → probability distribution over moves

**Value head:**
- 1 convolutional layer (1x1 kernel), then a fully connected layer (256 units)
- Final output: single scalar, tanh activation → [-1, +1]
- Predicts expected game outcome from current player's perspective

**Training specifics:**
- **1,600 MCTS simulations per move** during self-play
- **4.9 million self-play games** over the course of training
- Hardware: **4 TPUs** for self-play generation, additional TPUs for training
- Batch size: 2,048 positions
- Learning rate: 0.01, annealed during training
- Optimizer: SGD with momentum 0.9
- Training duration: **~3 days** to defeat the version of AlphaGo that beat Lee Sedol (100-0)
- **40 days** of total training to reach final strength (Elo **5,185**)

### 6.4 AlphaZero: Generalization

AlphaZero (Silver et al., 2018) took the same algorithm and applied it to three games with **no game-specific tuning** — the same architecture, the same hyperparameters, only the rules changed.

**Architecture:** 20 residual blocks, 256 filters (same as AlphaGo Zero's smaller version)
**Training:** 700,000 training steps, batch size 4,096

**Hardware (massive scale):**
- **5,000 first-generation TPUs** for self-play game generation
- **16 second-generation TPUs** for network training
- **800 MCTS simulations per move** (half of AlphaGo Zero's 1,600)

**Results:**

| Game | Time to Superhuman | Opponent | Score |
|------|-------------------|----------|-------|
| Chess | **9 hours** | Stockfish (strongest classical engine) | **28W / 72D / 0L** (100 games) |
| Shogi | **12 hours** | Elmo (strongest shogi engine) | 91.2W / 2.1D / 6.7L |
| Go | **13 days** | AlphaGo Zero (3-day version) | Won convincingly |

**The chess result is staggering.** Stockfish represents 50+ years of human chess programming expertise — hand-tuned evaluation functions, opening books, endgame tablebases, alpha-beta search optimized to examine 70 million positions per second. AlphaZero learned to defeat it in 9 hours with zero chess knowledge beyond the rules, searching only 80,000 positions per second (875x fewer). It compensated with *much better* position evaluation.

**What AlphaZero's chess style revealed:** It rediscovered known openings (the Queen's Gambit, the English Opening) and also played entirely novel strategies. It was willing to sacrifice material for long-term positional advantages — something previously considered "human-like" rather than "computer-like." This suggests that certain strategic principles are optimal, not merely cultural conventions.

### 6.5 Module 6 Summary

| System | Human Data | Architecture | Training | Go Elo |
|--------|-----------|-------------|----------|--------|
| AlphaGo (2016) | 30M positions | Separate policy (13 CNN) + value nets | SL → RL → MCTS | ~3,700 |
| AlphaGo Zero (2017) | None | Single dual-head ResNet (40 blocks, 256 filters) | Pure self-play, 1600 sims/move | **5,185** |
| AlphaZero (2018) | None | Same architecture (20 blocks, 256 filters) | Pure self-play, 800 sims/move | ~5,200+ |

---

## Module 7: MuZero — Learning the Rules

### 7.1 The Remaining Assumption

AlphaGero/Zero still requires **a perfect simulator of the game rules.** During MCTS, the algorithm needs to:
1. Know which moves are legal
2. Apply a move and get the resulting board state
3. Know when the game is over

For board games with known rules, this is trivial. But what about:
- Video games (Atari) where the dynamics are complex?
- Real-world robotics where you can't perfectly simulate physics?
- Any domain where you don't have a perfect model?

### 7.2 MuZero's Innovation

MuZero (Schrittwieser et al., 2020) **learns** a model of the environment, then plans in the learned model's latent space.

Three networks:
- **Representation function** h: s → hidden_state (encodes a real observation into a latent state)
- **Dynamics function** g: (hidden_state, action) → (next_hidden_state, reward) (predicts what happens next)
- **Prediction function** f: hidden_state → (policy, value) (evaluates a latent state)

**During MCTS:** Instead of applying moves in a real simulator, MuZero applies moves in its *learned* dynamics model. It plans entirely in latent space — the hidden states don't need to correspond to real board positions, they just need to be useful for prediction.

### 7.3 Training and Scale

**For board games (Go, chess, shogi):**
- **1,000 TPU v3** chips for self-play generation
- **16 TPU v3** chips for network training
- **800 MCTS simulations per move** (same as AlphaZero)
- Network architecture: similar ResNet body to AlphaZero, plus the dynamics model

**For Atari (57 games):**
- **800 TPU v3** chips for data generation (acting in environments)
- **8 TPU v3** chips for training
- **50 MCTS simulations per action** (much fewer than board games — Atari requires real-time decisions)
- The dynamics model must learn much more complex physics (pixel dynamics vs. board state transitions)

### 7.4 The Remarkable Result

MuZero matched AlphaZero's performance in Go, chess, and shogi — **without being given the rules.** It also achieved superhuman performance on 57 Atari games, matching the specialized state-of-the-art (MuZero: 731% mean human-normalized score vs. R2D2's 868%, but MuZero uses a single algorithm across all games).

**Why this matters — the progression in four steps:**

| System | Knows Rules? | Human Data? | General? | What it demonstrated |
|--------|-------------|-------------|----------|---------------------|
| AlphaGo | Yes | Yes (30M positions) | Go only | NN + MCTS + RL beats humans |
| AlphaGo Zero | Yes | No | Go only | Self-play alone surpasses human knowledge |
| AlphaZero | Yes | No | Chess, Shogi, Go | Same algorithm works across games |
| MuZero | **No** | No | Board games + Atari | Agent can learn the rules *and* the strategy |

This is the closest we've come to a general game-playing agent:
- No human data
- No knowledge of the rules
- Learns its own world model
- Plans using the learned model

**The open question:** MuZero still requires a well-defined reward signal and discrete timesteps. The next frontier is extending this to continuous control, real-world robotics, and open-ended environments — domains where even the reward function isn't given.

---

## Module 8: Hardware and Scale

### 8.1 Why Hardware Matters

Every concept in Modules 1-7 requires massive computation:
- Neural network training: matrix multiplications (forward pass, backprop)
- Self-play: thousands of parallel games
- MCTS: thousands of network evaluations per move
- Replay buffers: storing and sampling millions of transitions

The history of game-playing AI is inseparable from the history of hardware.

### 8.2 CPU vs. GPU: The Fundamental Difference

**CPU (Central Processing Unit):**
- Few cores (4-64), each very powerful
- Optimized for sequential, branching logic
- Great at: if/else logic, operating systems, single-threaded algorithms
- **Our MiniPong CPU training:** ~35 steps/s

**GPU (Graphics Processing Unit):**
- Thousands of cores (NVIDIA A100: 6,912 CUDA cores), each relatively simple
- Optimized for doing the *same operation* on many data elements simultaneously
- Great at: matrix multiplication, convolution, any "embarrassingly parallel" task
- **Our MiniPong MPS training:** ~160 steps/s (4.5x faster)

**Why neural networks love GPUs:** A neural network forward pass is a sequence of matrix multiplications. Multiplying two 1000x1000 matrices requires 10^9 multiply-add operations — but they're all independent. A GPU can distribute these across thousands of cores.

### 8.3 NVIDIA GPU Architecture (Simplified)

An NVIDIA GPU (like the A100 used for large-scale training) has:

**Streaming Multiprocessors (SMs):** The GPU is divided into SMs. Each SM contains:
- **CUDA cores**: General-purpose floating-point units. Execute one multiply-add per clock cycle.
- **Tensor Cores**: Specialized matrix-multiply units. Perform a 4x4 matrix multiply per clock cycle (much faster than CUDA cores for this specific operation). This is the hardware that makes transformer training and large neural networks feasible.

**Concrete GPU specifications:**

| GPU | CUDA Cores | Tensor Cores | Memory | Bandwidth | FP16 TFLOPS |
|-----|-----------|-------------|--------|-----------|-------------|
| A100 (2020) | 6,912 | 432 (3rd gen) | 80 GB HBM2e | 2.0 TB/s | 312 |
| H100 (2023) | 16,896 | 528 (4th gen) | 80 GB HBM3 | 3.35 TB/s | 990 |

The H100 is roughly **3x faster** than the A100 for training, driven by more Tensor Cores and faster memory.

**Memory hierarchy:**
- **HBM (High Bandwidth Memory):** The main GPU memory (A100: 80GB, 2 TB/s bandwidth). This is where model weights and activations live. HBM stacks DRAM dies vertically with through-silicon vias (TSVs) — a physical innovation that enables the bandwidth needed for ML.
- **L2 Cache:** Shared across all SMs (~40MB on A100, ~50MB on H100)
- **Shared Memory/L1:** Per-SM, very fast (~100KB per SM)
- **Registers:** Per-thread, fastest

**The memory wall:** Often the bottleneck is *not* compute but memory bandwidth — moving data to/from the computation units. A 24M-parameter AlphaGo Zero model fits comfortably in GPU memory. But during training, you need to store activations for every layer (for backpropagation), optimizer states (2x model size for Adam), and gradient buffers. The total memory footprint is typically 4-8x the model size. This is why techniques like mixed-precision training (FP16 instead of FP32) help: they halve memory traffic and double Tensor Core throughput.

### 8.4 Apple's MPS (Metal Performance Shaders)

Our MiniPong training uses Apple's MPS — Metal Performance Shaders on the M-series chips.

**The M-series architecture is fundamentally different from NVIDIA:**
- **Unified memory:** CPU and GPU share the same RAM (no PCIe transfer bottleneck)
- **Neural Engine:** Dedicated hardware for neural network inference (not used by PyTorch MPS backend)
- **GPU cores:** ~10 (M1) to ~40 (M3 Max) GPU compute units, each with many ALUs

**Why MPS is 4.5x faster than CPU for our tiny model:** Even a small 3-layer CNN benefits from GPU parallelism. The convolution operation slides a filter across the image — each position is independent and can be computed in parallel.

**Why MPS is much slower than an A100 for large models:** The M-series GPU has ~100x fewer compute units than an A100, and lower memory bandwidth. Our MiniPong model is tiny — a real AlphaGo-scale model would be 100-1000x larger.

### 8.5 Google TPUs

AlphaGo and AlphaGo Zero used Google's custom Tensor Processing Units (TPUs):

**TPU v1 (2016):** Inference-only. Core: a **256x256 systolic array** — a grid of multiply-accumulate units where data flows in from two sides and partial sums accumulate as they move through the grid. **92 TOPS** (tera operations per second) at INT8. Used in the AlphaGo vs Lee Sedol match for neural network inference during MCTS.

**TPU v2 (2017):** Added training support by including **BFloat16** (Brain Floating Point) — a 16-bit format with the same dynamic range as FP32 but lower precision. **45 TFLOPS**, **16GB HBM**. Used for AlphaGo Zero training.

**TPU v3 (2018):** Water-cooled, **420 TFLOPS**, 32GB HBM. Used for AlphaZero and MuZero. Can be assembled into **"pods" of 1,024 chips** connected by a high-speed 2D torus network.

**TPU v4 (2021):** 275 TFLOPS per chip, organized into pods of **4,096 chips** via 3D torus topology. Used for training large language models (PaLM, Gemini).

**Key difference from GPUs: the systolic array.** GPUs have thousands of independent cores that all execute the same instruction (SIMD). TPUs have a 2D grid where data flows through multiply-accumulate units sequentially — input activations flow in from the left, weights are preloaded, and partial sums flow downward. This is less flexible than GPUs but more power-efficient for the specific operation that dominates neural network training: matrix multiplication.

**Which DeepMind system used which hardware:**

| System | Self-Play | Training | Inference (at match time) |
|--------|----------|---------|--------------------------|
| AlphaGo (2016) | CPUs | GPUs | 1,202 CPUs + 176 GPUs + 48 TPU v1 |
| AlphaGo Zero (2017) | 4 TPUs | TPU v2 | ~4 TPUs |
| AlphaZero (2018) | 5,000 TPU v1 | 16 TPU v2 | Similar to training |
| MuZero (2020, board) | 1,000 TPU v3 | 16 TPU v3 | Similar to training |
| MuZero (2020, Atari) | 800 TPU v3 | 8 TPU v3 | Similar to training |

### 8.6 Distributed Training

Single-GPU training is too slow for AlphaGo-scale problems. Solutions:

**Data parallelism:** Multiple GPUs each process different mini-batches, then average their gradients.
- Each GPU has a copy of the full model
- Each GPU processes a different batch of training data
- Gradients are summed across GPUs (AllReduce operation)
- All GPUs update their models identically
- **Linear speedup** with number of GPUs (ideally)

**Self-play parallelism (unique to game AI):**
- Many workers generate self-play games using the current best network
- A separate cluster trains the network on accumulated game data
- New network is evaluated against the current best
- If better, it becomes the new self-play policy
- **AlphaZero:** 5,000 TPU v1 workers generating self-play games, 16 TPU v2 for training
- **MuZero:** 1,000 TPU v3 for self-play, 16 TPU v3 for training

**The bandwidth challenge:** As you add more GPUs, the gradient communication (AllReduce) becomes the bottleneck. Solutions:
- **Gradient compression:** Send compressed gradients instead of full tensors
- **Ring AllReduce:** Communicate gradients in a ring topology (NCCL library)
- **Asynchronous updates:** Don't wait for all GPUs to finish (but reduces training stability)

### 8.7 Compute Scaling Laws

A recurring pattern in AI research:

| System | Hardware | Self-Play Games | Training Time | Training Steps |
|--------|----------|-----------------|---------------|----------------|
| DQN (Atari, 2015) | 1 GPU | N/A | ~12-14 days | 50M frames |
| AlphaGo (2016) | 176 GPUs + 48 TPU v1 | Millions (RL stage) | Weeks | N/A |
| AlphaGo Zero (2017) | 4 TPUs | 4.9M games | 40 days | 29M steps |
| AlphaZero Go (2018) | 5,000 TPU v1 + 16 TPU v2 | Continuous | 13 days | 700k steps |
| AlphaZero Chess (2018) | Same | Continuous | 9 hours | 700k steps |
| MuZero Board (2020) | 1,000 TPU v3 + 16 TPU v3 | Continuous | Similar | Similar |
| **Our MiniPong** | **1 Apple M-series** | **N/A** | **103 minutes** | **1M steps** |

**The trend:** AlphaZero achieves better results than AlphaGo Zero despite fewer training *steps* (700k vs. 29M) because it uses 100x more hardware for self-play generation, producing higher-quality training data faster. More hardware → more self-play games per unit time → faster improvement.

### 8.8 Our MiniPong in Context

| Metric | Our MiniPong | AlphaGo Zero | AlphaZero (Go) |
|--------|-------------|-------------|---------------|
| Parameters | ~50K | ~24M (40 blocks) | ~24M (20 blocks) |
| Training steps | 1M | ~29M | 700k |
| Self-play games | N/A (single agent vs. wall) | ~4.9M | Continuous |
| MCTS sims/move | N/A | 1,600 | 800 |
| Hardware | 1 Apple M-series GPU | 4 TPUs | 5,000 TPU v1 + 16 TPU v2 |
| Training time | 103 minutes | 40 days | 13 days |
| State space | 256^28,224 | ~2.1 x 10^170 | ~2.1 x 10^170 |
| Action space | 3 | 362 | 362 |
| Peak performance | Hit ratio 1.0 (at 600k) | Elo 5,185 | Elo ~5,200+ |

---

## Module 9: The Mathematics

### 9.1 Convergence of Q-Learning

**Theorem (Watkins & Dayan, 1992):** Tabular Q-learning converges to Q* with probability 1, given:
1. All state-action pairs are visited infinitely often
2. The learning rate satisfies: sum alpha_t = infinity, sum alpha_t^2 < infinity
3. The MDP has bounded rewards

**Condition 1** is why we need exploration (epsilon-greedy). **Condition 2** is why we decay the learning rate. **Condition 3** is naturally satisfied in games.

**The catch:** This guarantee is for *tabular* Q-learning only. With function approximation (neural networks), there are **no convergence guarantees.** DQN can diverge, oscillate, or settle on a suboptimal policy. The 1M training collapse we observed is a real-world example.

### 9.2 The Deadly Triad

Sutton & Barto identify the "deadly triad" of conditions that can cause instability in RL with function approximation:

1. **Function approximation** (neural network instead of table)
2. **Bootstrapping** (using estimated values to update other estimates — the target network trick)
3. **Off-policy learning** (learning from data generated by a different policy — the replay buffer)

Any two of three are fine. All three together can diverge. DQN has all three.

**The target network and replay buffer are mitigations, not solutions.** They reduce instability but don't eliminate it. This is why DQN training can collapse after initial success — and why it took until 2015 to make neural Q-learning work at all.

### 9.3 UCB and Regret Bounds

The exploration bonus in MCTS uses the **Upper Confidence Bound (UCB1)** formula:

> UCT(node) = Q(node)/N(node) + c * sqrt(ln(N(parent)) / N(node))

This comes from the **multi-armed bandit** literature. UCB1 achieves **logarithmic regret** — the accumulated loss from not always picking the best action grows as O(log n), which is provably optimal.

**Connection to MCTS:** Each child of a node is treated as an "arm" of a bandit. UCB1 balances exploring rarely-visited moves with exploiting known-good moves. The theoretical guarantee ensures that MCTS converges to the minimax value with enough simulations.

### 9.4 Policy Gradient Convergence

The policy gradient theorem gives an **unbiased gradient estimate**, meaning:

> E[estimated gradient] = true gradient

With enough samples and a small enough learning rate, policy gradient methods converge to a **local optimum** (not necessarily global). The policy space is non-convex, so global optimality is not guaranteed.

**PPO's clipping** provides a practical guarantee: the KL divergence between consecutive policies is bounded, preventing catastrophic policy collapse.

### 9.5 Why Self-Play Works

Self-play creates a non-stationary training distribution — the opponent keeps getting better. Why doesn't this cause divergence?

**Empirical observation:** Self-play creates a natural curriculum. Early in training, both players are weak, so the games are simple. As both improve, the games become more complex. This progressive difficulty is analogous to curriculum learning.

**Theoretical concern:** The policy can cycle (A beats B, B beats C, C beats A — like rock-paper-scissors). AlphaGo Zero mitigates this by evaluating new networks against the *current best* and only promoting them if they win decisively (>55%).

---

## Module 10: Software Engineering at Scale

### 10.1 The Self-Play Infrastructure

Building a system like AlphaGo Zero requires solving several distributed systems problems:

**Data generation:** Thousands of parallel self-play games, each using the current best neural network for MCTS. This is a classic producer-consumer architecture:
- **Producers:** Self-play workers generating game data
- **Consumer:** Training pipeline consuming game data
- **Shared state:** The current best network (read by all workers)

**Game data pipeline:**
1. Self-play workers store completed games in a shared buffer
2. Training workers sample games from the buffer
3. Training produces a candidate network
4. Evaluation: candidate vs. current best (400 games)
5. If candidate wins >55%, promote it
6. Update the network served to self-play workers

### 10.2 Reproducibility Challenges

RL systems are notoriously difficult to reproduce:

- **Random seeds propagate differently** across hardware configurations
- **Floating-point non-determinism** in GPU operations (different reduction orders)
- **Distributed timing** introduces non-deterministic data ordering
- **Hyperparameter sensitivity** — small changes can cause large performance differences

**Mitigations:**
- Fix random seeds everywhere possible
- Log everything (our JSONL logging approach)
- Use deterministic GPU operations where available (at a speed cost)
- Report results as mean +/- standard deviation over multiple seeds
- Checkpoint frequently (our eval_every_steps approach)

### 10.3 Evaluation Infrastructure

How do you know if your agent is improving?

**Elo rating:** A relative skill rating system where the probability of player A beating player B is:

> P(A beats B) = 1 / (1 + 10^((Elo_B - Elo_A) / 400))

A 400-Elo difference means the stronger player wins ~91% of the time.

**Self-play Elo tracking:** Play each new network version against previous versions. Track Elo over training time. This is how AlphaGo Zero's training curves are presented.

**External benchmarks:** Play against known-strength opponents:
- For Go: play against GNU Go, Pachi, Fuego, then human professionals
- For chess: play against Stockfish at various depths
- For Atari: compare against human scores and previous algorithms

### 10.4 The Full System Architecture

```
+--------------------+     +-------------------+
|  Self-Play Workers |     |  Evaluation Arena  |
|  (many CPUs/GPUs)  |     |  (candidate vs.    |
|  - Current best    |     |   current best)    |
|  - MCTS + network  |     |  - 400 games       |
|  - Generate games  |     |  - Promote if >55% |
+--------+-----------+     +---------+---------+
         |                            |
         v                            |
+--------+-----------+                |
|   Game Data Buffer |                |
|   (shared memory)  |                |
+--------+-----------+                |
         |                            |
         v                            |
+--------+-----------+     +----------+---------+
|  Training Pipeline |     |  Model Repository  |
|  (GPU cluster)     |---->|  - Best network    |
|  - Sample games    |     |  - Candidate       |
|  - Update network  |     |  - History         |
+--------------------+     +--------------------+
```

### 10.5 Lessons for Software Engineers

Building game-playing AI systems teaches several general software engineering lessons:

1. **Observability is everything.** Without comprehensive logging and metrics, you're flying blind. Our JSONL logs, TensorBoard, eval metrics, and progress reporting are the minimum viable observability stack.

2. **Checkpoint early and often.** Neural network training is non-monotonic (our 1M collapse proves it). You need to be able to go back to the best version.

3. **Separate data generation from training.** The self-play workers and training pipeline should be independent systems with a clear interface (the game data buffer).

4. **Make evaluation deterministic and automated.** Scenario-based testing (our scenarios/) with clear pass/fail criteria is essential. "It looks like it's playing better" is not a metric.

5. **Version everything.** The model, the hyperparameters, the training data, the evaluation results. You need to be able to answer "what changed between version A and version B?"

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| **MDP** | Markov Decision Process — the mathematical framework for sequential decision-making |
| **Policy** | A mapping from states to actions (the agent's strategy) |
| **Value function** | Expected cumulative reward from a state or state-action pair |
| **Q-function** | Action-value function — Q(s,a) = expected return from state s, action a |
| **Bellman equation** | Recursive decomposition of value into immediate reward + discounted future value |
| **DQN** | Deep Q-Network — Q-learning with a neural network function approximator |
| **Replay buffer** | Memory storing past transitions, sampled randomly for training |
| **Target network** | Frozen copy of the network used to compute stable training targets |
| **Policy gradient** | Methods that directly optimize the policy (vs. learning values) |
| **Actor-Critic** | Architecture with a policy network (actor) and value network (critic) |
| **MCTS** | Monte Carlo Tree Search — builds a search tree guided by random/neural simulations |
| **UCB** | Upper Confidence Bound — exploration formula balancing exploit vs. explore |
| **Self-play** | Agent trains by playing against copies of itself |
| **ResNet** | Residual Network — deep network with skip connections |
| **TPU** | Tensor Processing Unit — Google's custom hardware with systolic arrays for matrix operations |
| **Systolic array** | 2D grid of multiply-accumulate units where data flows through in a wave pattern |
| **HBM** | High Bandwidth Memory — vertically stacked DRAM providing massive bandwidth for GPUs/TPUs |
| **Tensor Core** | NVIDIA specialized hardware unit that performs 4x4 matrix multiplies per clock cycle |
| **BFloat16** | Brain Floating Point 16-bit format — same exponent range as FP32, less mantissa precision |
| **Elo** | Rating system for relative skill comparison (400 Elo gap ≈ 91% win rate) |
| **Catastrophic forgetting** | Neural network loses previously learned skills when trained on new data distribution |
| **PUCT** | Predictor + UCT — AlphaGo's modified UCB formula using a neural network prior |

---

## Appendix B: Reading List (Primary Sources)

1. **Watkins & Dayan (1992)** — Q-learning convergence proof
2. **Mnih et al. (2015)** — "Human-level control through deep reinforcement learning" (DQN, Nature)
3. **Silver et al. (2016)** — "Mastering the game of Go with deep neural networks and tree search" (AlphaGo, Nature)
4. **Silver et al. (2017)** — "Mastering the game of Go without human knowledge" (AlphaGo Zero, Nature)
5. **Silver et al. (2018)** — "A general reinforcement learning algorithm that masters chess, shogi, and Go" (AlphaZero, Science)
6. **Schrittwieser et al. (2020)** — "Mastering Atari, Go, chess and shogi by planning with a learned model" (MuZero, Nature)
7. **Sutton & Barto (2018)** — "Reinforcement Learning: An Introduction" (2nd edition) — the textbook
8. **Schulman et al. (2017)** — "Proximal Policy Optimization Algorithms" (PPO)
