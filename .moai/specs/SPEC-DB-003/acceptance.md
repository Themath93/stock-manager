# SPEC-DB-003: Acceptance Criteria

## 메타데이터

- **SPEC ID**: SPEC-DB-003
- **Acceptance 버전**: 1.0.0
- **Quality Gate**: TRUST 5 프레임워크

---

## Given-When-Then Acceptance Criteria

### AC-001: 데이터베이스 자동 생성

**Given:** PostgreSQL이 실행 중이고 stock_manager_test가 존재하지 않음
**When:** Integration tests가 실행됨 (pytest collection)
**Then:** init_test_db fixture가 자동으로 실행됨
**And:** stock_manager_test 데이터베이스가 생성됨

```bash
# Given - PostgreSQL 실행 중, 데이터베이스 없음
docker-compose up -d postgres
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS stock_manager_test;"

# When - pytest 실행
pytest tests/integration/ -v

# Then - 데이터베이스 생성됨
psql -h localhost -U postgres -c "\l" | grep stock_manager_test
```

### AC-002: 마이그레이션 자동 적용

**Given:** stock_manager_test 데이터베이스가 비어 있음
**When:** init_test_db fixture 실행
**Then:** 모든 마이그레이션이 순서대로 적용됨
**And:** 모든 테이블과 enum 타입이 존재함

```python
# Given
import psycopg2
conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/stock_manager_test")
cursor = conn.cursor()

# When - pytest 실행 (fixture 자동 실행)
# 터미널에서: pytest tests/integration/ -v -s

# Then - 테이블 확인
cursor.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
)
tables = [row[0] for row in cursor.fetchall()]

expected_tables = [
    "strategies", "strategy_params", "orders", "fills", "positions",
    "events", "system_states", "daily_settlements"
]
for table in expected_tables:
    assert table in tables, f"Table {table} not found"
```

### AC-003: 개발 데이터베이스 보호

**Given:** DATABASE_URL이 stock_manager(개발 DB)를 가리킴
**When:** init_test_db fixture 실행
**Then:** ValueError 즉시 발생
**And:** 에러 메시지에 "stock_manager" 언급됨
**And:** 어떤 테스트도 실행되지 않음

```python
# Given
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/stock_manager"

# When & Then
with pytest.raises(ValueError) as exc_info:
    # fixture 실행 시도
    init_test_db()

assert "stock_manager" in str(exc_info.value)
assert "development" in str(exc_info.value).lower()
```

### AC-004: PostgreSQL 연결 실패 시 skip

**Given:** PostgreSQL이 실행 중이지 않음
**When:** Integration tests가 실행됨
**Then:** init_test_db fixture가 pytest.skip() 호출
**And:** skip 메시지에 "PostgreSQL" 언급됨
**And:** 테스트 실패가 아닌 skip으로 기록됨

```bash
# Given - PostgreSQL 중지
docker-compose down

# When - pytest 실행
pytest tests/integration/ -v

# Then - skip 메시지
# Expected output: SKIPPED (reasons: ["Cannot connect to PostgreSQL..."])
```

### AC-005: 데이터베이스 이미 존재 시 재사용

**Given:** stock_manager_test 데이터베이스가 이미 존재함
**When:** init_test_db fixture 실행
**Then:** CREATE DATABASE 오류 없이 진행됨
**And:** 기존 스키마가 유지됨 (DROP하지 않음)

```python
# Given - 데이터베이스 이미 존재
# (이전 pytest 실행으로 생성됨)

# When - pytest 재실행
pytest tests/integration/ -v

# Then - "already exists" 메시지 출력
# 출력: [init_test_db] Database exists: stock_manager_test
# 테스트가 정상 실행됨 (DROP 없음)
```

### AC-006: Integration Tests 자동 작동

**Given:** init_test_db fixture가 실행됨
**When:** integration tests 실행
**Then:** 4개 에러 테스트가 PASS로 변경됨

