.PHONY: lint typecheck test docker-build docker-smoke whitepapers-acquire whitepapers-verify emulator-smoke validate

lint:
	ruff check .

typecheck:
	mypy src

test:
	pytest

docker-build:
	docker build -f Dockerfile.demo -t retro-rl-demo .
	docker build -f Dockerfile.train --build-arg BASE_IMAGE=python:3.12-slim -t retro-rl-train .

docker-smoke:
	docker run --rm retro-rl-demo src.train.record_video --help
	docker run --rm retro-rl-train --help

whitepapers-acquire:
	python scripts/acquire_whitepapers.py

whitepapers-verify:
	python scripts/verify_whitepapers.py

emulator-smoke:
	python scripts/emulator_smoke.py

validate: lint typecheck test docker-build docker-smoke emulator-smoke
