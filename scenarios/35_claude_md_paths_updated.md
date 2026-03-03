# Scenario: CLAUDE.md Paths Updated to Package Locations

## Category
infrastructure

## Preconditions
- Repository has been restructured per `specs/package_restructure.md`
- CLAUDE.md has been updated with new paths

## Behavioral Expectation
CLAUDE.md references factory scripts and infrastructure at their new `packages/` locations. The Factory-Protected Files list uses `packages/dark-factory/scripts/` paths. The stale "6 Gate 0 agents" description is replaced with the correct two-tier description.

## Evaluation Method
```bash
python -c "
from pathlib import Path
import sys

errors = []
content = Path('CLAUDE.md').read_text()

# Should NOT contain old paths
old_paths = [
    '/scripts/run_scenarios.py',
    '/scripts/compile_feedback.py',
    '/scripts/nfr_checks.py',
    '/scripts/check_test_quality.py',
    '/scripts/strip_holdout.py',
    '/scripts/restore_holdout.py',
    '/scripts/persist_decisions.py',
    '/.github/codex/prompts/factory_fix.md',
    '.claude/skills/factory-orchestrate/review-prompts/',
]

for old in old_paths:
    if old in content:
        errors.append(f'CLAUDE.md still contains old path: {old}')

# Should contain new paths
new_paths = [
    'packages/dark-factory/scripts/',
    'packages/review-prompts/',
    'packages/dark-factory/prompts/factory_fix.md',
]

for new in new_paths:
    if new not in content:
        errors.append(f'CLAUDE.md missing new path reference: {new}')

# Should NOT contain the stale '6 Gate 0 agents' or '5 tool agents + 1 adversarial'
if '6 Gate 0 agents' in content or '5 tool agents' in content:
    errors.append('CLAUDE.md still has stale Gate 0 agent count description')

# Should contain the correct two-tier description
if 'Tier 1' not in content or 'Tier 2' not in content:
    errors.append('CLAUDE.md missing Tier 1/Tier 2 Gate 0 description')

if errors:
    for e in errors:
        print(f'  FAIL: {e}')
    sys.exit(1)
print('PASS: CLAUDE.md paths updated to package locations')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
