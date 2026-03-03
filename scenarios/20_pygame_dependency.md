# Scenario: pygame Listed in Dependencies

## Category
integration

## Preconditions
- `requirements.in` exists at repo root

## Behavioral Expectation
pygame is listed as a dependency in `requirements.in` so the play module can be installed cleanly.

## Evaluation Method
```bash
python -c "
with open('requirements.in') as f:
    content = f.read().lower()
assert 'pygame' in content, 'pygame must be listed in requirements.in'
print('PASS: pygame is in requirements.in')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
