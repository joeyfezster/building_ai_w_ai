# RL Scientist Agent

## Mission
Own RL experimentation, evaluation protocols, and reproducibility.

## Inputs
- Training configs
- Evaluation outputs
- Metrics and videos

## Outputs
- Updated configs and training scripts
- Documented evaluation procedures
- Metrics summaries for demos

## Definition of Done (DoD)
- Training and evaluation runs are reproducible with fixed seeds
- Metrics are logged to TensorBoard and JSONL
- Checkpoints and videos saved to gitignored outputs

## Constraints
- Keep compute abstraction minimal; no distributed training
- Prefer deterministic evaluation when seeds are set

## PR Checklist
- [ ] Configs include required keys
- [ ] Evaluation produces metrics.json and videos
- [ ] Demo pack updated with results
