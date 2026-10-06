# Quality Tooling Setup

## Local checks

Run the following before submitting Sprint 13 work:

```bash
ruff check backend
mypy backend
pytest backend/tests
```

## Optional checks

```bash
vulture backend
```

## Tooling

The repository already includes the required development tools in requirements-dev.txt and pyproject.toml.
