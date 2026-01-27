# SPEC-DB-003: Integration Test Database Schema Initialization

## 메타데이터

- **SPEC ID**: SPEC-DB-003
- **제목**: Integration Test Database Schema Initialization
- **생성일**: 2026-01-28
- **상태**: planned
- **버전**: 1.0.0
- **우선순위**: MEDIUM
- **담당자**: Alfred (workflow-spec)
- **관련 SPEC**: SPEC-DB-001 (Pool Fix), SPEC-DB-002 (API Interface)
- **유형**: Test Infrastructure (not feature)

---

## 변경 이력 (History)

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-28 | Alfred | 초기 SPEC 작성 |

---

## 개요

Integration Test 실행을 위한 PostgreSQL Test Database 자동 초기화 시스템을 구축하여 4개의 에러가 발생하는 테스트를 복구합니다.

**문제 정의:**
- Integration tests가 `stock_manager_test` 데이터베이스를 요구하지만 데이터베이스가 존재하지 않음
- 테스트 fixture가 스키마 초기화를 수행하지 않음
- 마이그레이션 파일이 존재하지만 자동 적용되지 않음

**현재 상태:**
- 4개 테스트 에러: database "stock_manager_test" does not exist
- 실패 테스트: test_full_market_lifecycle, test_system_state_persistence, test_state_recovery_with_orders, test_daily_settlement_creation, test_market_open_close_with_settlement
- 존재하는 마이그레이션: db/migrations/0001_init.sql, 0002_add_order_fill_fields.sql
- 존재하는 스키마: src/stock_manager/adapters/storage/schema/market_lifecycle_schema.sql

**목표:**
- pytest fixture를 통한 테스트 데이터베이스 자동 생성
- 모든 마이그레이션 자동 적용
- 테스트 간 데이터 격리 및 정리
- 개발 데이터베이스와 테스트 데이터베이스 분리

---

## 환경 (Environment)

### 기술 스택

- **Python**: 3.13+
- **데이터베이스**: PostgreSQL 15
- **테스트**: pytest, pytest-asyncio
- **fixture**: pytest fixtures (autouse, scope)
- **관리자 접속**: postgresql://postgres:postgres@localhost:5432/postgres (default db)

### 영향 받는 파일

1. **Test Fixtures** (생성)
   - `tests/integration/conftest.py` (수정 - init_test_db fixture 추가)

2. **DB Utilities** (생성)
   - `tests/integration/db_utils.py` (new - DB 초기화 헬퍼)

3. **Migration Files** (기존, 활용)
   - `db/migrations/0001_init.sql`
   - `db/migrations/0002_add_order_fill_fields.sql`
   - `src/stock_manager/adapters/storage/schema/market_lifecycle_schema.sql`

4. **Integration Tests** (수정 불필요, fixture 자동 적용)
   - `tests/integration/service_layer/test_market_lifecycle_integration.py`
   - `tests/integration/adapters/storage/test_postgresql_integration.py`

### PostgreSQL Schema 구조

**Core Tables (0001_init.sql):**
- strategies, strategy_params, orders, fills, positions
- events, strategy_param_drafts, trade_journals, ai_job_runs

**Market Lifecycle Tables (market_lifecycle_schema.sql):**
- system_states
- daily_settlements

---

## 가정 (Assumptions)

### 기술적 가정

1. **PostgreSQL 관리자 접근**
   - 테스트 환경에서 postgres 사용자로 데이터베이스 생성 가능하다고 가정
   - confidence: HIGH
   - evidence: docker-compose 설정 확인
   - risk if wrong: 테스트 DB 생성 실패
   - validation method: postgres 접속 권한 확인

2. **마이그레이션 순서 의존성**
   - 0001_init.sql → 0002_add_order_fill_fields.sql 순서가 중요하다고 가정
   - confidence: HIGH
   - evidence: 파일 번호 체계
   - risk if wrong: 스키마 생성 실패
   - validation method: 순서대로 적용 테스트

3. **fixture scope**
   - module scope가 적절하다고 가정 (모든 테스트가 동일 스키마 사용)
   - confidence: MEDIUM
   - evidence: 현재 테스트 구조
   - risk if wrong: 테스트 간 데이터 간섭
   - validation method: 테스트 격리 확인

### 비즈니스 가정

