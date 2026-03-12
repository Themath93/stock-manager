# ADR Index

Architecture Decision Records (ADR) for stock-manager.

Purpose:
- Record major technical and operational decisions in-repo.
- Preserve decision context for agents and contributors.

Status convention:
- Proposed
- Accepted
- Superseded

## ADR List

| ID | Title | Status | Date |
|---|---|---|---|
| [0001](0001-mock-first-safety-gate.md) | Mock-first safety gate for live execution | Accepted | 2026-02-26 |
| [0002](0002-coverage-threshold-85.md) | Coverage threshold policy fixed at 85 | Accepted | 2026-02-26 |
| [0003](0003-kis-broker-adapter-pattern.md) | KIS Broker Adapter Pattern | Accepted | 2026-03-02 |
| [0004](0004-disk-backed-oauth-token-cache.md) | Disk-Backed OAuth Token Cache | Accepted | 2026-03-02 |
| [0005](0005-investor-persona-consensus-model.md) | Investor Persona Consensus Model (10+1) | Accepted | 2026-03-02 |
| [0006](0006-hybrid-rule-llm-persona-evaluation.md) | Hybrid Rule+LLM Persona Evaluation | Accepted | 2026-03-02 |
| [0007](0007-threading-concurrency-strategy.md) | Thread-Per-Component Concurrency Strategy | Accepted | 2026-03-02 |
| [0008](0008-pydantic-settings-dataclasses-split.md) | Pydantic-Settings for Config, Dataclasses for Domain | Accepted | 2026-03-02 |
| [0009](0009-kis-endpoint-authority-and-mode-isolation.md) | KIS Endpoint Authority and Mode Isolation | Accepted | 2026-03-05 |
| [0010](0010-engine-market-hours-enforcement-by-mode.md) | Engine Market-Hours Enforcement By Mode | Accepted | 2026-03-06 |

## Template

```markdown
# ADR-XXXX: Title

- Status: Proposed | Accepted | Superseded
- Date: YYYY-MM-DD
- Decision Makers: ...

## Context

## Decision

## Consequences

## Alternatives Considered
```
