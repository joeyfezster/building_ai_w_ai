# Scenario: Agent Takeover Toggle Logic

## Category
environment

## Preconditions
- `src/play/play_minipong.py` exists and is importable
- Play module exposes a testable game state class or controller

## Behavioral Expectation
The agent takeover toggle works correctly:
1. Both sides start as human-controlled.
2. Toggling agent on a side switches it to AI control.
3. Toggling again switches it back to human control.
4. Both sides can be agent-controlled simultaneously.
5. State survives game restart (the toggle is not reset when R is pressed).

## Evaluation Method
```bash
python -c "
from src.play.play_minipong import GameController

gc = GameController()

# Both sides start as human
assert gc.get_controller('left') == 'human', 'Left should start as human'
assert gc.get_controller('right') == 'human', 'Right should start as human'

# Toggle left to agent
gc.toggle_agent('left')
assert gc.get_controller('left') == 'agent', 'Left should be agent after toggle'
assert gc.get_controller('right') == 'human', 'Right should still be human'

# Toggle right to agent (both agent)
gc.toggle_agent('right')
assert gc.get_controller('left') == 'agent', 'Left should still be agent'
assert gc.get_controller('right') == 'agent', 'Right should be agent after toggle'

# Toggle left back to human
gc.toggle_agent('left')
assert gc.get_controller('left') == 'human', 'Left should be human after second toggle'
assert gc.get_controller('right') == 'agent', 'Right should still be agent'

# Simulate restart — agent state must persist
gc.restart()
assert gc.get_controller('left') == 'human', 'Left should remain human after restart'
assert gc.get_controller('right') == 'agent', 'Right should remain agent after restart'

print('PASS: agent takeover toggle logic is correct')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
