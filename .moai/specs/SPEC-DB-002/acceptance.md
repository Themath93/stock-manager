# SPEC-DB-002: Acceptance Criteria

## 메타데이터

- **SPEC ID**: SPEC-DB-002
- **Acceptance 버전**: 1.0.0
- **Quality Gate**: TRUST 5 프레임워크

---

## Given-When-Then Acceptance Criteria

### AC-001: cursor() 기본 동작

**Given:** PostgreSQLAdapter가 연결됨
**When:** 사용자가 with adapter.cursor() as cursor: 블록 실행
**Then:** DB-API 2.0 호환 커서가 반환됨
**And:** 블록 완료 후 커넥션이 풀로 반환됨

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When
with adapter.cursor() as cursor:
    cursor.execute("SELECT 1 as test")
    result = cursor.fetchone()

# Then
assert result["test"] == 1
```

### AC-002: cursor() RealDictCursor 기본 사용

**Given:** PostgreSQLAdapter가 연결됨
**When:** 사용자가 cursor() 호출 시 cursor_factory 미지정
**Then:** RealDictCursor가 기본으로 사용됨
**And:** 행이 딕셔너리로 액세스 가능함

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When - cursor_factory 미지정
with adapter.cursor() as cursor:
    cursor.execute("SELECT symbol, qty FROM positions LIMIT 1")
    row = cursor.fetchone()

# Then - 딕셔너리 액세스
assert row["symbol"] is not None
assert row["qty"] is not None
```

### AC-003: cursor() 정상 완료 시 커밋

**Given:** PostgreSQLAdapter가 연결됨
**When:** 사용자가 cursor() 블록에서 INSERT 실행 후 정상 종료
**Then:** 트랜잭션이 커밋됨
**And:** 데이터가 데이터베이스에 저장됨

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When
with adapter.cursor() as cursor:
    cursor.execute(
        "INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        ("TEST-CURSOR-001", "key-cursor-001", "005930", "BUY", "MARKET", 100, None, "NEW")
    )

# Then - 커밋되었으므로 다른 커서에서 조회 가능
with adapter.cursor() as cursor:
    cursor.execute("SELECT * FROM orders WHERE broker_order_id = %s", ("TEST-CURSOR-001",))
    result = cursor.fetchone()
    assert result is not None
```

### AC-004: cursor() 예외 시 롤백

**Given:** PostgreSQLAdapter가 연결됨
**When:** 사용자가 cursor() 블록에서 예외 발생
**Then:** 트랜잭션이 롤백됨
**And:** 데이터가 저장되지 않음
**And:** 커넥션이 풀로 반환됨
**And:** 예외가 호출자에게 전파됨

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When - 예외 발생
try:
    with adapter.cursor() as cursor:
        cursor.execute(
            "INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            ("TEST-CURSOR-002", "key-cursor-002", "005930", "BUY", "MARKET", 100, None, "NEW")
        )
        cursor.execute("INSERT INTO nonexistent_table VALUES (1)")  # 예외
except Exception:
    pass

# Then - 롤백되었으므로 레코드 없음
with adapter.cursor() as cursor:
    cursor.execute("SELECT * FROM orders WHERE broker_order_id = %s", ("TEST-CURSOR-002",))
    result = cursor.fetchone()
    assert result is None
```

### AC-005: cursor()와 execute_query() 공존

**Given:** PostgreSQLAdapter가 연결됨
**When:** 사용자가 cursor()와 execute_query()를 혼합 사용
**Then:** 두 API 모두 정상 작동함
**And:** 커넥션 풀이 올바르게 관리됨

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When - 혼합 사용
with adapter.cursor() as cursor:
    cursor.execute("SELECT 1 as test")
    result1 = cursor.fetchone()

result2 = adapter.execute_query("SELECT 2 as test", fetch_one=True)

# Then
assert result1["test"] == 1
assert result2["test"] == 2
```

### AC-006: PositionService 호환성

**Given:** PositionService가 PostgreSQLAdapter로 초기화됨
**When:** PositionService.get_all_positions() 호출
**Then:** cursor() 메서드가 정상 작동함
**And:** 포지션 목록이 반환됨

```python
# Given
from stock_manager.service_layer.position_service import PositionService
position_service = PositionService(adapter)

# When - cursor() 사용하는 메서드
positions = position_service.get_all_positions()

