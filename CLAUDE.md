# MiniPong RL System — Dark Factory

End-to-end proof that a reinforcement learning agent can learn Pong from pixels, built entirely by AI agents orchestrated through a convergence loop.

## First-Time Setup

After cloning, run these commands immediately:

```bash
make install-hooks    # REQUIRED: sets up git hooks (ruff + mypy on every commit)
make deps             # install Python dependencies
```

`make install-hooks` is non-negotiable — it's the local quality gate that catches issues before they hit CI. Without it, lint/typecheck failures only surface in CI, wasting iteration time.

## Operating Model

This repo is built by a **dark factory loop**, not by humans writing code. Code is treated as opaque weights — correctness is inferred exclusively from externally observable behavior, never from source inspection.

The loop: **Seed → Agent → Validate → Feedback → Repeat until satisfied.**

## Source of Truth

- `/specs/` — Component specifications. This is what the coding agent reads. The specs define what the system should do.
- `/scenarios/` — Behavioral holdout evaluation criteria. These are what the system is evaluated against. **Scenarios must NEVER be modified by the coding agent (Codex).** They are the holdout set — the agent never sees its own evaluation criteria.
- `/docs/dark_factory.md` — Full factory documentation: how the loop works, how to trigger it, how to write scenarios, when to escalate.

## Factory-Protected Files

The following files are **never touched by the Attractor (Codex)**. They are factory infrastructure, not product code. The Codex-facing version of this list lives in `.github/codex/prompts/factory_fix.md` — keep both in sync when adding protected files.

- `/scenarios/` — holdout evaluation criteria
- `/scripts/run_scenarios.py` — scenario evaluation runner
- `/scripts/compile_feedback.py` — feedback compiler
- `/.github/workflows/factory.yaml` — factory orchestrator
- `/.github/codex/prompts/factory_fix.md` — Codex prompt template
- `/specs/` — component specifications (read-only for Codex)
- `/agents/` — pre-factory agent definitions (reference only)
- `/scripts/strip_holdout.py` — holdout stripping script (isolation gate)
- `/scripts/restore_holdout.py` — holdout restoration script
- `/scripts/nfr_checks.py` — Gate 2 NFR checker
- `/scripts/check_test_quality.py` — Gate 0 test quality scanner
- `/.github/codex/prompts/adversarial_review.md` — Gate 0 adversarial review checklist
- `/docs/code_quality_standards.md` — universal quality standards
- `/CLAUDE.md` — this file

## Code Quality Standards

All code written in this repository — by Codex, Claude Code, or humans — must follow the standards in `docs/code_quality_standards.md`. This includes:
- Anti-vacuous test rules (no mocking the system under test, no stub assertions)
- Anti-gaming rules (no hardcoded lookup tables, no overfitting)
- Implementation honesty (real imports, real configs, real dependencies)
- Test hygiene and quality gates

These standards are enforced by Gate 0 (adversarial review), Gate 1 (lint/typecheck/test), Gate 2 (NFR checks), and the LLM-as-judge.

## Quick Commands

```bash
make install-hooks         # set up git hooks (ruff + mypy on every commit, no virtualenv needed)
make validate              # lint + typecheck + test + docker-build + docker-smoke + env-smoke
make run-scenarios         # run holdout scenario evaluation
make compile-feedback      # compile validation results into feedback markdown
make nfr-check             # run Gate 2 NFR checks (code quality, complexity, dead code, security)
make factory-local         # run one factory iteration locally (Gate 1 → Gate 2 → Gate 3 → feedback)
make factory-status        # show current iteration count and satisfaction score
```

## Human Decision Log

- `/ProjectLeadAsks.md` — Open questions and decisions requiring the project lead's input. **Check this file at every session start.** Update it when questions are resolved or new ones arise. This file survives context compaction — it's the canonical list of what's pending.

## Stack

- Python 3.12, pip-tools for dependency management
- PyTorch, Gymnasium, NumPy for RL
- ruff + mypy + pytest for quality
- GitHub Actions for CI and validation
- OpenAI Codex as the non-interactive coding agent (attractor)
- Claude Code as factory orchestrator (skill: `/factory-orchestrate`)
- PR review pack generator (skill: `/pr-review-pack`) — `.claude/skills/pr-review-pack/` contains the review pack generation skill with template, scripts, and reference docs
