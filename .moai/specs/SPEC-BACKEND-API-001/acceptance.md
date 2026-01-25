# 수용 기준: 한국투자증권 OpenAPI 브로커 어댑터

## 1. 개요

본 문서는 SPEC-BACKEND-API-001의 구현 완료를 위한 수용 기준을 정의합니다. Given/When/Then 테스트 시나리오, 엣지 케이스, 성공 기준, 품질 게이트을 포함합니다.

## 1.1 업데이트 내역 (v1.1.0)

- **2026-01-25:** approval_key 발급 테스트 시나리오 추가 (NEW-001)
- **2026-01-25:** 토큰 자동 갱신 테스트 시나리오 추가 (NEW-002)
- **2026-01-25:** 구현 현황에 따른 기존 시나리오 상태 업데이트

---

## 2. 테스트 시나리오 (Given/When/Then)

### 시나리오 1: REST API 인증 성공

**Given:**
- 유효한 KIS_APP_KEY, KIS_APP_SECRET이 환경 변수에 설정됨
- 한국투자증권 OpenAPI 서버가 정상 작동 중

**When:**
- 사용자가 `broker.authenticate()` 호출

**Then:**
- AuthenticationToken 객체가 반환됨
- access_token이 채워짐
- expires_at이 현재 시간 + 24시간으로 설정됨
- events 테이블에 "INFO" 레벨 인증 성공 이벤트 기록됨

---

### 시나리오 2: REST API 주문 전송 성공

**Given:**
- 유효한 인증 토큰이 존재함
- OrderRequest 객체가 생성됨
  - account_id: "12345678"
  - symbol: "005930"
  - side: "BUY"
  - order_type: "LIMIT"
  - qty: 10
  - price: 50000
  - idempotency_key: "order-20260123-001"

**When:**
- 사용자가 `broker.place_order(order)` 호출

**Then:**
- broker_order_id (ODNO)가 반환됨
- orders 테이블에 주문 레코드 생성됨
  - broker_order_id: 반환된 ID
  - idempotency_key: "order-20260123-001"
  - status: "SENT"
- events 테이블에 "INFO" 레벨 주문 전송 이벤트 기록됨

---

### 시나리오 3: WebSocket 연결 및 호가 수신

**Given:**
- 유효한 approval_key가 발급됨
- WebSocket 서버가 정상 작동 중

**When:**
- 사용자가 `broker.connect_websocket()` 호출
- 사용자가 `broker.subscribe_quotes(["005930"], callback)` 호출

**Then:**
- WebSocket 연결이 성공적으로 설정됨
- 호가 채널 (H0UNASP0) 구독 등록됨
- 주가 호가 메시지 수신 시 callback이 호출됨
- QuoteEvent 객체로 변환됨
  - symbol: "005930"
  - bid_price: 호가 매수가
  - ask_price: 호가 매도가
  - bid_qty: 매수 잔량
  - ask_qty: 매도 잔량

---

### 시나리오 4: 토큰 자동 갱신

**Given:**
- 인증 토큰이 30분 전 발급됨 (만료까지 23.5시간)
- 토큰 만료 5분 전 체크 로직이 활성화됨

**When:**
- 현재 시간이 토큰 만료까지 4분 59초 남은 상태에서 `broker.authenticate()` 호출

**Then:**
- 기존 토큰이 만료되지 않았더라도 갱신됨
- 새 access_token이 발급됨
- 새 expires_at이 24시간 후로 설정됨
- 이전 토큰이 폐기됨

---

### 시나리오 5: WebSocket 재연결

**Given:**
- WebSocket이 정상 연결됨
- 네트워크 장애로 연결이 끊어짐

**When:**
- 연결 끊김 감지

**Then:**
- 1초 후 첫 번째 재연결 시도
- 실패 시 2초 후 두 번째 재연결 시도
- 성공 시 데이터 수신 재개
- 5회 연속 실패 시 ConnectionError 발생
- events 테이블에 "ERROR" 레벨 재연결 실패 이벤트 기록됨

---

### 시나리오 6: 401 Unauthorized 발생 시 토큰 갱신 후 재시도

**Given:**
- 인증 토큰이 만료됨 (24시간 경과)
- 사용자가 `broker.place_order(order)` 호출

**When:**
- REST API가 401 Unauthorized 응답 반환

**Then:**
- 자동으로 토큰 갱신 시도
- 새 토큰 발급 후 원래 요청 재시도 (최대 3회)
- 성공 시 주문 정상 처리
- 3회 실패 시 AuthenticationError 발생
- events 테이블에 "WARN" 레벨 토큰 갱신 이벤트 기록됨

**구현 상태:** PENDING (NEW-002)

---

### 시나리오 7: WebSocket approval_key 발급 성공 (NEW-001)

**Given:**
- 유효한 access_token이 존재함
- KIS OpenAPI 서버가 정상 작동 중

**When:**
- 사용자가 `broker.get_approval_key()` 호출

