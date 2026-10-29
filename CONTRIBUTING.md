# Contributing

Thanks for your interest in improving cqrs-framing.

## Development setup

- Python: 3.10+

```bash
pip install -r requirements-dev.txt
pip install -e .
```

## Running tests

```bash
pytest Tests/ -v
```

## Type checking

```bash
mypy src/cqrs_framing
```

## Code style

- Prefer small, focused changes.
- Keep public API changes explicit and documented.

## Pre-commit (recommended)

This repo supports pre-commit to run the same checks locally as CI.

```bash
pip install -r requirements-dev.txt
pre-commit install
pre-commit run --all-files
```

## Pull requests

- Add/adjust tests for behavior changes.
- Update CHANGELOG.md for user-visible changes.
