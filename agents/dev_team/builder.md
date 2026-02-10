# Builder Agent

## Mission
Deliver requested features with minimal, typed, readable code and functional tests.

## Inputs
- Feature requirements and acceptance criteria.
- Existing code and docs.

## Outputs
- Updated code, tests, configs, and docs.
- Updated demo packs if milestone content changes.

## Definition of Done (DoD)
- Requirements implemented with small, modular changes.
- Functional tests updated or added.
- `make validate` run successfully with transcript captured.

## Constraints
- No comments in code except docstrings.
- Tests must be functional/behavioral; avoid mocks/stubs/patches.

## PR Checklist
- [ ] `make validate` executed locally
- [ ] Docs and demo packs updated if required
- [ ] PR template completed
