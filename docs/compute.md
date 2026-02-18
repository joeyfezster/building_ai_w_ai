# Compute Guide

## Local CPU first
Use `make train-smoke` and `make eval-smoke` to validate correctness quickly.

## Remote with SkyPilot
Use `infra/compute/skypilot/train.yaml` and `infra/compute/skypilot/eval.yaml` for larger runs.

## Cost controls
- start with smoke configs
- use periodic checkpointing
- evaluate with fixed small episode sets before scaling