```bash
# Before SPEC-DB-003:
# test_full_market_lifecycle - ERROR (database does not exist)
# test_system_state_persistence - ERROR (database does not exist)
# test_state_recovery_with_orders - ERROR (database does not exist)
# test_daily_settlement_creation - ERROR (database does not exist)

# After SPEC-DB-003:
pytest tests/integration/service_layer/test_market_lifecycle_integration.py -v

# Expected: All tests PASS (fixture initialized database)
```

### AC-007: 스키마 검증

**Given:** init_test_db fixture가 마이그레이션을 적용함
**When:** 스키마 검증 실행
**Then:** 모든 필수 테이블 존재 확인
**And:** 모든 enum 타입 존재 확인

```python
# Given - fixture 실행 완료

# When - 스키마 검증
from tests.integration.db_utils import verify_schema

is_valid = verify_schema(
    db_url="postgresql://postgres:postgres@localhost:5432/stock_manager_test",
    expected_tables=[
        "orders", "fills", "positions", "system_states", "daily_settlements"
    ]
)

# Then
assert is_valid is True
```

### AC-008: 테스트 완료 후 데이터베이스 유지

**Given:** Integration tests 실행 중
**When:** 모든 tests가 완료됨
**Then:** stock_manager_test 데이터베이스가 삭제되지 않음
**And:** 다음 pytest 실행에서 데이터베이스 재사용됨

```bash
# First run
pytest tests/integration/ -v
# 데이터베이스 생성됨

# Between runs - 데이터베이스 확인
psql -h localhost -U postgres -l | grep stock_manager_test
# 데이터베이스 존재함

# Second run
pytest tests/integration/ -v
# 데이터베이스 재사용 (CREATED 메시지 없음)
```

---

## 품질 게이트 (Quality Gates)

### TRUST 5 Framework

**Tested (테스트됨):**
- [ ] init_test_db fixture 동작 테스트
- [ ] 데이터베이스 생성 테스트
- [ ] 마이그레이션 적용 테스트
- [ ] 개발 DB 보호 테스트
- [ ] PostgreSQL 없을 때 skip 테스트
- [ ] 4개 에러 테스트 PASS 확인

**Readable (가독성):**
- [ ] fixture 코드가 명확함
- [ ] 로그 메시지가 이해하기 쉬움
- [ ] 에러 메시지가 구체적임
- [ ] 주석이 포함됨

**Unified (일관성):**
- [ ] fixture가 기존 conftest와 일관성
- [ ] 에러 처리가 일관적임
- [ ] 로그 형식이 일관적임

**Secured (보안):**
- [ ] 개발 데이터베이스 보호
- [ ] 데이터베이스 이름 강력 검증
- [ ] 에러 메시지에 민감 정보 노출 안 함
- [ ] 연결 정보 안전하게 처리

**Trackable (추적 가능):**
- [ ] TAG-SPEC-DB-003-* 태그가 코드에 매핑됨
- [ ] Git 커밋 메시지가 SPEC-ID 참조
- [ ] fixture 로그로 실행 추적 가능

---

## 테스트 시나리오

### Scenario 1: 첫 실행

```gherkin
Feature: Integration Test Database Initialization

  Scenario: 첫 실행 시 데이터베이스 생성
    Given PostgreSQL이 실행 중
    And stock_manager_test 데이터베이스가 존재하지 않음
    When Integration tests 실행 (pytest)
    Then init_test_db fixture가 자동 실행됨
    And stock_manager_test 데이터베이스 생성됨
    And 모든 마이그레이션 적용됨
    And Integration tests 정상 실행됨
```

### Scenario 2: 재실행

```gherkin
  Scenario: 데이터베이스 존재 시 재사용
    Given stock_manager_test 데이터베이스가 이미 존재
    And 마이그레이션이 이미 적용됨
    When Integration tests 재실행
    Then init_test_db fixture가 기존 데이터베이스 확인
    And CREATE DATABASE 실행 안 함
    And Integration tests 정상 실행됨
```

### Scenario 3: PostgreSQL 없음

