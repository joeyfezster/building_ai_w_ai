# Scenario: Play Module Importable

## Category
integration

## Preconditions
- `src/play/play_minipong.py` exists
- pygame is installed

## Behavioral Expectation
The play module is importable without side effects (no window opened on import). It must expose the main entry point and import game env + agent dependencies cleanly.

## Evaluation Method
```bash
python -c "
import src.play.play_minipong as play
assert hasattr(play, 'main'), 'play_minipong must have a main() function'
print('PASS: play module imports cleanly')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message. No pygame window opened.

## Evidence Required
- stdout/stderr from the evaluation command
