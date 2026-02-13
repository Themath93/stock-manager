# Repository Guidelines

## Project Structure & Module Organization
- `stock_manager/`: main application package.
- `stock_manager/adapters/broker/kis/`: KIS API client, auth, token cache, and endpoint wrappers.
- `stock_manager/trading/`: order execution, risk, positions, rate limiting, and strategies.
- `stock_manager/monitoring/`, `stock_manager/persistence/`, `stock_manager/notifications/`, `stock_manager/cli/`: runtime services.
- `tests/unit/` and `tests/integration/`: automated tests; `tests/fixtures/` and `tests/factories/` provide test data/helpers.
- `scripts/`: utility tooling (for example `scripts/generate_kis_apis.py`, `scripts/fix_domestic_await.py`).
- `docs/` and `docs_raw/`: generated and source documentation/data for KIS APIs.
- Generated artifacts (`build/`, `dist/`, `htmlcov/`, `*.egg-info`) should not be edited manually.

## Build, Test, and Development Commands
- `./setup.sh`: bootstrap local environment and guided configuration.
- `python -m venv .venv && source .venv/bin/activate`: create and activate virtualenv.
- `pip install -e '.[dev,cli]'`: install project with dev and CLI dependencies.
- `stock-manager setup`: interactive `.env` setup wizard.
- `stock-manager doctor`: validate environment and KIS connectivity basics.
- `pytest tests/unit/`: run fast unit tests.
- `pytest -m integration -v`: run integration tests (requires external services like PostgreSQL/KIS).
- `pytest tests/`: run full suite with coverage gate.
- `uv build`: build distribution artifacts.

## Coding Style & Naming Conventions
- Python style: 4-space indentation, explicit type hints for new/changed public APIs.
- Lint/format baseline uses Ruff (`line-length = 100`, see `pyproject.toml`).
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Keep broker adapter code focused on transport; place business logic in domain/service layers.

## Testing Guidelines
- Framework: `pytest` with `pytest-cov` and `pytest-asyncio`.
- Test discovery is configured as:
  - files: `test_*.py`
  - classes: `Test*`
  - functions: `test_*`
- Coverage is enforced (`--cov-fail-under=80`) and HTML reports are generated in `htmlcov/`.
- Use markers (`integration`, `unit`, `slow`, `red/green/refactor`) consistently.

## Commit & Pull Request Guidelines
- Follow existing commit style: `feat:`, `fix:`, `docs:`, `chore:` (optionally scoped, e.g. `docs(sync): ...`).
- Avoid vague subjects (for example `commit`); state intent and affected area.
- PRs should include:
  - concise summary of behavior changes,
  - linked issue/SPEC when applicable,
  - test evidence (commands/results),
  - config or env var changes (`.env.example` updates if needed).

## Security & Configuration Tips
- Never commit secrets; keep credentials in `.env` only.
- Prefer paper trading (`KIS_USE_MOCK=true`) during development.
- Treat local token/cache/runtime files as local state, not source-controlled assets.