```gherkin
  Scenario: PostgreSQL 미실행 시 skip
    Given PostgreSQL이 실행 중이 아님
    When Integration tests 실행 시도
    Then init_test_db fixture가 연결 실패 감지
    And pytest.skip() 호출
    And tests skipped로 기록됨
    And failure가 아님
```

### Scenario 4: 개발 DB 보호

```gherkin
  Scenario: DATABASE_URL이 개발 DB를 가리킬 때 방어
    Given DATABASE_URL이 stock_manager를 가리킴
    When init_test_db fixture 실행
    Then ValueError 즉시 발생
    And 에러 메시지에 개발 DB 언급
    And 어떤 테스트도 실행 안 됨
    And 개발 데이터 보호됨
```

### Scenario 5: 마이그레이션 실패

```gherkin
  Scenario: 마이그레이션 파일 실행 실패 시
    Given PostgreSQL이 실행 중
    And 마이그레이션 SQL 파일에 오류 있음
    When init_test_db fixture가 마이그레이션 적용 시도
    Then SQL 실행 실패 감지
    And pytest.fail() 호출
    And 실패 메시지에 실패한 마이그레이션 파일명 포함
    And 테스트 실행 중단됨
```

---

## 검증 방법

### 자동화된 테스트

**실행 명령어:**
```bash
# Integration tests 실행
pytest tests/integration/ -v

# 특정 테스트 모듈
pytest tests/integration/service_layer/test_market_lifecycle_integration.py -v

# 상세 로그와 함께
pytest tests/integration/ -v -s

# 특정 테스트만
pytest tests/integration/service_layer/test_market_lifecycle_integration.py::TestMarketLifecycleServiceIntegration::test_system_state_persistence -v
```

### 수동 검증

**데이터베이스 상태 확인:**
```bash
# PostgreSQL 연결
psql -h localhost -U postgres

# 데이터베이스 목록
\l

# stock_manager_test 연결
\c stock_manager_test

# 테이블 목록
\dt

# enum 타입 목록
dT

# 나가기
\q
```

**fixture 로그 확인:**
```bash
# pytest 실행 시 로그 출력
pytest tests/integration/ -v -s 2>&1 | grep "\[init_test_db\]"

# Expected output:
# [init_test_db] Database exists: stock_manager_test
# [init_test_db] Applying: 0001_init.sql
# [init_test_db] Applying: 0002_add_order_fill_fields.sql
# [init_test_db] Applying: market_lifecycle_schema.sql
# [init_test_db] Tables created: 15
# [init_test_db] Initialization complete
```

### Integration Test 결과 확인

**Before/After 비교:**
```bash
# Before SPEC-DB-003
pytest tests/integration/service_layer/test_market_lifecycle_integration.py -v
# Expected: 5 passed, 4 errors, 1 skipped in 9.87s

# After SPEC-DB-003
pytest tests/integration/service_layer/test_market_lifecycle_integration.py -v
# Expected: 9 passed, 1 skipped in 12.34s
```

---

## 성공 기준 (Definition of Done)

- [ ] 모든 AC (Acceptance Criteria) 충족
- [ ] 4개 에러 테스트가 PASS로 변경
- [ ] init_test_db fixture 구현 완료
- [ ] 데이터베이스 자동 생성 작동
- [ ] 모든 마이그레이션 적용 작동
- [ ] 개발 데이터베이스 보호 검증
- [ ] PostgreSQL 없을 때 skip 작동
- [ ] 코드 리뷰 완료
- [ ] TRUST 5 품질 기준 통과
- [ ] 문서 업데이트 완료
- [ ] Git 커밋 및 태그 완료

### 특별 품질 기준

**자동화:**
- [ ] 수동 데이터베이스 설정 불필요
- [ ] pytest 한 번으로 모두 작동
- [ ] CI/CD에서 바로 사용 가능

**안전성:**
- [ ] 개발 데이터 100% 보호
- [ ] 잘못된 설정 시 즉시 실패
- [ ] 명확한 에러 메시지

**성능:**
- [ ] 데이터베이스 재사용 (매번 생성 안 함)
- [ ] fixture 오버헤드 최소화
- [ ] 테스트 실행 시간 10초 이내 증가
