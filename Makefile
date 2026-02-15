.PHONY: install fmt lint type test sec all ci clean

install:
	pip install -e ".[dev]"

fmt:
	ruff format src/ tests/
	ruff check --fix src/ tests/

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

type:
	mypy src/aipea/

test:
	pytest tests/ -v --cov=src/aipea --cov-report=term-missing --cov-fail-under=75

sec:
	ruff check src/ tests/ --select S

all: fmt lint type test

ci: lint type test
