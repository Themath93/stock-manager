# SPEC-DB-001: PostgreSQL Connection Pool Leak Fix

## 메타데이터

- **SPEC ID**: SPEC-DB-001
- **제목**: PostgreSQL Connection Pool Leak Fix
- **생성일**: 2026-01-28
- **상태**: planned
- **버전**: 1.0.0
- **우선순위**: HIGH
- **담당자**: Alfred (workflow-spec)
- **관련 SPEC**: SPEC-DB-002 (API Interface), SPEC-DB-003 (Schema Init)
- **부모 SPEC**: 없음 (독립적인 버그 수정 SPEC)

---

## 변경 이력 (History)

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-28 | Alfred | 초기 SPEC 작성 |

---

## 개요

PostgreSQLAdapter의 커넥션 풀 누수 문제를 수정하여 6개의 실패하는 테스트를 복구합니다.

**문제 정의:**
- `psycopg2.pool.PoolError: connection pool exhausted` 에러 발생
- 원인: `with self._connection_pool.getconn() as conn:` 패턴이 psycopg2에서 지원되지 않음
- 영향: 커넥션이 풀로 반환되지 않아 연결 고갈 발생

**현재 상태:**
- 6개 테스트 실패: test_insert_fill, test_update_order_status, test_transaction_rollback, test_fetch_all_orders, test_orders_unique_constraint, test_positions_unique_constraint
- PostgreSQLAdapter가 잘못된 컨텍스트 매니저 패턴 사용

**목표:**
- 커넥션 풀 누수 완전 해결
- 정상적인 풀 반환 로직 구현
- 커넥션 풀 상태 모니터링 추가

---

## 환경 (Environment)

### 기술 스택

- **Python**: 3.13+
- **데이터베이스**: PostgreSQL 15
- **데이터베이스 어댑터**: psycopg2-binary (ThreadedConnectionPool)
- **테스트**: pytest, pytest-asyncio

### 영향 받는 파일

1. **PostgreSQLAdapter** (`src/stock_manager/adapters/storage/postgresql_adapter.py`)
   - `execute_query()` 메서드 (line 110)
   - `execute_transaction()` 메서드 (line 148)
   - `transaction()` 컨텍스트 매니저 (line 174)

2. **Integration Tests** (`tests/integration/adapters/storage/test_postgresql_integration.py`)
   - TestPostgreSQLCRUDOperations 클래스 (3개 실패)
   - TestPostgreSQLConstraints 클래스 (3개 실패)

### psycopg2 ThreadedConnectionPool 동작

- `pool.getconn()`: 풀에서 커넥션 가져오기
- `pool.putconn(conn)`: 풀에 커넥션 반환 (반드시 호출 필요)
- 컨텍스트 매니저 프로토콜 미지원 → 직접 관리 필요

---

## 가정 (Assumptions)

### 기술적 가정

1. **psycopg2 ThreadedConnectionPool 동작**
   - ThreadedConnectionPool.getconn()은 컨텍스트 매니저를 지원하지 않는다고 가정
   - confidence: HIGH
   - evidence: psycopg2 문서 확인, 코드 실행 실패 확인
   - risk if wrong: 수정해도 문제 지속
   - validation method: psycopg2 공식 문서 확인

2. **스레드 안전성**
   - ThreadedConnectionPool은 스레드 안전하다고 가정
   - confidence: HIGH
   - evidence: psycopg2 문서
   - risk if wrong: 동시 접근 시 데이터 레이스 발생
   - validation method: 다중 스레드 테스트 실행

### 비즈니스 가정

1. **테스트 환경**
   - 테스트용 PostgreSQL이 로컬에서 실행 중이라고 가정
   - confidence: MEDIUM
   - evidence: docker-compose 설정 존재
   - risk if wrong: 테스트 실행 불가
   - validation method: DB 연결 확인 스크립트

---

## 요구사항 (Requirements)

### TAG BLOCK

