# SPEC-CLI-001: Acceptance Criteria (수용 기준)

## Metadata

- **SPEC ID**: SPEC-CLI-001
- **Title**: CLI Worker Entrypoints Implementation
- **Version**: 1.0.0
- **Status**: planned
- **Last Updated**: 2026-01-29

---

## Overview

This document defines the acceptance criteria for SPEC-CLI-001 in **Given-When-Then** format (Gherkin syntax). Each criterion can be automated as a test.

---

## Test Scenarios

### Scenario 1: Worker Start Command (REQ-ED-001)

**Given** the application is installed and environment variables are configured
**When** user executes `stock-manager worker start --worker-id worker-001`
**Then** the system shall:
- Load configuration from environment variables
- Initialize database connection successfully
- Create WorkerMain instance with all dependencies
- Start worker event loop
- Log "Starting Worker worker-001" message
- Return exit code 0

**Test Command**:
```bash
stock-manager worker start --worker-id worker-001 --log-level INFO
```

**Expected Output**:
```
2026-01-29 10:00:00 | INFO | __main__ | Stock Manager Trading Bot - Starting Worker
2026-01-29 10:00:00 | INFO | __main__ | Configuration loaded: KIS Mode=PAPER
2026-01-29 10:00:00 | INFO | __main__ | Auto-generated worker ID: worker-001
2026-01-29 10:00:00 | INFO | __main__ | Signal handlers registered: SIGTERM, SIGINT
2026-01-29 10:00:01 | INFO | __main__ | Database connection established
2026-01-29 10:00:01 | INFO | __main__ | Services initialized successfully
2026-01-29 10:00:01 | INFO | __main__ | Starting worker event loop...
```

---

### Scenario 2: Auto-Generated Worker ID (REQ-SD-002)

**Given** the application is installed
**When** user executes `stock-manager worker start` without `--worker-id`
**Then** the system shall:
- Generate UUID-based worker ID (format: worker-{8-hex-chars})
- Log auto-generated worker ID
- Start worker with generated ID

**Test Command**:
```bash
stock-manager worker start | grep "Auto-generated worker ID"
```

**Expected Output**:
```
Auto-generated worker ID: worker-a1b2c3d4
```

---

### Scenario 3: Log Level Configuration (REQ-SD-001)

**Given** the application is installed
**When** user executes `stock-manager worker start --log-level DEBUG`
**Then** the system shall:
- Set logging level to DEBUG
- Output DEBUG level logs
- Show verbose information

**Test Command**:
```bash
stock-manager worker start --log-level DEBUG | grep "DEBUG"
```

**Expected Output**: DEBUG messages should appear in logs

---

### Scenario 4: Debug Mode (REQ-SD-004)

**Given** the application is installed
**When** user executes `stock-manager worker start --debug`
**Then** the system shall:
- Override log level to DEBUG
- Enable verbose exception traces
- Log all dependency initialization steps

**Test Command**:
```bash
stock-manager worker start --debug
```

**Expected Output**: Should see detailed dependency initialization logs

---

### Scenario 5: Configuration Validation Failure (REQ-ED-004)

**Given** environment variables are not configured
**When** user executes `stock-manager worker start`
**Then** the system shall:
- Log configuration validation error
- Exit with code 1
- Not attempt to start worker

**Test Command**:
```bash
unset KIS_APP_KEY KIS_APP_SECRET SLACK_BOT_TOKEN
stock-manager worker start
echo $?
```

**Expected Output**:
```
Configuration validation failed: ...
```
**Expected Exit Code**: 1

---

### Scenario 6: Database Connection Failure (REQ-ED-005)

**Given** configuration is valid but database is not running
**When** user executes `stock-manager worker start`
**Then** the system shall:
- Log database connection error
- Exit with code 2
- Not attempt to start worker

**Test Command**:
```bash
# Stop database
docker stop postgres
stock-manager worker start
echo $?
```

**Expected Output**:
```
Database connection failed: ...
```
**Expected Exit Code**: 2

---

### Scenario 7: SIGTERM Signal Handling (REQ-ED-002)

**Given** worker is running
**When** user sends SIGTERM signal (`kill -TERM <pid>`)
**Then** the system shall:
- Log "Signal 15 received, initiating graceful shutdown"
- Set WorkerMain._running = False
- Wait for worker loop to complete
- Release stock locks if holding
- Close database connections
- Exit with code 0

**Test Command**:
```bash
stock-manager worker start --worker-id test-001 &
WORKER_PID=$!
sleep 2
kill -TERM $WORKER_PID
wait $WORKER_PID
echo $?
```

