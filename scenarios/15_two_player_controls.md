# Scenario: Two-Player Keyboard Controls

## Category
environment

## Preconditions
- `src/play/play_minipong.py` exists and is importable
- Play module exposes an internal game state or testable action-mapping function

## Behavioral Expectation
The play module maps keyboard inputs to paddle actions correctly:
- Left player: Q=UP, A=DOWN, no key=STAY
- Right player: P=UP, L=DOWN, no key=STAY

The action mapping must be decoupled from the pygame event loop so it can be tested without a display.

## Evaluation Method
```bash
python -c "
from src.play.play_minipong import get_action_from_keys

# Simulate key states as a dict or set of pressed keys
# Left player: Q=UP(0), A=DOWN(1), neither=STAY(2)
assert get_action_from_keys('left', pressed={'q'}) == 0, 'Q should map to UP(0) for left'
assert get_action_from_keys('left', pressed={'a'}) == 1, 'A should map to DOWN(1) for left'
assert get_action_from_keys('left', pressed=set()) == 2, 'No key should map to STAY(2) for left'

# Right player: P=UP(0), L=DOWN(1), neither=STAY(2)
assert get_action_from_keys('right', pressed={'p'}) == 0, 'P should map to UP(0) for right'
assert get_action_from_keys('right', pressed={'l'}) == 1, 'L should map to DOWN(1) for right'
assert get_action_from_keys('right', pressed=set()) == 2, 'No key should map to STAY(2) for right'

print('PASS: two-player keyboard controls map correctly')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
