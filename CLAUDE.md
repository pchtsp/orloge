# Project Conventions

## Testing

- Use `unittest` (not pytest) for writing and running unit tests.
- Run tests via: `uv run python -m unittest discover -s tests`

## Package Manager

- Always use `uv` for dependency management, package installation, and running tools.
- Do **not** manually activate the virtual environment; `uv run` handles it automatically.
- Install packages: `uv add <package>` (or `uv add --dev <package>` for dev-only tools)
- Sync dependencies: `uv sync`

## Linting and formatting

- Use **ruff** for linting and formatting (not black).
- Run: `uv run ruff check orloge tests` and `uv run ruff format orloge tests` (or `ruff format orloge tests --check` to only check).

## Type checking

- Use **ty** for type checking (not mypy or pyright).
- Run type checks via: `uv run ty check orloge tests`

## Commands

- Do not start commands with `cd` to move to the root directory of this project, you're already there.

# Verify After Every Change

After making any code change to the repo, run all three checks before considering the task done:

1. **Unit tests**: `uv run python -m unittest discover -s tests`
2. **Type checking**: `uv run ty check orloge tests`
3. **Linting and formatting**: `uv run ruff check orloge tests` and `uv run ruff format orloge tests --check`
