# Scenario: Player Status Tags Reflect True State

## Category
environment

## Preconditions
- `src/play/play_minipong.py` exists and is importable
- Play module exposes a testable game state class or controller

## Behavioral Expectation
The player status tag must accurately reflect who is currently controlling each paddle at all times:
- Human left: "Keyboard: Up:Q, Down:A"
- Human right: "Keyboard: Up:P, Down:L"
- Agent: "AI Agent"
- Debug mode agent: "Policy: <policy_name>"

Tags must update immediately when a takeover toggle occurs and survive game restarts.

## Evaluation Method
```bash
python -c "
from src.play.play_minipong import GameController

# Normal mode (no debug)
gc = GameController(debug=False)

# Both human initially
left_tag = gc.get_status_tag('left')
right_tag = gc.get_status_tag('right')
assert 'Keyboard' in left_tag, f'Left human tag should contain Keyboard, got: {left_tag}'
assert 'Up:Q' in left_tag, f'Left human tag should show Q key, got: {left_tag}'
assert 'Down:A' in left_tag, f'Left human tag should show A key, got: {left_tag}'
assert 'Keyboard' in right_tag, f'Right human tag should contain Keyboard, got: {right_tag}'
assert 'Up:P' in right_tag, f'Right human tag should show P key, got: {right_tag}'
assert 'Down:L' in right_tag, f'Right human tag should show L key, got: {right_tag}'

# Toggle left to agent
gc.toggle_agent('left')
left_tag = gc.get_status_tag('left')
assert left_tag == 'AI Agent', f'Left agent tag should be AI Agent, got: {left_tag}'
right_tag = gc.get_status_tag('right')
assert 'Keyboard' in right_tag, f'Right should still show Keyboard, got: {right_tag}'

# Toggle back to human — tag must revert
gc.toggle_agent('left')
left_tag = gc.get_status_tag('left')
assert 'Keyboard' in left_tag, f'Left should revert to Keyboard tag, got: {left_tag}'

# Restart — tags must persist state
gc.toggle_agent('right')
gc.restart()
right_tag = gc.get_status_tag('right')
assert right_tag == 'AI Agent', f'Right agent tag should survive restart, got: {right_tag}'

# Debug mode shows policy name
gc_debug = GameController(debug=True, checkpoint_path='checkpoint_50000.pt')
gc_debug.toggle_agent('left')
left_tag = gc_debug.get_status_tag('left')
assert 'Policy:' in left_tag, f'Debug agent tag should contain Policy:, got: {left_tag}'
assert 'checkpoint_50000' in left_tag, f'Debug tag should show checkpoint name, got: {left_tag}'

# Debug mode with no checkpoint falls back to random
gc_no_ckpt = GameController(debug=True)
gc_no_ckpt.toggle_agent('left')
left_tag = gc_no_ckpt.get_status_tag('left')
assert 'random' in left_tag.lower(), f'Debug tag without checkpoint should show random, got: {left_tag}'

print('PASS: player status tags accurately reflect true state in all modes')
"
```

## Pass Criteria
Script exits with code 0 and prints PASS message.

## Evidence Required
- stdout/stderr from the evaluation command
