# SPEC-DB-001: Acceptance Criteria

## 메타데이터

- **SPEC ID**: SPEC-DB-001
- **Acceptance 버전**: 1.0.0
- **Quality Gate**: TRUST 5 프레임워크

---

## Given-When-Then Acceptance Criteria

### AC-001: execute_query 커넥션 반환

**Given:** PostgreSQL 연결 풀이 초기화됨
**When:** 사용자가 execute_query()를 호출하여 SELECT 쿼리 실행
**Then:** 쿼리 결과가 반환되고 커넥션이 풀로 반환됨
**And:** pool_status를 확인하면 모든 커넥션이 반환됨

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()
initial_status = adapter.pool_status

# When
result = adapter.execute_query("SELECT 1 as test", fetch_one=True)

# Then
assert result["test"] == 1
final_status = adapter.pool_status
# 커넥션이 반환되었는지 확인 (방법은 구현에 따라 다름)
```

### AC-002: execute_query 예외 시 커넥션 반환

**Given:** PostgreSQL 연결 풀이 초기화됨
**When:** 사용자가 execute_query()를 호출하여 잘못된 쿼리 실행
**Then:** 예외가 발생하고 커넥션이 풀로 반환됨
**And:** 후속 execute_query() 호출이 정상 작동

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When - 잘못된 쿼리
with pytest.raises(Exception):
    adapter.execute_query("SELECT * FROM nonexistent_table")

# Then - 커넥션이 반환되었으므로 다음 호출이 성공
result = adapter.execute_query("SELECT 1 as test", fetch_one=True)
assert result["test"] == 1
```

### AC-003: execute_transaction 커넥션 반환

**Given:** PostgreSQL 연결 풀이 초기화됨
**When:** 사용자가 execute_transaction()을 호출하여 여러 쿼리 실행
**Then:** 트랜잭션이 커밋되고 커넥션이 풀로 반환됨

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When
queries = [
    ("INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
     ("TEST-001", "key-001", "005930", "BUY", "MARKET", 100, None, "NEW")),
    ("UPDATE orders SET status = %s WHERE broker_order_id = %s",
     ("SENT", "TEST-001")),
]
result = adapter.execute_transaction(queries)

# Then
assert result is True
# 커넥션이 반환되었는지 확인
```

### AC-004: execute_transaction 실패 시 커넥션 반환

**Given:** PostgreSQL 연결 풀이 초기화됨
**When:** 사용자가 execute_transaction()을 호출하고 트랜잭션 중 실패
**Then:** 예외가 발생하고 커넥션이 풀로 반환됨
**And:** 롤백이 자동으로 수행됨

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When - 존재하지 않는 테이블 참조
queries = [
    ("INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
     ("TEST-002", "key-002", "005930", "BUY", "MARKET", 100, None, "NEW")),
    ("INSERT INTO nonexistent_table VALUES (1)", None),
]
result = adapter.execute_transaction(queries)

# Then
assert result is False  # 실패 반환
# 첫 번째 INSERT가 롤백되었는지 확인
order = adapter.execute_query(
    "SELECT * FROM orders WHERE broker_order_id = %s",
    params=("TEST-002",),
    fetch_one=True
)
assert order is None  # 롤백됨
```

### AC-005: transaction 컨텍스트 매니저 커넥션 반환

**Given:** PostgreSQL 연결 풀이 초기화됨
**When:** 사용자가 with adapter.transaction() 블록 사용
**Then:** 블록 완료 후 커넥션이 풀로 반환됨

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When
with adapter.transaction() as conn:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                   ("TEST-003", "key-003", "005930", "BUY", "MARKET", 100, None, "NEW"))

