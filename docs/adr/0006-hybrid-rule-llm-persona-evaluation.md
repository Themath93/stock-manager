# ADR-0006: Hybrid Rule+LLM Persona Evaluation

- Status: Accepted
- Date: 2026-03-02
- Decision Makers: stock-manager maintainers

## Context

Pure rule-based evaluation is fast and deterministic but misses qualitative nuances (management quality, narrative shifts).
Pure LLM evaluation captures nuance but is costly, slow, and non-deterministic.
A hybrid approach is needed to combine the strengths of both while controlling cost and maintaining reliability.

## Decision

Adopt a two-stage evaluation pipeline:

- **Stage 1 (Rules — always runs)**: Every persona's `screen_rule` executes deterministically. This produces the baseline signal and is sufficient for clear-cut cases.
- **Stage 2 (LLM — conditional)**: For borderline signals (near-threshold scores), an LLM review is triggered via `hybrid.py` to provide qualitative validation. LLM is called only when the rule score falls within a configurable ambiguity band.
- **Circuit breaker** (`circuit_breaker.py`): Protects against LLM API failures with exponential backoff. After consecutive failures, the breaker opens and Stage 2 is skipped.
- **Daily call budget** (`config.py`): Hard cap on LLM invocations per day to control cost.
- **Graceful degradation**: If the LLM is unavailable or budget is exhausted, the rule-only result from Stage 1 is used as the final signal.

## Consequences

Positive:
- Most evaluations complete in milliseconds (rules only) with LLM cost incurred only for ambiguous cases.
- Circuit breaker prevents cascading failures from LLM outages.
- System remains fully functional without LLM access.

Negative:
- Two-stage logic adds complexity to the evaluation path.
- LLM ambiguity-band threshold requires calibration per persona.

## Alternatives Considered

1. Always call LLM for every evaluation.
   - Rejected due to cost ($0.01+ per call × 10 personas × N stocks) and latency.
2. Rules only, no LLM integration.
   - Rejected because qualitative signals are valuable for borderline decisions.
3. LLM first, rules as fallback.
   - Rejected because it inverts the cost profile: LLM becomes the hot path.

## See Also

- [ADR-0005](0005-investor-persona-consensus-model.md) — 10+1 페르소나 합의 모델 (이 결정이 기반하는 모델)
