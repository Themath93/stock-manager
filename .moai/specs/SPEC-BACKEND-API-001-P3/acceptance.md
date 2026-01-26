# Acceptance Criteria: SPEC-BACKEND-API-001-P3

## 개요

본 문서는 SPEC-BACKEND-API-001-P3 (KISBrokerAdapter 구현 완료)의 인수 기준(Acceptance Criteria)을 정의합니다. Given-When-Then 형식의 시나리오로 구현 검증 방법을 제공합니다.

---

## 검증 전제 조건 (Preconditions)

### 환경 설정
- [x] Python 3.13+ 설치됨
- [x] PostgreSQL 15 실행 중 (docker-compose)
- [x] KIS OpenAPI app_key, app_secret 발급됨
- [x] 환경 변수 설정됨 (ACCOUNT_ID, KIS_APP_KEY, KIS_APP_SECRET)

### 의존 컴포넌트
- [x] KISRestClient Phase 2 완료 (토큰, approval_key, 해시키)
- [x] KISWebSocketClient 완료 (연결, 구독, 재연결)
- [x] OrderService 완료 (주문 생성, 전송, 취소)

---

## 인수 기준 (Acceptance Criteria)

### AC-001: KISBrokerAdapter 초기화

**Story**: As a developer, I want to initialize KISBrokerAdapter with account_id so that I can perform trading operations.

**Given-When-Then**:

```gherkin
Scenario: 정상적인 KISBrokerAdapter 초기화
  Given a KISConfig instance with valid app_key and app_secret
  And a valid account_id "1234567890"
  When KISBrokerAdapter is initialized with config and account_id
  Then KISBrokerAdapter instance should be created successfully
  And account_id should be stored as instance variable
  And _initialized flag should be False
  And ws_client should be None

Scenario: account_id가 None인 경우 초기화 실패
  Given a KISConfig instance with valid app_key and app_secret
  And account_id is None
  When KISBrokerAdapter is initialized with config and account_id
  Then ValueError should be raised immediately
  And error message should contain "account_id is required"
  And KISBrokerAdapter instance should not be created

Scenario: account_id가 빈 문자열인 경우 초기화 실패
  Given a KISConfig instance with valid app_key and app_secret
  And account_id is empty string ""
  When KISBrokerAdapter is initialized with config and account_id
  Then ValueError should be raised immediately
  And error message should contain "account_id is required"
```

**검증 방법**:
```python
def test_kis_broker_adapter_init_with_valid_account_id():
    config = KISConfig(
        app_key="test_key",
        app_secret="test_secret",
        mode=KISMode.PAPER,
    )
    adapter = KISBrokerAdapter(config=config, account_id="1234567890")

    assert adapter.account_id == "1234567890"
    assert adapter._initialized is False
    assert adapter.ws_client is None

def test_kis_broker_adapter_init_with_none_account_id():
    config = KISConfig(
        app_key="test_key",
        app_secret="test_secret",
        mode=KISMode.PAPER,
    )

    with pytest.raises(ValueError, match="account_id is required"):
        KISBrokerAdapter(config=config, account_id=None)
```

---

### AC-002: cancel_order 정상 작동

**Story**: As a trading system, I want to cancel an order using broker_order_id so that I can exit positions.

**Given-When-Then**:

```gherkin
Scenario: 정상적인 주문 취소
  Given a KISBrokerAdapter instance with account_id "1234567890"
  And an order was placed with broker_order_id "ORDER123"
  When cancel_order("ORDER123") is called
  Then KISRestClient.cancel_order should be called with broker_order_id="ORDER123" and account_id="1234567890"
  And cancel_order should return True
  And log should contain "Order cancelled successfully: ORDER123"

Scenario: 주문 취소 API 실패
  Given a KISBrokerAdapter instance with account_id "1234567890"
  And KIS API returns error for broker_order_id "INVALID_ORDER"
  When cancel_order("INVALID_ORDER") is called
  Then cancel_order should return False
  And log should contain "Order cancellation failed: INVALID_ORDER"
  And no exception should be raised

Scenario: 주문 취소 중 API 에러 발생
  Given a KISBrokerAdapter instance with account_id "1234567890"
  And KISRestClient raises APIError during cancellation
  When cancel_order("ORDER123") is called
  Then cancel_order should catch APIError
  And cancel_order should return False
  And log should contain error message
  And no exception should propagate to caller
```

