# Runtime Trading Guardrails

This document is the authoritative source for engine-managed runtime trading guardrails.

Scope:
- Focus on `TradingEngine` runtime behavior and command-surface boundaries.
- Do not use this document for KIS endpoint authority, payload contract, or rate-limit policy.

## Policy Summary

- `live + market_hours_enabled=True` means engine-managed buy orders are locally blocked outside weekday `09:00-15:20 KST`.
- `mock + market_hours_enabled=True` means the engine bypasses the local market-hours buy block and continues to risk checks and broker submission.
- Sell paths are unaffected by market-hours enforcement.
- Broker or simulator rejection remains possible even when the engine does not block locally.

## Command Surface Matrix

| Surface | Primary Path | Engine Market-Hours Guard Applies | Notes |
|---|---|---|---|
| `stock-manager run` | `stock_manager/cli/trading_commands.py` -> `TradingEngine` | Yes | Runtime sessions inherit live-only local buy blocking. |
| Slack session (`/sm start`) | `stock_manager/slack_bot/session_manager.py` -> `TradingEngine` | Yes | Slack-managed runtime uses the same engine policy as `run`. |
| Strategy auto-buy cycle | `TradingEngine._run_strategy_cycle()` -> `TradingEngine.buy()` | Yes | Strategy-originated buys follow the same local policy as manual engine buys. |
| `stock-manager trade buy --execute` | `stock_manager/cli/trading_commands.py` -> `OrderExecutor.buy()` | No | This is a broker-direct path and is outside engine market-hours enforcement scope. |

## Evidence In Repo

### Runtime Implementation

- [stock_manager/engine.py](../stock_manager/engine.py)
  - `TradingEngine.buy()` applies market-hours blocking only when `_should_enforce_market_hours()` returns true.
  - `_run_preflight_checks()` logs live blocking vs mock bypass at engine startup.
- [stock_manager/cli/trading_commands.py](../stock_manager/cli/trading_commands.py)
  - `run` constructs `TradingEngine`.
  - `trade buy --execute` constructs `OrderExecutor` directly and does not pass through engine buy guards.

### Behavioral Evidence

- [tests/unit/test_engine.py](../tests/unit/test_engine.py)
  - `test_buy_rejected_outside_market_hours`
  - `test_buy_not_blocked_outside_market_hours_in_mock_when_enabled`
  - `test_start_warns_outside_market_hours_in_live_mode`
  - `test_start_logs_mock_market_hours_override`
- [tests/integration/test_trading_simulation.py](../tests/integration/test_trading_simulation.py)
  - `test_scenario5_buy_blocked_sell_allowed_outside_hours`
  - `test_scenario5_mock_buy_not_blocked_outside_hours`

## Fast Verification

```bash
uv run pytest tests/unit/test_engine.py -k 'market_hours or start_warns_outside_market_hours_in_live_mode or start_logs_mock_market_hours_override' --no-cov -q
uv run pytest tests/integration/test_trading_simulation.py -k 'scenario5' --no-cov -q
```

## Related Documents

- [docs/knowledge-map.md](knowledge-map.md)
- [docs/quality-gates.md](quality-gates.md)
- [docs/adr/0001-mock-first-safety-gate.md](adr/0001-mock-first-safety-gate.md)
- [docs/adr/0010-engine-market-hours-enforcement-by-mode.md](adr/0010-engine-market-hours-enforcement-by-mode.md)
- [docs/kis-endpoint-guardrails.md](kis-endpoint-guardrails.md)
