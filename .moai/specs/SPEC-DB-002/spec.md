# SPEC-DB-002: PostgreSQLAdapter API Interface Extension

## 메타데이터

- **SPEC ID**: SPEC-DB-002
- **제목**: PostgreSQLAdapter API Interface Extension - cursor() Method
- **생성일**: 2026-01-28
- **상태**: planned
- **버전**: 1.0.0
- **우선순위**: HIGH
- **담당자**: Alfred (workflow-spec)
- **의존 SPEC**: SPEC-DB-001 (Connection Pool Fix)
- **관련 SPEC**: SPEC-DB-003 (Schema Init)

---

## 변경 이력 (History)

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-28 | Alfred | 초기 SPEC 작성 |

---

## 개요

PostgreSQLAdapter에 DB-API 2.0 호환 cursor() 컨텍스트 매니저를 추가하여 서비스 레이어와의 API 불일치를 해결합니다.

**문제 정의:**
- 서비스 레이어(PositionService, MarketLifecycleService)가 `with db.cursor() as cursor:` 패턴 사용
- PostgreSQLAdapter가 cursor() 메서드를 제공하지 않음
- DatabasePort 인터페이스에 cursor() 정의 없음

**현재 상태:**
- 1개 테스트 실패: test_system_state_persistence (AttributeError: 'PostgreSQLAdapter' object has no attribute 'cursor')
- PositionService 5개 메서드에서 cursor() 패턴 사용
- MarketLifecycleService에서 cursor() 패턴 사용

**목표:**
- PostgreSQLAdapter에 cursor() 컨텍스트 매니저 추가
- DatabasePort 인터페이스 확장
- 서비스 레이어와의 호환성 확보
- 기존 execute_query() API와의 공존

---

## 환경 (Environment)

### 기술 스택

- **Python**: 3.13+
- **데이터베이스**: PostgreSQL 15
- **데이터베이스 어댑터**: psycopg2-binary (ThreadedConnectionPool, RealDictCursor)
- **테스트**: pytest, pytest-asyncio

### 영향 받는 파일

1. **PostgreSQLAdapter** (`src/stock_manager/adapters/storage/postgresql_adapter.py`)
   - cursor() 컨텍스트 매니저 추가 (new method)

2. **DatabasePort 인터페이스** (`src/stock_manager/adapters/storage/port.py`)
   - cursor() 추상 메서드 추가

3. **Service Layer** (수정 불필요, 호환성 확인만)
   - `src/stock_manager/service_layer/position_service.py` (lines 124, 143, 175, 194, 209)
   - `src/stock_manager/service_layer/market_lifecycle_service.py`

4. **Integration Tests**
   - `tests/integration/service_layer/test_market_lifecycle_integration.py`

### DB-API 2.0 Cursor 인터페이스

```python
# Standard DB-API 2.0 cursor pattern
with connection.cursor() as cursor:
    cursor.execute(query, params)
    results = cursor.fetchall()
    connection.commit()
```

### psycopg2 RealDictCursor 특징

- 컬럼 이름으로 딕셔너리 액세스 지원
- `row["column_name"]` 패턴
- fetchone(), fetchall(), fetchmany() 메서드

---

## 가정 (Assumptions)

### 기술적 가정

1. **커넥션 풀 안전성**
   - cursor() 메서드는 ThreadedConnectionPool과 안전하게 통합 가능하다고 가정
   - confidence: HIGH
   - evidence: psycopg2 커넥션은 스레드당 하나 사용
   - risk if wrong: 스레드 안전성 문제 발생
   - validation method: 다중 스레드 테스트

2. **트랜잭션 경계**
   - cursor() 컨텍스트 매니저 내에서 자동 커밋이 적절하다고 가정
   - confidence: MEDIUM
   - evidence: 서비스 레이어 사용 패턴 분석
   - risk if wrong: 트랜잭션 일관성 문제
   - validation method: 트랜잭션 테스트

3. **기존 API와의 공존**
   - cursor()와 execute_query()가 공존 가능하다고 가정
   - confidence: HIGH
   - evidence: 동일한 백엔드 사용
   - risk if wrong: API 혼란
   - validation method: 양쪽 모두 사용하는 테스트

