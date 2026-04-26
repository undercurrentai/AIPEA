.PHONY: install fmt lint type test sec all ci mut sbom score deps live adversarial adversarial-update-baseline

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

live:
	pytest tests/test_live.py -v

mut:
	mutmut run --paths-to-mutate src --simple-output

sbom:
	syft dir:. -o spdx-json > sbom.spdx.json

score:
	python tools/ci/generate_scorecard.py

deps:
	pip list --outdated 2>/dev/null || true

adversarial:
	pytest tests/test_adversarial.py -v -m adversarial

adversarial-update-baseline:
	python -m tests.test_adversarial --update-baseline