1. **테스트 데이터베이스 분리**
   - 개발용 stock_manager와 테스트용 stock_manager_test를 분리한다고 가정
   - confidence: HIGH
   - evidence: 현재 conftest.py 설정
   - risk if wrong: 테스트가 개발 데이터를 방해
   - validation method: 데이터베이스 이름 확인

---

## 요구사항 (Requirements)

### TAG BLOCK

```
TAG-SPEC-DB-003-001: init_test_db fixture 구현
TAG-SPEC-DB-003-002: 데이터베이스 생성 로직
TAG-SPEC-DB-003-003: 마이그레이션 자동 적용
TAG-SPEC-DB-003-004: 스키마 검증
TAG-SPEC-DB-003-005: 테스트 데이터 정리
TAG-SPEC-DB-003-006: 개발 DB 보호
```

### 1. Ubiquitous Requirements (항상 지원)

**REQ-UB-001: 테스트 데이터베이스 자동 초기화**
- Integration test suite 시작 전 테스트 데이터베이스가 초기화되어야 한다 (SHALL)
- init_test_db fixture가 module scope, autouse로 실행되어야 한다 (SHALL)
- 모든 테이블과 enum 타입이 존재해야 한다 (SHALL)
- 왜: 모든 integration test가 유효한 스키마를 필요로 함
- 영향: 없으면 모든 integration test 실패

**REQ-UB-002: 마이그레이션 순차 적용**
- 모든 마이그레이션 파일이 순서대로 적용되어야 한다 (SHALL)
- 마이그레이션 실패 시 즉시 실패를 보고해야 한다 (SHALL)
- 이미 적용된 마이그레이션은 건너뛰어야 한다 (SHOULD)
- 왜: 스키마 일관성 유지
- 영향: 순서가 틀리면 FK 오류 발생

**REQ-UB-003: 개발 데이터베이스 보호**
- 테스트 초기화는 개발 데이터베이스(stock_manager)를 수정해서는 안 된다 (MUST NOT)
- 테스트 데이터베이스 이름이 stock_manager_test여야 한다 (MUST)
- fixture는 데이터베이스 이름을 검증해야 한다 (SHALL)
- 왜: 테스트가 개발 환경을 방해하면 안 됨
- 영향: 개발 데이터 손실

### 2. Event-Driven Requirements (WHEN X, THEN Y)

**REQ-ED-001: pytest collection 시작 시 데이터베이스 초기화**
- WHEN pytest collects integration tests
- THEN init_test_db fixture SHALL be triggered (autouse)
- AND SHALL create stock_manager_test database if not exists
- AND SHALL apply all migrations
- 왜: 자동화로 수동 설정 불필요
- 영향: 수동 설정은 잊기 쉬움

**REQ-ED-002: 데이터베이스 미존재 시 생성**
- WHEN init_test_db fixture runs
- AND stock_manager_test database does not exist
- THEN fixture SHALL CREATE DATABASE stock_manager_test
- 왜: 첫 실행 시 데이터베이스 없음
- 영향: 없으면 CREATE DATABASE 권한 에러

**REQ-ED-003: 마이그레이션 실패 시 실패 보고**
- WHEN migration SQL file execution fails
- THEN fixture SHALL log error details
- AND SHALL raise exception with failed migration name
- AND SHALL prevent tests from running
- 왜: 불완전한 스키마로 테스트 실행 방지
- 영향: 불명확한 실패는 디버깅 어려움

**REQ-ED-004: 테스트 완료 후 데이터베이스 유지**
- WHEN test module completes
- THEN fixture SHALL keep stock_manager_test database
- AND SHALL NOT drop database
- 왜: 테스트 실행 간 데이터베이스 재생성 비용 절감
- 영향: 매번 생성하면 느려짐

### 3. State-Driven Requirements (IF condition, THEN action)

**REQ-SD-001: 데이터베이스 이미 존재 시 확인**
- IF stock_manager_test database already exists
- THEN fixture SHALL verify schema compatibility
- AND SHALL apply missing migrations only
- 왜: 불필요한 생성 방지
- 영향: 이미 존재하면 에러 발생

**REQ-SD-002: PostgreSQL 연결 실패 시 처리**
- IF cannot connect to PostgreSQL server
- THEN fixture SHALL skip with clear message
- AND SHALL NOT fail test collection
- 왜: DB 없이도 pytest collection은 가능해야 함
- 영향: 실패하면 다른 테스트도 실행 불가

