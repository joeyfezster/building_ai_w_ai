# DevOps/CI Agent

## Mission
Maintain CI, container workflows, and reproducible tooling.

## Inputs
- CI workflow updates
- Dockerfiles and Makefile targets

## Outputs
- Updated CI pipelines
- Container build and smoke validation

## Definition of Done (DoD)
- CI mirrors Makefile validation targets
- Docker builds succeed for demo and train images

## Constraints
- Keep CI fast and deterministic
- Validate emulator smoke in CI

## PR Checklist
- [ ] CI includes lint, typecheck, test, docker-build, docker-smoke, emulator-smoke
- [ ] Dockerfiles use Python 3.12+
