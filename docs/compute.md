# Compute

## Local vs remote GPU

- **Local**: Use a local GPU when iterating quickly or collecting early demos.
- **Remote**: Use short-lived GPU instances for larger training runs.

## SkyPilot abstraction

We use a minimal SkyPilot YAML abstraction under `infra/compute/skypilot/` to keep training portable across providers. It is a stub for now and intentionally avoids distributed training.

## Suggested providers

- RunPod
- Lambda Labs
- Vast.ai
