# Factory Validation Strategy

How we validate the factory's own components and their integration.

## Component Inventory

| Component | Type | Location | Validated By |
|-----------|------|----------|-------------|
| Scenario runner | Script | `scripts/run_scenarios.py` | `tests/test_factory_run_scenarios.py` + lint + typecheck |
| Feedback compiler | Script | `scripts/compile_feedback.py` | `tests/test_factory_compile_feedback.py` + lint + typecheck |
| Factory orchestrator | Workflow | `.github/workflows/factory.yaml` | CI dry-run + manual trigger |
| Attractor prompt | Markdown | `.github/codex/prompts/factory_fix.md` | Human review + adversarial review |
| Adversarial review | Markdown | `.github/codex/prompts/adversarial_review.md` | Human review |
| Satisfaction dashboard | Streamlit | `src/dashboard/pages/factory.py` | lint + manual verification |
| Scenario files | Markdown | `scenarios/*.md` | Format validator in CI |
| Factory CI | Workflow | `.github/workflows/ci.yaml` (factory-self-test job) | Self-referential (runs on itself) |

## Validation Layers

### Layer 1: Static Analysis (Automated, Every Push)
- **ruff check** on all factory Python scripts
- **mypy** on factory scripts (with `--ignore-missing-imports`)
- **Scenario format validator** — ensures all `.md` files in `/scenarios/` have required sections
- **Factory integrity check** — verifies protected files exist and are referenced in CLAUDE.md

### Layer 2: Unit Tests (Automated, Every Push)
- `test_factory_run_scenarios.py` — 19 tests covering:
  - Scenario markdown parsing (7 tests)
  - Scenario execution with real bash commands (11 tests)
  - Dataclass serialization (1 test)
- `test_factory_compile_feedback.py` — 29 tests covering:
  - Results loading and missing file handling (3 tests)
  - CI log loading and truncation (3 tests)
  - Iteration counting (3 tests)
  - Feedback history loading (3 tests)
  - Root cause inference from error patterns (7 tests)
  - Feedback compilation output structure (9 tests)
  - End-to-end integration (1 test)

### Layer 3: Adversarial Review (Manual, Per PR)
- Review guidelines at `.github/codex/prompts/adversarial_review.md`
- Checks for: stam tests, gaming, architectural dishonesty, spec violations
- Applied to attractor output (product code), not to factory infrastructure

### Layer 4: Integration Testing (Manual, Pre-Factory-Crank)
- `make factory-local` — runs one full iteration without Codex
- Verifies: scenario discovery → execution → result JSON → feedback compilation
- This is the integration test for the factory pipeline

## What's NOT Tested (Known Gaps)

| Gap | Risk | Mitigation | When to Fix |
|-----|------|-----------|-------------|
| factory.yaml workflow logic | Can't unit test GH Actions | Manual trigger + review | Post-first-crank |
| Codex invocation | Requires API key + billing | Test with mock prompt first | First crank |
| Filesystem shuffle | Works on Linux (CI), untested race conditions | Sequential execution | Post-first-crank |
| Dashboard data display | Needs Streamlit runtime | Manual `make dashboard` | Post-first-crank |
| Adversarial review effectiveness | New, unproven | Track false negative rate | Ongoing |
| Factory workflow concurrency | Multiple factory runs on same branch | Lock via GH concurrency groups | Post-first-crank |

## Test Hygiene Rules

### For Factory Tests
1. **No mocking factory internals.** Tests import and exercise real functions.
2. **Use `tmp_path` fixtures** for file operations — never touch the real filesystem.
3. **Real bash execution** in scenario runner tests — subprocess.run, not mocked.
4. **Every assertion tests a meaningful property** — not just "doesn't crash."

### For Product Tests (Enforced by Anti-Gaming Rules)
1. No mocking the system under test.
2. No stub implementations (`return True`, `pass`, hardcoded lookup tables).
3. No patching away tested logic.
4. No test-only config shortcuts that trivialize behavior.

## How to Run Factory Validation Locally

```bash
# Full factory self-test
ruff check scripts/run_scenarios.py scripts/compile_feedback.py
mypy scripts/run_scenarios.py scripts/compile_feedback.py --ignore-missing-imports
pytest tests/test_factory_run_scenarios.py tests/test_factory_compile_feedback.py -v

# Integration test (no Codex)
make factory-local

# Dashboard manual check
make dashboard
# Navigate to "Factory" page in sidebar
```