```
TAG-SPEC-DB-001-001: execute_query 메서드 커넥션 누수 수정
TAG-SPEC-DB-001-002: execute_transaction 메서드 커넥션 누수 수정
TAG-SPEC-DB-001-003: transaction 컨텍스트 매니저 커넥션 누수 수정
TAG-SPEC-DB-001-004: 커넥션 풀 상태 모니터링 추가
TAG-SPEC-DB-001-005: 스레드 안전성 검증
TAG-SPEC-DB-001-006: 커넥션 누수 테스트 커버리지
```

### 1. Ubiquitous Requirements (항상 지원)

**REQ-UB-001: 커넥션 풀 반환 보장**
- PostgreSQLAdapter는 모든 작업 완료 후 커넥션을 풀에 반환해야 한다 (SHALL)
- execute_query() 메서드는 try-finally 블록으로 커넥션 반환을 보장해야 한다 (SHALL)
- execute_transaction() 메서드는 try-finally 블록으로 커넥션 반환을 보장해야 한다 (SHALL)
- transaction() 컨텍스트 매니저는 finally 블록에서 putconn()을 호출해야 한다 (SHALL)
- 왜: 커넥션 누수는 풀 고갈로 이어져 모든 DB 작업 중단
- 영향: 수정하지 않으면 지속적인 테스트 실패

**REQ-UB-002: 커넥션 풀 상태 추적**
- PostgreSQLAdapter는 현재 풀 상태를 제공해야 한다 (SHALL)
- pool_status 속성은 사용 중인 커넥션 수를 포함해야 한다 (SHALL)
- 디버깅을 위해 풀 사용량 로깅을 제공해야 한다 (SHOULD)
- 왜: 누수 디버깅과 모니터링에 필요
- 영향: 없으면 문제 진단 어려움

**REQ-UB-003: 에러 메시지 명확성**
- 커넥션 풀 고갈 시 명확한 에러 메시지를 제공해야 한다 (SHALL)
- 에러 메시지는 풀 설정 정보를 포함해야 한다 (SHALL)
- 왜: 문제 진단 속도 향상
- 영향: 불명확한 에러는 디버깅 지연

### 2. Event-Driven Requirements (WHEN X, THEN Y)

**REQ-ED-001: execute_query 호출 시 커넥션 반환**
- WHEN execute_query(query, params, fetch_one, fetch_all) is called
- THEN PostgreSQLAdapter SHALL get connection from pool via getconn()
- AND SHALL execute query with cursor
- AND SHALL commit if no fetch, return results if fetch
- AND SHALL ALWAYS return connection via putconn() in finally block
- 왜: 모든 경로에서 커넥션 반환 보장
- 영향: finally 없이 예외 발생 시 누수 발생

**REQ-ED-002: execute_transaction 호출 시 커넥션 반환**
- WHEN execute_transaction(queries) is called
- THEN PostgreSQLAdapter SHALL get connection from pool
- AND SHALL execute all queries in transaction
- AND SHALL commit on success
- AND SHALL ALWAYS return connection via putconn() in finally block
- 왜: 트랜잭션 실패 시에도 커넥션 반환 필요
- 영향: 예외 경로에서 누수 발생

**REQ-ED-003: transaction 컨텍스트 매니저 종료 시 커넥션 반환**
- WHEN with adapter.transaction(): block exits (normally or exception)
- THEN transaction context manager SHALL commit on success, rollback on failure
- AND SHALL ALWAYS call putconn() in finally block
- 왜: 컨텍스트 매니저는 예외 발생 가능성 높음
- 영향: finally 없으면 모든 예외에서 누수

**REQ-ED-004: 커넥션 풀 고갈 시 에러**
- WHEN connection pool is exhausted (max connections in use)
- THEN ThreadedConnectionPool SHALL raise PoolError
- AND PostgreSQLAdapter SHALL catch and re-raise with clear message
- 왜: 원인 파악을 위해 명확한 에러 필요
- 영향: 불명확한 에러는 디버깅 어려움

### 3. State-Driven Requirements (IF condition, THEN action)

**REQ-SD-001: 커넥션 풀 초기화 상태 확인**
- IF _connection_pool is None
- AND execute_query(), execute_transaction(), or transaction() is called
- THEN PostgreSQLAdapter SHALL raise RuntimeError immediately
- AND SHALL include message "Connection pool not initialized. Call connect() first."
- 왜: 초기화되지 않은 풀 사용 방지
- 영향: 명확하지 않은 에러는 혼란 야기