### 비즈니스 가정

1. **서비스 레이어 호환성**
   - 서비스 레이어는 cursor() 패턴을 계속 사용할 것이라고 가정
   - confidence: HIGH
   - evidence: 현재 코드 패턴
   - risk if wrong: 불필요한 추상화 계층
   - validation method: 서비스 레이어 개발자와 협의

---

## 요구사항 (Requirements)

### TAG BLOCK

```
TAG-SPEC-DB-002-001: cursor() 컨텍스트 매니저 구현
TAG-SPEC-DB-002-002: DatabasePort 인터페이스 확장
TAG-SPEC-DB-002-003: 트랜잭션 경계 준수
TAG-SPEC-DB-002-004: execute_query()와의 공존
TAG-SPEC-DB-002-005: 서비스 레이어 통합 검증
TAG-SPEC-DB-002-006: RealDictCursor 기본 사용
```

### 1. Ubiquitous Requirements (항상 지원)

**REQ-UB-001: cursor() 컨텍스트 매니저 제공**
- PostgreSQLAdapter는 cursor() 컨텍스트 매니저 메서드를 제공해야 한다 (SHALL)
- cursor()는 RealDictCursor를 기본으로 사용해야 한다 (SHALL)
- cursor()는 선택적 cursor_factory 파라미터를 지원해야 한다 (SHALL)
- cursor()는 DB-API 2.0 표준을 따라야 한다 (SHALL)
- 왜: 서비스 레이어와의 호환성 필요
- 영향: 없으면 서비스 레이어 사용 불가

**REQ-UB-002: DatabasePort 인터페이스 확장**
- DatabasePort 인터페이스는 cursor() 추상 메서드를 정의해야 한다 (SHALL)
- 모든 DatabasePort 구현은 cursor()를 제공해야 한다 (MUST)
- 왜: 인터페이스 계약 정의
- 영향: 인터페이스 불일치로 LSP 위반

**REQ-UB-003: 커넥션 풀 관리**
- cursor()는 커넥션 풀을 사용해야 한다 (SHALL)
- cursor()는 컨텍스트 종료 시 커넥션을 반환해야 한다 (SHALL)
- cursor()는 SPEC-DB-001의 putconn() 패턴을 따라야 한다 (SHALL)
- 왜: 커넥션 누수 방지
- 영향: 누수 발생 시 풀 고갈

### 2. Event-Driven Requirements (WHEN X, THEN Y)

**REQ-ED-001: cursor() 진입 시 커넥션 획득**
- WHEN with adapter.cursor() as cursor: block is entered
- THEN adapter SHALL get connection from pool via getconn()
- AND SHALL create cursor from connection
- AND SHALL yield cursor to caller
- 왜: 컨텍스트 매니저 진입 시 초기화 필요
- 영향: 없으면 커서 사용 불가

**REQ-ED-002: cursor() 정상 종료 시 커밋 및 반환**
- WHEN with adapter.cursor() as cursor: block exits normally
- THEN adapter SHALL commit transaction
- AND SHALL close cursor
- AND SHALL return connection to pool via putconn()
- 왜: 정상 완료 시 커밋 필요
- 영향: 없으면 변경사항 반영 안 됨

**REQ-ED-003: cursor() 예외 시 롤백 및 반환**
- WHEN with adapter.cursor() as cursor: block exits with exception
- THEN adapter SHALL rollback transaction
- AND SHALL close cursor
- AND SHALL return connection to pool via putconn()
- AND SHALL re-raise exception to caller
- 왜: 예외 시 롤백 필요
- 영향: 없으면 부분적 데이터 저장

**REQ-ED-004: cursor_factory 지정 시 사용**
- WHEN cursor(cursor_factory=CustomCursor) is called
- THEN adapter SHALL use CustomCursor instead of RealDictCursor
- 왜: 사용자 정의 커서 지원
- 영향: 없으면 유연성 저하

### 3. State-Driven Requirements (IF condition, THEN action)