# Then
assert isinstance(positions, list)
```

### AC-007: cursor_factory 지정

**Given:** PostgreSQLAdapter가 연결됨
**When:** 사용자가 cursor(cursor_factory=CustomCursor) 호출
**Then:** 지정한 cursor_factory가 사용됨

```python
# Given
from psycopg2.extensions import cursor as Cursor
adapter = PostgreSQLAdapter()
adapter.connect()

# When - 기본 RealDictCursor 대신 일반 cursor 사용
with adapter.cursor(cursor_factory=Cursor) as cursor:
    cursor.execute("SELECT 1 as test")
    result = cursor.fetchone()

# Then - 튜플로 반환 (딕셔너리 아님)
assert result[0] == 1
```

### AC-008: 커넥션 풀 초기화 안 됨

**Given:** PostgreSQLAdapter가 연결되지 않음
**When:** 사용자가 cursor() 호출
**Then:** RuntimeError가 발생함
**And:** 에러 메시지에 "Connection pool not initialized" 포함됨

```python
# Given - connect() 호출 안 함
adapter = PostgreSQLAdapter()
# adapter.connect()  # 호출하지 않음

# When - cursor() 시도
# Then
with pytest.raises(RuntimeError) as exc_info:
    with adapter.cursor() as cursor:
        pass

assert "Connection pool not initialized" in str(exc_info.value)
```

### AC-009: 중첩 cursor() 호출

**Given:** PostgreSQLAdapter가 연결됨
**When:** 사용자가 cursor()를 중첩하여 호출
**Then:** 각 cursor가 독립적인 커넥션 사용
**And:** 모두 정상 작동함

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When - 중첩 cursor()
with adapter.cursor() as cursor1:
    cursor1.execute("SELECT 1 as test1")
    result1 = cursor1.fetchone()

    with adapter.cursor() as cursor2:
        cursor2.execute("SELECT 2 as test2")
        result2 = cursor2.fetchone()

# Then
assert result1["test1"] == 1
assert result2["test2"] == 2
```

### AC-010: cursor() 후 커넥션 반환 확인

**Given:** PostgreSQLAdapter가 max_connections=1로 연결됨
**When:** 사용자가 cursor() 사용 후 다시 cursor() 호출
**Then:** 두 번째 호출이 성공함 (커넥션이 반환되었으므로)

```python
# Given
adapter = PostgreSQLAdapter(min_connections=1, max_connections=1)
adapter.connect()

# When - 첫 번째 cursor()
with adapter.cursor() as cursor:
    cursor.execute("SELECT 1")

# And - 두 번째 cursor() (성공해야 함)
with adapter.cursor() as cursor:
    cursor.execute("SELECT 2")

# Then - 예외 없이 완료됨
```

---

## 품질 게이트 (Quality Gates)

### TRUST 5 Framework

**Tested (테스트됨):**
- [ ] cursor() 기본 동작 테스트
- [ ] RealDictCursor 기본 사용 테스트
- [ ] 커밋/롤백 테스트
- [ ] 예외 처리 테스트
- [ ] execute_query()와의 공존 테스트
- [ ] PositionService 통합 테스트

**Readable (가독성):**
- [ ] cursor() 메서드가 명확하게 구조화됨
- [ ] @contextmanager 데코레이터 사용이 명확함
- [ ] 변수 명명이 일관적임 (conn, cur)
- [ ] Docstring이 포함됨

**Unified (일관성):**
- [ ] cursor()가 execute_query()와 동일한 풀 관리 패턴 사용
- [ ] 에러 처리가 일관적임
- [ ] DatabasePort 인터페이스가 준수됨

**Secured (보안):**
- [ ] SQL 인젝션 방지 (params 사용)
- [ ] 에러 메시지에 민감 정보 노출 안 함
- [ ] 커넥션 정보 로깅 시 마스킹

**Trackable (추적 가능):**
- [ ] TAG-SPEC-DB-002-* 태그가 코드에 매핑됨
- [ ] Git 커밋 메시지가 SPEC-ID 참조
- [ ] 변경사항이 추적 가능함

---

## 테스트 시나리오

### Scenario 1: 기본 cursor() 사용

```gherkin
Feature: PostgreSQLAdapter cursor() Method

  Scenario: cursor() 기본 동작
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 with adapter.cursor() as cursor: 블록 실행
    And SELECT 쿼리 실행
    Then 결과가 딕셔너리로 반환됨
    And 커넥션이 풀로 반환됨
```

### Scenario 2: 트랜잭션 처리