**검증 방법**:
```python
def test_cancel_order_success(mock_rest_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter.rest_client = mock_rest_client
    mock_rest_client.cancel_order.return_value = True

    result = adapter.cancel_order("ORDER123")

    assert result is True
    mock_rest_client.cancel_order.assert_called_once_with(
        broker_order_id="ORDER123",
        account_id="1234567890",
    )

def test_cancel_order_api_failure(mock_rest_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter.rest_client = mock_rest_client
    mock_rest_client.cancel_order.return_value = False

    result = adapter.cancel_order("INVALID_ORDER")

    assert result is False

def test_cancel_order_api_error(mock_rest_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter.rest_client = mock_rest_client
    mock_rest_client.cancel_order.side_effect = APIError("API Error")

    result = adapter.cancel_order("ORDER123")

    assert result is False
```

---

### AC-003: WebSocket 지연 초기화

**Story**: As a performance-conscious developer, I want WebSocket to initialize lazily so that startup time is minimized.

**Given-When-Then**:

```gherkin
Scenario: subscribe_quotes 호출 시 WebSocket 초기화
  Given a KISBrokerAdapter instance with account_id
  And WebSocket is not initialized (_initialized == False)
  When subscribe_quotes(["005930"], callback) is called
  Then _initialize_websocket should be called automatically
  And approval_key should be fetched from REST API
  And WebSocket connection should be established
  And quote subscription should be sent for symbol "005930"
  And _initialized flag should be True

Scenario: subscribe_executions 호출 시 WebSocket 초기화
  Given a KISBrokerAdapter instance with account_id
  And WebSocket is not initialized (_initialized == False)
  When subscribe_executions(callback) is called
  Then _initialize_websocket should be called automatically
  And WebSocket connection should be established
  And execution subscription should be sent
  And _initialized flag should be True

Scenario: 이미 초기화된 경우 중복 초기화 방지
  Given a KISBrokerAdapter instance with account_id
  And WebSocket is already initialized (_initialized == True)
  When subscribe_quotes(["000660"], callback) is called
  Then _initialize_websocket should NOT be called again
  And new subscription should be added to existing WebSocket
```

**검증 방법**:
```python
def test_subscribe_quotes_initializes_websocket(mock_ws_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter._initialized = False
    adapter.ws_client = mock_ws_client

    callback = lambda quote: None
    adapter.subscribe_quotes(["005930"], callback)

    assert adapter._initialized is True
    mock_ws_client.connect_websocket.assert_called_once()
    mock_ws_client.subscribe_quotes.assert_called_once_with(["005930"], callback)

def test_subscribe_quotes_no_reinitialization(mock_ws_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter._initialized = True
    adapter.ws_client = mock_ws_client

    callback = lambda quote: None
    adapter.subscribe_quotes(["000660"], callback)

    mock_ws_client.connect_websocket.assert_not_called()
    mock_ws_client.subscribe_quotes.assert_called_once_with(["000660"], callback)
```

---

### AC-004: 인증 토큰 발급

**Story**: As a trading system, I need to authenticate with KIS API to access trading features.

**Given-When-Then**:

```gherkin
Scenario: 정상적인 인증 토큰 발급
  Given a KISBrokerAdapter instance with valid config
  When authenticate() is called
  Then AuthenticationToken should be returned
  And token should have valid access_token field
  And token should have expires_in field (seconds)
  And token should have expires_at field (datetime)
  And token should be cached in TokenManager
  And log should contain "Authentication successful"

Scenario: 인증 실패 시 예외 발생
  Given a KISBrokerAdapter instance with invalid credentials
  When authenticate() is called
  Then AuthenticationError should be raised
  And error message should contain "Authentication failed"
  And no token should be cached
```

**검증 방법**:
```python
def test_authenticate_success(mock_rest_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter.rest_client = mock_rest_client
    mock_token = AuthenticationToken(
        access_token="test_token",
        token_type="Bearer",
        expires_in=86400,
        expires_at=datetime.now() + timedelta(seconds=86400),
    )
    mock_rest_client.get_access_token.return_value = mock_token

    token = adapter.authenticate()

    assert token.access_token == "test_token"
    assert token.expires_in == 86400
    mock_rest_client.get_access_token.assert_called_once()

def test_authenticate_failure(mock_rest_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter.rest_client = mock_rest_client
    mock_rest_client.get_access_token.side_effect = AuthenticationError("Auth failed")

    with pytest.raises(AuthenticationError):
        adapter.authenticate()
```

---

### AC-005: WebSocket 연결 관리

**Story**: As a real-time trading system, I need to manage WebSocket connection for live market data.

**Given-When-Then**:

