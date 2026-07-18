# Contributing to Project Monolith

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Set up the development environment:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
make dev-install
```

## Development Workflow

### Code Style
- All Python code follows the rules configured in `pyproject.toml` (ruff + mypy)
- Run `make lint` before committing
- Run `make format` to auto-format
- Run `make typecheck` to verify types
- Run `make test` to run tests

### Pre-commit
Install pre-commit hooks before your first commit:
```bash
pre-commit install
```
Hooks automatically run ruff, mypy, and file checks on staged changes.

### Commit Messages
Use Conventional Commits format:
```
feat: add whale wallet tracking
fix: resolve price alert off-by-one
refactor: extract db_retry to core/database
docs: add CHANGELOG
```

Allowed types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `style`.

## Pull Request Process

1. Ensure all CI checks pass (lint, typecheck, test, coverage)
2. Update `CHANGELOG.md` under the `Unreleased` section
3. Request review from a maintainer
4. Squash-merge into `main`

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful, constructive, and inclusive.
