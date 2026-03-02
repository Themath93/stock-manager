# Stock Manager Knowledge Map

This document is the harness-first navigation map for agents and developers.

Scope policy:
- Include repository knowledge, module boundaries, runbook commands, and safety invariants.
- Do not change trading business logic while iterating on this map.

## 1) Entry Points

| Path | Role | Primary Dependencies | Fast Verification |
|---|---|---|---|
| `stock_manager/main.py` | CLI entrypoint and command router (`setup`, `doctor`, `run`, `trade`, `smoke`, `slack`) | `stock_manager/cli/*`, `stock_manager/slack_bot/*` | `uv run stock-manager --help` |
| `stock_manager/cli/setup_wizard.py` | Environment setup wizard | `.env`, config writers | `uv run stock-manager setup --skip-verify` |
| `stock_manager/cli/doctor.py` | Environment consistency diagnostics | `.env` parsing/validation | `uv run stock-manager doctor` |
| `stock_manager/cli/trading_commands.py` | Runtime command orchestration | engine, broker adapter, strategy options | `uv run stock-manager run --duration-sec 5 --skip-auth` |
| `stock_manager/engine.py` | Runtime orchestrator (execution, risk, monitoring, persistence) | trading, monitoring, persistence, notifications | `uv run pytest tests/unit/test_engine.py -q` |
| `docs/quality-gates.md` | Single matrix for lint/type/test/build enforcement | CI workflow, pyproject, AGENTS, README | `uv run pytest --cov=stock_manager --cov-fail-under=85` |
| `docs/harness-week1-execution-plan.md` | Week-1 execution checklist for harness improvements | knowledge-map, harness-engineering-plan, CI docs | `uv run stock-manager doctor` |
| `docs/adr/README.md` | Architecture decision index and ADR discovery entry | adr records, harness-engineering-plan | `uv run pytest tests/unit/` |

## 2) Module Boundary Map

| Layer | Path | Responsibility | Notes |
|---|---|---|---|
| CLI Layer | `stock_manager/main.py`, `stock_manager/cli/` | user command surface and argument parsing | no domain decisions here |
| Domain Trading | `stock_manager/trading/` | order/risk/positions/strategy/pipeline logic | should remain transport-agnostic where possible |
| Broker Adapter | `stock_manager/adapters/broker/kis/` | KIS REST/WebSocket transport and endpoint wrappers | external API integration boundary |
| Runtime Monitoring | `stock_manager/monitoring/` | price watch and reconciliation loops | background operational control |
| Persistence | `stock_manager/persistence/` | state save/load and startup recovery | local state truth synchronization |
| Notifications | `stock_manager/notifications/` | Slack/no-op notification formatting and dispatch | operational observability |
| Safety Gate | `stock_manager/qa/mock_gate.py` | mock-to-live promotion constraints | production safety boundary |

## 3) Runtime Flow Map

1. `stock-manager setup` writes and validates `.env`.
2. `stock-manager doctor` checks configuration format and readiness.
3. `stock-manager run` builds runtime context and starts `TradingEngine`.
4. `TradingEngine.start()` loads persisted state and reconciles with broker view.
5. Engine executes strategies/pipeline through trading services and broker adapter.
6. Monitoring and reconciliation loops enforce ongoing consistency and risk controls.

Reference diagram: `docs/execution-diagrams.md`.

## 4) Safety Invariants (Knowledge-Level)

These are map-level constraints that must stay visible to all agents:

- Mock-first operation: `KIS_USE_MOCK=true` is the default development path.
- Live trading requires explicit execution and promotion-gate pass.
- Runtime state persistence path is local and should never be committed as source.
- Credentials live in `.env` only; no secret material in git.

Primary references:
- `README.md`
- `AGENTS.md`
- `stock_manager/qa/mock_gate.py`

## 5) Verification Map

| Goal | Command |
|---|---|
| Unit suite (fast path) | `uv run pytest tests/unit/` |
| Full test suite | `uv run pytest` |
| Lint | `uv run ruff check` |
| Type check | `uv run mypy stock_manager` |
| Architecture boundary | `uv run lint-imports --config pyproject.toml` |
| Package build | `uv build` |

## 6) Current Documentation Drift Signals

- Coverage policy is unified at `--cov-fail-under=85` across CI, pytest defaults, and root docs.
- CI quality gate visibility is now mapped in `docs/quality-gates.md`; PR blocking path includes lint/type/unit+coverage/build.
- Nightly full-suite checks are scheduled in `.github/workflows/nightly-full-suite.yml`.
- Drift/GC scheduled checks are defined in `.github/workflows/drift-gc.yml`.

These are documentation and process visibility issues and should be fixed without changing trading logic.

## 7) Map Maintenance Rules

- Update this map when command surface or module boundaries change.
- Every new top-level operational module should be added to Section 2.
- Keep this file short and navigational; deep details belong in target module docs.