```gherkin
Scenario: WebSocket 정상 연결
  Given a KISBrokerAdapter instance with account_id
  When connect_websocket() is called
  Then approval_key should be fetched from REST API
  And KISWebSocketClient should be created with approval_key
  And WebSocket connection should be established
  And _initialized flag should be True
  And ping thread should be started for connection keep-alive

Scenario: WebSocket 연결 종료
  Given a KISBrokerAdapter instance with active WebSocket connection
  When disconnect_websocket() is called
  Then WebSocket connection should be closed
  And ping thread should be stopped
  And _initialized flag should be False
  And ws_client should remain instantiated (not None)

Scenario: WebSocket 연결 실패 시 재시도
  Given a KISBrokerAdapter instance
  And WebSocket connection fails during connect_websocket()
  Then KISWebSocketClient should attempt reconnection
  And exponential backoff should be applied (1s, 2s, 4s, ...)
  And after max retries, ConnectionError should be raised
```

**검증 방법**:
```python
def test_connect_websocket_success(mock_ws_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")

    adapter.connect_websocket()

    assert adapter._initialized is True
    assert adapter.ws_client is not None
    mock_ws_client.connect_websocket.assert_called_once()

def test_disconnect_websocket(mock_ws_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter.ws_client = mock_ws_client
    adapter._initialized = True

    adapter.disconnect_websocket()

    mock_ws_client.disconnect_websocket.assert_called_once()
    assert adapter._initialized is False
```

---

### AC-006: 계좌 조회 기능

**Story**: As a trader, I need to query my account balance and positions to make trading decisions.

**Given-When-Then**:

```gherkin
Scenario: 예수금 조회
  Given a KISBrokerAdapter instance with account_id "1234567890"
  When get_cash("1234567890") is called
  Then KIS API should be queried with account_id="1234567890"
  And cash balance should be returned as Decimal
  And log should contain cash amount (masked)

Scenario: 주식잔고 조회
  Given a KISBrokerAdapter instance with account_id "1234567890"
  When get_stock_balance("1234567890") is called
  Then KIS API should be queried with account_id="1234567890"
  And list of positions should be returned
  And each position should contain pdno, hldg_qty, pchs_avg_pric

Scenario: 주문 목록 조회
  Given a KISBrokerAdapter instance with account_id "1234567890"
  When get_orders("1234567890") is called
  Then KIS API should be queried with account_id="1234567890"
  And list of orders should be returned
  And each order should contain ODNO, PDNO, ORD_QTY, ORD_TPS
```

**검증 방법**:
```python
def test_get_cash(mock_rest_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter.rest_client = mock_rest_client
    mock_rest_client.get_cash.return_value = Decimal("100000000")

    cash = adapter.get_cash("1234567890")

    assert cash == Decimal("100000000")
    mock_rest_client.get_cash.assert_called_once_with("1234567890")

def test_get_stock_balance(mock_rest_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter.rest_client = mock_rest_client
    mock_balance = [
        {"pdno": "005930", "hldg_qty": "100", "pchs_avg_pric": "80000"},
    ]
    mock_rest_client.get_stock_balance.return_value = mock_balance

    balance = adapter.get_stock_balance("1234567890")

    assert len(balance) == 1
    assert balance[0]["pdno"] == "005930"
```

---

### AC-007: 보안 및 개인정보 보호

**Story**: As a security-conscious developer, I want to ensure sensitive information is not exposed in logs.

**Given-When-Then**:

```gherkin
Scenario: account_id 로그 시 마스킹
  Given a KISBrokerAdapter instance with account_id "1234567890"
  When any operation logs account_id
  Then log should contain masked account_id "123456****"
  And log should NOT contain plaintext "1234567890"

Scenario: approval_key 로그 시 마스킹
  Given a KISBrokerAdapter instance
  When approval_key is fetched and logged
  Then log should contain first 8 characters only "abcd1234..."
  And log should NOT contain full approval_key

Scenario: access_token 로그 시 마스킹
  Given a KISBrokerAdapter instance
  When access_token is present in logs
  Then log should contain masked token format "token: ****..."
  And log should NOT contain plaintext token
```

**검증 방법**:
```python
def test_account_id_masking_in_logs(caplog):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")

    with caplog.at_level(logging.INFO):
        adapter.cancel_order("ORDER123")

    assert "123456****" in caplog.text
    assert "1234567890" not in caplog.text

def test_approval_key_masking_in_logs(caplog, mock_rest_client):
    adapter = KISBrokerAdapter(config=mock_config, account_id="1234567890")
    adapter.rest_client = mock_rest_client
    mock_rest_client.get_approval_key.return_value = "abcd1234567890efgh"

    with caplog.at_level(logging.INFO):
        adapter._get_approval_key_from_rest()

    assert "abcd1234..." in caplog.text
    assert "abcd1234567890efgh" not in caplog.text
```

---

### AC-008: TRUST 5 품질 준수

**Story**: As a quality-focused team, we want to ensure all code meets TRUST 5 standards.

**Quality Gates**:

