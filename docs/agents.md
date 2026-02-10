# Agents Operating Model

## Two agent families

- **Play-agents**: RL policies that learn game control from pixels. These live under `src/` and include DQN, replay buffers, and environment wrappers.
- **Dev-team agents**: LLM instruction sets that define how work is produced and validated. These live under `agents/` and are required for every PR.

## PR workflow

1) Choose a dev-team agent role for the work (builder, reviewer, demo producer, etc.).
2) Follow the workflow in `agents/workflows/collaboration.md`.
3) Run `make validate` before marking the PR ready.
4) Use the PR template in `agents/workflows/pr_template.md` and include command transcripts.

## Engineering conventions

- Prefer small, typed modules with clear names.
- No comments in code except docstrings.
- Tests are functional/behavioral; avoid mocks/stubs/patches.
- Logging is JSONL for machines and readable console output for humans.