**REQ-SD-001: 커넥션 풀 초기화 확인**
- IF _connection_pool is None
- AND cursor() is called
- THEN PostgreSQLAdapter SHALL raise RuntimeError
- AND SHALL include message "Connection pool not initialized"
- 왜: 초기화되지 않은 상태 방지
- 영향: 명확하지 않은 에러는 혼란 야기

**REQ-SD-002: 선택적 cursor_factory 처리**
- IF cursor_factory parameter is None
- THEN cursor() SHALL use RealDictCursor as default
- 왜: 기본 동작 정의
- 영향: 없으면 매번 지정 필요

### 4. Optional Requirements (가능하면 지원)

**REQ-OP-001: 중첩 cursor() 지원**
- WHERE multiple cursor() calls are needed
- PostgreSQLAdapter SHOULD support nested cursor contexts
- AND each cursor SHOULD use separate connection from pool
- 왜: 복잡한 쿼리 패턴 지원
- 영향: 제한 시 유연성 저하

**REQ-OP-002: 커넥션 재사용 최적화**
- WHERE performance is critical
- cursor() COULD reuse connections within same thread
- AND COULD minimize pool get/put overhead
- 왜: 성능 최적화
- 영향: 미미한 성능 향상

### 5. Unwanted Behaviors (금지된 동작)

**REQ-UN-001: 커넥션 풀 우회 금지**
- cursor()는 직접 커넥션을 생성해서는 안 된다 (MUST NOT)
- cursor()는 반드시 pool.getconn()을 사용해야 한다 (MUST)
- 왜: 풀 관리 우회로 연결 관리 실패
- 영향: 커넥션 누수 및 리소스 낭비

**REQ-UN-002: 커넥션 누수 금지**
- cursor()는 어떤 circumstances에서도 커넥션을 누수해서는 안 된다 (MUST NOT)
- cursor()는 finally 블록에서 putconn()을 보장해야 한다 (MUST)
- 왜: 단일 누수도 반복 호출 시 풀 고갈
- 영향: 서비스 중단

**REQ-UN-003: execute_query()와의 동작 불일치 금지**
- cursor()는 execute_query()와 동일한 풀 관리를 사용해야 한다 (MUST)
- cursor()는 execute_query()와 동일한 에러 처리를 해야 한다 (MUST)
- 왜: API 일관성 유지
- 영향: 혼란 및 버그 유발

---

## 상세 설계 (Specifications)

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  PositionService, MarketLifecycleService                   │
│                                                             │
│  Usage Pattern:                                            │
│  with db.cursor() as cursor:                               │
│      cursor.execute(query, params)                         │
│      results = cursor.fetchall()                           │
└───────────────────────────┬─────────────────────────────────┘
                            │ DatabasePort interface
                            │ execute_query(), cursor()
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQLAdapter                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Methods:                                           │    │
│  │  - execute_query() → high-level API                │    │
│  │  - execute_transaction() → high-level API          │    │
│  │  - cursor(cursor_factory=None) → NEW               │    │
│  │       Returns: Context manager with cursor          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  cursor() behavior:                                         │
│  1. Check pool initialized                                  │
│  2. Get connection: pool.getconn()                         │
│  3. Create cursor: conn.cursor(factory)                    │
│  4. Yield cursor to caller                                 │
│  5. On exit: commit/rollback, putconn()                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           psycopg2.ThreadedConnectionPool                   │
│  - getconn() → psycopg2.connection                         │
│  - putconn(conn) → return to pool                          │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 구현: cursor() 메서드

**PostgreSQLAdapter에 추가할 cursor() 메서드:**