```gherkin
Scenario: Tested - 테스트 커버리지
  Given all acceptance criteria tests are implemented
  When pytest --cov is executed
  Then code coverage should be 85% or higher
  And all tests should pass
  And no test should be skipped

Scenario: Readable - linter 통과
  Given ruff linter is configured
  When ruff check is executed on KISBrokerAdapter code
  Then zero linter errors should be reported
  And warnings should be minimal or documented

Scenario: Unified - formatter 통과
  Given black formatter is configured
  When black --check is executed on KISBrokerAdapter code
  Then zero formatting issues should be reported

Scenario: Secured - 보안 검사
  Given sensitive data masking is implemented
  When logs are reviewed for sensitive information
  Then no plaintext account_id should appear
  And no plaintext approval_key should appear
  And no plaintext access_token should appear

Scenario: Trackable - Git 커밋 규칙
  Given Git commits are made for implementation
  When commit messages are reviewed
  Then all commits should follow Conventional Commits format
  And TAG comments should be present in code
  And commit messages should reference SPEC-BACKEND-API-001-P3
```

**검증 방법**:
```bash
# Tested
pytest --cov=src/stock_manager/adapters/broker/kis --cov-report=html tests/
# Expect: 85%+ coverage

# Readable
ruff check src/stock_manager/adapters/broker/kis/
# Expect: 0 errors

# Unified
black --check src/stock_manager/adapters/broker/kis/
# Expect: 0 would reformat

# Secured
grep -r "1234567890" logs/  # Should not find plaintext account_id
grep -r "approval_key.*:" logs/ | grep -v "\.\.\."  # Should not find full key

# Trackable
git log --oneline -5 | grep -E "feat|fix|refactor:"  # Should find conventional commits
```

---

## 통합 테스트 시나리오 (Integration Test Scenarios)

### INT-001: 주문 전체 생명주기

```gherkin
Scenario: 주문 생성 → 전송 → 체결 → 취소
  Given a KISBrokerAdapter instance with valid config
  And an OrderRequest for symbol "005930", side=BUY, qty=10
  When place_order is called
  Then broker_order_id should be returned (e.g., "ORDER123")
  And order status should be "SENT"

  When WebSocket receives execution event for "ORDER123"
  Then OrderService.process_fill should be called
  And order status should change to "PARTIAL" or "FILLED"

  When cancel_order is called with "ORDER123"
  Then KIS API should cancel the order
  And cancel_order should return True
  And order status should change to "CANCELED"
```

### INT-002: WebSocket 재연결 후 구독 복구

```gherkin
Scenario: WebSocket 연결 실패 후 재연결 시 구독 복구
  Given a KISBrokerAdapter instance
  And quotes are subscribed for ["005930", "000660"]
  When WebSocket connection fails
  Then KISWebSocketClient should attempt reconnection
  And after reconnection, quotes for ["005930", "000660"] should be re-subscribed
  And quote callbacks should continue to receive events
```

### INT-003: 인증 토큰 만료 후 자동 갱신

```gherkin
Scenario: 토큰 만료 시 자동 갱신 및 재시도
  Given a KISBrokerAdapter instance
  And access_token is expired (expires_at < now)
  When place_order is called
  Then KIS API should return 401 Unauthorized
  And TokenManager should detect token expiry
  And TokenManager should refresh token automatically
  And place_order should be retried with new token
  And order should be placed successfully
```

---

## Definition of Done (완료 정의)

### 코드 완료
- [x] 모든 BrokerPort 인터페이스 메서드 구현
- [x] NotImplementedError 없음
- [x] TODO 코멘트 모두 제거
- [x] 타입 힌트 100% 적용

### 테스트 완료
- [ ] 단위 테스트 90%+ 커버리지
- [ ] 통합 테스트 모든 시나리오 통과
- [ ] 에러 케이스 테스트 포함
- [ ] 다중 스레드 테스트 통과

### 품질 완료
- [ ] ruff linter 통과 (0 errors)
- [ ] black formatter 통과
- [ ] mypy type checker 통과
- [ ] 민감 정보 마스킹 확인

### 문서 완료
- [ ] README Phase 3 상태 업데이트
- [ ] API 문서 업데이트
- [ ] 사용 예제 코드 추가

### 검토 완료
- [ ] 코드 리뷰 승인
- [ ] 보안 검토 통과
- [ ] 성능 테스트 통과

---

## 참고 (References)

### 관련 문서
- [spec.md](./spec.md) - 상세 요구사항
- [plan.md](./plan.md) - 구현 계획

### 테스트 도구
- pytest: 테스트 프레임워크
- pytest-asyncio: 비동기 테스트
- pytest-cov: 커버리지 리포트
- httpx.MockTransport: HTTP API 모킹
