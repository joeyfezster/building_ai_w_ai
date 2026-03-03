# Scenario: Full CPU Pipeline End-to-End

## Category
integration

## Preconditions
- All Python dependencies installed
- No GPU required
- MiniPong environment, training pipeline, evaluation, and verification all exist

## Behavioral Expectation
The complete pipeline runs on CPU: train (short smoke run) → evaluate → verify-learning (with relaxed thresholds). This proves the system is wired end-to-end and can produce artifacts from scratch.

## Evaluation Method
```bash
python -m src.train.train_dqn --config configs/dqn_minipong.yaml --run-id scenario_e2e 2>&1 && \
python -m src.train.evaluate --run-id scenario_e2e --episodes 2 --seeds 1 2 2>&1 && \
python -m src.train.verify_learning --run-id scenario_e2e --min-return-gain -999 --min-hits-gain -999 2>&1; \
echo "EXIT_CODE=$?"
```

## Pass Criteria
All three commands complete without unhandled exceptions. Exit code 0 for the full chain (with relaxed verification thresholds).

## Evidence Required
- stdout/stderr from each pipeline stage
- Final exit code
- Artifact directory listing
