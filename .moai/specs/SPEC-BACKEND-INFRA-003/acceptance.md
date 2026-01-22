# 수용 기준: 장 시작/종료 및 상태 복구 라이프사이클

## 1. 개요

본 문서는 SPEC-BACKEND-INFRA-003의 구현 완료를 위한 수용 기준을 정의합니다. Given/When/Then 테스트 시나리오, 엣지 케이스, 성공 기준, 품질 게이트를 포함합니다.

---

## 2. 테스트 시나리오 (Given/When/Then)

### 시나리오 1: 장 시작 초기화 완료

**Given:**
- 스케줄러가 설정됨 (장 시작 시간: 08:30:00 KST)
- 시스템 상태: OFFLINE
- 환경 변수: KIS_APP_KEY, KIS_APP_SECRET, DB_URL 설정됨

**When:**
- 08:30:00 KST에 `market_lifecycle_service.open_market()` 호출

**Then:**
- 시스템 상태: INITIALIZING
- MarketOpenEvent 발행됨
- 1단계: 설정 로드 완료
- 2단계: 인증 완료 (access_token 발급)
- 3단계: 계좌 확인 완료 (예수금 조회)
- 4단계: 전략 파라미터 로드 완료
- 5단계: 상태 복구 완료
- 6단계: 리스크 가드레일 초기화 완료
- 7단계: 유니버스 확정 완료
- 8단계: 실시간 이벤트 등록 완료 (호가, 체결, 주문 상태)
- 시스템 상태: READY
- MarketReadyEvent 발행됨

---

### 시나리오 2: 상태 복구 및 미체결 주문 복구

**Given:**
- DB에 미체결 주문 존재 (status: SENT, PARTIAL)
  - Order 1: status SENT, broker_order_id: ODNO-001
  - Order 2: status PARTIAL, broker_order_id: ODNO-002

**When:**
- 장 시작 프로세스 중 5단계: 상태 복구 실행
- 브로커 주문 상태 조회

**Case 1: DB와 브로커 상태 일치**
- Order 1: 브로커 상태 SENT
- Order 2: 브로커 상태 PARTIAL

**Then:**
- 상태 동기화 필요 없음
- StateRecoveredEvent 발행 (status: SUCCESS)
- 불일치 수: 0

**Case 2: DB와 브로커 상태 불일치**
- Order 1: 브로커 상태 FILLED
- Order 2: 브로커 상태 CANCELED

**Then:**
- 브로커 상태 우선 적용
- Order 1: DB 상태 SENT → FILLED 업데이트
- Order 2: DB 상태 PARTIAL → CANCELED 업데이트
- StateRecoveredEvent 발행 (status: SUCCESS)
- 불일치 수: 2
- 불일치 주문 ID: [1, 2] 기록
- events 테이블에 INFO 레벨 로그 기록됨

---

### 시나리오 3: 장 마감 정산

**Given:**
- 시스템 상태: READY
- 포지션:
  - 005930: 10주, 평균가 50,000원
  - 006960: 5주, 평균가 80,000원
- 체결 기록:
  - 005930: 매수 10주 @ 50,000, 매도 5주 @ 52,000
  - 006960: 매수 5주 @ 80,000

**When:**
- 15:30:00 KST에 `market_lifecycle_service.close_market()` 호출

**Then:**
- 시스템 상태: CLOSING
- MarketCloseEvent 발행됨
- 1단계: 시스템 상태 CLOSING 전환 완료
- 2단계: 미체결 주문 취소 확인 완료
- 3단계: 포지션 스냅샷 생성 완료
- 4단계: 일일 정산 계산 완료
  - 005930 실현 손익: (52,000 - 50,000) * 5 = 10,000원
  - 006960 실현 손익: 0원
  - 총 실현 손익: 10,000원
  - 005930 평가 손익: 5주 * (현재 가격 - 52,000)
  - 006960 평가 손익: 5주 * (현재 가격 - 80,000)
- 5단계: DailySettlementEvent 발행
- 6단계: 실시간 이벤트 구독 해제 완료
- 7단계: WebSocket 연결 종료 완료
- 8단계: 시스템 상태: CLOSED
- MarketClosedEvent 발행됨

---

### 시나리오 4: 거래 중지 모드

**Given:**
- 장 시작 프로세스 중 5단계: 상태 복구 실행

**When:**
- 브로커 주문 상태 조회 중 치명적 오류 발생

**Then:**
- 상태 복구 중단
- 시스템 상태: STOPPED
- StopModeEvent 발행됨 (ERROR 레벨)
- events 테이블에 ERROR 레벨 로그 기록됨
- 주문 전송 차단됨

