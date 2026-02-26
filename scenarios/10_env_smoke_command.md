# Scenario: env-smoke Makefile Target Works

## Category
integration

## Preconditions
- `make env-smoke` target exists in Makefile
- MiniPong environment is importable

## Behavioral Expectation
The `make env-smoke` command creates a MiniPong environment, resets it with a seed, and verifies the observation dtype is uint8. This is the quickest integration test that the environment is wired correctly.

## Evaluation Method
```bash
make env-smoke 2>&1; echo "EXIT_CODE=$?"
```

## Pass Criteria
Exit code 0. Observation shape printed to stdout.

## Evidence Required
- stdout/stderr from make env-smoke
- Exit code
