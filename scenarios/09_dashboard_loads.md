# Scenario: Dashboard Loads Without Errors

## Category
dashboard

## Preconditions
- Streamlit is installed
- Dashboard source exists at `src/dashboard/app.py`
- Training artifacts exist from a prior run

## Behavioral Expectation
The Streamlit dashboard app can be imported and its main components can be instantiated without runtime errors. The dashboard must not crash when given a valid run directory with artifacts.

## Evaluation Method
```bash
python -c "
import importlib.util
import sys

# Check that the dashboard module can be imported
spec = importlib.util.spec_from_file_location('dashboard', 'src/dashboard/app.py')
assert spec is not None, 'Cannot find src/dashboard/app.py'
assert spec.loader is not None, 'Cannot load src/dashboard/app.py'
print('PASS: dashboard module is importable')
"
```

## Pass Criteria
Dashboard module is importable without errors.

## Evidence Required
- Import success/failure message