```gherkin
  Scenario: cursor() 정상 완료 시 커밋
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 cursor() 블록에서 INSERT 실행
    And 블록이 정상 완료됨
    Then 트랜잭션이 커밋됨
    And 데이터가 저장됨

  Scenario: cursor() 예외 시 롤백
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 cursor() 블록에서 예외 발생
    Then 트랜잭션이 롤백됨
    And 데이터가 저장되지 않음
    And 커넥션이 풀로 반환됨
```

### Scenario 3: 서비스 레이어 통합

```gherkin
  Scenario: PositionService 호환성
    Given PositionService가 PostgreSQLAdapter로 초기화됨
    When PositionService.get_all_positions() 호출
    Then cursor() 메서드가 정상 작동
    And 포지션 목록 반환

  Scenario: MarketLifecycleService 호환성
    Given MarketLifecycleService가 PostgreSQLAdapter 사용
    When test_system_state_persistence 실행
    Then cursor() 메서드가 정상 작동
    And 테스트 통과
```

### Scenario 4: API 공존

```gherkin
  Scenario: cursor()와 execute_query() 혼합 사용
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 cursor()와 execute_query() 번갈아 사용
    Then 두 API 모두 정상 작동
    And 커넥션 풀이 올바르게 관리됨
```

### Scenario 5: 커넥션 풀 관리

```gherkin
  Scenario: cursor() 후 커넥션 반환
    Given max_connections=1로 어댑터 연결
    When 사용자가 cursor() 사용
    And 다시 cursor() 호출
    Then 두 번째 호출이 성공
    And PoolError 발생 안 함

  Scenario: 중첩 cursor() 호출
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 cursor()를 중첩 호출
    Then 각 cursor가 독립 커넥션 사용
    And 모두 정상 작동
```

---

## 검증 방법

### 자동화된 테스트

**실행 명령어:**
```bash
# cursor() 전용 테스트
pytest tests/integration/adapters/storage/test_postgresql_cursor.py -v

# 서비스 레이어 통합 테스트
pytest tests/integration/service_layer/test_position_service_integration.py -v
pytest tests/integration/service_layer/test_market_lifecycle_integration.py::TestMarketLifecycleServiceIntegration::test_system_state_persistence -v

# 전체 통합 테스트
pytest tests/integration/ -v

# 커버리지 확인
pytest --cov=stock_manager.adapters.storage.postgresql_adapter tests/integration/ -v
```

### 수동 검증

**cursor() 인터랙티브 테스트:**
```python
from stock_manager.adapters.storage.postgresql_adapter import create_postgresql_adapter

adapter = create_postgresql_adapter(
    database_url="postgresql://postgres:postgres@localhost:5432/stock_manager"
)
adapter.connect()

# 기본 사용
with adapter.cursor() as cursor:
    cursor.execute("SELECT * FROM orders LIMIT 5")
    for row in cursor.fetchall():
        print(row["symbol"], row["status"])

# 커스텀 cursor_factory
from psycopg2.extensions import cursor as Cursor
with adapter.cursor(cursor_factory=Cursor) as cursor:
    cursor.execute("SELECT * FROM orders LIMIT 5")
    for row in cursor.fetchall():
        print(row[0], row[1])  # 튜플 액세스

adapter.close()
```

### API 공존 검증

**혼합 사용 스크립트:**
```python
# cursor() 사용
with adapter.cursor() as cursor:
    cursor.execute("INSERT INTO orders ...")
    # 자동 커밋

# execute_query() 사용
adapter.execute_query("INSERT INTO orders ...")
# 자동 커밋

# transaction() 사용
with adapter.transaction() as conn:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders ...")
    # 커밋 필요 또는 자동 커밋
```

---

## 성공 기준 (Definition of Done)

- [ ] 모든 AC (Acceptance Criteria) 충족
- [ ] test_system_state_persistence PASS
- [ ] PositionService 모든 메서드 작동
- [ ] MarketLifecycleService cursor() 사용 작동
- [ ] 코드 리뷰 완료
- [ ] 테스트 커버리지 85% 이상
- [ ] TRUST 5 품질 기준 통과
- [ ] 문서 업데이트 완료
- [ ] Git 커밋 및 태그 완료

### 특별 품질 기준

**LSP (Liskov Substitution Principle) 준수:**
- [ ] DatabasePort의 모든 구현체가 cursor() 제공
- [ ] MockAdapter에 cursor() 스텁 추가
- [ ] 인터페이스 계약 준수

**Backward Compatibility:**
- [ ] 기존 execute_query() 사용 코드 수정 불필요
- [ ] 기존 테스트 모두 통과
- [ ] API 변경 없이 추가만 이루어짐
