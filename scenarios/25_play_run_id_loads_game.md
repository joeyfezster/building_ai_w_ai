# Scenario: Play --run-id Loads Visible Game Window

## Category
play

## Preconditions
- A trained checkpoint exists (from a prior training run)
- `play_minipong.py` accepts `--run-id`, `--left-agent`, `--right-agent`, `--debug` flags
- pygame is installed

## Behavioral Expectation
Running `python -m src.play.play_minipong --run-id <id> --left-agent --right-agent --debug` from a fresh command line opens a visible pygame window with two AI agents playing against each other using the trained checkpoint. The game must not crash on startup — the checkpoint's frame stacking must be compatible with the play environment.

## Evaluation Method
```bash
# Launch the game in the background, let it run for 3 seconds, then kill it
timeout 5 python -m src.play.play_minipong --run-id scenario_learn_cpu_10000 --left-agent --right-agent --debug 2>&1; EXIT_CODE=$?
# timeout returns 124 if the process was still running (good — means it didn't crash)
# exit 0 means it exited cleanly (also fine — e.g. if no display)
python -c "
exit_code = ${EXIT_CODE}
# 124 = timeout killed it (game was running successfully)
# 0 = clean exit
# anything else = crash
if exit_code in (0, 124):
    print(f'PASS: Game launched successfully (exit code {exit_code})')
else:
    print(f'FAIL: Game crashed with exit code {exit_code}')
    exit(1)
"
```

## Pass Criteria
The game process either runs until killed by timeout (exit 124) or exits cleanly (exit 0). It must NOT crash with a RuntimeError, ModuleNotFoundError, or shape mismatch.

## Evidence Required
- Exit code from timeout
- Any stderr output (should be empty or just warnings)
