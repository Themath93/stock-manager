# SPEC-FIX-001: 수용 기준 (Acceptance Criteria)

## 수용 기준

### AC-001: SQL Placeholder %s 사용

**Given:** Service Layer 모든 SQL 쿼리

**When:** Grep으로 placeholder 패턴 검색

**Then:** $1, $2 패턴이 존재하지 않음
**And:** 모든 쿼리가 %s 사용

### AC-002: LockService 정상 동작

**Given:** lock_service.py가 수정됨

**When:** acquire_lock 호출

**Then:** Database ProgrammingError 없이 실행

### AC-003: WorkerLifecycleService 정상 동작

**Given:** worker_lifecycle_service.py가 수정됨

**When:** register_worker 호출

**Then:** Database ProgrammingError 없이 실행

### AC-004: DailySummaryService 정상 동작

**Given:** daily_summary_service.py가 수정됨

**When:** create_summary 호출

**Then:** Database ProgrammingError 없이 실행

### AC-005: Market Data Poller 데이터 반환

**Given:** market_data_poller.py mock 구현

**When:** discover_candidates 호출

**Then:** 빈 리스트가 아닌 MarketData 리스트 반환
**And:** 각 항목에 symbol, name, price 필드 존재

### AC-006: Placeholder 검증 스크립트

**Given:** 프로젝트 루트

**When:** 다음 명령 실행

```bash
grep -r '\$[1-9]' src/stock_manager/service_layer/ | grep -v '.pyc'
```

**Then:** 출력이 비어 있어야 함 (exit code 1)

## Integration Test Scenarios

### 시나리오 1: Lock Service 동작

```gherkin
Scenario: Lock acquisition with %s placeholders
  Given stock_locks 테이블이 존재
  When worker가 "AAPL" 종목 lock 획득 시도
  Then lock이 성공적으로 생성됨
  And ProgrammingError가 발생하지 않음
```

### 시나리오 2: Market Data Polling

```gherkin
Scenario: Discover candidates with mock data
  Given market_data_poller가 초기화됨
  When discover_candidates 호출
  Then 최소 1개 이상의 candidate 반환
  And 첫 번째 candidate에 symbol 필드 존재
```

## Definition of Done

- [ ] 모든 AC 통과
- [ ] Grep 검증 통과 ($1, $2 패턴 없음)
- [ ] 단위 테스트 통과
- [ ] Service 통합 테스트 통과
- [ ] Market Data Poller mock 데이터 반환 확인
