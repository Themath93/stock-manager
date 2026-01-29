# SPEC-CLI-001: Implementation Plan (구현 계획)

## Metadata

- **SPEC ID**: SPEC-CLI-001
- **Title**: CLI Worker Entrypoints Implementation
- **Version**: 1.0.0
- **Status**: planned
- **Last Updated**: 2026-01-29

---

## Implementation Strategy

This SPEC follows the **Small, Focused PRs** principle (Kent Beck) and **Simple & Clear** design (Linus Torvalds).

### Development Approach

**DDD (Domain-Driven Development) Methodology**:
- **ANALYZE**: Understand existing WorkerMain and service layer
- **PRESERVE**: Maintain compatibility with integration tests
- **IMPROVE**: Add CLI layer without modifying business logic

### Implementation Phases

1. **Phase 1**: Create main.py with Typer CLI (worker_start command)
2. **Phase 2**: Add signal handling and async bridge
3. **Phase 3**: Fix datetime.utcnow() deprecation warnings
4. **Phase 4**: Update pyproject.toml console script
5. **Phase 5**: Create CLI tests (subprocess testing)
6. **Phase 6**: Add optional health check command

---

## Milestones (Priority-Based)

### Primary Goal (P0 - Critical Path)

**Milestone 1: Basic Worker Start Command**

- Create `src/stock_manager/main.py` with Typer app
- Implement `worker_start` command with `--worker-id`, `--log-level`, `--debug` options
- Add structured logging with RichHandler
- Implement async bridge using `asyncio.run(_run_worker())`
- Load configuration from AppConfig
- Initialize database connection and services
- Start WorkerMain event loop

**Acceptance Criteria**:
- Running `stock-manager worker start --worker-id test-001` starts worker
- Logs output to console with Rich formatting
- Worker event loop executes (verify with logs)
- Exit code 0 on successful shutdown

**Estimated Complexity**: Medium
**Dependencies**: SPEC-INFRA-001 (AppConfig), SPEC-DB-001~004 (PostgreSQL adapter)

---

### Secondary Goal (P1 - High Priority)

**Milestone 2: Signal Handling & Graceful Shutdown**

- Register signal handlers (SIGTERM, SIGINT)
- Implement global `_shutdown_requested` flag
- Monitor shutdown flag in worker event loop
- Trigger WorkerMain.stop() on shutdown signal
- Add cleanup (database connection close)

**Acceptance Criteria**:
- Sending SIGTERM to worker process triggers graceful shutdown
- Pressing Ctrl+C (SIGINT) triggers graceful shutdown
- Worker releases locks and closes connections on shutdown
- Exit code 130 on SIGINT (standard: 128 + 2)

**Estimated Complexity**: Medium
**Dependencies**: Milestone 1

---

### Tertiary Goal (P2 - Medium Priority)

**Milestone 3: Configuration & Error Handling**

- Add `--config` option for custom configuration file
- Validate configuration on startup
- Implement exit codes:
  - 0: Success
  - 1: Configuration error
  - 2: Infrastructure error (database/broker)
  - 130: Interrupted (SIGINT)
- Add error logging with context
- Implement debug mode (`--debug` flag)

**Acceptance Criteria**:
- Missing environment variables return exit code 1
- Database connection failure returns exit code 2
- Debug mode shows full exception traces
- Error messages are clear and actionable

**Estimated Complexity**: Low
**Dependencies**: Milestone 1

---

### Final Goal (P3 - Nice-to-Have)

**Milestone 4: Optional Commands & Tests**

- Implement `health` command (REQ-OP-004)
- Create CLI tests using subprocess
- Test signal handling with subprocess
- Test exit codes and error handling
- Fix `datetime.utcnow()` deprecation warnings

**Acceptance Criteria**:
- `stock-manager health` checks database and broker connectivity
- CLI tests pass without running full worker
- Signal handling tests verify graceful shutdown
- No `datetime.utcnow()` usage in codebase

