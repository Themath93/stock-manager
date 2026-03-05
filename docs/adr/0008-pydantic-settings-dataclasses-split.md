# ADR-0008: Pydantic-Settings for Config, Dataclasses for Domain

- Status: Accepted
- Date: 2026-03-02
- Decision Makers: stock-manager maintainers

## Context

Configuration classes need environment-variable loading, type coercion, and secret masking.
Domain model classes need lightweight, immutable value objects with minimal overhead.
Using the same base class for both creates unnecessary coupling and runtime cost.

## Decision

Split class strategy by purpose:

- **`pydantic_settings.BaseSettings`** for configuration only:
  - Used in `adapters/broker/kis/config.py`, `notifications/config.py`, and application-level settings.
  - Leverages `env_prefix` for namespaced environment variables (e.g., `KIS_APP_KEY`).
  - Uses `SecretStr` for credentials to prevent accidental logging of secrets.
  - Limited to ~3 config files across the codebase.

- **`@dataclass` / `@dataclass(frozen=True)`** for all domain models:
  - Used in `trading/models.py` and throughout the trading domain.
  - `frozen=True` variants are thread-safe for shared reads across threads (see ADR-0007).
  - Zero Pydantic runtime overhead for objects created at high frequency (e.g., per-stock evaluation results).
  - Standard library only — no third-party dependency in the domain layer.

## Consequences

Positive:
- Configuration gets full Pydantic power (env loading, validation, secret masking) where it matters.
- Domain models stay lightweight and dependency-free.
- `frozen=True` dataclasses are inherently thread-safe for concurrent reads.

Negative:
- Two different class systems require contributors to know which to use where.
- Pydantic validation is unavailable for domain models (mitigated by type hints and tests).

## Alternatives Considered

1. Use `pydantic.BaseModel` for everything.
   - Rejected due to unnecessary runtime overhead for high-frequency domain objects.
2. Use `attrs` library.
   - Rejected to avoid adding a third-party dependency when stdlib `dataclass` suffices.
3. Use plain dicts for configuration.
   - Rejected because dicts lack type safety, env-var loading, and secret masking.
4. Use `OmegaConf` / `hydra`.
   - Rejected as over-engineered for the project's configuration complexity.

## See Also

- [ADR-0007](0007-threading-concurrency-strategy.md) — 스레딩 전략 (frozen 데이터클래스의 스레드 안전 근거)
- [glossary.md](../glossary.md) — TradingConfig, KISConfig 도메인 용어 정의
