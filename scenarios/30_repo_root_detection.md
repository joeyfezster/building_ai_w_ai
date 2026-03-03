# Scenario: REPO_ROOT Detection Works From Package Depth

## Category
infrastructure

## Preconditions
- Repository has been restructured per `specs/package_restructure.md`
- Factory scripts have been moved to `packages/dark-factory/scripts/`

## Behavioral Expectation
All factory scripts that previously used `Path(__file__).resolve().parent.parent` to find the repo root now use the `.git` sentinel walk-up pattern. This correctly finds the repo root regardless of the script's depth in the directory tree.

## Evaluation Method
```bash
python -c "
from pathlib import Path
import ast
import sys

errors = []

factory_scripts = [
    'packages/dark-factory/scripts/run_gate0.py',
    'packages/dark-factory/scripts/nfr_checks.py',
    'packages/dark-factory/scripts/check_test_quality.py',
    'packages/dark-factory/scripts/run_scenarios.py',
    'packages/dark-factory/scripts/compile_feedback.py',
    'packages/dark-factory/scripts/strip_holdout.py',
    'packages/dark-factory/scripts/restore_holdout.py',
    'packages/dark-factory/scripts/persist_decisions.py',
]

for script_path in factory_scripts:
    p = Path(script_path)
    if not p.exists():
        errors.append(f'Script not found: {script_path}')
        continue

    content = p.read_text()

    # Check that the old pattern is NOT present
    if '.parent.parent' in content and 'parent.parent' in content:
        # More precise: check if it's used for REPO_ROOT
        # Allow .parent.parent in other contexts (like Path(__file__).parent.parent / 'assets')
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'parent.parent' in line and ('REPO_ROOT' in line or 'repo_root' in line):
                # Check it's not the new pattern (which uses .parents not .parent.parent)
                if '.resolve().parent.parent' in line:
                    errors.append(f'{script_path}:{i} still uses old .parent.parent pattern for repo root')

    # Check that the .git sentinel pattern IS present
    if '(\".git\")' not in content and \"('.git')\" not in content and '/.git' not in content:
        if '_get_repo_root' not in content and 'get_repo_root' not in content:
            errors.append(f'{script_path} does not use .git sentinel pattern for repo root detection')

# Verify the detection actually works by importing and calling it
sys.path.insert(0, 'packages/dark-factory/scripts')
try:
    # Try to verify run_gate0 can find repo root
    import importlib.util
    spec = importlib.util.spec_from_file_location('run_gate0', 'packages/dark-factory/scripts/run_gate0.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    repo_root = mod.REPO_ROOT
    if not (repo_root / '.git').is_dir():
        errors.append(f'run_gate0.py REPO_ROOT={repo_root} does not contain .git')
    if not (repo_root / 'src').is_dir():
        errors.append(f'run_gate0.py REPO_ROOT={repo_root} does not contain src/')
except Exception as e:
    errors.append(f'Failed to import run_gate0.py and verify REPO_ROOT: {e}')

if errors:
    for e in errors:
        print(f'  FAIL: {e}')
    sys.exit(1)
print('PASS: REPO_ROOT detection uses .git sentinel and works from packages/ depth')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
