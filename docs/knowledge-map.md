# Stock Manager Knowledge Map

This document is the harness-first navigation map for agents and developers.

Scope policy:
- Include repository knowledge, module boundaries, runbook commands, and safety invariants.
- Do not change trading business logic while iterating on this map.

## 1) Entry Points

| Path | Role | Primary Dependencies | Fast Verification |
|---|---|---|---|
| `stock_manager/main.py` | CLI entrypoint and command router (`setup`, `doctor`, `run`, `trade`, `smoke`, `verify`, `slack`) | `stock_manager/cli/*`, `stock_manager/slack_bot/*` | `uv run stock-manager --help` |
| `stock_manager/cli/setup_wizard.py` | Environment setup wizard | `.env`, config writers | `uv run stock-manager setup --skip-verify` |
| `stock_manager/cli/doctor.py` | Environment consistency diagnostics | `.env` parsing/validation | `uv run stock-manager doctor` |
| `stock_manager/cli/trading_commands.py` | Runtime command orchestration (`run` uses engine, `trade` can call broker direct) | engine, broker adapter, strategy options | `uv run stock-manager run --duration-sec 5 --skip-auth` |
| `stock_manager/cli/verify_commands.py` | Guarded live verification flow (`verify live-roundtrip`) with artifact capture | `doctor`, promotion gate, engine, KIS runtime, persistence | `uv run stock-manager verify live-roundtrip --help` |
| `stock_manager/slack_bot/app.py` | Slack `/sm` command router and response policy | `command_parser.py`, `session_manager.py`, Slack formatters | `uv run pytest tests/unit/test_slack_bot_app.py -q` |
| `stock_manager/slack_bot/session_manager.py` | Slack-managed engine lifecycle and live gate enforcement | trading CLI helpers, engine, Slack notifier | `uv run pytest tests/slack_bot/test_session_manager.py --no-cov -q` |
| `stock_manager/engine.py` | Runtime orchestrator (execution, risk, monitoring, persistence) | trading, monitoring, persistence, notifications | `uv run pytest tests/unit/test_engine.py -q` |
| `stock_manager/persistence/state.py` | Durable trading state schema and atomic persistence (`TradingState` v4) | trading models, recovery, engine | `uv run pytest tests/unit/test_state.py --no-cov -q` |
| `stock_manager/persistence/recovery.py` | Startup crash recovery and pending-order convergence from broker truth | state, KIS daily orders/balance, engine start | `uv run pytest tests/unit/test_recovery.py --no-cov -q` |
| `docs/runtime-trading-guardrails.md` | Authoritative map for engine-managed market-hours policy by mode | `engine.py`, `trading_commands.py`, engine tests | `uv run pytest tests/unit/test_engine.py -k 'market_hours' --no-cov -q` |
| `docs/quality-gates.md` | Single matrix for lint/type/test/build enforcement | CI workflow, pyproject, AGENTS, README | `uv run pytest --cov=stock_manager --cov-fail-under=85` |
| `docs/kis-endpoint-guardrails.md` | KIS endpoint drift incident runbook and prevention controls | `client.py`, KIS API wrappers, CI guard script | `uv run python scripts/validate_kis_endpoint_policy.py` |
| `docs/harness-week1-execution-plan.md` | Week-1 execution checklist for harness improvements | knowledge-map, harness-engineering-plan, CI docs | `uv run stock-manager doctor` |
| `docs/slack-sm-human/README.md` | Human operator guide for Slack `/sm` session control | Slack bot parser, session manager, operational policy | read-only doc |
| `docs/slack-sm-ai/README.md` | AI command-generation protocol for Slack `/sm` | Slack bot parser constraints and safety rules | read-only doc |
| `docs/adr/README.md` | Architecture decision index and ADR discovery entry | adr records, harness-engineering-plan | `uv run pytest tests/unit/` |

## 2) Module Boundary Map

| Layer | Path | Responsibility | Notes |
|---|---|---|---|
| CLI Layer | `stock_manager/main.py`, `stock_manager/cli/` | user command surface and argument parsing | no domain decisions here |
| Slack Control Surface | `stock_manager/slack_bot/` | `/sm` parsing, session lifecycle, Slack-specific UX | same engine policy, different command surface |
| Domain Trading | `stock_manager/trading/` | order/risk/positions/strategy/pipeline logic | should remain transport-agnostic where possible |
| Broker Adapter | `stock_manager/adapters/broker/kis/` | KIS REST/WebSocket transport and endpoint wrappers | external API integration boundary |
| Runtime Monitoring | `stock_manager/monitoring/` | price watch and reconciliation loops | background operational control |
| Persistence | `stock_manager/persistence/` | state save/load and startup recovery | local state truth synchronization |
| Notifications | `stock_manager/notifications/` | Slack/no-op notification formatting and dispatch | operational observability |
| Safety Gate | `stock_manager/qa/mock_gate.py` | mock-to-live promotion constraints | production safety boundary |