```python
from contextlib import contextmanager
from typing import Optional, Type
from psycopg2.extensions import cursor as Cursor
from psycopg2.extras import RealDictCursor

class PostgreSQLAdapter(DatabasePort):

    # ... 기존 메서드들 ...

    @contextmanager
    def cursor(self, cursor_factory: Optional[Type] = None):
        """Context manager for DB-API 2.0 compatible cursor

        Provides a cursor context manager compatible with service layer
        expectations. Manages connection pool integration automatically.

        Args:
            cursor_factory: Optional cursor factory class (default: RealDictCursor)

        Yields:
            psycopg2.cursor: DB-API 2.0 compatible cursor

        Raises:
            RuntimeError: If connection pool is not initialized

        Example:
            >>> with adapter.cursor() as cursor:
            ...     cursor.execute("SELECT * FROM orders WHERE id = %s", (1,))
            ...     order = cursor.fetchone()

        Note:
            - Automatically commits on successful completion
            - Automatically rolls back on exception
            - Always returns connection to pool
        """
        # 1. Pool 초기화 확인
        if self._connection_pool is None:
            raise RuntimeError("Connection pool not initialized. Call connect() first.")

        # 2. cursor_factory 기본값 설정
        factory = cursor_factory or RealDictCursor

        conn = None
        cur = None

        try:
            # 3. 커넥션 획득
            conn = self._connection_pool.getconn()

            # 4. 커서 생성
            cur = conn.cursor(cursor_factory=factory)

            # 5. 커서 yield
            yield cur

            # 6. 정상 완료 시 커밋
            conn.commit()

        except Exception as e:
            # 7. 예외 시 롤백
            if conn:
                conn.rollback()
            logger.error(f"Cursor operation failed: {e}")
            raise

        finally:
            # 8. 정리 및 커넥션 반환
            if cur:
                cur.close()
            if conn:
                self._connection_pool.putconn(conn)
```

### DatabasePort 인터페이스 확장

```python
# port.py 수정
from abc import ABC, abstractmethod
from typing import Optional, Type
from psycopg2.extensions import cursor as Cursor

class DatabasePort(ABC):
    """Database adapter port

    Abstract interface for database operations. Concrete implementations
    (e.g., PostgreSQL, SQLite) will implement this port.
    """

    @abstractmethod
    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
    ) -> Optional[Any]:
        """Execute a SQL query"""
        pass

    @abstractmethod
    def execute_transaction(
        self,
        queries: list[tuple[str, Optional[tuple]]],
    ) -> bool:
        """Execute multiple queries in a transaction"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection"""
        pass

    # NEW: cursor() 메서드 추가
    @abstractmethod
    def cursor(self, cursor_factory: Optional[Type] = None):
        """Context manager for DB-API 2.0 compatible cursor

        Provides a low-level cursor interface for complex queries
        that require fine-grained control over transactions.

        Args:
            cursor_factory: Optional cursor factory class

        Yields:
            DB-API 2.0 compatible cursor

        Example:
            >>> with db.cursor() as cursor:
            ...     cursor.execute("SELECT * FROM orders")
            ...     results = cursor.fetchall()
        """
        pass
```

### 서비스 레이어 사용 예시

**PositionService (수정 불필요, 이미 사용 중):**

```python
# position_service.py line 124
def get_all_positions(self) -> List[Position]:
    query = """
    SELECT id, symbol, qty, avg_price, created_at, updated_at
    FROM positions
    ORDER BY symbol
    """

    with self.db.cursor() as cursor:  # ← 이 패턴이 작동하게 됨
        cursor.execute(query)
        rows = cursor.fetchall()

    positions = []
    for row in rows:
        positions.append(self._row_to_position(row))

    return positions
```

**MarketLifecycleService (수정 불필요):**

```python
# test_market_lifecycle_integration.py line 136
with market_lifecycle_service.db.cursor() as cursor:  # ← 작동
    cursor.execute(query)
    row = cursor.fetchone()
```

### API 공존 전략

```
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQLAdapter Public API                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  High-Level API (Existing):                                │
│  - execute_query(query, params, fetch_one, fetch_all)      │
│  - execute_transaction(queries)                            │
│                                                             │
│  Low-Level API (New):                                      │
│  - cursor(cursor_factory) → context manager                │
│                                                             │
│  Both use:                                                 │
│  - ThreadedConnectionPool for connection management        │
│  - getconn() / putconn() pattern for pool safety           │
│  - try/finally for guaranteed cleanup                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Usage Recommendations:
- execute_query(): Simple SELECT, INSERT, UPDATE, DELETE
- execute_transaction(): Multi-statement transactions
- cursor(): Complex queries, manual transaction control, bulk operations
```

---

