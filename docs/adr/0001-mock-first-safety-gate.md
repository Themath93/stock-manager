# ADR-0001: Mock-first safety gate for live execution

- Status: Accepted
- Date: 2026-02-26
- Decision Makers: stock-manager maintainers

## Context

This project executes market orders. Risk exposure is high if live execution is enabled unintentionally.
The repository already contains a promotion gate pattern (`stock_manager/qa/mock_gate.py`) and execution commands that require explicit live confirmation.

## Decision

Adopt and keep a mock-first execution policy as a hard operational invariant:

- Default mode is mock (`KIS_USE_MOCK=true`) for development and validation.
- Live execution requires explicit flags and promotion-gate pass.
- Gate evidence is maintained in local runtime artifacts and validated by run/trade command paths.

## Consequences

Positive:
- Strong guardrail against accidental live trading.
- Clear and testable promotion path from mock to live.

Negative:
- Additional operational steps before live execution.
- Requires documentation and evidence discipline to avoid gate confusion.

## Alternatives Considered

1. Allow live by default with optional mock mode.
   - Rejected due to safety risk.
2. Remove promotion gate and rely only on manual reviewer checks.
   - Rejected due to low reproducibility and auditability.

## See Also

- [ADR-0002](0002-coverage-threshold-85.md) — 커버리지 임계값 정책 (동반 품질 정책)
- [ADR-0010](0010-engine-market-hours-enforcement-by-mode.md) — 엔진 장시간 로컬 가드 정책
- [runtime-trading-guardrails.md](../runtime-trading-guardrails.md) — 엔진 런타임 가드레일 authoritative source
- [quality-gates.md](../quality-gates.md) — 품질 게이트 강제 위치 매트릭스
- [knowledge-map.md](../knowledge-map.md) — 안전 불변량 섹션에서 참조