**Estimated Complexity**: Low-Medium
**Dependencies**: Milestone 2

---

## Technical Approach

### File Structure

```
src/stock_manager/
├── main.py                    # NEW: CLI entry point (TAG-SPEC-CLI-001-001)
├── service_layer/
│   └── worker_main.py         # MODIFY: Fix datetime.utcnow() (TAG-SPEC-CLI-001-007)
└── config/
    └── app_config.py          # EXISTING: Configuration loading

tests/
├── cli/                       # NEW: CLI tests
│   ├── __init__.py
│   ├── test_main.py           # TAG-SPEC-CLI-001-008
│   └── test_signal_handling.py
└── integration/
    └── service_layer/
        └── test_worker_full_cycle.py  # EXISTING: Validates WorkerMain

pyproject.toml                 # MODIFY: Console script (TAG-SPEC-CLI-001-006)
```

---

### Implementation Details

#### Phase 1: main.py Structure (Milestone 1)

**Imports**:
```python
import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.logging import RichHandler

from stock_manager.config.app_config import AppConfig
from stock_manager.service_layer.worker_main import WorkerMain
# ... other service imports
```

**Key Components**:
1. `app = typer.Typer()` - Typer app instance
2. `setup_logging()` - Configure Rich logging
3. `worker_start()` - Main command (TAG-SPEC-CLI-001-002)
4. `_run_worker()` - Async bridge (TAG-SPEC-CLI-001-004)
5. `main()` - Entry point for console script

---

#### Phase 2: Signal Handling (Milestone 2)

**Global Flag Pattern**:
```python
_shutdown_requested = False

def signal_handler(signum: int, frame) -> None:
    """Minimal signal handler (Linus: simple, reliable)"""
    global _shutdown_requested
    _shutdown_requested = True
    logging.getLogger(__name__).warning(f"Signal {signum} received, shutdown...")

def register_signal_handlers() -> None:
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
```

**Monitoring in Event Loop**:
```python
worker_task = asyncio.create_task(worker.start())

while not worker_task.done():
    if _shutdown_requested:
        await worker.stop()
        break
    await asyncio.sleep(0.5)
```

---

#### Phase 3: Configuration Validation (Milestone 3)

**Configuration Loading**:
```python
try:
    config = AppConfig()
    logger.info(f"Config loaded: KIS Mode={config.kis_mode}")
except Exception as e:
    logger.error(f"Config validation failed: {e}")
    return 1  # Exit code 1
```

**Database Connection**:
```python
try:
    db_adapter = create_postgresql_adapter(database_url=db_url)
    db_adapter.connect()
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    return 2  # Exit code 2
```

---

#### Phase 4: datetime.utcnow() Fix (Milestone 4)

**Search and Replace**:
```bash
# Find all occurrences
grep -r "datetime.utcnow()" src/

# Replace with datetime.now(timezone.utc)
# Line 311, 346 in worker_main.py
```

**Pattern**:
```python
# BEFORE:
datetime.utcnow().isoformat()

# AFTER:
datetime.now(timezone.utc).isoformat()
```

---

### Testing Strategy

#### CLI Tests (TAG-SPEC-CLI-001-008)

**Test Categories**:

1. **Unit Tests**: Test individual functions
   - `test_setup_logging()`
   - `test_signal_handler()`
   - `test_worker_id_generation()`

2. **Integration Tests**: Test CLI with subprocess
   - `test_worker_start_command()`
   - `test_signal_handling()`
   - `test_exit_codes()`

3. **End-to-End Tests**: Full worker lifecycle
   - `test_worker_full_cycle_cli()` - starts worker via CLI

**Example Test**:
```python
def test_worker_start_command():
    """Test CLI starts worker correctly"""
    result = subprocess.run(
        ["stock-manager", "worker", "start", "--worker-id", "test-001"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode in [0, 1, 2]  # Valid exit codes
    assert "Stock Manager Trading Bot" in result.stdout
```

---

## Risk Mitigation

