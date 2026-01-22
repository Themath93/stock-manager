# 수용 기준: 주문 실행 및 상태 관리 시스템

## 1. 개요

본 문서는 SPEC-BACKEND-002의 구현 완료를 위한 수용 기준을 정의합니다. Given/When/Then 테스트 시나리오, 엣지 케이스, 성공 기준, 품질 게이트를 포함합니다.

---

## 2. 테스트 시나리오 (Given/When/Then)

### 시나리오 1: 주문 생성 및 idempotency_key 중복 방지

**Given:**
- OrderRequest 객체 생성됨
  - symbol: "005930"
  - side: "BUY"
  - order_type: "LIMIT"
  - qty: 10
  - price: 50000
  - idempotency_key: "order-20260123-001"

**When:**
- 사용자가 `order_service.create_order(request)` 호출 (1회)

**Then:**
- Order 객체가 반환됨
- order.idempotency_key == "order-20260123-001"
- order.status == "NEW"
- orders 테이블에 레코드 생성됨
- OrderCreatedEvent 발행됨

**When:**
- 사용자가 동일한 idempotency_key로 `create_order(request)` 호출 (2회)

**Then:**
- 기존 Order 객체가 반환됨 (새 레코드 생성 안 함)
- IdempotencyConflictEvent 발행됨 (WARN 레벨)
- orders 테이블에 새 레코드 없음

---

### 시나리오 2: 주문 전송 및 체결 처리

**Given:**
- Order 객체 생성됨 (status: NEW)
- OrderRequest 객체 생성됨

**When:**
- 사용자가 `order_service.create_order(request)` 호출
- 사용자가 `order_service.send_order(order_id)` 호출

**Then:**
- 브로커에 주문 전송됨
- broker_order_id 할당됨
- order.status == "SENT"로 업데이트됨
- OrderSentEvent 발행됨

**When:**
- FillEvent 수신됨
  - broker_order_id: 할당된 ID
  - symbol: "005930"
  - side: "BUY"
  - qty: 5
  - price: 50000

**Then:**
- fills 테이블에 체결 레코드 생성됨
- order.filled_qty == 5
- order.status == "PARTIAL"
- order.avg_fill_price == 50000
- PositionUpdatedEvent 발행됨

**When:**
- FillEvent 추가 수신됨
  - qty: 5 (나머지)

**Then:**
- fills 테이블에 체결 레코드 추가됨
- order.filled_qty == 10
- order.status == "FILLED"
- positions 테이블 업데이트됨
  - symbol: "005930"
  - qty: 10
  - avg_price: 50000
- OrderFilledEvent 발행됨

---

### 시나리오 3: 포지션 계산 (매수/매도 혼합)

**Given:**
- 매수 체결 1: 005930, BUY, 10주, 50000원
- 매수 체결 2: 005930, BUY, 5주, 51000원
- 매도 체결 1: 005930, SELL, 8주, 52000원

**When:**
- 사용자가 `position_service.calculate_position("005930")` 호출

**Then:**
- position.qty == 7 ((10+5) - 8)
- position.avg_price == 50357.14 (가중 평균)
  - 총 매수 금액: (10*50000 + 5*51000) = 755,000원
  - 평균 단가: 755,000 / 15 = 50,333.33원
  - 총 매도 금액: 8 * 52,000 = 416,000원
  - 잔존 금액: 755,000 - 416,000 = 339,000원
  - 잔존 평균: 339,000 / 7 = 48,428.57원 (수정: 체결별 평균가 반영 필요)

**정정된 계산:**
- 매수 체결 1: 10주 * 50,000 = 500,000원
- 매수 체결 2: 5주 * 51,000 = 255,000원
- 총 매수: 15주, 755,000원
- 매도 체결 1: 8주, 416,000원
- 잔존: 7주, 339,000원
- 잔존 평균: 339,000 / 7 = 48,428.57원

---

### 시나리오 4: 리스크 검증 통과

**Given:**
- 리스크 설정:
  - 일 손실 한도: 100만원
  - 종목별 최대 노출: 200만원
  - 총 포지션 수: 5
- 현재 상태:
  - 실현 손익: -50만원
  - 005930 포지션: 100만원

