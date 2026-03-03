# Scenario: Lint and Typecheck Pass

## Category
integration

## Preconditions
- ruff and mypy are installed
- `make lint` and `make typecheck` targets exist

## Behavioral Expectation
The codebase passes ruff linting and mypy type checking without errors. This is Layer 1 validation — if these fail, behavioral scenarios are not evaluated.

## Evaluation Method
```bash
make lint 2>&1; LINT_EXIT=$?
make typecheck 2>&1; TYPE_EXIT=$?
if [ $LINT_EXIT -eq 0 ] && [ $TYPE_EXIT -eq 0 ]; then
    echo "PASS: lint and typecheck both pass"
else
    echo "FAIL: lint=$LINT_EXIT, typecheck=$TYPE_EXIT"
    exit 1
fi
```

## Pass Criteria
Both `make lint` and `make typecheck` exit with code 0.

## Evidence Required
- stdout/stderr from both commands
- Exit codes
