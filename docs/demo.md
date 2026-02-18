# Demo steps

1. `make deps`
2. `make train-smoke`
3. `make eval-smoke`
4. `make verify-learning`
5. `python -m src.train.record_video --run-id demo_cpu --label random_baseline`
6. `python -m src.train.record_video --run-id demo_cpu --checkpoint artifacts/demo_cpu/checkpoints/step_300.pt --label early`
7. `python -m src.train.record_video --run-id demo_cpu --checkpoint artifacts/demo_cpu/checkpoints/step_600.pt --label mid`
8. `python -m src.train.record_video --run-id demo_cpu --checkpoint artifacts/demo_cpu/checkpoints/step_1200.pt --label late`
9. `python -m src.train.make_montage --run_id demo_cpu`
10. `make dashboard`