**REQ-SD-002: 커넥션 획득 실패 시 처리**
- IF getconn() raises PoolError (pool exhausted)
- THEN execute_query() SHALL not catch exception (let it propagate)
- AND SHALL ensure connection is not returned (none to return)
- 왜: PoolError는 이미 처리된 예외
- 영향: 불필요한 예외 처리는 디버깅 방해

### 4. Optional Requirements (가능하면 지원)

**REQ-OP-001: 커넥션 풀 사용량 로깅**
- WHERE debugging is needed
- PostgreSQLAdapter SHOULD log connection pool usage
- AND SHOULD include current/min/max connection counts
- 왜: 누수 추적에 도움
- 영향: 로그 오버헤드 고려

**REQ-OP-002: 커넥션 누수 감지 테스트**
- WHERE test coverage is important
- Tests SHOULD verify connection pool after operations
- AND SHOULD assert pool returns to expected size
- 왜: 회귀 방지
- 영향: 테스트 실행 시간 증가

### 5. Unwanted Behaviors (금지된 동작)

**REQ-UN-001: 커넥션 누수 금지**
- PostgreSQLAdapter는 어떤 circumstances에서도 커넥션을 누수해서는 안 된다 (MUST NOT)
- 모든 코드 경로는 putconn()을 호출해야 한다 (MUST)
- 예외 경로를 포함한 모든 경로에서 finally 블록을 사용해야 한다 (MUST)
- 왜: 단일 누수도 반복 호출 시 풀 고갈
- 영향: 프로덕션에서 서비스 중단

**REQ-UN-002: 컨텍스트 매니저 잘못된 사용 금지**
- `with pool.getconn() as conn:` 패턴을 사용해서는 안 된다 (MUST NOT)
- psycopg2 ThreadedConnectionPool은 컨텍스트 매니저를 지원하지 않음
- 왜: 동작하지 않는 코드, 커넥션 누수 발생
- 영향: 버그의 직접적 원인

---

## 상세 설계 (Specifications)

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  (OrderService, PositionService, MarketLifecycleService)    │
└───────────────────────────┬─────────────────────────────────┘
                            │ DatabasePort interface
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQLAdapter                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  State:                                             │    │
│  │  - _connection_pool: ThreadedConnectionPool         │    │
│  │  - min_connections: int                             │    │
│  │  - max_connections: int                             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Methods:                                           │    │
│  │  - connect() → initialize pool                      │    │
│  │  - execute_query() → getconn, execute, putconn     │    │
│  │  - execute_transaction() → getconn, exec, putconn  │    │
│  │  - transaction() → context manager with putconn     │    │
│  │  - close() → closeall()                             │    │
│  │  - pool_status → dict                               │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           psycopg2.ThreadedConnectionPool                   │
│  - getconn() → psycopg2.connection                         │
│  - putconn(conn) → return to pool                          │
│  - closeall() → close all connections                      │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 수정 사항

**1. execute_query() 수정**

```python
# Before (line 110) - WRONG
def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
    with self._connection_pool.getconn() as conn:  # Not supported!
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return None

# After - CORRECT
def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
    if self._connection_pool is None:
        raise RuntimeError("Connection pool not initialized. Call connect() first.")

    conn = None
    try:
        conn = self._connection_pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return None
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        logger.debug(f"Query: {query}")
        logger.debug(f"Params: {params}")
        raise
    finally:
        if conn:
            self._connection_pool.putconn(conn)
```

**2. execute_transaction() 수정**

```python
# Before (line 148) - WRONG
def execute_transaction(self, queries):
    with self._connection_pool.getconn() as conn:  # Not supported!
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for query, params in queries:
                cursor.execute(query, params)
            conn.commit()
            return True

# After - CORRECT
def execute_transaction(self, queries):
    if self._connection_pool is None:
        raise RuntimeError("Connection pool not initialized. Call connect() first.")

    conn = None
    try:
        conn = self._connection_pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for query, params in queries:
                cursor.execute(query, params)
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Transaction execution failed: {e}")
        logger.debug(f"Queries: {queries}")
        # Rollback is automatic on exception
        return False
    finally:
        if conn:
            self._connection_pool.putconn(conn)
```