**Expected Output**:
```
Signal 15 received, initiating graceful shutdown...
Shutdown signal detected, stopping worker...
Worker stopped with exit code: 0
```
**Expected Exit Code**: 0

---

### Scenario 8: SIGINT Signal Handling (REQ-ED-003)

**Given** worker is running
**When** user presses Ctrl+C (sends SIGINT)
**Then** the system shall:
- Log "Signal 2 received, initiating graceful shutdown"
- Trigger graceful shutdown via WorkerMain.stop()
- Allow cleanup to complete (max 30 seconds)
- Exit with code 130

**Test Command**:
```bash
stock-manager worker start --worker-id test-002 &
WORKER_PID=$!
sleep 2
kill -INT $WORKER_PID
wait $WORKER_PID
echo $?
```

**Expected Output**:
```
Signal 2 received, initiating graceful shutdown...
Worker interrupted by user
```
**Expected Exit Code**: 130

---

### Scenario 9: Structured Logging (REQ-UB-003)

**Given** worker is running
**When** logs are output
**Then** the system shall:
- Include timestamp in format `YYYY-MM-DD HH:MM:SS`
- Include log level (INFO, DEBUG, WARNING, ERROR)
- Include logger name
- Include worker ID in log messages
- Use Rich formatting for console output

**Expected Format**:
```
2026-01-29 10:00:00 | INFO | __main__ | Stock Manager Trading Bot - Starting Worker
```

---

### Scenario 10: Exit Code Standards (REQ-UB-004)

**Given** worker execution completes
**When** checking exit code
**Then** the system shall return:
- 0 for successful shutdown
- 1 for configuration error
- 2 for infrastructure error (database/broker)
- 130 for SIGINT (128 + 2)

**Test Cases**:
```bash
# Success case
stock-manager worker start --worker-id test-003 &
WORKER_PID=$!
sleep 2
kill -TERM $WORKER_PID
wait $WORKER_PID
echo $?  # Should be 0

# Configuration error
unset KIS_APP_KEY
stock-manager worker start
echo $?  # Should be 1

# Database error
DATABASE_URL="invalid://url" stock-manager worker start
echo $?  # Should be 2

# SIGINT
stock-manager worker start &
WORKER_PID=$!
sleep 2
kill -INT $WORKER_PID
wait $WORKER_PID
echo $?  # Should be 130
```

---

### Scenario 11: Type Safety (REQ-UB-005)

**Given** CLI code is written
**When** running mypy type checker
**Then** the system shall:
- Have type hints for all function arguments
- Have type hints for all return values
- Pass mypy strict mode without errors

**Test Command**:
```bash
mypy src/stock_manager/main.py --strict
```

**Expected Result**: No type errors

---

### Scenario 12: datetime.utcnow() Fix (REQ-UN-004)

**Given** codebase exists
**When** searching for deprecated datetime usage
**Then** the system shall:
- Not contain `datetime.utcnow()` calls
- Use `datetime.now(timezone.utc)` instead

**Test Command**:
```bash
grep -r "datetime.utcnow()" src/
```

**Expected Result**: No matches found

---

### Scenario 13: Business Logic Separation (REQ-UN-003)

**Given** main.py is implemented
**When** reviewing code
**Then** the system shall:
- Not contain trading strategy logic
- Not contain business rules in CLI layer
- Only delegate to WorkerMain and service layer

**Verification**: Manual code review

---

### Scenario 14: CLI Testability (REQ-OP-004, TAG-SPEC-CLI-001-008)

**Given** CLI tests are written
**When** running tests
**Then** the system shall:
- Test CLI commands without running full worker (use subprocess)
- Test signal handling with subprocess
- Test exit codes and error messages
- Achieve 85%+ coverage for CLI code

**Test Command**:
```bash
pytest tests/cli/test_main.py -v --cov=src/stock_manager/main --cov-report=term-missing
```

**Expected Result**: All tests pass, coverage >85%

---

### Scenario 15: Console Script Entry (TAG-SPEC-CLI-001-006)

**Given** package is installed
**When** user executes `stock-manager` command
**Then** the system shall:
- Execute `stock_manager.main:main()` function
- Show help message with available commands
- List `worker-start` and `health` commands

**Test Command**:
```bash
stock-manager --help
```

