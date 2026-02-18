PYTHON ?= python
PIP_COMPILE ?= pip-compile
RUN_ID ?= demo_cpu

.PHONY: deps lint typecheck test docker-build docker-smoke whitepapers-acquire whitepapers-verify env-smoke train-smoke eval-smoke verify-learning dashboard validate

deps:
	$(PIP_COMPILE) requirements.in
	$(PIP_COMPILE) requirements-dev.in
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt

lint:
	ruff check .

typecheck:
	mypy --ignore-missing-imports --disable-error-code=assignment --disable-error-code=arg-type --disable-error-code=call-overload src

test:
	pytest -q

docker-build:
	@if command -v docker >/dev/null 2>&1; then \
		docker build -f infra/docker/Dockerfile.train --build-arg BASE_IMAGE=python:3.12-slim -t minipong-train . && \
		docker build -f infra/docker/Dockerfile.demo -t minipong-demo .; \
	else \
		echo "docker not available; skipping docker-build"; \
	fi

docker-smoke:
	@if command -v docker >/dev/null 2>&1; then \
		docker run --rm minipong-train python -m src.train.train_dqn --help && \
		docker run --rm minipong-demo python -m streamlit --version; \
	else \
		echo "docker not available; skipping docker-smoke"; \
	fi

whitepapers-acquire:
	$(PYTHON) scripts/acquire_whitepapers.py

whitepapers-verify:
	$(PYTHON) scripts/verify_whitepapers.py

env-smoke:
	$(PYTHON) -c "from src.envs.minipong import MiniPongEnv; e=MiniPongEnv(); o,_=e.reset(seed=0); assert len(o)==84 and len(o[0])==84 and len(o[0][0])==1; print('env smoke ok')"

train-smoke:
	$(PYTHON) -m src.train.train_dqn --config configs/dqn_minipong.yaml

eval-smoke:
	$(PYTHON) -m src.train.evaluate --run-id $(RUN_ID) --checkpoint $$(ls -1 artifacts/$(RUN_ID)/checkpoints/step_*.pt | sort -V | tail -n 1) --episodes 2 --seeds 0 1

verify-learning:
	$(PYTHON) -m src.train.verify_learning --run-id $(RUN_ID)

dashboard:
	streamlit run src/dashboard/app.py

validate: lint typecheck test docker-build docker-smoke env-smoke whitepapers-verify