**3. transaction() 컨텍스트 매니저 확인**

```python
# Current implementation (line 174-198) - CORRECT already!
@contextmanager
def transaction(self):
    if self._connection_pool is None:
        raise RuntimeError("Connection pool not initialized. Call connect() first.")

    conn = None
    try:
        conn = self._connection_pool.getconn()
        conn.autocommit = False
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Transaction failed: {e}")
        raise
    finally:
        if conn:
            self._connection_pool.putconn(conn)  # Already correct!
```

### 커넥션 수명 주기

```
Request → execute_query()
    ↓
pool.getconn() → conn
    ↓
try:
    cursor.execute(query)
    fetch/commit
except Exception:
    log and raise
finally:
    pool.putconn(conn)  # ← CRITICAL: Always executed
    ↓
Connection returned to pool
```

---

## 추적성 (Traceability)

### TAG Mapping

| TAG | 설명 | 파일 | 라인 |
|-----|------|------|------|
| TAG-SPEC-DB-001-001 | execute_query 커넥션 누수 수정 | postgresql_adapter.py | 84-126 |
| TAG-SPEC-DB-001-002 | execute_transaction 커넥션 누수 수정 | postgresql_adapter.py | 128-159 |
| TAG-SPEC-DB-001-003 | transaction 컨텍스트 매니저 확인 | postgresql_adapter.py | 173-198 |
| TAG-SPEC-DB-001-004 | 커넥션 풀 상태 모니터링 | postgresql_adapter.py | 200-223 |
| TAG-SPEC-DB-001-005 | 스레드 안전성 검증 | tests/integration/test_postgresql_integration.py | TBD |
| TAG-SPEC-DB-001-006 | 커넥션 누수 테스트 | tests/integration/test_postgresql_integration.py | TBD |

### Requirements Coverage

| Requirement | Component | Status |
|-------------|-----------|--------|
| REQ-UB-001: 커넥션 풀 반환 보장 | execute_query, execute_transaction, transaction | TODO |
| REQ-UB-002: 커넥션 풀 상태 추적 | pool_status property | EXISTS |
| REQ-UB-003: 에러 메시지 명확성 | error handling | TODO |
| REQ-ED-001: execute_query 커넥션 반환 | execute_query method | TODO |
| REQ-ED-002: execute_transaction 커넥션 반환 | execute_transaction method | TODO |
| REQ-ED-003: transaction 컨텍스트 매니저 커넥션 반환 | transaction context manager | VERIFIED |
| REQ-ED-004: 커넥션 풀 고갈 시 에러 | error handling | TODO |
| REQ-SD-001: 커넥션 풀 초기화 상태 확인 | all methods | EXISTS |
| REQ-UN-001: 커넥션 누수 금지 | all methods | TODO |
| REQ-UN-002: 컨텍스트 매니저 잘못된 사용 금지 | all methods | TODO |

### 테스트 커버리지

| 테스트 | 현재 상태 | 수정 후 예상 |
|-------|----------|-------------|
| test_insert_fill | FAIL (pool exhausted) | PASS |
| test_update_order_status | FAIL (pool exhausted) | PASS |
| test_transaction_rollback | FAIL (pool exhausted) | PASS |
| test_fetch_all_orders | FAIL (pool exhausted) | PASS |
| test_orders_unique_constraint | FAIL (pool exhausted) | PASS |
| test_positions_unique_constraint | FAIL (pool exhausted) | PASS |

---

## 참고 (References)

### 관련 문서

- [psycopg2.pool documentation](https://www.psycopg.org/docs/pool.html)
- [DB-API 2.0 specification](https://www.python.org/dev/peps/pep-0249/)
- [SPEC-DB-002](../SPEC-DB-002/) - PostgreSQLAdapter API Interface
- [SPEC-DB-003](../SPEC-DB-003/) - Database Schema Initialization

### 연관 SPEC

- **SPEC-BACKEND-API-001-P3**: KIS Broker Adapter (연동 테스트)
- **SPEC-DB-002**: PostgreSQLAdapter API Interface (의존)
- **SPEC-DB-003**: Integration Test Schema Initialization (의존)