## 추적성 (Traceability)

### TAG Mapping

| TAG | 설명 | 파일 | 라인 |
|-----|------|------|------|
| TAG-SPEC-DB-002-001 | cursor() 컨텍스트 매니저 구현 | postgresql_adapter.py | TBD (new method) |
| TAG-SPEC-DB-002-002 | DatabasePort 인터페이스 확장 | port.py | TBD (new abstract method) |
| TAG-SPEC-DB-002-003 | 트랜잭션 경계 준수 | postgresql_adapter.py | cursor() method |
| TAG-SPEC-DB-002-004 | execute_query()와의 공존 | postgresql_adapter.py | 전체 클래스 |
| TAG-SPEC-DB-002-005 | 서비스 레이어 통합 검증 | service_layer/*.py | 기존 사용 위치 |
| TAG-SPEC-DB-002-006 | RealDictCursor 기본 사용 | postgresql_adapter.py | cursor() default param |

### Requirements Coverage

| Requirement | Component | Status |
|-------------|-----------|--------|
| REQ-UB-001: cursor() 컨텍스트 매니저 제공 | PostgreSQLAdapter.cursor() | TODO |
| REQ-UB-002: DatabasePort 인터페이스 확장 | DatabasePort.cursor() | TODO |
| REQ-UB-003: 커넥션 풀 관리 | cursor() implementation | TODO |
| REQ-ED-001: cursor() 진입 시 커넥션 획득 | cursor().__enter__ | TODO |
| REQ-ED-002: cursor() 정상 종료 시 커밋 및 반환 | cursor().__exit__ success | TODO |
| REQ-ED-003: cursor() 예외 시 롤백 및 반환 | cursor().__exit__ exception | TODO |
| REQ-ED-004: cursor_factory 지정 시 사용 | cursor() parameters | TODO |
| REQ-SD-001: 커넥션 풀 초기화 확인 | cursor() validation | TODO |
| REQ-SD-002: 선택적 cursor_factory 처리 | cursor() default param | TODO |
| REQ-UN-001: 커넥션 풀 우회 금지 | cursor() implementation | TODO |
| REQ-UN-002: 커넥션 누수 금지 | cursor() finally block | TODO |
| REQ-UN-003: execute_query()와의 동작 불일치 금지 | cursor() consistency | TODO |

### 서비스 레이어 사용 위치

| 파일 | 라인 | 메서드 | 사용 패턴 |
|------|------|--------|----------|
| position_service.py | 124 | get_all_positions() | with db.cursor() |
| position_service.py | 143 | _get_fills_by_symbol() | with db.cursor() |
| position_service.py | 175 | _upsert_position() | with db.cursor() |
| position_service.py | 194 | _get_position_from_db() | with db.cursor() |
| position_service.py | 209 | _log_event() | with db.cursor() |
| test_market_lifecycle_integration.py | 136 | test_system_state_persistence | with db.cursor() |

---

## 참고 (References)

### 관련 문서

- [Python DB-API 2.0 Specification](https://www.python.org/dev/peps/pep-0249/)
- [psycopg2.cursor documentation](https://www.psycopg.org/docs/cursor.html)
- [psycopg2.extras.RealDictCursor](https://www.psycopg.org/docs/extras.html#psycopg2.extras.RealDictCursor)
- [Python contextlib.contextmanager](https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager)

### 연관 SPEC

- **SPEC-DB-001**: Connection Pool Leak Fix (선행 조건)
- **SPEC-DB-003**: Database Schema Initialization (병렬 진행 가능)
- **SPEC-BACKEND-API-001-P3**: KIS Broker Adapter (연동 테스트)

### 코드 예시

**DB-API 2.0 표준 사용:**
```python
# Standard pattern
with connection.cursor() as cursor:
    cursor.execute(query, params)
    results = cursor.fetchall()
    connection.commit()
```

**psycopg2 RealDictCursor:**
```python
# Dict-like row access
cursor = conn.cursor(cursor_factory=RealDictCursor)
cursor.execute("SELECT id, name FROM users")
row = cursor.fetchone()
print(row["id"], row["name"])  # Dict access
```