**Expected Output**:
```
Usage: stock-manager [OPTIONS] COMMAND [ARGS]...

  Stock Manager Trading Bot - Automated trading system

Options:
  --install-completion  Install completion for the current shell.
  --show-completion     Show completion for the current shell, to copy it or customize the installation.
  --help                Show this message and exit.

Commands:
  worker-start  Start Stock Manager worker
  health        Health check command
```

---

### Scenario 16: Health Check Command (REQ-OP-004)

**Given** application is installed
**When** user executes `stock-manager health`
**Then** the system shall:
- Check database connectivity
- Verify broker connection (TODO)
- Return exit code 0 if all checks pass
- Return exit code 1 if any check fails

**Test Command**:
```bash
stock-manager health
echo $?
```

**Expected Output**:
```
Running health checks...
Checking database connection...
✅ Database connection: OK
✅ Health check passed
```
**Expected Exit Code**: 0

---

## Quality Gates

### TRUST 5 Validation

**Tested (T)**:
- [ ] All scenarios have automated tests
- [ ] Coverage >85% for CLI code
- [ ] Integration tests pass (no regression)

**Readable (R)**:
- [ ] Type hints for all functions
- [ ] Docstrings for public APIs
- [ ] ruff linting passes

**Unified (U)**:
- [ ] Black formatting applied
- [ ] Import ordering consistent
- [ ] Line length <=100

**Secured (S)**:
- [ ] No secrets in code
- [ ] Input validation on all arguments
- [ ] Proper error handling

**Trackable (T)**:
- [ ] TAG comments in code
- [ ] Clear commit messages
- [ ] PR linked to SPEC-CLI-001

---

## Test Execution Checklist

### Pre-Implementation Tests

- [ ] Verify existing integration tests pass
- [ ] Verify WorkerMain works correctly
- [ ] Verify database schema is ready

### Post-Implementation Tests

- [ ] Run all scenarios above
- [ ] Run integration tests (no regression)
- [ ] Run CLI tests (subprocess tests)
- [ ] Manual testing: Start worker, send signals
- [ ] Verify logging output format
- [ ] Verify exit codes

---

## Definition of Done

SPEC-CLI-001 is **COMPLETE** when:

1. **Core Functionality**:
   - [ ] `stock-manager worker start` works
   - [ ] Signal handling (SIGTERM, SIGINT) works
   - [ ] Exit codes are correct (0, 1, 2, 130)
   - [ ] Logging is structured and clear

2. **Testing**:
   - [ ] All test scenarios pass
   - [ ] CLI tests pass (subprocess tests)
   - [ ] Integration tests pass (no regression)
   - [ ] Coverage >85% for CLI code

3. **Code Quality**:
   - [ ] Type hints complete
   - [ ] Docstrings complete
   - [ ] ruff linting passes
   - [ ] No datetime.utcnow() usage

4. **Documentation**:
   - [ ] README.md updated with CLI usage
   - [ ] Code comments explain signal handling
   - [ ] TAG comments mapped to requirements

5. **Integration**:
   - [ ] Console script entry works
   - [ ] Environment variable loading works
   - [ ] Database connection works
   - [ ] WorkerMain integration works

---

## Verification Commands

### Quick Verification (5 minutes)

```bash
# 1. Install dependencies
poetry install --extras cli

# 2. Check help
stock-manager --help

# 3. Test health check
stock-manager health

# 4. Start worker (background)
stock-manager worker start --worker-id test-quick &
WORKER_PID=$!

# 5. Check logs
sleep 2
ps -p $WORKER_PID

# 6. Send SIGTERM
kill -TERM $WORKER_PID
wait $WORKER_PID
echo $?  # Should be 0

# 7. Run CLI tests
pytest tests/cli/ -v
```

### Full Verification (15 minutes)

```bash
# 1. Run all tests
pytest tests/ -v --cov

# 2. Check type hints
mypy src/stock_manager/main.py --strict

# 3. Check formatting
ruff check src/stock_manager/main.py

# 4. Test all exit codes
./tests/cli/test_exit_codes.sh

# 5. Test signal handling
./tests/cli/test_signals.sh

# 6. Verify no deprecated datetime
grep -r "datetime.utcnow()" src/

# 7. Manual smoke test
stock-manager worker start --worker-id manual-test --log-level DEBUG
# Press Ctrl+C after 5 seconds, verify graceful shutdown
```

---

## References

- Test Scenarios: Derived from EARS requirements in spec.md
- Gherkin Syntax: https://cucumber.io/docs/gherkin/
- Subprocess Testing: Python subprocess module
- Signal Testing: kill command, signal module