**REQ-SD-003: 잘못된 데이터베이스 이름 시 방지**
- IF DATABASE_URL points to stock_manager (dev database)
- THEN fixture SHALL raise error immediately
- AND SHALL prevent any test execution
- 왜: 개발 데이터 보호
- 영향: 개발 데이터 손실 위험

### 4. Optional Requirements (가능하면 지원)

**REQ-OP-001: 테스트 간 데이터 정리**
- WHERE test isolation is important
- Fixture SHOULD provide option to truncate tables between tests
- AND SHOULD preserve schema structure
- 왜: 일부 테스트는 깨끗한 상태 필요
- 영향: 선택 사항으로 제공

**REQ-OP-002: 데이터베이스 재생성 옵션**
- WHERE fresh database is needed
- Fixture COULD provide --recreate-db flag
- AND COULD drop and recreate database
- 왜: 스키마 변경 시 유용
- 영향: 마이그레이션 재적용 가능

**REQ-OP-003: 초기화 상세 로깅**
- WHERE debugging initialization issues
- Fixture COULD log each migration applied
- AND COULD log table creation confirmation
- 왜: 문제 진단에 도움
- 영향: 로그 오버헤드 고려

### 5. Unwanted Behaviors (금지된 동작)

**REQ-UN-001: 개발 데이터베이스 수정 금지**
- Init fixture는 stock_manager 데이터베이스를 수정해서는 안 된다 (MUST NOT)
- Init fixture는 stock_manager 데이터베이스를 삭제해서는 안 된다 (MUST NOT)
- 왜: 개발 데이터베이스는 테스트와 격리되어야 함
- 영향: 데이터 손실, 개발 중단

**REQ-UN-002: 마이그레이션 건너뛰기 금지**
- Init fixture는 마이그레이션을 순서대로 적용해야 한다 (MUST)
- Init fixture는 마이그레이션을 무시해서는 안 된다 (MUST NOT)
- 왜: 스키마 불일치로 테스트 실패
- 영향: FK 제약조건 위반

**REQ-UN-003: fixture 실행 실패 후 테스트 진행 금지**
- Init fixture 실패 시 테스트가 실행되어서는 안 된다 (MUST NOT)
- Init fixture는 모든 테스트를 skip해야 한다 (SHALL)
- 왜: 스키마 없는 테스트는 무의미
- 영향: 불명확한 실패 쇄도

---

## 상세 설계 (Specifications)

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    pytest Collection                        │
│  pytest tests/integration/                                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│            conftest.py Fixture Discovery                    │
│  - autouse=True (자동 실행)                                 │
│  - scope="module" (모듈당 한 번)                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              init_test_db Fixture                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. Validate DATABASE_URL                            │    │
│  │    - Must be stock_manager_test                      │    │
│  │ 2. Connect to postgres (default db)                 │    │
│  │    - For database creation                           │    │
│  │ 3. CREATE DATABASE IF NOT EXISTS                     │    │
│  │ 4. Apply migrations in order                         │    │
│  │    - 0001_init.sql                                   │    │
│  │    - 0002_add_order_fill_fields.sql                  │    │
│  │    - market_lifecycle_schema.sql                     │    │
│  │ 5. Verify schema                                     │    │
│  │    - Check tables exist                              │    │
│  │    - Check enums exist                               │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           Integration Tests Run                             │
│  - All tests see valid schema                              │
│  - Tests can use stock_manager_test                        │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 구현: init_test_db Fixture

**conftest.py에 추가할 fixture:**