**When:**
- 사용자가 OrderRequest 생성 (005930, BUY, 10주, 50,000원)
- 리스크 검증 통과

**Then:**
- 주문 생성됨
- 주문 전송됨
- RiskViolationEvent 발행 안 함

---

### 시나리오 5: 리스크 검증 실패

**Given:**
- 리스크 설정:
  - 종목별 최대 노출: 150만원
- 현재 상태:
  - 005930 포지션: 100만원

**When:**
- 사용자가 OrderRequest 생성 (005930, BUY, 15주, 50,000원)
- 리스크 검증 실패 (100만원 + 75만원 > 150만원)

**Then:**
- 주문 생성됨
- 주문 상태 REJECTED
- 브로커 전송 안 함
- RiskViolationEvent 발행됨 (WARN 레벨)
- events 테이블에 로깅됨

---

### 시나리오 6: DB 트랜잭션 롤백

**Given:**
- 주문 생성 요청
- DB 연결 불안정

**When:**
- 주문 저장 중 DB 오류 발생

**Then:**
- 진행 중인 모든 DB 변경 롤백
- DatabaseError 발생
- orders 테이블에 부분적 레코드 없음
- events 테이블에 ERROR 레벨 로그 기록됨

---

## 3. 엣지 케이스 테스트

### EC-001: idempotency_key 충돌 (동시 요청)

**Given:**
- 동시에 동일한 idempotency_key로 주문 요청 2개

**When:**
- 첫 번째 요청 완료
- 두 번째 요청 도착

**Then:**
- 첫 번째 요청은 성공
- 두 번째 요청은 기존 주문 반환
- DB UNIQUE 제약 위반 방지
- IdempotencyConflictEvent 발행

---

### EC-002: 체결 수량 초과

**Given:**
- 주문 수량: 10주
- 체결 누적: 8주

**When:**
- FillEvent 수신 (qty: 5주)

**Then:**
- 오류 처리 (체결 수량 초과)
- order.filled_qty == 8 (변경 없음)
- order.status == "PARTIAL" (변경 없음)
- events 테이블에 WARN 레벨 로그 기록됨

---

### EC-003: 주문 취소 실패 (이미 체결됨)

**Given:**
- 주문 상태: FILLED
- 체결 완료

**When:**
- 사용자가 `cancel_order(order_id)` 호출

**Then:**
- 취소 실패 에러 발생
- 주문 상태 FILLED 유지
- events 테이블에 WARN 레벨 로그 기록됨
- 에러 메시지에 "이미 체결됨" 포함

---

### EC-004: 포지션 수량 0

**Given:**
- 005930 매수 체결: 10주
- 005930 매도 체결: 10주

**When:**
- 사용자가 `calculate_position("005930")` 호출

**Then:**
- position.qty == 0
- position.avg_price == 0 또는 None
- 포지션 레코드 유지 또는 삭제 (정책 결정 필요)

---

### EC-005: 동시 체결 이벤트

**Given:**
- WebSocket 연결됨
- 동일 주문에 대해 여러 체결 이벤트 수신

**When:**
- 체결 이벤트 1: qty: 3
- 체결 이벤트 2: qty: 4 (동시 수신)

**Then:**
- 체결 이벤트 순차적 처리
- 체결 누적 정확 (3 → 7)
- 주문 상태 PARTIAL (누적 < 10) 또는 FILLED (누적 >= 10)
- row-level lock으로 동시성 문제 방지

---

### EC-006: 브로커 주문 상태 불일치

**Given:**
- DB 주문 상태: PARTIAL
- 브로커 주문 상태: FILLED

**When:**
- 사용자가 `sync_order_status(order_id)` 호출

**Then:**
- 브로커 상태 우선 적용
- DB 주문 상태: FILLED
- StateSyncEvent 발행
- events 테이블에 INFO 레벨 로그 기록됨

---

### EC-007: 리스크 검증 중 DB 오류

**Given:**
- 리스크 검증 필요
- DB 연결 불안정

**When:**
- 리스크 검증 중 DB 오류 발생

**Then:**
- 주문 생성 차단
- RiskViolationEvent 발행 (검증 실패 간주)
- events 테이블에 ERROR 레벨 로그 기록됨

---

## 4. 성공 기준

