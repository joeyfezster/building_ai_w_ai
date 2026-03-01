.PHONY: deps install-hooks lint typecheck test docker-build docker-smoke whitepapers-acquire whitepapers-verify env-smoke train-smoke eval-smoke verify-learning dashboard play play-debug play-agent-vs-agent validate run-scenarios compile-feedback nfr-check factory-local factory-status persist-decisions

deps:
	pip-compile requirements.in
	pip-compile requirements-dev.in
	pip install -r requirements.txt -r requirements-dev.txt

install-hooks: ## Set up git hooks (ruff + mypy on every commit, no virtualenv needed)
	git config core.hooksPath .githooks
	@echo "✅ Git hooks installed from .githooks/"

# ── Quality ──────────────────────────────────────────────
lint:
	ruff check .

typecheck:
	mypy src

test:
	pytest -q

# ── Docker ───────────────────────────────────────────────
docker-build:
	docker build -f infra/docker/Dockerfile.train --build-arg BASE_IMAGE=python:3.12-slim -t minipong-train .
	docker build -f infra/docker/Dockerfile.demo -t minipong-demo .

docker-smoke:
	docker run --rm minipong-train python -m src.train.train_dqn --help
	docker run --rm minipong-demo python -m src.train.record_video --help

# ── Whitepapers ──────────────────────────────────────────
whitepapers-acquire:
	python scripts/acquire_whitepapers.py

whitepapers-verify:
	python scripts/verify_whitepapers.py

# ── Environment ──────────────────────────────────────────
env-smoke:
	python -c "from src.envs.minipong import MiniPongEnv; env=MiniPongEnv(); obs,_=env.reset(seed=0); assert obs.dtype.name=='uint8'; print(obs.shape)"

# ── Training ─────────────────────────────────────────────
train-smoke:
	python -m src.train.train_dqn --config configs/dqn_minipong.yaml --run-id smoke_run

eval-smoke:
	python -m src.train.evaluate --run-id smoke_run --episodes 2 --seeds 1 2

verify-learning:
	python -m src.train.verify_learning --run-id smoke_run --min-return-gain -0.1 --min-hits-gain -0.1

# ── Dashboard ────────────────────────────────────────────
dashboard:
	streamlit run src/dashboard/app.py


# ── Interactive Play ─────────────────────────────────────
play:
	python -m src.play.play_minipong

play-debug:
	python -m src.play.play_minipong --debug

play-agent-vs-agent:
	python -m src.play.play_minipong --left-agent --right-agent

# ── Validation ───────────────────────────────────────────
validate: lint typecheck test docker-build docker-smoke env-smoke whitepapers-verify

# ── Dark Factory ─────────────────────────────────────────
run-scenarios: ## Run holdout scenario evaluation
	python scripts/run_scenarios.py

compile-feedback: ## Compile validation results into feedback markdown
	python scripts/compile_feedback.py

nfr-check: ## Run Gate 2 NFR checks (non-blocking quality analysis)
	@mkdir -p artifacts/factory
	python scripts/nfr_checks.py --output artifacts/factory/nfr_results.json
	python scripts/nfr_checks.py

factory-local: ## Run one factory iteration locally (Gate 1 → Gate 2 → Gate 3 → feedback)
	@mkdir -p artifacts/factory
	@echo "=== Gate 1: lint + typecheck + test ==="
	@make lint 2>&1 | tee -a artifacts/factory/ci_output.log; \
	LINT_EXIT=$$?; \
	make typecheck 2>&1 | tee -a artifacts/factory/ci_output.log; \
	TYPE_EXIT=$$?; \
	make test 2>&1 | tee -a artifacts/factory/ci_output.log; \
	TEST_EXIT=$$?; \
	if [ $$LINT_EXIT -ne 0 ] || [ $$TYPE_EXIT -ne 0 ] || [ $$TEST_EXIT -ne 0 ]; then \
		echo "Gate 1 FAILED — skipping Gates 2-3"; \
		echo '{"total":0,"passed":0,"failed":0,"skipped":0,"satisfaction_score":0.0,"results":[],"timestamp":"N/A","gate1_failed":true}' > artifacts/factory/scenario_results.json; \
	else \
		echo ""; \
		echo "=== Gate 2: NFR checks (non-blocking) ==="; \
		make nfr-check 2>&1 | tee -a artifacts/factory/ci_output.log || true; \
		echo ""; \
		echo "=== Gate 3: Behavioral scenarios ==="; \
		python scripts/run_scenarios.py --timeout 180 || true; \
	fi
	@echo ""
	@echo "=== Compiling feedback ==="
	@python scripts/compile_feedback.py
	@echo ""
	@echo "=== Factory iteration complete ==="
	@make factory-status

persist-decisions: ## Persist PR decisions to cumulative log (usage: make persist-decisions PR=6)
	python scripts/persist_decisions.py --pr $(PR)

factory-status: ## Show current iteration count and satisfaction score
	@echo "--- Factory Status ---"
	@if [ -f artifacts/factory/iteration_count.txt ]; then \
		echo "Iteration: $$(cat artifacts/factory/iteration_count.txt)"; \
	else \
		echo "Iteration: 0 (not started)"; \
	fi
	@if [ -f artifacts/factory/scenario_results.json ]; then \
		python -c "import json; r=json.load(open('artifacts/factory/scenario_results.json')); print(f'Satisfaction: {r.get(\"satisfaction_score\", 0):.0%} ({r.get(\"passed\", 0)}/{r.get(\"total\", 0)} scenarios)')"; \
	else \
		echo "Satisfaction: N/A (no results yet)"; \
	fi
