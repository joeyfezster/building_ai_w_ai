# Scenario: Makefile Factory Targets Reference New Paths

## Category
infrastructure

## Preconditions
- Repository has been restructured per `specs/package_restructure.md`
- Makefile has been updated with new script paths

## Behavioral Expectation
The Makefile's factory-related targets (`run-scenarios`, `compile-feedback`, `nfr-check`, `persist-decisions`) reference scripts at their new `packages/dark-factory/scripts/` locations. The `make nfr-check` target executes successfully from the repo root.

## Evaluation Method
```bash
python -c "
from pathlib import Path
import subprocess
import sys

errors = []

makefile = Path('Makefile').read_text()

# Verify Makefile references new paths
old_refs = [
    'python scripts/run_scenarios.py',
    'python scripts/compile_feedback.py',
    'python scripts/nfr_checks.py',
    'python scripts/persist_decisions.py',
]

for ref in old_refs:
    if ref in makefile:
        errors.append(f'Makefile still contains old path: {ref}')

new_refs = [
    'python packages/dark-factory/scripts/run_scenarios.py',
    'python packages/dark-factory/scripts/compile_feedback.py',
    'python packages/dark-factory/scripts/nfr_checks.py',
    'python packages/dark-factory/scripts/persist_decisions.py',
]

for ref in new_refs:
    if ref not in makefile:
        errors.append(f'Makefile missing new path: {ref}')

if errors:
    for e in errors:
        print(f'  FAIL: {e}')
    sys.exit(1)
print('PASS: Makefile factory targets use new paths')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