# Then - 커넥션이 반환되었으므로 다음 작업 가능
result = adapter.execute_query("SELECT 1 as test", fetch_one=True)
assert result["test"] == 1
```

### AC-006: transaction 예외 시 커넥션 반환

**Given:** PostgreSQL 연결 풀이 초기화됨
**When:** 사용자가 with adapter.transaction() 블록에서 예외 발생
**Then:** 롤백이 수행되고 커넥션이 풀로 반환됨

```python
# Given
adapter = PostgreSQLAdapter()
adapter.connect()

# When - 예외 발생
with pytest.raises(Exception):
    with adapter.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (broker_order_id, idempotency_key, symbol, side, order_type, qty, price, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                       ("TEST-004", "key-004", "005930", "BUY", "MARKET", 100, None, "NEW"))
        cursor.execute("INSERT INTO nonexistent_table VALUES (1)")  # 예외

# Then - 롤백되었으므로 레코드 없음
order = adapter.execute_query(
    "SELECT * FROM orders WHERE broker_order_id = %s",
    params=("TEST-004",),
    fetch_one=True
)
assert order is None

# And - 커넥션이 반환되었으므로 다음 작업 가능
result = adapter.execute_query("SELECT 1 as test", fetch_one=True)
assert result["test"] == 1
```

### AC-007: 반복 실행 시 커넥션 풀 누수 없음

**Given:** PostgreSQL 연결 풀이 초기화됨 (max_connections=10)
**When:** 사용자가 execute_query()를 20회 반복 호출
**Then:** PoolError가 발생하지 않음
**And:** 모든 호출이 성공

```python
# Given
adapter = PostgreSQLAdapter(min_connections=1, max_connections=10)
adapter.connect()

# When - 풀 크기보다 많이 호출
for i in range(20):
    result = adapter.execute_query("SELECT %s as iteration", params=(i,), fetch_one=True)
    assert result["iteration"] == i

# Then - PoolError 없이 모두 성공
# (실제 검증 방법은 구현에 따라 다름)
```

### AC-008: 커넥션 풀 고갈 시 명확한 에러

**Given:** PostgreSQL 연결 풀이 초기화됨 (max_connections=1)
**When:** 사용자가 동시에 2개 이상의 커넥션 요청
**Then:** PoolError 또는 명확한 에러 메시지 발생

```python
# Given
adapter = PostgreSQLAdapter(min_connections=1, max_connections=1)
adapter.connect()

# When - 풀 크기 초과 시도
# (실제 테스트는 스레드 또는 비동기로 수행)
# 예시만 보여줌:
try:
    # 첫 번째 커넥션 보류
    conn1 = adapter._connection_pool.getconn()
    # 두 번째 커넥션 시도 (실패 예상)
    conn2 = adapter._connection_pool.getconn()
except pool.PoolError as e:
    # Then - 명확한 에러 메시지
    assert "exhausted" in str(e).lower() or "pool" in str(e).lower()
finally:
    adapter._connection_pool.putconn(conn1)
```

---

## 품질 게이트 (Quality Gates)

### TRUST 5 Framework

**Tested (테스트됨):**
- [ ] 모든 실패하던 6개 테스트가 PASS
- [ ] 커넥션 누수 감지 테스트 추가
- [ ] 예외 상황 테스트 커버리지

**Readable (가독성):**
- [ ] try-finally 블록이 명확하게 구조화됨
- [ ] 변수 명명이 명확함 (conn, finally 등)
- [ ] 주석이 포함된 경우 명확함

**Unified (일관성):**
- [ ] execute_query, execute_transaction, transaction 모두 동일 패턴 사용
- [ ] 에러 처리가 일관적임
- [ ] 코드 스타일이 프로젝트 규칙과 일치

**Secured (보안):**
- [ ] SQL 인젝션 방지 (params 사용)
- [ ] 에러 메시지에 민감 정보 노출 안 함
- [ ] 커넥션 정보 로깅 시 마스킹

**Trackable (추적 가능):**
- [ ] 모든 변경사항이 git commit으로 기록됨
- [ ] TAG-SPEC-DB-001-* 태그가 코드에 매핑됨
- [ ] 커밋 메시지가 SPEC-ID 참조

---

## 테스트 시나리오

### Scenario 1: 정상 작동 흐름

```gherkin
Feature: PostgreSQL Connection Pool Management

  Scenario: execute_query 성공 시 커넥션 반환
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 SELECT 쿼리 실행
    Then 쿼리 결과 반환됨
    And 커넥션이 풀로 반환됨
    And 후속 쿼리가 정상 작동
