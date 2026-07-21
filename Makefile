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
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['__pycache__', '.pytest_cache', '.mypy_cache', '.coverage', 'htmlcov', '*.egg-info']]" 2>/dev/null || true
	python -c "import pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]" 2>/dev/null || true

security-check:
	PYTHONPATH=src python src/security_check.py
