# ADR-0007: Thread-Per-Component Concurrency Strategy

- Status: Accepted
- Date: 2026-03-02
- Decision Makers: stock-manager maintainers

## Context

The system has multiple concurrent workloads: price monitoring, position adjustment, persona evaluation fan-out, and WebSocket streaming.
Python's GIL prevents true CPU parallelism, but these workloads are I/O-bound (HTTP calls, WebSocket reads, file I/O), making threading effective.

## Decision

Use the standard library `threading` module as the sole concurrency primitive:

- **Dedicated threads**: Long-lived components (engine loop, WebSocket client, price monitor) each run in their own `threading.Thread`.
- **Lock discipline**: `Lock` for simple mutual exclusion (e.g., position state); `RLock` for re-entrant call paths (e.g., nested adapter calls).
- **Thread pool fan-out**: `ThreadPoolExecutor(max_workers=5)` in `evaluator.py` for parallel persona evaluation across stocks.
- **Immutable shared data**: `frozen=True` dataclasses (see ADR-0008) for read-only data shared across threads, eliminating the need for locks on those objects.
- **Rate limiter**: `rate_limiter.py` uses `threading.Condition` for token-bucket throttling of KIS API calls.

## Consequences

Positive:
- Standard library only — no third-party concurrency dependencies.
- I/O-bound workloads achieve effective concurrency despite the GIL.
- `frozen=True` dataclasses provide thread-safe shared reads without locking overhead.

Negative:
- CPU-bound tasks (if any emerge) will not benefit from threading.
- Thread debugging is harder than single-threaded code; disciplined lock ordering is required.

## Alternatives Considered

1. `asyncio` event loop.
   - Rejected because it requires async-coloring all call paths and complicates integration with synchronous libraries.
2. `multiprocessing` / `ProcessPoolExecutor`.
   - Rejected due to IPC overhead and complexity for primarily I/O-bound workloads.
3. Third-party actor frameworks (e.g., `pykka`, `ray`).
   - Rejected to avoid external dependencies for a problem solvable with stdlib.

## See Also

- [ADR-0005](0005-investor-persona-consensus-model.md) — 페르소나 합의 모델 (ThreadPoolExecutor 팬아웃 근거)
- [ADR-0008](0008-pydantic-settings-dataclasses-split.md) — frozen 데이터클래스 (스레드 안전 공유 데이터)
- [execution-diagrams.md](../execution-diagrams.md) — 시스템 컴포넌트 관계도
