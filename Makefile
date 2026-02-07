.PHONY: lint test typecheck

lint:
	ruff check .

typecheck:
	mypy src

test:
	pytest -q
