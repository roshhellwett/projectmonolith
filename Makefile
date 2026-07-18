.PHONY: install dev-install lint format typecheck test coverage clean security-check

install:
	pip install -e .

dev-install:
	pip install -e . -r requirements-dev.txt

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy .

test:
	PYTHONPATH=src pytest

coverage:
	PYTHONPATH=src pytest --cov --cov-report=term-missing

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .coverage htmlcov *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

security-check:
	PYTHONPATH=src python src/security_check.py