```python
# tests/integration/conftest.py

import os
import pytest
import psycopg2
from psycopg2 import sql
from pathlib import Path

@pytest.fixture(scope="module", autouse=True)
def init_test_db():
    """
    Initialize test database with schema migrations.

    This fixture runs automatically before any integration tests.
    It creates the stock_manager_test database (if needed) and
    applies all migration files in order.
    """
    # 1. Get test database URL
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/stock_manager_test"
    )

    # Parse database name
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip("/")

    # 2. Validate test database name
    if db_name == "stock_manager":
        raise ValueError(
            "ERROR: DATABASE_URL points to development database 'stock_manager'. "
            "Tests must use 'stock_manager_test' to protect development data."
        )

    if db_name != "stock_manager_test":
        pytest.skip(f"Test database is not 'stock_manager_test': {db_name}")

    # 3. Connect to postgres (default db) for database creation
    admin_conn = None
    try:
        admin_conn = psycopg2.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database="postgres",  # Default db for CREATE DATABASE
            user=parsed.username or "postgres",
            password=parsed.password or ""
        )
        admin_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        admin_cursor = admin_conn.cursor()

        # 4. Create database if not exists
        admin_cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)
        )
        if admin_cursor.fetchone() is None:
            admin_cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
            )
            print(f"[init_test_db] Created database: {db_name}")
        else:
            print(f"[init_test_db] Database exists: {db_name}")

        admin_cursor.close()
        admin_conn.close()

    except psycopg2.OperationalError as e:
        pytest.skip(f"Cannot connect to PostgreSQL: {e}")
    except Exception as e:
        pytest.fail(f"Failed to initialize test database: {e}")

    # 5. Apply migrations
    test_conn = None
    try:
        test_conn = psycopg2.connect(db_url)
        test_cursor = test_conn.cursor()

        # Migration files in order
        project_root = Path(__file__).parent.parent.parent
        migrations = [
            project_root / "db" / "migrations" / "0001_init.sql",
            project_root / "db" / "migrations" / "0002_add_order_fill_fields.sql",
            project_root / "src" / "stock_manager" / "adapters" / "storage" / "schema" / "market_lifecycle_schema.sql",
        ]

        for migration_file in migrations:
            if migration_file.exists():
                print(f"[init_test_db] Applying: {migration_file.name}")
                with open(migration_file, 'r') as f:
                    migration_sql = f.read()
                test_cursor.execute(migration_sql)
                test_conn.commit()
            else:
                print(f"[init_test_db] Skipping (not found): {migration_file}")

        # 6. Verify schema
        test_cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
        tables = [row[0] for row in test_cursor.fetchall()]
        print(f"[init_test_db] Tables created: {len(tables)}")

        test_cursor.close()
        test_conn.close()

        print(f"[init_test_db] Initialization complete")

    except Exception as e:
        if test_conn:
            test_conn.close()
        pytest.fail(f"Failed to apply migrations: {e}")

    # 7. Yield to tests
    yield

    # 8. Cleanup (optional - keep database for next run)
    print(f"[init_test_db] Tests complete, database preserved")
```

### DB Utils Helper Module

**tests/integration/db_utils.py (새 파일):**

```python
"""
Database utilities for integration tests.

Provides helper functions for database initialization,
schema verification, and test data management.
"""

import psycopg2
from typing import List, Optional
from pathlib import Path


def create_database_if_not_exists(
    admin_url: str,
    db_name: str
) -> bool:
    """Create database if it doesn't exist.

    Args:
        admin_url: PostgreSQL admin connection URL
        db_name: Database name to create

    Returns:
        True if database was created, False if already existed
    """
    # Implementation details...
    pass


def apply_migration(
    db_url: str,
    migration_file: Path
) -> bool:
    """Apply a single migration file.

    Args:
        db_url: Database connection URL
        migration_file: Path to SQL migration file

    Returns:
        True if migration was applied successfully
    """
    # Implementation details...
    pass


def verify_schema(
    db_url: str,
    expected_tables: List[str]
) -> bool:
    """Verify that all expected tables exist.

    Args:
        db_url: Database connection URL
        expected_tables: List of expected table names

    Returns:
        True if all tables exist
    """
    # Implementation details...
    pass


def truncate_tables(
    db_url: str,
    exclude_tables: Optional[List[str]] = None
) -> None:
    """Truncate all tables (for test cleanup).

    Args:
        db_url: Database connection URL
        exclude_tables: Tables to skip (e.g., for lookup data)
    """
    # Implementation details...
    pass
```

### Migration Files Structure

```
db/migrations/
├── 0001_init.sql                    # Core schema
├── 0002_add_order_fill_fields.sql   # Additional fields
└── (future migrations)

src/stock_manager/adapters/storage/schema/
├── market_lifecycle_schema.sql      # System states, settlements
├── worker_schema.sql                # Worker tables (if needed)
└── (other schema files)
```

### 테스트 데이터베이스 수명 주기