**Then:**
- `/oauth2/Approval` 엔드포인트로 POST 요청 전송
- approval_key가 성공적으로 반환됨
- approval_key가 안전하게 저장됨
- events 테이블에 "INFO" 레벨 발급 성공 이벤트 기록됨
- WebSocket 연결 시 approval_key가 헤더에 포함됨

**검증:**
```python
# Given
broker = KISBrokerAdapter(config)
await broker.authenticate()  # access_token 발급

# When
approval_key = await broker.get_approval_key()

# Then
assert approval_key is not None
assert len(approval_key) > 0
assert broker.approval_key == approval_key
```

**구현 상태:** PENDING (NEW-001)

---

### 시나리오 8: approval_key 발급 실패 시 재시도 (NEW-001)

**Given:**
- 유효한 access_token이 존재함
- KIS OpenAPI 서버가 일시적 오류 상태

**When:**
- 사용자가 `broker.get_approval_key()` 호출
- 서버가 500 Internal Server Error 또는 타임아웃 반환

**Then:**
- 지수 백오프로 최대 3회 재시도 (1s, 2s, 4s)
- 3회 실패 후 AuthenticationError 발생
- events 테이블에 "ERROR" 레벨 발급 실패 이벤트 기록됨
- WebSocket 연결 시도 차단

**구현 상태:** PENDING (NEW-001)

---

### 시나리오 9: 토큰 만료 5분 전 자동 갱신 (NEW-002)

**Given:**
- 인증 토큰이 23시간 56분 전 발급됨 (만료까지 4분)
- 시스템이 정상 작동 중

**When:**
- 사용자가 API 호출 (예: `broker.place_order(order)`)
- 내부적으로 `refresh_token_if_needed()` 체크 실행

**Then:**
- 토큰 만료까지 5분 미만임이 감지됨
- 자동으로 `get_access_token()` 재호출
- 새 access_token이 발급됨
- 기존 토큰이 안전하게 폐기됨
- 새 토큰으로 API 호출이 완료됨
- events 테이블에 "INFO" 레벨 토큰 갱신 이벤트 기록됨

**검증:**
```python
# Given
old_token = broker.auth_token.access_token
old_expires_at = broker.auth_token.expires_at
# 만료까지 4분 남은 상태로 설정

# When
await broker.place_order(order)  # 내부적으로 갱신 체크

# Then
assert broker.auth_token.access_token != old_token
assert broker.auth_token.expires_at > old_expires_at
```

**구현 상태:** PENDING (NEW-002)

---

### 시나리오 10: 토큰 갱신 중 API 호출 대기 (NEW-002)

**Given:**
- 토큰 만료까지 5분 미만임
- 여러 API 호출이 동시에 시도됨

**When:**
- 스레드 A가 `broker.place_order(order1)` 호출
- 스레드 B가 `broker.place_order(order2)` 호출
- 두 호출 모두 토큰 갱신 필요함을 감지

**Then:**
- 첫 번째 호출만 토큰 갱신 실행
- 두 번째 호출은 갱신 완료까지 대기
- 두 호출 모두 새 토큰으로 성공
- 중복 갱신 요청 방지됨 (락 또는 세마포어 사용)

**구현 상태:** PENDING (NEW-002)

---

## 3. 엣지 케이스 테스트

### EC-001: 잘못된 인증 자격증명

**Given:**
- KIS_APP_KEY가 잘못됨

**When:**
- 사용자가 `broker.authenticate()` 호출

**Then:**
- AuthenticationError 발생
- events 테이블에 "ERROR" 레벨 인증 실패 이벤트 기록됨
- 에러 메시지에 "잘못된 앱키 또는 시크릿" 포함

---

### EC-002: 네트워크 타임아웃

**Given:**
- 네트워크 연결이 느림

**When:**
- API 호출 시 30초 타임아웃 발생

**Then:**
- 최대 3회 지수 백오프 재시도 (1s, 2s, 4s)
- 성공 시 정상 응답 반환
- 3회 실패 시 ConnectionError 발생
- events 테이블에 "ERROR" 레벨 타임아웃 이벤트 기록됨

---

### EC-003: Rate Limit 초과 (429)

**Given:**
- 1초당 6회 이상 API 호출

**When:**
- REST API가 429 Too Many Requests 응답 반환

**Then:**
- 지수 백오프 재시도 (5s, 10s, 20s)
- RateLimitError 발생
- events 테이블에 "WARN" 레벨 Rate Limit 초과 이벤트 기록됨

---

### EC-004: 동시 WebSocket 연결 시도

**Given:**
- WebSocket이 이미 연결됨

**When:**
- 사용자가 다시 `broker.connect_websocket()` 호출

**Then:**
- 이미 연결됨 메시지 로그
- 중복 연결 시도 무시
- 기존 연결 유지

---

### EC-005: 잘못된 WebSocket 메시지 수신

**Given:**
- WebSocket 연결됨

**When:**
- 서버에서 잘못된 포맷의 메시지 수신

**Then:**
- 메시지 파싱 실패 로그
- 오류가 발생한 메시지만 건너뜀
- 다른 메시지 정상 처리

---

