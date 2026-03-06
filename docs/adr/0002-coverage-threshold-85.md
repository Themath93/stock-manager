# ADR-0002: Coverage threshold policy fixed at 85

- Status: Accepted
- Date: 2026-02-26
- Decision Makers: stock-manager maintainers

## Context

Coverage policy drift existed across repository surfaces:

- CI workflow enforced `--cov-fail-under=85`.
- Some docs and pytest defaults referenced 80.

This mismatch reduced reproducibility and caused harness-audit drift findings.

## Decision

Standardize the project coverage threshold at 85 for all primary policy surfaces:

- CI workflow gate
- pytest default options in project config
- root guidance docs
- harness quality-gate matrix documentation

## Consequences

Positive:
- Consistent quality signal across local runs and CI.
- Lower policy ambiguity for agents and contributors.

Negative:
- Slightly stricter baseline may require additional test maintenance.

## Alternatives Considered

1. Lower CI to 80 for immediate consistency.
   - Rejected because CI already runs at 85 and this weakens current quality bar.
2. Keep split policy (80 local, 85 CI).
   - Rejected because it preserves drift and inconsistent developer feedback.

## See Also

- [ADR-0001](0001-mock-first-safety-gate.md) — Mock-first 안전 정책 (동반 품질 정책)
- [quality-gates.md](../quality-gates.md) — 커버리지 게이트 강제 위치
