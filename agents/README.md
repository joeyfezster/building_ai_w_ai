# Agent Definitions (Pre-Factory Reference)

These agent role definitions were created before the dark factory pattern was adopted. In the factory model, a single **Attractor** (Codex) handles all coding — there is no multi-agent team.

## What's Here
- `dev_team/` — Role specs (architect, builder, reviewer, etc.) from the original multi-agent design
- `workflows/` — Collaboration and PR templates from the team-based approach

## How They're Used Now
The useful content from these files — validation guidelines, Definition of Done, hard constraints, PR checklists — has been consolidated into the Attractor's prompt template at `.github/codex/prompts/factory_fix.md`.

These files are kept as reference for the factory's design evolution. They are **not read by Codex** during factory iterations.

## Factory-Side Asset
This directory is factory infrastructure, not product code. It should NOT be modified by the Attractor.