```

### Scenario 2: 예외 처리

```gherkin
  Scenario: execute_query 실패 시 커넥션 반환
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 잘못된 쿼리 실행
    Then 예외가 발생함
    And 커넥션이 풀로 반환됨
    And 후속 쿼리가 정상 작동
```

### Scenario 3: 트랜잭션 처리

```gherkin
  Scenario: execute_transaction 커밋 시 커넥션 반환
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 여러 쿼리 트랜잭션 실행
    Then 트랜잭션이 커밋됨
    And 커넥션이 풀로 반환됨

  Scenario: execute_transaction 실패 시 롤백 및 커넥션 반환
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 트랜잭션 중 실패하는 쿼리 실행
    Then 트랜잭션이 롤백됨
    And 커넥션이 풀로 반환됨
    And False 반환됨
```

### Scenario 4: 컨텍스트 매니저

```gherkin
  Scenario: transaction 컨텍스트 매니저 정상 완료
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 with transaction() 블록 사용
    Then 블록 내 작업이 커밋됨
    And 커넥션이 풀로 반환됨

  Scenario: transaction 컨텍스트 매니저 예외 발생
    Given PostgreSQL 어댑터가 연결됨
    When 사용자가 with transaction() 블록에서 예외 발생
    Then 트랜잭션이 롤백됨
    And 커넥션이 풀로 반환됨
    And 예외가 전파됨
```

### Scenario 5: 스트레스 테스트

```gherkin
  Scenario: 반복 실행 시 누수 없음
    Given PostgreSQL 어댑터가 max_connections=10으로 연결됨
    When 사용자가 20회 쿼리 실행
    Then PoolError 없이 모두 성공
```

---

## 검증 방법

### 자동화된 테스트

**실행 명령어:**
```bash
# PostgreSQL 연결 확인
docker-compose up -d postgres

# Integration tests 실행
pytest tests/integration/adapters/storage/test_postgresql_integration.py -v

# 특정 테스트 실행
pytest tests/integration/adapters/storage/test_postgresql_integration.py::TestPostgreSQLCRUDOperations::test_insert_fill -v

# 커버리지 확인
pytest --cov=stock_manager.adapters.storage.postgresql_adapter tests/integration/adapters/storage/test_postgresql_integration.py
```

### 수동 검증

**커넥션 풀 상태 확인:**
```python
# PostgreSQL에서 직접 커넥션 수 확인
SELECT count(*) FROM pg_stat_activity WHERE datname = 'stock_manager';

# 어댑터에서 상태 확인
adapter = PostgreSQLAdapter()
adapter.connect()
print(adapter.pool_status)
```

### 성능 벤치마크

**반복 실행 테스트:**
```python
import time

adapter = PostgreSQLAdapter()
adapter.connect()

start = time.time()
for i in range(100):
    adapter.execute_query("SELECT %s", params=(i,), fetch_one=True)
end = time.time()

print(f"100 queries in {end - start:.2f}s")
print(f"Average: {(end - start) / 100 * 1000:.2f}ms per query")
```

---

## Definition of Done

- [ ] 모든 AC (Acceptance Criteria) 충족
- [ ] 6개 실패하던 테스트가 PASS
- [ ] 코드 리뷰 완료
- [ ] 테스트 커버리지 85% 이상
- [ ] TRUST 5 품질 기준 통과
- [ ] 문서 업데이트 완료
- [ ] Git 커밋 및 태그 완료
