# Scenario: verify-learning Command Exists and Runs

## Category
pipeline

## Preconditions
- `make verify-learning` target exists in Makefile
- Training artifacts exist from a prior run

## Behavioral Expectation
The `make verify-learning` command executes without import errors or crashes. It reads evaluation artifacts and produces a clear pass/fail verdict with supporting metrics. Even if learning hasn't occurred (smoke run too short), the command itself must be functional.

## Evaluation Method
```bash
python -m src.train.train_dqn --config configs/dqn_minipong.yaml --run-id scenario_verify_test 2>&1 && \
python -m src.train.verify_learning --run-id scenario_verify_test --min-return-gain -999 --min-hits-gain -999 2>&1; \
echo "EXIT_CODE=$?"
```

## Pass Criteria
The verify-learning command runs without Python import errors or unhandled exceptions. Exit code is 0 (with relaxed thresholds) or non-zero with a clear error message explaining why verification failed.

## Evidence Required
- stdout/stderr from verify-learning
- Exit code