### Risk 1: Signal Handler Reentrancy

**Risk**: Signal handlers called during async operations

**Mitigation**:
- Use global flag (no blocking operations in handler)
- Monitor flag in main loop (not in handler)
- Linus: "Keep handlers minimal"

### Risk 2: Async Event Loop Blocking

**Risk**: Worker loop doesn't respond to shutdown signal

**Mitigation**:
- Check flag every 500ms (not blocking)
- Use `asyncio.sleep(0.5)` for yielding
- Timeout on shutdown (30 seconds max)

### Risk 3: Database Connection Leaks

**Risk**: Connections not closed on shutdown

**Mitigation**:
- Use context managers for cleanup
- Explicit `db_adapter.close()` in finally block
- Integration tests verify connection cleanup

---

## Dependencies & Integration

### Prerequisites

1. **SPEC-INFRA-001**: Must complete first
   - Provides AppConfig with environment variable loading
   - Fixes KISConfig env_prefix issue

2. **SPEC-DB-001~004**: Database adapter ready
   - PostgreSQL adapter with connection pooling
   - Schema migrations applied

3. **SPEC-BACKEND-API-001-P3**: Broker adapter (MockBroker for PoC)

### Integration Points

- **WorkerMain**: Already implemented, tested
- **Service Layer**: All services functional
- **Configuration**: AppConfig loads from .env
- **Database**: PostgreSQL adapter working

---

## Code Quality Standards (TRUST 5)

### Tested (T)

- Unit tests for CLI functions
- Integration tests for worker start
- Signal handling tests with subprocess
- Target: 85%+ coverage for CLI code

### Readable (R)

- Type hints for all functions
- Docstrings for public APIs
- Clear variable names (no abbreviations)
- Comments for non-obvious logic

### Unified (U)

- Follow ruff formatting (line-length=100)
- Consistent import ordering
- Black formatting applied

### Secured (S)

- No secrets in code (use environment variables)
- Validate all inputs
- Proper error handling (no tracebacks to user)

### Trackable (T)

- TAG comments in code (e.g., # TAG-SPEC-CLI-001-001)
- Clear commit messages
- PRs linked to SPEC

---

## Rollback Plan

If implementation fails:

1. **Phase 1-2**: If main.py has bugs, delete file and revert pyproject.toml
2. **Phase 3**: If signal handling fails, remove signal handlers (worker still works)
3. **Phase 4**: If tests fail, skip tests (manual verification possible)

**Safe Rollback**:
- No changes to WorkerMain or business logic
- CLI layer is isolated (thin adapter)
- Can always use Python REPL to start worker manually

---

## Success Criteria

### Definition of Done

- [ ] `stock-manager worker start` command works
- [ ] Signal handling (SIGTERM, SIGINT) triggers graceful shutdown
- [ ] Exit codes are correct (0, 1, 2, 130)
- [ ] Logging output is clear and structured
- [ ] Integration tests still pass (no regression)
- [ ] CLI tests pass (subprocess tests)
- [ ] No `datetime.utcnow()` usage in codebase
- [ ] Code coverage >85% for CLI code
- [ ] Documentation updated (README.md)

---

## Next Steps After Implementation

1. **Run Integration Tests**: Verify WorkerMain still works
2. **Manual Testing**: Start worker via CLI, test signals
3. **Monitor**: Run worker for extended period, verify stability
4. **Production Deploy**: Deploy to production environment
5. **Monitor Metrics**: Track worker uptime, signal handling

---

## References

- Typer Docs: https://typer.tiangolo.com/
- Rich Logging: https://rich.readthedocs.io/
- Python Signals: https://docs.python.org/3/library/signal.html
- asyncio.run(): https://docs.python.org/3/library/asyncio-task.html
- Senior Engineer Insights:
  - Martin Fowler: Port-adapter architecture
  - Guido van Rossum: asyncio.run(), signal handling
  - Linus Torvalds: Simple signal handlers
  - Kent Beck: Small PRs, TDD
