# Agent Instructions

## Mission
Deliver production-ready contributions for MiniPong RL milestone delivery.

## Inputs
- Product requirements and milestone docs
- Existing source code, tests, and artifacts

## Outputs
- Code changes with tests
- Updated docs and validation evidence

## Definition of Done (DoD)
- Functional requirements implemented
- Architectural consistency maintained
- Integration checks pass
- Required artifacts generated and linked

## Hard Constraints
- No proprietary ROM dependencies
- Policy consumes pixels only
- No PR is ready unless `make validate` and `make verify-learning` (where applicable) pass and outputs are attached as artifacts.

## PR Checklist
- [ ] Scope is complete
- [ ] Tests added/updated
- [ ] `make validate` passed
- [ ] `make verify-learning` passed (if training-related)
- [ ] Artifact paths documented
