# Scenario: Package Directory Structure Exists

## Category
infrastructure

## Preconditions
- Repository has been restructured per `specs/package_restructure.md`

## Behavioral Expectation
The `packages/` directory contains the expected subdirectories and key files for both the PR review pack and the dark factory, plus the shared review-prompts directory.

## Evaluation Method
```bash
python -c "
from pathlib import Path
import sys

errors = []

# Shared review prompts
for f in ['code_health_review.md', 'security_review.md', 'test_integrity_review.md', 'adversarial_review.md']:
    p = Path('packages/review-prompts') / f
    if not p.exists():
        errors.append(f'Missing shared review prompt: {p}')

# PR review pack structure
for f in [
    'packages/pr-review-pack/SKILL.md',
    'packages/pr-review-pack/assets/template.html',
    'packages/pr-review-pack/scripts/generate_diff_data.py',
    'packages/pr-review-pack/scripts/render_review_pack.py',
    'packages/pr-review-pack/scripts/scaffold_review_pack_data.py',
    'packages/pr-review-pack/references/build-spec.md',
    'packages/pr-review-pack/references/data-schema.md',
    'packages/pr-review-pack/examples/zone-registry.example.yaml',
]:
    if not Path(f).exists():
        errors.append(f'Missing PR review pack file: {f}')

# Dark factory structure
for f in [
    'packages/dark-factory/SKILL.md',
    'packages/dark-factory/scripts/run_gate0.py',
    'packages/dark-factory/scripts/nfr_checks.py',
    'packages/dark-factory/scripts/check_test_quality.py',
    'packages/dark-factory/scripts/run_scenarios.py',
    'packages/dark-factory/scripts/compile_feedback.py',
    'packages/dark-factory/scripts/strip_holdout.py',
    'packages/dark-factory/scripts/restore_holdout.py',
    'packages/dark-factory/scripts/persist_decisions.py',
    'packages/dark-factory/prompts/factory_fix.md',
    'packages/dark-factory/workflows/factory.yaml',
    'packages/dark-factory/docs/dark_factory.md',
    'packages/dark-factory/docs/code_quality_standards.md',
]:
    if not Path(f).exists():
        errors.append(f'Missing dark factory file: {f}')

# License files
for pkg in ['packages/pr-review-pack', 'packages/dark-factory']:
    for f in ['LICENSE', 'NOTICE']:
        if not (Path(pkg) / f).exists():
            errors.append(f'Missing {f} in {pkg}')

if not Path('LICENSE').read_text().startswith('                                 Apache License'):
    errors.append('Root LICENSE is not Apache 2.0')

if not Path('NOTICE').exists():
    errors.append('Root NOTICE file missing')

if errors:
    for e in errors:
        print(f'  FAIL: {e}')
    sys.exit(1)
print('PASS: all package directories and key files exist')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
