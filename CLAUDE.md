# Repository Guidelines

## Project Structure & Module Organization
- `stock_manager/`: main application package.
- `stock_manager/adapters/broker/kis/`: KIS API client, auth, token cache, and endpoint wrappers.
- `stock_manager/trading/`: order execution, risk, positions, rate limiting, and strategies.
- `stock_manager/monitoring/`, `stock_manager/persistence/`, `stock_manager/notifications/`, `stock_manager/cli/`: runtime services.
- `tests/unit/` and `tests/integration/`: automated tests; `tests/fixtures/` and `tests/factories/` provide test data/helpers.
- `scripts/`: utility tooling (for example `scripts/generate_kis_apis.py`, `scripts/fix_domestic_await.py`).
- `docs/`: repository documentation, including [docs/knowledge-map.md](docs/knowledge-map.md), [docs/runtime-trading-guardrails.md](docs/runtime-trading-guardrails.md), [docs/quality-gates.md](docs/quality-gates.md), [docs/harness-engineering-plan.md](docs/harness-engineering-plan.md), [docs/harness-week1-execution-plan.md](docs/harness-week1-execution-plan.md), and [docs/adr/README.md](docs/adr/README.md).
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
- Coverage is enforced (`--cov-fail-under=85`) and HTML reports are generated in `htmlcov/`.
- Use markers (`integration`, `unit`, `slow`, `red/green/refactor`) consistently.

## Git Workflow
- 변경사항 push 전에 반드시 `pytest --cov --cov-fail-under=85 -q`를 실행하여 커버리지 85% 이상 확인 후 push할 것. CI에서 커버리지 실패가 발견되면, 즉시 로컬에서 커버리지 갭을 수정하고 모든 CI 게이트(lint, test, coverage)를 한 번에 통과시킬 것.
- merge 시 branch protection이 블로킹하면 `--admin` 플래그로 우회. 사용자에게 묻지 말고 바로 적용할 것.
- ship 워크플로우: test+coverage 통과 → commit(conventional) → push → PR 생성 → merge. 이 전체 플로우를 `/ship` 스킬로 일괄 실행 가능.

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
- Engine-managed market-hours policy by mode is documented in [docs/runtime-trading-guardrails.md](docs/runtime-trading-guardrails.md).
- Treat local token/cache/runtime files as local state, not source-controlled assets.

## CI/CD Policy
- CI 실패 시 1차 오류만 보지 말고, 커버리지 게이트(`--cov-fail-under=85`)도 함께 확인한다.
- push 전에 반드시 로컬에서 테스트와 커버리지를 통과시킨다:
  `uv run pytest tests/unit tests/fixtures --cov=stock_manager --cov-fail-under=85 -q`
- ruff check도 push 전 통과 필수: `uv run ruff check`
- 코드 변경 시 관련 테스트를 추가하거나 갱신한다 (새 기능 → 테스트 추가, 버그 수정 → 재현 테스트).
