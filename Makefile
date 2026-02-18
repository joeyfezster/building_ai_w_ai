.PHONY: deps lint typecheck test docker-build docker-smoke whitepapers-acquire whitepapers-verify env-smoke train-smoke eval-smoke verify-learning dashboard validate

deps:
	pip-compile requirements.in
	pip-compile requirements-dev.in
	pip install -r requirements.txt -r requirements-dev.txt

lint:
	ruff check .

typecheck:
	mypy src

test:
	pytest -q

docker-build:
	docker build -f infra/docker/Dockerfile.train --build-arg BASE_IMAGE=python:3.12-slim -t minipong-train .
	docker build -f infra/docker/Dockerfile.demo -t minipong-demo .

docker-smoke:
	docker run --rm minipong-train python -m src.train.train_dqn --help
	docker run --rm minipong-demo python -m src.train.record_video --help

whitepapers-acquire:
	python scripts/acquire_whitepapers.py

whitepapers-verify:
	python scripts/verify_whitepapers.py

env-smoke:
	python -c "from src.envs.minipong import MiniPongEnv; env=MiniPongEnv(); obs,_=env.reset(seed=0); assert obs.dtype.name=='uint8'; print(obs.shape)"

train-smoke:
	python -m src.train.train_dqn --config configs/dqn_minipong.yaml --run-id smoke_run

eval-smoke:
	python -m src.train.evaluate --run-id smoke_run --episodes 2 --seeds 1 2

verify-learning:
	python -m src.train.verify_learning --run-id smoke_run --min-return-gain -0.1 --min-hits-gain -0.1

dashboard:
	streamlit run src/dashboard/app.py

validate: lint typecheck test docker-build docker-smoke env-smoke whitepapers-verify
