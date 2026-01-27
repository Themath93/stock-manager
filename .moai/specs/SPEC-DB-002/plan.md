# SPEC-DB-002: Implementation Plan

## 메타데이터

- **SPEC ID**: SPEC-DB-002
- **계획 버전**: 1.0.0
- **마일스톤**: 1단계 (필수 구현)

---

## 구현 마일스톤

### Milestone 1: cursor() 컨텍스트 매니저 구현 (필수)

**목표:** DB-API 2.0 호환 cursor() 메서드 구현

#### 작업 항목

1. **PostgreSQLAdapter에 cursor() 메서드 추가**
   - @contextmanager 데코레이터 사용
   - 커넥션 풀 통합 (getconn/putconn)
   - 예외 처리 및 정리

2. **DatabasePort 인터페이스 확장**
   - cursor() 추상 메서드 정의
   - docstring 추가

3. **서비스 레이어 호환성 검증**
   - PositionService 테스트
   - MarketLifecycleService 테스트
   - 기존 코드 수정 불필요 확인

### Milestone 2: 테스트 및 최적화 (선택)

**목표:** 안정성 및 성능 검증

#### 작업 항목

1. **cursor() 전용 테스트 작성**
   - 정상 작동 흐름
   - 예외 처리
   - 트랜잭션 경계

2. **API 공존 테스트**
   - cursor()와 execute_query() 동시 사용
   - 커넥션 풀 상태 확인

3. **성능 최적화**
   - 불필요한 오버헤드 제거
   - 벤치마킹

---

## 기술 접근 방법

### 1. DDD 개발 방법론 적용

**ANALYZE 단계:**
- 서비스 레이어 cursor() 사용 패턴 분석
- DB-API 2.0 표준 요구사항 확인
- psycopg2 RealDictCursor 동작 이해

**PRESERVE 단계:**
- 서비스 레이어 기존 테스트 유지
- cursor() 사용 패턴 스냅샷
- execute_query() API 동작 보존

**IMPROVE 단계:**
- cursor() 메서드 추가
- 인터페이스 확장
- 통합 테스트 통과

### 2. 수정 전략

**파일 1:** `src/stock_manager/adapters/storage/postgresql_adapter.py`

**추가 내용:**
- cursor() 컨텍스트 매니저 메서드 (new)
- import 문 추가: contextmanager (new)

**수정 원칙:**
- 기존 메서드는 수정하지 않음
- 새로운 메서드만 추가
- execute_query()와 동일한 풀 관리 패턴 사용

**파일 2:** `src/stock_manager/adapters/storage/port.py`

**추가 내용:**
- cursor() 추상 메서드 (new)

**수정 원칙:**
- 기존 메서드는 유지
- 새로운 추상 메서드만 추가
- LSP (Liskov Substitution Principle) 준수

### 3. 테스트 전략

**기존 테스트 (수정 불필요):**
- PositionService의 cursor() 사용이 자동으로 작동
- MarketLifecycleService의 cursor() 사용이 자동으로 작동

**새로운 테스트:**
- cursor() 컨텍스트 매니저 동작
- 예외 시 롤백
- 커넥션 반환 확인

---

## 아키텍처 설계

### cursor() 수명 주기

```
┌──────────────────────────────────────────────────────────────┐
│  with adapter.cursor() as cursor:                           │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  1. __enter__() 호출                                        │
│     IF _connection_pool is None:                            │
│         raise RuntimeError                                  │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  2. 커넥션 획득                                              │
│     conn = pool.getconn()                                   │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  3. 커서 생성                                                │
│     cursor = conn.cursor(cursor_factory)                    │
│     factory = RealDictCursor (default)                      │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  4. yield cursor                                            │
│     caller can use cursor.execute(), fetchall(), etc.       │
└───────────────────────────┬──────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
                    ▼               ▼
              성공 시           예외 시
            ┌─────────┐     ┌─────────────┐
            │ commit  │     │  rollback   │
            └────┬────┘     └──────┬──────┘
                 │                │
                 └────────┬───────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│  5. __exit__() 호출 (항상 실행)                              │
│     finally:                                                 │
│         if cursor: cursor.close()                            │
│         if conn: pool.putconn(conn)  ← 핵심                 │
└──────────────────────────────────────────────────────────────┘
```

### 코드 구조

**cursor() 메서드 구조:**

```python
@contextmanager
def cursor(self, cursor_factory=None):
    # 1. 초기화 확인
    if self._connection_pool is None:
        raise RuntimeError("...")

    # 2. 기본값 설정
    factory = cursor_factory or RealDictCursor

    conn = None
    cur = None

    try:
        # 3. 커넥션 획득
        conn = self._connection_pool.getconn()

        # 4. 커서 생성
        cur = conn.cursor(cursor_factory=factory)

        # 5. yield
        yield cur

        # 6. 성공 시 커밋
        conn.commit()

    except Exception as e:
        # 7. 예외 시 롤백
        if conn:
            conn.rollback()
        logger.error(f"...")
        raise

    finally:
        # 8. 정리 (항상 실행)
        if cur:
            cur.close()
        if conn:
            self._connection_pool.putconn(conn)
```

