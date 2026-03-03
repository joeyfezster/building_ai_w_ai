# Scenario: No Stale Path References to Moved Files

## Category
infrastructure

## Preconditions
- Repository has been restructured per `specs/package_restructure.md`

## Behavioral Expectation
After restructuring, no files outside `packages/` should reference the old paths of moved factory scripts (e.g., `scripts/run_scenarios.py` without the `packages/dark-factory/` prefix). The only exceptions are: product scripts that were NOT moved (e.g., `scripts/acquire_whitepapers.py`), self-referential comments within the moved scripts themselves, and this scenario file.

## Evaluation Method
```bash
python -c "
import subprocess
import sys

# Factory scripts that moved from scripts/ to packages/dark-factory/scripts/
moved_scripts = [
    'scripts/run_scenarios.py',
    'scripts/compile_feedback.py',
    'scripts/nfr_checks.py',
    'scripts/check_test_quality.py',
    'scripts/run_gate0.py',
    'scripts/strip_holdout.py',
    'scripts/restore_holdout.py',
    'scripts/persist_decisions.py',
]

# Old paths that should no longer appear (outside packages/)
old_paths = [
    '.github/codex/prompts/factory_fix.md',
    '.claude/skills/factory-orchestrate/review-prompts/',
    '.claude/skills/factory-orchestrate/SKILL.md',
    '.claude/skills/pr-review-pack/SKILL.md',
]

errors = []

for script in moved_scripts:
    # Search for bare references to this script (not under packages/)
    result = subprocess.run(
        ['grep', '-rn', '--include=*.py', '--include=*.yaml', '--include=*.md',
         '--include=Makefile', '--include=*.toml',
         script, '.'],
        capture_output=True, text=True
    )
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        # Skip matches inside packages/ (these are correct new-path refs or self-refs)
        if '/packages/' in line:
            continue
        # Skip scenarios (holdout, not modified)
        if '/scenarios/' in line:
            continue
        # Skip this spec file
        if 'package_restructure.md' in line:
            continue
        # Skip artifacts
        if '/artifacts/' in line:
            continue
        # Skip git objects
        if '/.git/' in line:
            continue
        # Skip worktree copies
        if '/.claude/worktrees/' in line:
            continue
        # This is a stale reference
        errors.append(f'Stale reference to {script}: {line.strip()[:120]}')

for old_path in old_paths:
    result = subprocess.run(
        ['grep', '-rn', '--include=*.py', '--include=*.yaml', '--include=*.md',
         '--include=Makefile', '--include=*.toml',
         old_path, '.'],
        capture_output=True, text=True
    )
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        if '/packages/' in line or '/scenarios/' in line or 'package_restructure.md' in line:
            continue
        if '/artifacts/' in line or '/.git/' in line or '/.claude/worktrees/' in line:
            continue
        errors.append(f'Stale reference to {old_path}: {line.strip()[:120]}')

if errors:
    print(f'Found {len(errors)} stale path references:')
    for e in errors[:20]:  # Show first 20
        print(f'  FAIL: {e}')
    if len(errors) > 20:
        print(f'  ... and {len(errors) - 20} more')
    sys.exit(1)
print('PASS: no stale path references found outside packages/')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
