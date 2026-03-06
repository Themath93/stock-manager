# ADR-0003: KIS Broker Adapter Pattern

- Status: Accepted
- Date: 2026-03-02
- Decision Makers: stock-manager maintainers

## Context

The domain layer must be isolated from KIS HTTP/WebSocket protocol details (URLs, headers, TR IDs).
Testability requires swapping real broker calls with mocks without touching domain logic.
Multiple API groups (domestic, overseas, OAuth) share common request patterns but differ in endpoints.

## Decision

Adopt a three-layer adapter architecture:

- **Pure-function API layer** (`apis/`): Each module returns a plain dict `{tr_id, url_path, params}` with no I/O side effects. This makes every KIS endpoint unit-testable without network access.
- **Facade adapter class** (`KISBrokerAdapter`): Orchestrates API dict construction, HTTP dispatch via injected `client.py`, and response parsing. Domain code depends only on this facade.
- **Injectable HTTP/WebSocket client** (`client.py`): Wraps `httpx.Client` with retry, rate-limit, and header injection. Constructor-injected into the adapter for mock/real swap.

Dependency rule enforced: `adapters/broker/kis/` may import from `trading/`, but `trading/` must never import from `adapters/`.

## Consequences

Positive:
- Domain logic has zero dependency on HTTP transport details.
- Mock testing requires only replacing the client injection; no monkeypatching needed.
- Adding a new KIS API endpoint is a single pure-function addition in `apis/`.

Negative:
- Extra indirection layer adds files and mapping boilerplate.
- Contributors must understand the dict-return convention for API modules.

## Alternatives Considered

1. Call `httpx` directly from domain code.
   - Rejected because it couples domain logic to transport and blocks unit testing.
2. Use a third-party KIS SDK wrapper library.
   - Rejected because no mature SDK existed and wrapping adds an opaque dependency.
3. Use `async` httpx throughout.
   - Deferred; current I/O-bound threading model (see ADR-0007) is sufficient.

## See Also

- [ADR-0004](0004-disk-backed-oauth-token-cache.md) — OAuth 토큰 캐시 (어댑터 하위 시스템)
- [ADR-0007](0007-threading-concurrency-strategy.md) — 스레딩 전략 (I/O 동시성 근거)
- [execution-diagrams.md](../execution-diagrams.md) — 시스템 아키텍처 및 컴포넌트 관계도