### API 공존 설계

```
┌─────────────────────────────────────────────────────────────┐
│           PostgreSQLAdapter Public Methods                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  High-Level API:                                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ execute_query(query, params, fetch_one, fetch_all)  │    │
│  │   → Abstracts cursor management                     │    │
│  │   → Simple one-liner queries                        │    │
│  │   → Auto commit/return connection                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Low-Level API:                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ cursor(cursor_factory) → Context Manager            │    │
│  │   → Direct cursor access                            │    │
│  │   → Manual transaction control                     │    │
│  │   → DB-API 2.0 compatible                           │    │
│  │   → Auto commit/rollback on exit                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Shared Internals:                                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ - ThreadedConnectionPool                            │    │
│  │ - getconn() / putconn() pattern                    │    │
│  │ - try/finally cleanup                               │    │
│  │ - Error logging                                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

Usage Decision Tree:
├─ Simple SELECT/INSERT/UPDATE/DELETE?
│  └─ Use execute_query()
├─ Multi-statement transaction?
│  └─ Use execute_transaction()
└─ Complex query, bulk operations, manual control?
   └─ Use cursor()
```

---

## 위험 요소 및 대응 계획

### Risk 1: 트랜잭션 경계 모호성

**위험:** cursor()와 execute_query()를 혼합 사용 시 트랜잭션 경계가 명확하지 않음

**확률:** MEDIUM
**영향:** HIGH

**대응:**
- cursor()는 독립 트랜잭션으로 처리
- execute_query()는 자동 커밋
- 혼합 사용 시 각각 독립적으로 처리됨을 문서화
- 필요시 transaction() 컨텍스트 매니저 사용 권장

### Risk 2: RealDictCursor 성능

**위험:** RealDictCursor가 일반 cursor보다 느릴 수 있음

**확률:** LOW
**영향:** MEDIUM

**대응:**
- RealDictCursor는 딕셔너리 오버헤드가 있음
- 그러나 편의성이 이점을 상회
- 성능이 중요한 경우 cursor_factory로 일반 cursor 지정 가능
- 벤치마크로 영향 확인

### Risk 3: 인터페이스 확장으로 인한 기존 구현 영향

**위험:** DatabasePort에 cursor() 추가로 다른 구현체 (Mock 등) 영향

**확률:** MEDIUM
**영향:** MEDIUM

**대응:**
- MockAdapter에 cursor() 스텁 추가
- 추상 메서드이므로 구현 강제
- 모든 DatabasePort 구현체 확인

### Risk 4: 서비스 레이어 커플링

**위험:** 서비스 레이어가 PostgreSQL 특정 API에 의존

**확률:** LOW
**영향:** MEDIUM

**대응:**
- cursor()는 표준 DB-API 2.0 패턴
- 대부분의 DB 어댑터가 유사한 패턴 지원
- PostgreSQL 특정 기능은 최소화

---

## 성공 기준

### Milestone 1 완료 기준

- [ ] PostgreSQLAdapter.cursor() 메서드 구현 완료
- [ ] DatabasePort.cursor() 추상 메서드 정의 완료
- [ ] PositionService 테스트 통과
- [ ] MarketLifecycleService 테스트 통과
- [ ] test_system_state_persistence PASS
- [ ] cursor()에서 커넥션 누수 없음
- [ ] execute_query()와 공존 가능

### Milestone 2 완료 기준

- [ ] cursor() 전용 테스트 작성 완료
- [ ] 예외 처리 테스트 통과
- [ ] 트랜잭션 경계 테스트 통과
- [ ] API 공존 테스트 통과
- [ ] 테스트 커버리지 85% 이상
- [ ] 성능 벤치마크 기록

---

## 의존성

### 선행 조건

- **SPEC-DB-001 완료**: Connection pool leak fix 필수
- PostgreSQL 데이터베이스 실행 중
- pytest 환경 설정 완료

### 후속 작업

- SPEC-DB-003: Database Schema Initialization (병렬 진행 가능)
- 서비스 레이어 추가 테스트 (선택)

---

## 구현 예상 시간

- Milestone 1: 3-4시간
  - cursor() 메서드 구현: 1.5시간
  - DatabasePort 인터페이스 수정: 0.5시간
  - 서비스 레이어 테스트 통과: 1시간
  - 버그 수정 및 검증: 1시간

- Milestone 2: 1-2시간 (선택)
  - cursor() 전용 테스트: 1시간
  - API 공존 테스트: 0.5시간
  - 벤치마킹: 0.5시간

**총 예상 시간:** 4-6시간