### 4.1 기능적 성공 기준

- [ ] 주문 생성 및 DB 저장 성공
- [ ] idempotency_key 중복 방지 기능 동작
- [ ] 주문 전송 및 broker_order_id 할당 성공
- [ ] 체결 처리 및 기록 성공
- [ ] 체결 누적 계산 정확
- [ ] 주문 상태 전이 (NEW → SENT → PARTIAL → FILLED) 정확
- [ ] 포지션 계산 및 업데이트 정확
- [ ] 리스크 검증 통합 기능 동작
- [ ] 리스크 위반 시 주문 차단 기능 동작
- [ ] 주문 취소 기능 동작
- [ ] 상태 동기화 기능 동작

### 4.2 비기능적 성공 기준

- [ ] OrderService가 OrderServicePort 인터페이스를 완전히 구현
- [ ] PositionService가 PositionServicePort 인터페이스를 완전히 구현
- [ ] 모든 주문/체결 동작이 try-except로 감싸짐
- [ ] 모든 오류가 events 테이블에 로깅됨
- [ ] DB 트랜잭션 롤백 기능 동작
- [ ] 동시성 이슈 방지 (row-level lock)

---

## 5. 품질 게이트 (Quality Gates)

### 5.1 코드 품질

| 항목 | 기준 | 측정 방법 |
|------|------|----------|
| 테스트 커버리지 | 70% 이상 | pytest-cov |
| 정적 분석 | 에러 0개, 경고 최소화 | pylint/flake8 |
| 타입 힌트 | 모든 함수/메서드 | mypy |
| 문서화 | 모든 공개 메서드 | docstring |

### 5.2 성능 기준

| 항목 | 기준 | 측정 방법 |
|------|------|----------|
| 주문 생성 시간 | < 100ms (P95) | 로그 분석 |
| 주문 전송 시간 | < 2s (P95) | 로그 분석 |
| 체결 처리 시간 | < 50ms (P95) | 로그 분석 |
| 포지션 계산 시간 | < 200ms (P95) | 로그 분석 |

### 5.3 신뢰성 기준

| 항목 | 기준 | 측정 방법 |
|------|------|----------|
| 주문 생성 성공률 | > 99.9% (정상 환경) | 로그 분석 |
| 체결 처리 성공률 | > 99.9% (정상 환경) | 로그 분석 |
| DB 트랜잭션 실패율 | < 0.1% | 로그 분석 |
| idempotency_key 충돌 방지 | 100% | 단위 테스트 |

---

## 6. 검증 방법

### 6.1 단위 테스트

```bash
# 실행 명령
pytest tests/unit/test_order_service.py -v --cov=src/stock_manager/service_layer
pytest tests/unit/test_position_service.py -v --cov=src/stock_manager/service_layer
pytest tests/unit/test_risk_service.py -v --cov=src/stock_manager/service_layer

# 커버리지 확인
pytest --cov=src/stock_manager/service_layer --cov-report=html
```

### 6.2 통합 테스트

```bash
# Mock 사용 (테스트 환경)
pytest tests/integration/test_order_flow.py -v --mock

# 실제 DB 사용 (테스트 환경)
pytest tests/integration/test_order_flow.py -v --db=test
```

### 6.3 수동 테스트 체크리스트

- [ ] 모의투자 환경에서 주문 전송 및 체결 확인
- [ ] idempotency_key 중복 방지 확인
- [ ] 포지션 계산 정확성 확인 (매수/매도 혼합)
- [ ] 리스크 위반 시 주문 차단 확인
- [ ] 주문 취소 기능 확인
- [ ] DB 트랜잭션 롤백 확인 (오류 시)

---

## 7. 롤백 기준

다음 조건 중 하나라도 충족되지 않으면 롤백 고려:

- [ ] 테스트 커버리지 70% 미달
- [ ] 핵심 기능 (주문 생성/전송, 체결 처리, 포지션 계산) 하나라도 실패
- [ ] idempotency_key 중복 방지 기능 실패
- [ ] 치명적 버그 (데이터 손실, 포지션 계산 오류) 발생
- [ ] 성능 기준 미달 (주문 전송 > 5초)
- [ ] DB 트랜잭션 롤백 실패
