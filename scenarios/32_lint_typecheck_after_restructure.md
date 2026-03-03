# Scenario: Lint and Typecheck Pass After Restructuring

## Category
infrastructure

## Preconditions
- Repository has been restructured per `specs/package_restructure.md`
- All dependencies installed (`pip install -r requirements.txt -r requirements-dev.txt`)

## Behavioral Expectation
After restructuring, `ruff check .` and `mypy src` pass without errors. The restructuring should not introduce any lint violations or type errors. The factory scripts at their new `packages/` locations should also pass lint.

## Evaluation Method
```bash
ruff check . && mypy src --ignore-missing-imports && echo "PASS: lint and typecheck pass after restructuring"
```

## Pass Criteria
Both commands exit with code 0 and the PASS message is printed.

## Evidence Required
- stdout/stderr from the evaluation command
