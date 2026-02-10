# Milestones

## Milestone 1: Dev-team agents as operating model

**Goal**: Run the project using explicit dev-team agent roles and workflows from day 1.

**Acceptance criteria**
- Dev-team agent prompts exist under `agents/dev_team` with missions, inputs, outputs, and definitions of done.
- PR workflow is documented and includes a mandatory `make validate` gate.
- Each milestone ships a new demo pack under `/demo_packs` with updated content.

## Milestone 2: Classic DQN Pong demo

**Goal**: Reproduce a classic DQN Pong result with reproducible artifacts.

**Acceptance criteria**
- Training smoke loop produces a checkpoint and TensorBoard metrics.
- Evaluation produces deterministic metrics and a recorded video.
- `/demo_packs/milestone_01` includes a full demo checklist, video script, and social copy.
