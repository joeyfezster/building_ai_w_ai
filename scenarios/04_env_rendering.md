# Scenario: Environment Rendering

## Category
environment

## Preconditions
- MiniPong environment is importable
- Environment supports render_mode="rgb_array"

## Behavioral Expectation
When instantiated with render_mode="rgb_array", the environment produces renderable frames. Frames are numpy arrays with valid pixel data suitable for video recording.

## Evaluation Method
```bash
python -c "
from src.envs.minipong import MiniPongEnv
import numpy as np

env = MiniPongEnv(render_mode='rgb_array')
obs, _ = env.reset(seed=0)
frame = env.render()
assert frame is not None, 'render() returned None'
assert isinstance(frame, np.ndarray), f'Expected ndarray, got {type(frame)}'
assert frame.dtype == np.uint8, f'Expected uint8 frame, got {frame.dtype}'
assert len(frame.shape) == 3, f'Expected 3D frame (H, W, C), got {frame.shape}'
assert frame.shape[2] in (1, 3), f'Expected 1 or 3 channels, got {frame.shape[2]}'
# Verify frame is not all black (something is rendered)
assert frame.max() > 0, 'Frame is all black — nothing rendered'
print(f'PASS: rendering works, frame shape={frame.shape}, max_pixel={frame.max()}')
"
```

## Pass Criteria
Script exits with code 0. Frame has valid dimensions and is not all-black.

## Evidence Required
- stdout with frame shape and pixel range