## 3) Runtime Flow Map

1. `stock-manager setup` writes and validates `.env`.
2. `stock-manager doctor` checks configuration format and readiness.
3. One of three control surfaces starts runtime:
   - `stock-manager run`
   - `stock-manager verify live-roundtrip`
   - Slack `/sm start`
4. `TradingEngine.start()` loads persisted state and reconciles with broker view.
5. Strategy/runtime paths submit orders into `pending_orders`; submission is not a fill.
6. Execution notice and reconciliation converge local state using broker truth.
7. Monitoring and reconciliation loops enforce ongoing consistency and risk controls.

Reference diagram: [execution-diagrams.md](execution-diagrams.md).

## 4) Safety Invariants (Knowledge-Level)

These are map-level constraints that must stay visible to all agents:

- Mock-first operation: `KIS_USE_MOCK=true` is the default development path. See [ADR-0001](adr/0001-mock-first-safety-gate.md).
- Endpoint authority isolation: wrapper modules must use relative `/uapi/...` paths, and runtime mode decides REST origin via `KISConfig.api_base_url`. See [ADR-0009](adr/0009-kis-endpoint-authority-and-mode-isolation.md).
- Engine-managed buy market-hours policy is live-only; mock bypasses the local block; direct `trade` execution is out of scope. See [runtime-trading-guardrails.md](runtime-trading-guardrails.md).
- Order submission and position state are separated: `order.submitted` is not `order.filled`, and positions open/close only from broker-confirmed execution or reconciliation evidence.
- Runtime convergence precedence is `execution notice > daily order > balance inference`; sell completion must not be inferred from balance-only disappearance.
- Live trading requires explicit execution and promotion-gate pass.
- `verify live-roundtrip` is the guarded path for collecting real payload evidence and proving state convergence on a live account.
- Runtime state persistence path is local and should never be committed as source.
- Credentials live in `.env` only; no secret material in git.

Primary references:
- [README.md](../README.md)
- [AGENTS.md](../AGENTS.md)
- `stock_manager/qa/mock_gate.py`
- [docs/slack-sm-human/README.md](slack-sm-human/README.md)
- [docs/slack-sm-ai/README.md](slack-sm-ai/README.md)

## 5) Verification Map

| Goal | Command |
|---|---|
| Unit suite (fast path) | `uv run pytest tests/unit/` |
| Engine state machine contract | `uv run pytest tests/unit/test_engine.py tests/unit/test_engine_notifications.py --no-cov -q` |
| Persistence + recovery contract | `uv run pytest tests/unit/test_state.py tests/unit/test_recovery.py --no-cov -q` |
| Live-payload parser/reconcile contract | `uv run pytest tests/unit/test_kis_live_contracts.py tests/unit/test_kis_websocket_client.py --no-cov -q` |
| Integration state convergence harness | `uv run pytest tests/integration/test_trading_simulation.py --no-cov -q` |
| Slack `/sm` command surface | `uv run pytest tests/unit/test_cli_main.py tests/unit/test_slack_bot_app.py tests/slack_bot/test_session_manager.py --no-cov -q` |
| Live verification command help/safety | `uv run stock-manager verify live-roundtrip --help` |
| Full test suite | `uv run pytest` |
| Lint | `uv run ruff check` |
| Type check | `uv run mypy stock_manager` |
| Architecture boundary | `uv run lint-imports --config pyproject.toml` |
| Package build | `uv build` |

## 6) Current Documentation Drift Signals

- Coverage policy is unified at `--cov-fail-under=85` across CI, pytest defaults, and root docs.
- CI quality gate visibility is now mapped in `docs/quality-gates.md`; PR blocking path includes lint/type/unit+coverage/build.
- KIS endpoint policy gate is in PR CI (`scripts/validate_kis_endpoint_policy.py`) to block absolute endpoint regressions in API wrappers.
- CLI surface now includes `verify live-roundtrip`; command lists that mention only `setup/doctor/run/trade/smoke/slack` are stale.
- Slack `/sm` guidance is now split into human and AI documents; operational docs should link the correct audience-specific guide instead of freehand examples only.
- The engine now uses broker-confirmed `pending_orders` convergence semantics; older docs/tests that assume optimistic buy/sell side-effects are stale.
- Fixture-backed live payload contract tests exist under `tests/fixtures/kis_live/` and `tests/unit/test_kis_live_contracts.py`; live-KIS parsing docs should reference them before inventing new samples.
- Nightly full-suite checks are scheduled in `.github/workflows/nightly-full-suite.yml`.
- Drift/GC scheduled checks are defined in `.github/workflows/drift-gc.yml`.

These are documentation and process visibility issues and should be fixed without changing trading logic.

## 7) Map Maintenance Rules

- Update this map when command surface or module boundaries change.
- Every new top-level operational module should be added to Section 2.
- Keep this file short and navigational; deep details belong in target module docs.
