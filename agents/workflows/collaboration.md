# Collaboration Workflow

## Scope

Use this workflow for every PR, regardless of size.

## Steps

1) Pick the primary dev-team agent role for the change.
2) Capture requirements and acceptance criteria.
3) Implement changes with small modules, type hints, and docstrings.
4) Update docs and demo packs when required.
5) Run `make validate` and capture command output in the PR template.
6) Request review and ensure all checklist items are satisfied.

## Required validations

- `make validate` must pass locally before marking a PR ready.
- Emulator smoke and whitepapers verify must be green or explicitly documented.