**When:**
- 사용자가 주문 생성 요청

**Then:**
- OrderError 발생 (거래 중지 모드)
- 주문 전송 안 함
- 감시/기록만 수행됨

---

### 시나리오 5: 스케줄러 정확성

**Given:**
- 스케줄러 설정
  - 장 시작 시간: 08:30:00 KST
  - 장 종료 시간: 15:30:00 KST
- Asia/Seoul 시간대 설정

**When:**
- 2026-01-23 08:30:00 KST 도달

**Then:**
- 장 시작 프로세스 실행됨
- 시스템 상태 OFFLINE → INITIALIZING → READY 전환
- MarketOpenEvent, MarketReadyEvent 발행됨

**When:**
- 2026-01-23 15:30:00 KST 도달

**Then:**
- 장 종료 프로세스 실행됨
- 시스템 상태 READY → CLOSING → CLOSED 전환
- MarketCloseEvent, MarketClosedEvent 발행됨

---

### 시나리오 6: 포지션 스냅샷 정확성

**Given:**
- 장 종료 시점 포지션:
  - 005930: 10주, 평균가 50,000원
  - 006960: 5주, 평균가 80,000원

**When:**
- 포지션 스냅샷 생성 실행

**Then:**
- 스냅샷 데이터:
  ```json
  {
    "timestamp": "2026-01-23 15:30:00 KST",
    "positions": [
      {"symbol": "005930", "qty": 10, "avg_price": 50000},
      {"symbol": "006960", "qty": 5, "avg_price": 80000}
    ]
  }
  ```
- positions 테이블 또는 별도 테이블에 저장됨
- JSONB 형식으로 저장됨

---

## 3. 엣지 케이스 테스트

### EC-001: 장 시작 시 브로커 인증 실패

**Given:**
- 브로커 인증 자격증명 잘못됨

**When:**
- 장 시작 프로세스 중 2단계: 인증 실행

**Then:**
- 장 시작 실패
- 시스템 상태 OFFLINE 유지
- MarketOpenError 발생
- events 테이블에 ERROR 레벨 로그 기록됨
- 재시작 필요

---

### EC-002: 상태 복구 중 DB 오류

**Given:**
- DB 연결 불안정

**When:**
- 장 시작 프로세스 중 5단계: 상태 복구 실행 중 DB 오류 발생

**Then:**
- 상태 복구 실패
- 시스템 상태 STOPPED로 전환
- StopModeEvent 발행 (ERROR 레벨)
- events 테이블에 ERROR 레벨 로그 기록됨
- 거래 중지 모드로 진입

---

### EC-003: 장 시작 시 WebSocket 연결 실패

**Given:**
- WebSocket 서버 다운

**When:**
- 장 시작 프로세스 중 8단계: 실시간 이벤트 등록 실행

**Then:**
- WebSocket 연결 실패
- 시스템 상태 STOPPED로 전환
- StopModeEvent 발행 (ERROR 레벨)
- events 테이블에 ERROR 레벨 로그 기록됨
- 거래 중지 모드로 진입

---

### EC-004: 장 종료 시 정산 오류

**Given:**
- 장 종료 시점 포지션 스냅샷 생성 중 DB 오류 발생

**When:**
- 장 종료 프로세스 중 3단계: 포지션 스냅샷 생성 실행

**Then:**
- 정산 실패
- 장 종료 프로세스 계속 (WebSocket 종료 등)
- 시스템 상태 CLOSED로 전환
- MarketCloseError 발생
- events 테이블에 ERROR 레벨 로그 기록됨
- 다음 장 시작 전 수동 정산 필요

---

### EC-005: 동시 장 시작 요청

**Given:**
- 스케줄러에서 08:30:00 KST에 장 시작 트리거
- 사용자가 수동으로 동시에 `open_market()` 호출

**When:**
- 두 번째 `open_market()` 호출 시도

**Then:**
- 첫 번째 요청 실행됨
- 두 번째 요청 거부 (이미 INITIALIZING 상태)
- events 테이블에 WARN 레벨 로그 기록됨

---

### EC-006: 상태 복구 시 여러 불일치

**Given:**
- DB 미체결 주문 10개
- 브로커 상태 5개만 FILLED, 나머지 SENT

**When:**
- 상태 복구 실행

**Then:**
- 5개 주문 상태 업데이트 (SENT → FILLED)
- StateRecoveredEvent 발행 (status: PARTIAL)
- 불일치 수: 5
- 불일치 주문 ID: [1, 2, 3, 4, 5] 기록
- events 테이블에 INFO 레벨 로그 기록됨