```
┌──────────────────────────────────────────────────────────────┐
│  pytest tests/integration/ 시작                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  init_test_db Fixture (autouse, module scope)                │
│                                                             │
│  1. DATABASE_URL 검증                                       │
│     IF db_name == "stock_manager": ERROR                    │
│     IF db_name != "stock_manager_test": SKIP                │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  2. PostgreSQL 연결                                          │
│     CONNECT to postgres (default db)                        │
│     IF connection fails: SKIP                               │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  3. 데이터베이스 생성                                        │
│     IF NOT EXISTS: CREATE DATABASE stock_manager_test       │
│     ELSE: Use existing                                      │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  4. 마이그레이션 적용                                        │
│     FOR each migration_file IN migrations:                  │
│         IF file exists:                                     │
│             READ SQL from file                              │
│             EXECUTE SQL                                     │
│             COMMIT                                          │
│         ELSE:                                               │
│             LOG warning                                     │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  5. 스키마 검증                                              │
│     VERIFY expected tables exist                            │
│     VERIFY expected enums exist                            │
│     IF verification fails: FAIL                             │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  6. 테스트 실행                                              │
│     YIELD to test module                                    │
│     All integration tests run with valid schema             │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  7. 정리 (선택)                                              │
│     KEEP database for next run                              │
│     DO NOT drop database                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 추적성 (Traceability)

### TAG Mapping

| TAG | 설명 | 파일 | 라인 |
|-----|------|------|------|
| TAG-SPEC-DB-003-001 | init_test_db fixture 구현 | conftest.py | TBD (new fixture) |
| TAG-SPEC-DB-003-002 | 데이터베이스 생성 로직 | conftest.py | fixture 내부 |
| TAG-SPEC-DB-003-003 | 마이그레이션 자동 적용 | conftest.py | fixture 내부 |
| TAG-SPEC-DB-003-004 | 스키마 검증 | conftest.py | fixture 내부 |
| TAG-SPEC-DB-003-005 | 테스트 데이터 정리 | db_utils.py | TBD (new file) |
| TAG-SPEC-DB-003-006 | 개발 DB 보호 | conftest.py | validation 로직 |

### Requirements Coverage

| Requirement | Component | Status |
|-------------|-----------|--------|
| REQ-UB-001: 테스트 데이터베이스 자동 초기화 | init_test_db fixture | TODO |
| REQ-UB-002: 마이그레이션 순차 적용 | migration application logic | TODO |
| REQ-UB-003: 개발 데이터베이스 보호 | database name validation | TODO |
| REQ-ED-001: pytest collection 시작 시 초기화 | autouse fixture | TODO |
| REQ-ED-002: 데이터베이스 미존재 시 생성 | CREATE DATABASE logic | TODO |
| REQ-ED-003: 마이그레이션 실패 시 실패 보고 | error handling | TODO |
| REQ-ED-004: 테스트 완료 후 데이터베이스 유지 | fixture cleanup | TODO |
| REQ-SD-001: 데이터베이스 이미 존재 시 확인 | EXISTS check | TODO |
| REQ-SD-002: PostgreSQL 연결 실패 시 처리 | skip on error | TODO |
| REQ-SD-003: 잘못된 데이터베이스 이름 시 방지 | validation | TODO |
| REQ-UN-001: 개발 데이터베이스 수정 금지 | name validation | TODO |
| REQ-UN-002: 마이그레이션 건너뛰기 금지 | ordered application | TODO |
| REQ-UN-003: fixture 실행 실패 후 테스트 진행 금지 | pytest.fail on error | TODO |

---

## 참고 (References)

### 관련 문서

- [pytest Fixtures Documentation](https://docs.pytest.org/en/stable/fixture.html)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [PostgreSQL CREATE DATABASE](https://www.postgresql.org/docs/current/sql-createdatabase.html)

### 연관 SPEC

- **SPEC-DB-001**: Connection Pool Leak Fix (병렬 진행 가능)
- **SPEC-DB-002**: PostgreSQLAdapter API Interface (병렬 진행 가능)
- **SPEC-BACKEND-API-001-P3**: KIS Broker Adapter (연동 테스트)

### Migration Files 참조

**db/migrations/0001_init.sql:**
- Core tables: strategies, orders, fills, positions, events
- Enums: order_side, order_type, order_status, event_level

**db/migrations/0002_add_order_fill_fields.sql:**
- Additional columns for orders/fills

**src/stock_manager/adapters/storage/schema/market_lifecycle_schema.sql:**
- Tables: system_states, daily_settlements
- Functions: update_updated_at_column()
- Triggers: Auto-update timestamps
