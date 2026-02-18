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
	mypy --ignore-missing-imports src

test:
	pytest -q

docker-build:
	docker build -f infra/docker/Dockerfile.train --build-arg BASE_IMAGE=python:3.12-slim -t minipong-train .
	docker build -f infra/docker/Dockerfile.demo -t minipong-demo .

docker-smoke:
	docker run --rm minipong-train python -m src.train.train_dqn --help
	docker run --rm minipong-demo python -m streamlit --version

whitepapers-acquire:
	$(PYTHON) scripts/acquire_whitepapers.py

whitepapers-verify:
	$(PYTHON) scripts/verify_whitepapers.py

env-smoke:
	$(PYTHON) -c "from src.envs.minipong import MiniPongEnv; e=MiniPongEnv(); o,_=e.reset(seed=0); assert o.shape==(84,84,1); print('env smoke ok')"

train-smoke:
	$(PYTHON) -m src.train.train_dqn --config configs/dqn_minipong.yaml

eval-smoke:
	$(PYTHON) -m src.train.evaluate --run-id $(RUN_ID) --checkpoint artifacts/$(RUN_ID)/checkpoints/step_1200.pt --episodes 2 --seeds 0 1

verify-learning:
	$(PYTHON) -m src.train.verify_learning --run-id $(RUN_ID)

dashboard:
	streamlit run src/dashboard/app.py

validate: lint typecheck test docker-build docker-smoke env-smoke whitepapers-verify
