# Scenario: All Platform Symlinks Resolve

## Category
infrastructure

## Preconditions
- Repository has been restructured per `specs/package_restructure.md`

## Behavioral Expectation
All 5 platform-required symlinks exist, are symbolic links (not copies), and resolve to valid targets. The targets contain the expected content.

## Evaluation Method
```bash
python -c "
from pathlib import Path
import os
import sys

errors = []

symlinks = {
    '.claude/skills/pr-review-pack': '../../packages/pr-review-pack',
    '.claude/skills/factory-orchestrate': '../../packages/dark-factory',
    '.github/workflows/factory.yaml': '../../packages/dark-factory/workflows/factory.yaml',
    'packages/pr-review-pack/review-prompts': '../review-prompts',
    'packages/dark-factory/review-prompts': '../review-prompts',
}

for link_path, expected_target in symlinks.items():
    p = Path(link_path)
    if not p.exists():
        errors.append(f'Symlink does not exist: {link_path}')
        continue
    if not p.is_symlink():
        errors.append(f'Path exists but is NOT a symlink: {link_path}')
        continue
    actual_target = os.readlink(str(p))
    if actual_target != expected_target:
        errors.append(f'Symlink {link_path} points to {actual_target!r}, expected {expected_target!r}')
        continue
    # Verify the resolved target has content
    resolved = p.resolve()
    if not resolved.exists():
        errors.append(f'Symlink {link_path} resolves to non-existent path: {resolved}')

# Verify key files are accessible through symlinks
if Path('.claude/skills/pr-review-pack/SKILL.md').exists():
    content = Path('.claude/skills/pr-review-pack/SKILL.md').read_text()
    if len(content) < 100:
        errors.append('pr-review-pack SKILL.md through symlink is too short')
else:
    errors.append('Cannot read pr-review-pack SKILL.md through symlink')

if Path('.claude/skills/factory-orchestrate/SKILL.md').exists():
    content = Path('.claude/skills/factory-orchestrate/SKILL.md').read_text()
    if len(content) < 100:
        errors.append('factory-orchestrate SKILL.md through symlink is too short')
else:
    errors.append('Cannot read factory-orchestrate SKILL.md through symlink')

# Verify shared review prompts accessible from both packages
for pkg in ['pr-review-pack', 'dark-factory']:
    rp = Path(f'packages/{pkg}/review-prompts/code_health_review.md')
    if not rp.exists():
        errors.append(f'Cannot read code_health_review.md through {pkg} symlink')

if errors:
    for e in errors:
        print(f'  FAIL: {e}')
    sys.exit(1)
print('PASS: all 5 symlinks resolve correctly')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
