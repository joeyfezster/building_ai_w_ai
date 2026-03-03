# Scenario: Old File Locations Are Cleaned Up

## Category
infrastructure

## Preconditions
- Repository has been restructured per `specs/package_restructure.md`

## Behavioral Expectation
Files that were moved to `packages/` no longer exist at their old locations (as real files). The old locations may exist as symlinks if they are one of the 5 platform-required symlinks. The superseded `adversarial_review.md` in `.github/codex/prompts/` is deleted.

## Evaluation Method
```bash
python -c "
from pathlib import Path
import sys

errors = []

# These files should NOT exist as real files at old locations
# (they may exist as symlinks if they're platform-required)
must_be_gone = [
    'scripts/run_gate0.py',
    'scripts/nfr_checks.py',
    'scripts/check_test_quality.py',
    'scripts/run_scenarios.py',
    'scripts/compile_feedback.py',
    'scripts/strip_holdout.py',
    'scripts/restore_holdout.py',
    'scripts/persist_decisions.py',
    'docs/dark_factory.md',
    'docs/code_quality_standards.md',
    '.github/codex/prompts/adversarial_review.md',
]

for f in must_be_gone:
    p = Path(f)
    if p.exists() and not p.is_symlink():
        errors.append(f'File still exists at old location (should be moved): {f}')

# These should exist as symlinks, NOT as real directories
symlink_dirs = [
    '.claude/skills/pr-review-pack',
    '.claude/skills/factory-orchestrate',
]

for d in symlink_dirs:
    p = Path(d)
    if p.exists() and not p.is_symlink():
        errors.append(f'Directory exists as real dir (should be symlink): {d}')
    elif not p.exists():
        errors.append(f'Symlink does not exist: {d}')

# .github/workflows/factory.yaml should be a symlink
p = Path('.github/workflows/factory.yaml')
if p.exists() and not p.is_symlink():
    errors.append('factory.yaml exists as real file (should be symlink)')

# Product scripts should still exist
product_scripts = [
    'scripts/acquire_whitepapers.py',
    'scripts/verify_whitepapers.py',
    'scripts/package_artifacts.py',
    'scripts/create_postmerge_issues.py',
]
for f in product_scripts:
    if not Path(f).exists():
        errors.append(f'Product script was accidentally removed: {f}')

# .github/codex/prompts/ should be empty or contain only factory_fix.md (if not moved)
codex_dir = Path('.github/codex/prompts')
if codex_dir.exists():
    remaining = list(codex_dir.glob('*'))
    for r in remaining:
        if r.name not in ['.gitkeep']:  # allow .gitkeep
            errors.append(f'Unexpected file in old codex prompts dir: {r}')

if errors:
    for e in errors:
        print(f'  FAIL: {e}')
    sys.exit(1)
print('PASS: old file locations cleaned up, product scripts intact')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
