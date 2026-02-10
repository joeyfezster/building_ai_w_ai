# Dev-Team Agents

Dev-team agents define how work is produced, reviewed, and shipped. They are distinct from play-agents (RL models) in `src/`.

## Roles

- **Builder**: implements features with tests and docs.
- **Reviewer**: validates correctness, runs `make validate`, and enforces standards.
- **RL Scientist**: owns training/evaluation protocol and metrics.
- **Demo Producer**: packages demos and demo packs.
- **Pack Writer**: maintains docs and demo packs.
- **Architect**: keeps the system modular and minimal.
- **DevOps/CI**: owns CI and container workflows.

## Workflow

Use the collaboration workflow in `agents/workflows/collaboration.md` and the PR template in `agents/workflows/pr_template.md`.
