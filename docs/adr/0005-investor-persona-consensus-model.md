# ADR-0005: Investor Persona Consensus Model (10+1)

- Status: Accepted
- Date: 2026-03-02
- Decision Makers: stock-manager maintainers

## Context

A single trading model or investment philosophy is inherently biased toward one market regime.
Combining diverse investment perspectives through structured consensus reduces style-specific blind spots and improves decision robustness.

## Decision

Implement a 10+1 persona ensemble with consensus voting:

- **10 binding personas**: Each has a deterministic `screen_rule` method that returns a buy/hold/sell signal. Personas span 6 categories (`PersonaCategory`): value, growth, momentum, income, contrarian, and macro.
- **1 non-binding advisory** (`WoodAdvisory`): Provides qualitative innovation-theme commentary without a vote, used for supplementary context only.
- **Consensus aggregation**: `aggregator.py` collects all 10 binding votes and applies a configurable threshold (default: majority) to produce a final decision.
- **Parallel evaluation**: `evaluator.py` fans out persona evaluation via `ThreadPoolExecutor` (see ADR-0007).

Each persona is a subclass of `BasePersona` with a stable interface: `screen_rule(stock_data) -> Signal`.

## Consequences

Positive:
- Diversified signal reduces single-philosophy bias.
- Adding a new persona requires only subclassing `BasePersona` and registering it.
- Deterministic rules enable reproducible backtesting.

Negative:
- 10 persona evaluations per stock increase computation time (mitigated by threading).
- Consensus threshold tuning requires empirical validation.

## Alternatives Considered

1. Single LLM agent making all decisions.
   - Rejected due to non-determinism, cost, and single-point-of-failure bias.
2. Single rule-based screener with weighted scoring.
   - Rejected because a monolithic scorer is harder to extend and debug than independent personas.
3. Weighted-vote model (personas with different vote weights).
   - Deferred; equal weighting is simpler to reason about and tune initially.

## See Also

- [ADR-0006](0006-hybrid-rule-llm-persona-evaluation.md) — 하이브리드 규칙+LLM 평가 (페르소나 평가 파이프라인)
- [ADR-0007](0007-threading-concurrency-strategy.md) — 스레딩 전략 (ThreadPoolExecutor 팬아웃)
- [glossary.md](../glossary.md) — 도메인 용어 정의 (PersonaCategory, ConsensusResult 등)
- [README.md](../../README.md) — 시스템 아키텍처 개요
