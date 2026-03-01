# Scenario: Play Makefile Targets Exist

## Category
integration

## Preconditions
- Makefile exists at repo root

## Behavioral Expectation
The Makefile defines `play`, `play-debug`, and `play-agent-vs-agent` targets. Each target invokes the correct Python module with the expected arguments.

## Evaluation Method
```bash
python -c "
import re

with open('Makefile') as f:
    content = f.read()

# Check targets exist
for target in ['play:', 'play-debug:', 'play-agent-vs-agent:']:
    assert target in content, f'Missing Makefile target: {target}'

# Check play target runs the right module
assert 'src.play.play_minipong' in content, 'play target must run src.play.play_minipong'

# Check play-debug passes --debug flag
lines = content.split('\n')
in_debug_target = False
found_debug_flag = False
for line in lines:
    if line.startswith('play-debug:') or line.startswith('play-debug :'):
        in_debug_target = True
        continue
    if in_debug_target:
        if line.startswith('\t') or line.startswith(' '):
            if '--debug' in line:
                found_debug_flag = True
                break
        elif line.strip() and not line.startswith('\t') and not line.startswith(' '):
            break
assert found_debug_flag, 'play-debug target must pass --debug flag'

print('PASS: all play Makefile targets present and correct')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
