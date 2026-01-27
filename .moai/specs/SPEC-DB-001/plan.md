# SPEC-DB-001: Implementation Plan

## 메타데이터

- **SPEC ID**: SPEC-DB-001
- **계획 버전**: 1.0.0
- **마일스톤**: 1단계 (필수 수정)

---

## 구현 마일스톤

### Milestone 1: Connection Pool Leak Fix (필수)

**목표:** 커넥션 풀 누수 완전 해결

#### 작업 항목

1. **execute_query() 메서드 수정**
   - `with pool.getconn() as conn:` 패턴 제거
   - try-finally 블록으로 putconn() 보장
   - 예외 처리 개선

2. **execute_transaction() 메서드 수정**
   - `with pool.getconn() as conn:` 패턴 제거
   - try-finally 블록으로 putconn() 보장
   - 트랜잭션 롤백 확인

3. **transaction() 컨텍스트 매니저 검증**
   - 현재 구현이 올바른지 확인
   - 필요시 개선

4. **커넥션 풀 상태 모니터링 강화**
   - pool_status 속성 개선
   - 디버깅용 로깅 추가

### Milestone 2: Test Coverage (선택)

**목표:** 회귀 방지를 위한 테스트 강화

#### 작업 항목

1. **커넥션 누수 감지 테스트**
   - 풀 상태 확인 테스트
   - 반복 호출 후 풀 상태 검증

2. **스레드 안전성 테스트**
   - 동시 실행 테스트
   - 경합 조건 확인

---

## 기술 접근 방법

### 1. DDD 개발 방법론 적용

**ANALYZE 단계:**
- 현재 PostgreSQLAdapter 구조 분석
- 커넥션 수명 주기 매핑
- 누수 발생 지점 식별

**PRESERVE 단계:**
- 기존 테스트 작성 (Characterization Tests)
- execute_query, execute_transaction 동작 스냅샷
- 풀 상태 확인 방법 문서화

**IMPROVE 단계:**
- 커넥션 반환 로직 수정
- 테스트 통과 확인
- 리팩토링

### 2. 수정 전략

**파일:** `src/stock_manager/adapters/storage/postgresql_adapter.py`

**수정 범위:**
- Line 84-126: execute_query() 메서드
- Line 128-159: execute_transaction() 메서드
- Line 173-198: transaction() 컨텍스트 매니저 (검증만)

**수정 원칙:**
1. 최소 변경 범위
2. API 호환성 유지
3. 모든 예외 경로에서 finally 보장

### 3. 테스트 전략

**기존 테스트:**
- `tests/integration/adapters/storage/test_postgresql_integration.py`
- 6개 실패 테스트가 PASS 되는지 확인

**추가 테스트:**
- 커넥션 풀 상태 검증
- 반복 실행 후 누수 확인
- 예외 상황에서 커넥션 반환 확인

---

## 아키텍처 설계

### 커넥션 수명 주기

```
┌──────────────────────────────────────────────────────────────┐
│  execute_query() 호출                                        │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  1. pool 초기화 확인                                         │
│     IF _connection_pool is None:                             │
│         raise RuntimeError                                   │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  2. 커넥션 획득                                              │
│     conn = pool.getconn()                                    │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  3. try:                                                     │
│     cursor = conn.cursor()                                   │
│     cursor.execute(query)                                    │
│     fetch_one/fetch_all/commit                               │
└───────────────────────────┬──────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
                    ▼               ▼
              성공 시           예외 시
            결과 반환        예외 전파
                    │               │
                    └───────┬───────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  4. finally: (항상 실행)                                     │
│     pool.putconn(conn)  ← 핵심 수정 사항                    │
└──────────────────────────────────────────────────────────────┘
```

### 코드 구조

**execute_query() 수정 후 구조:**

```python
def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
    # 1. 초기화 확인
    if self._connection_pool is None:
        raise RuntimeError("Connection pool not initialized")

    conn = None  # 2. finally에서 접근 가능하도록

    try:
        # 3. 커넥션 획득
        conn = self._connection_pool.getconn()

        # 4. 쿼리 실행
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
        # 5. 에러 로깅 및 재전파
        logger.error(f"Query failed: {e}")
        raise

    finally:
        # 6. 항상 커넥션 반환 (핵심 수정)
        if conn:
            self._connection_pool.putconn(conn)
```

---

## 위험 요소 및 대응 계획

### Risk 1: psycopg2 버전 호환성

**위험:** 다른 psycopg2 버전에서 동작差异

**확률:** LOW
**영향:** MEDIUM

**대응:**
- psycopg2-binary 2.9+ 확인
- 공식 문서 참조
- 테스트 환경에서 검증

### Risk 2: 스레드 안전성

**위험:** ThreadedConnectionPool 동시 접근 시 문제

**확률:** LOW
**영향:** HIGH

**대응:**
- ThreadedConnectionPool은 스레드 안전함
- 그러나 어댑터 수준에서 공유 상태 최소화
- 다중 스레드 테스트로 검증

### Risk 3. 성능 영향

**위험:** try-finally 추가로 인한 성능 저하

**확률:** LOW
**영향:** LOW

**대응:**
- finally 블록 오버헤드는 미미함
- 벤치마크로 확인
- 커넥션 풀의 이점이 훨씬 큼

---

## 성공 기준

### Milestone 1 완료 기준

- [ ] execute_query()에서 모든 경로가 putconn() 호출
- [ ] execute_transaction()에서 모든 경로가 putconn() 호출
- [ ] transaction() 컨텍스트 매니저가 올바름
- [ ] 6개 실패 테스트가 PASS
- [ ] 커넥션 풀 고갈 에러가 발생하지 않음

### Milestone 2 완료 기준

- [ ] 반복 실행 테스트 통과
- [ ] 스레드 안전성 테스트 통과
- [ ] 테스트 커버리지 85% 이상 유지
- [ ] pool_status가 정확한 정보 제공

---

## 의존성

### 선행 조건

- PostgreSQL 데이터베이스 실행 중
- pytest 환경 설정 완료
- psycopg2-binary 설치됨

### 후속 작업

- SPEC-DB-002: PostgreSQLAdapter API Interface (이 SPEC 완료 후 시작)
- SPEC-DB-003: Database Schema Initialization (병렬 진행 가능)

---

## 구현 예상 시간

- Milestone 1: 2-3시간
  - 코드 수정: 1시간
  - 테스트 실행 및 검증: 1시간
  - 버그 수정: 1시간

- Milestone 2: 1-2시간 (선택)
  - 추가 테스트 작성: 1시간
  - 검증 및 수정: 1시간

**총 예상 시간:** 3-5시간
