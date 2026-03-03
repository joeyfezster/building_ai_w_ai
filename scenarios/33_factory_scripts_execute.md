# Scenario: Factory Scripts Execute From New Location

## Category
infrastructure

## Preconditions
- Repository has been restructured per `specs/package_restructure.md`
- Factory scripts are at `packages/dark-factory/scripts/`

## Behavioral Expectation
Key factory scripts can be invoked from the repo root at their new `packages/dark-factory/scripts/` paths. They should accept `--help` without errors, confirming imports and REPO_ROOT detection work correctly.

## Evaluation Method
```bash
python -c "
import subprocess
import sys

errors = []

scripts_with_help = [
    'packages/dark-factory/scripts/run_gate0.py',
    'packages/dark-factory/scripts/run_scenarios.py',
    'packages/dark-factory/scripts/nfr_checks.py',
    'packages/dark-factory/scripts/compile_feedback.py',
    'packages/dark-factory/scripts/check_test_quality.py',
]

for script in scripts_with_help:
    result = subprocess.run(
        [sys.executable, script, '--help'],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        errors.append(f'{script} --help failed (exit {result.returncode}): {result.stderr[:200]}')

# Also verify run_gate0.py can import and find its sibling scripts
result = subprocess.run(
    [sys.executable, '-c', '''
import sys
sys.path.insert(0, \"packages/dark-factory/scripts\")
import importlib.util
spec = importlib.util.spec_from_file_location(\"run_gate0\", \"packages/dark-factory/scripts/run_gate0.py\")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
# Verify CHECKS list references resolve
from pathlib import Path
for name, cmd, desc in mod.CHECKS:
    script_path = cmd[1]  # Second element is the script path
    if not Path(script_path).exists():
        print(f\"FAIL: CHECKS entry {name} references non-existent {script_path}\")
        sys.exit(1)
print(\"PASS: all CHECKS script references resolve\")
'''],
    capture_output=True, text=True, timeout=30
)
if result.returncode != 0:
    errors.append(f'run_gate0.py CHECKS verification failed: {result.stderr[:200]}')

if errors:
    for e in errors:
        print(f'  FAIL: {e}')
    sys.exit(1)
print('PASS: factory scripts execute from new location')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
