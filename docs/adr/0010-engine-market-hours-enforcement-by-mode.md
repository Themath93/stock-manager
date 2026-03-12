# ADR-0010: Engine Market-Hours Enforcement By Mode

- Status: Accepted
- Date: 2026-03-06
- Decision Makers: stock-manager maintainers

## Context

The repository now enforces market-hours behavior in `TradingEngine` based on runtime mode:

- live engine sessions locally block buy orders outside weekday `09:00-15:20 KST`,
- mock engine sessions bypass that local block and continue to broker submission,
- sell paths remain unaffected.

This behavior was discoverable only through engine code, tests, and a section inside the KIS endpoint runbook.
That created harness drift:

- runtime trading policy and endpoint authority policy were mixed in one runbook,
- entry docs did not clearly show which command surfaces use engine enforcement,
- direct CLI trade execution could be mistaken for an engine-managed path.

## Decision

Adopt the following runtime policy and documentation boundaries:

1. `TradingEngine` market-hours enforcement is a live-only local buy guard when `market_hours_enabled=True`.
2. Mock engine sessions bypass the local market-hours buy block and continue to risk and broker handling.
3. `stock-manager trade buy --execute` remains outside this policy because it calls `OrderExecutor` directly rather than `TradingEngine.buy()`.
4. Broker and simulator rejection behavior is not changed by this decision.
5. `docs/runtime-trading-guardrails.md` becomes the authoritative documentation source for this runtime policy.

## Consequences

Positive:
- Runtime policy is discoverable within entry docs and ADR index navigation.
- Command-surface scope is explicit, reducing confusion between `run` and direct `trade` paths.
- Harness evidence now points to the exact tests that verify the invariant.

Negative:
- Documentation maintenance now spans an extra runtime guardrails document and ADR.
- Contributors must keep runtime guardrails docs aligned whenever command routing changes.

## Alternatives Considered

1. Keep market-hours policy only inside `docs/kis-endpoint-guardrails.md`.
   - Rejected because endpoint authority and runtime trading policy are separate concerns.
2. Document policy only in code and tests.
   - Rejected because harness discoverability and 2-hop navigation would remain weak.
3. Add a new blocking CI gate just for this invariant.
   - Rejected because existing unit and nightly suite coverage already provide evidence; the current gap is visibility, not enforcement.

## See Also

- [ADR-0001](0001-mock-first-safety-gate.md) - Mock-first operational policy.
- [ADR-0009](0009-kis-endpoint-authority-and-mode-isolation.md) - Endpoint authority isolation policy.
- [runtime-trading-guardrails.md](../runtime-trading-guardrails.md) - Authoritative runtime policy map.