### EC-006: 주문 취소 실패 (이미 체결됨)

**Given:**
- 주문이 이미 체결됨 (status: FILLED)

**When:**
- 사용자가 `broker.cancel_order(broker_order_id)` 호출

**Then:**
- 취소 실패 에러 발생
- events 테이블에 "WARN" 레벨 취소 실패 이벤트 기록됨
- 에러 메시지에 "이미 체결됨" 포함

---

## 4. 성공 기준 (업데이트: v1.1.0)

### 4.1 기능적 성공 기준

| 항목 | 상태 | 비고 |
|------|------|------|
| REST API 인증 성공 (모의/실전 환경) | ✅ 완료 | access_token 발급 구현됨 |
| REST API 주문 전송 성공 (매수/매도, 지정가/시장가) | ⚠️ 부분 완료 | 기본 구현 완료, 통합 테스트 필요 |
| REST API 주문 취소 성공 | ⏳ 예정 | KISBrokerAdapter 완성 후 |
| REST API 주문 조회 성공 | ⏳ 예정 | KISBrokerAdapter 완성 후 |
| REST API 예수금 조회 성공 | ⏳ 예정 | KISBrokerAdapter 완성 후 |
| WebSocket 연결 성공 | ✅ 완료 | 연결/종료 메서드 구현됨 |
| WebSocket 호가 구독 및 수신 성공 | ✅ 완료 | subscribe_quotes 구현됨 |
| WebSocket 체결 이벤트 구독 및 수신 성공 | ✅ 완료 | subscribe_executions 구현됨 |
| **approval_key 발급 기능 (NEW-001)** | ⏳ 예정 | `/oauth2/Approval` 엔드포인트 호출 필요 |
| **토큰 자동 갱신 기능 (NEW-002)** | ⚠️ 부분 완료 | 만료 체크만 구현, 자동 갱신 로직 필요 |
| WebSocket 재연결 기능 동작 | ✅ 완료 | 지수 백오프 재연결 구현됨 |
| 401 에러 시 토큰 갱신 후 재시도 기능 동작 | ⏳ 예정 | NEW-002 완료 후 |

### 4.2 비기능적 성공 기준

| 항목 | 상태 | 비고 |
|------|------|------|
| KISBrokerAdapter가 BrokerPort 인터페이스를 완전히 구현 | ⚠️ 진행 중 | 주요 메서드 구현됨, 일부 TODO 존재 |
| MockBrokerAdapter로 테스트 가능 | ✅ 완료 | 테스트 더블 구현됨 |
| 모든 외부 API 호출이 try-except로 감싸짐 | ✅ 완료 | 예외 처리 포함됨 |
| 모든 오류가 events 테이블에 로깅됨 | ✅ 완료 | 로깅 구현됨 |
| 민감 정보(appkey, appsecret, token)가 로그에서 마스킹됨 | ✅ 완료 | 마스킹 처리됨 |
| 환경별 URL(LIVE/PAPER) 자동 전환 기능 동작 | ✅ 완료 | KISConfig에서 MODE 기반 전환 |

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
| API 응답 시간 | < 2초 (P95) | 로그 분석 |
| WebSocket 메시지 수신 지연 | < 100ms (P95) | 타임스탬프 비교 |
| 재연결 성공률 | > 95% | 로그 분석 |

### 5.3 신뢰성 기준

| 항목 | 기준 | 측정 방법 |
|------|------|----------|
| API 호출 성공률 | > 99% (정상 환경) | 로그 분석 |
| WebSocket 연결 유지 시간 | > 8시간 (장 중) | 로그 분석 |
| 오류 복구 시간 | < 30초 | 로그 분석 |

---

## 6. 검증 방법

### 6.1 단위 테스트

```bash
# 실행 명령
pytest tests/unit/test_broker_adapter.py -v --cov=src/stock_manager/adapters/broker

# 커버리지 확인
pytest --cov=src/stock_manager/adapters/broker --cov-report=html
```

### 6.2 통합 테스트

```bash
# Mock 사용 (테스트 환경)
pytest tests/integration/test_kis_api.py -v --mock

# 실제 API 사용 (모의투자 환경)
pytest tests/integration/test_kis_api.py -v --mode=paper
```

### 6.3 수동 테스트 체크리스트

- [ ] 모의투자 환경에서 주문 전송 및 체결 확인
- [ ] WebSocket 호가/체결 데이터 실시간 수신 확인
- [ ] 네트워크 끊김 시 재연결 동작 확인
- [ ] 토큰 만료 전 자동 갱신 동작 확인
- [ ] 실전/모의 환경 전환 확인

---

## 7. 롤백 기준

다음 조건 중 하나라도 충족되지 않으면 롤백 고려:

- [ ] 테스트 커버리지 70% 미달
- [ ] 핵심 기능 (인증, 주문, WebSocket) 하나라도 실패
- [ ] 치명적 버그 (데이터 손실, 보안 취약점) 발생
- [ ] 성능 기준 미달 (API 응답 > 5초)
- [ ] 신뢰성 기준 미달 (연결 유지 < 1시간)