---

### EC-007: 스케줄러 시간 오차

**Given:**
- 시스템 시간 1초 느림

**When:**
- 2026-01-23 08:30:00 KST 도달 (실제 08:30:01)

**Then:**
- 장 시작 프로세스 1초 지연 실행
- 허용 가능한 오차 (< 5초)
- events 테이블에 WARN 레벨 로그 기록됨 (시간 오차)

---

## 4. 성공 기준

### 4.1 기능적 성공 기준

- [ ] 장 시작 프로세스 완료 (1~9단계)
- [ ] 장 종료 프로세스 완료 (1~8단계)
- [ ] 상태 복구 기능 동작 (DB/브로커 동기화)
- [ ] 미체결 주문 복구 기능 동작
- [ ] 포지션 스냅샷 생성 기능 동작
- [ ] 일일 정산 계산 기능 동작
- [ ] 스케줄러 통합 기능 동작
- [ ] 거래 중지 모드 기능 동작
- [ ] 실시간 이벤트 등록/해제 기능 동작
- [ ] 시스템 상태 전이 정확 (OFFLINE → INITIALIZING → READY → TRADING → CLOSING → CLOSED)

### 4.2 비기능적 성공 기준

- [ ] MarketLifecycleService가 MarketLifecyclePort 인터페이스를 완전히 구현
- [ ] StateRecoveryService가 StateRecoveryPort 인터페이스를 완전히 구현
- [ ] 모든 라이프사이클 동작이 try-except로 감싸짐
- [ ] 모든 오류가 events 테이블에 로깅됨
- [ ] 장 시작 시간 오차 < 5초
- [ ] 장 종료 시간 오차 < 5초
- [ ] 상태 복구 시간 < 30초 (100개 미체결 주문 기준)

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
| 장 시작 완료 시간 | < 60초 | 로그 분석 |
| 장 종료 완료 시간 | < 30초 | 로그 분석 |
| 상태 복구 시간 | < 30초 (100개 주문) | 로그 분석 |
| 포지션 스냅샷 생성 시간 | < 5초 | 로그 분석 |

### 5.3 신뢰성 기준

| 항목 | 기준 | 측정 방법 |
|------|------|----------|
| 장 시작 성공률 | > 99% (정상 환경) | 로그 분석 |
| 장 종료 성공률 | > 99% (정상 환경) | 로그 분석 |
| 상태 복구 성공률 | > 95% (정상 환경) | 로그 분석 |
| 스케줄러 정확성 | 오차 < 5초 | 로그 분석 |

---

## 6. 검증 방법

### 6.1 단위 테스트

```bash
# 실행 명령
pytest tests/unit/test_market_lifecycle_service.py -v --cov=src/stock_manager/service_layer
pytest tests/unit/test_state_recovery_service.py -v --cov=src/stock_manager/service_layer

# 커버리지 확인
pytest --cov=src/stock_manager/service_layer --cov-report=html
```

### 6.2 통합 테스트

```bash
# Mock 사용 (테스트 환경)
pytest tests/integration/test_market_lifecycle.py -v --mock

# 실제 DB 사용 (테스트 환경)
pytest tests/integration/test_market_lifecycle.py -v --db=test
```

### 6.3 수동 테스트 체크리스트

- [ ] 스케줄러 장 시작 시간 정확성 확인
- [ ] 장 시작 전체 프로세스 확인 (1~9단계)
- [ ] 상태 복구 기능 확인 (DB/브로커 동기화)
- [ ] 미체결 주문 복구 기능 확인
- [ ] 스케줄러 장 종료 시간 정확성 확인
- [ ] 장 종료 전체 프로세스 확인 (1~8단계)
- [ ] 포지션 스냅샷 생성 확인
- [ ] 일일 정산 계산 확인
- [ ] 거래 중지 모드 확인 (오류 시)
- [ ] 시스템 상태 전이 확인

---

## 7. 롤백 기준

다음 조건 중 하나라도 충족되지 않으면 롤백 고려:

- [ ] 테스트 커버리지 70% 미달
- [ ] 핵심 기능 (장 시작, 상태 복구, 장 종료) 하나라도 실패
- [ ] 상태 복구 실패 시 거래 중지 모드 작동하지 않음
- [ ] 스케줄러 시간 오차 > 10초
- [ ] 치명적 버그 (데이터 손실, 상태 불일치) 발생
- [ ] 성능 기준 미달 (장 시작 > 120초)
