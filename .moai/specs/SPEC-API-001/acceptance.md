# SPEC-API-001: 수용 기준 (Acceptance Criteria)

## 수용 기준

### AC-001: API ID 상수 정의

**Given:** KISRestClient 클래스

**When:** 클래스 속성 검사

**Then:** API_ORDER_CASH, API_ORDER_CANCEL 상수 존재

### AC-002: place_order TR_ID 헤더

**Given:** 유효한 OrderRequest 객체

**When:** place_order 호출

**Then:** _make_request가 tr_id 매개변수와 함께 호출됨
**And:** tr_id가 None이 아님

### AC-003: cancel_order TR_ID 헤더

**Given:** 유효한 broker_order_id와 account_id

**When:** cancel_order 호출

**Then:** _make_request가 tr_id 매개변수와 함께 호출됨

### AC-004: get_orders TR_ID 헤더

**Given:** 유효한 account_id

**When:** get_orders 호출

**Then:** _make_request가 tr_id 매개변수와 함께 호출됨

### AC-005: 모의투자 TR_ID 사용

**Given:** config.mode == Mode.PAPER

**When:** KIS API 호출

**Then:** paper_tr_id 값 사용

### AC-006: 실거래 TR_ID 사용

**Given:** config.mode == Mode.LIVE

**When:** KIS API 호출

**Then:** real_tr_id 값 사용

### AC-007: TR_ID 누락 시 에러

**Given:** 존재하지 않는 API ID

**When:** get_tr_id 호출

**Then:** ValueError 발생
**And:** 에러 메시지에 "TR_ID not found" 포함

## Integration Test Scenarios

### 시나리오 1: 주문 전송 with TR_ID

```gherkin
Scenario: place_order includes TR_ID in headers
  Given KIS API credentials가 설정됨
  And 모의투자 모드로 설정됨
  When 사용자가 현금 주문 요청
  Then TR_ID 헤더가 "TTTC0801U"로 설정됨
  And 요청이 KIS 서버로 전송됨
  And 주문 ID가 반환됨
```

### 시나리오 2: 주문 취소 with TR_ID

```gherkin
Scenario: cancel_order includes TR_ID in headers
  Given 유효한 broker_order_id
  When 사용자가 주문 취소 요청
  Then TR_ID 헤더가 "TTTC0901U"로 설정됨
  And 취소 요청이 전송됨
```

### 시나리오 3: TR_ID 매핑 누락

```gherkin
Scenario: API ID not in mapping
  Given TR_ID 매핑 파일에 없는 API ID
  When get_tr_id 호출
  Then ValueError가 발생
  And 에러 메시지에 해당 API ID 포함
```

## Definition of Done

- [ ] 모든 AC 통과
- [ ] 단위 테스트 작성 완료
- [ ] 모든 KIS API 메서드에 TR_ID 포함
- [ ] 모의투자/실거래 TR_ID 구분 확인
- [ ] TR_ID 매핑 파일 로드 검증
- [ ] 통합 테스트 통과 (실제 환경에서)
