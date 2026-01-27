# Broker Adapter

한국투자증권 OpenAPI와 통신하는 브로커 어댑터 패키지입니다.

## 개요

Port/Adapter 패턴을 사용하여 외부 브로커 시스템과의 통신을 추상화합니다. 실전/모의 투자 환경을 모두 지원합니다.

## 구조

```
src/stock_manager/adapters/broker/
├── port/
│   ├── __init__.py
│   └── broker_port.py          # BrokerPort 추상 인터페이스
├── kis/
│   ├── __init__.py
│   ├── kis_config.py           # KIS OpenAPI 설정
│   ├── kis_rest_client.py      # REST API 클라이언트
│   ├── kis_websocket_client.py  # WebSocket 클라이언트
│   └── kis_broker_adapter.py   # KIS 브로커 어댑터 (구현체)
└── mock/
    ├── __init__.py
    └── mock_broker_adapter.py  # Mock 브로커 어댑터 (테스트용)
```

## 사용법

### 1. 설정 파일 (.env)

```env
# 환경 모드
MODE=PAPER  # 또는 LIVE

# KIS API 키
KIS_APP_KEY=your_app_key_here
KIS_APP_SECRET=your_app_secret_here

# 커스텀 URL (선택사항)
# KIS_REST_BASE_URL=https://custom-url
# KIS_WS_URL=ws://custom-ws-url
```

### 2. 기본 사용법

```python
from src.stock_manager.adapters.broker.kis import KISConfig, KISBrokerAdapter
from src.stock_manager.adapters.broker.port import (
    OrderRequest,
    OrderSide,
    OrderType,
)

# 1. 설정 로드
config = KISConfig()

# 2. 브로커 어댑터 초기화 (account_id 파라미터 필요)
broker = KISBrokerAdapter(config, account_id="1234567890")

# 3. 인증
token = broker.authenticate()
print(f"Access token: {token.access_token}")

# 4. 주문 전송
order = OrderRequest(
    account_id="1234567890",
    symbol="005930",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    qty=100,
    price=50000,
    idempotency_key="unique_order_id",
)
order_id = broker.place_order(order)
print(f"Order placed: {order_id}")

# 5. WebSocket 연결
broker.connect_websocket()

# 6. 호가 구독
def handle_quote(quote):
    print(f"Quote: {quote.symbol} Bid: {quote.bid_price} Ask: {quote.ask_price}")

broker.subscribe_quotes(["005930"], handle_quote)

# 7. 체결 구독
def handle_fill(fill):
    print(f"Fill: {fill.symbol} {fill.qty} @ {fill.price}")

broker.subscribe_executions(handle_fill)

# 8. WebSocket 연결 종료
broker.disconnect_websocket()
```

### 3. Mock 브로커 사용 (테스트용)

```python
from src.stock_manager.adapters.broker.mock import MockBrokerAdapter
from src.stock_manager.adapters.broker.port import OrderRequest, OrderSide

# Mock 브로커 초기화
mock_broker = MockBrokerAdapter()

# 인증
token = mock_broker.authenticate()

# 주문 전송 (인-메모리 시뮬레이션)
order = OrderRequest(
    account_id="1234567890",
    symbol="005930",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    qty=100,
    idempotency_key="test_order_id",
)
order_id = mock_broker.place_order(order)

# 주문 취소
mock_broker.cancel_order(order_id)
```

## API 참고

### BrokerPort 인터페이스

```python
class BrokerPort(ABC):
    @abstractmethod
    def authenticate(self) -> AuthenticationToken:
        """인증 토큰 발급"""

    @abstractmethod
    def place_order(self, order: OrderRequest) -> str:
        """주문 전송"""

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> bool:
        """주문 취소"""

    @abstractmethod
    def get_orders(self, account_id: str) -> List[Order]:
        """주문 목록 조회"""

    @abstractmethod
    def get_cash(self, account_id: str) -> Decimal:
        """예수금 조회"""

    @abstractmethod
    def subscribe_quotes(self, symbols: List[str], callback: Callable):
        """호가 구독"""

    @abstractmethod
    def subscribe_executions(self, callback: Callable):
        """체결 구독"""

    @abstractmethod
    def connect_websocket(self):
        """WebSocket 연결"""

    @abstractmethod
    def disconnect_websocket(self):
        """WebSocket 연결 종료"""
```

## 데이터 모델

### AuthenticationToken

```python
@dataclass
class AuthenticationToken:
    access_token: str
    token_type: str
    expires_in: int  # seconds
    expires_at: datetime  # calculated timestamp
```

### OrderRequest

```python
@dataclass
class OrderRequest:
    account_id: str       # 계좌 ID (10자)
    symbol: str           # 종목 코드
    side: OrderSide        # BUY 또는 SELL
    order_type: OrderType  # MARKET 또는 LIMIT
    qty: Decimal           # 주문 수량
    price: Optional[Decimal]  # 주문 가격 (지정가만 필수)
    idempotency_key: str  # 중복 방지 키
```

### FillEvent

```python
@dataclass
class FillEvent:
    broker_order_id: str  # 브로커 주문 ID
    symbol: str          # 종목 코드
    side: OrderSide       # BUY 또는 SELL
    qty: Decimal         # 체결 수량
    price: Decimal        # 체결 가격
    filled_at: datetime  # 체결 시간
```

### QuoteEvent

```python
@dataclass
class QuoteEvent:
    symbol: str      # 종목 코드
    bid_price: Decimal    # 매도 호가
    ask_price: Decimal    # 매수 호가
    bid_qty: Decimal      # 매도 호가 잔량
    ask_qty: Decimal      # 매수 호가 잔량
    timestamp: datetime   # 호가 시간
```

## 예외 처리

```python
from src.stock_manager.adapters.broker.port import (
    BrokerError,
    AuthenticationError,
    ConnectionError,
    APIError,
    RateLimitError,
)

try:
    broker.place_order(order)
except AuthenticationError:
    print("인증 실패: 토큰을 확인하세요.")
except ConnectionError:
    print("연결 실패: 네트워크를 확인하세요.")
except APIError:
    print("API 오류: 요청을 다시 시도하세요.")
except RateLimitError:
    print("Rate Limit 초과: 호출 빈도를 줄이세요.")
except BrokerError as e:
    print(f"브로커 에러: {e}")
```

## 재연결 로직

WebSocket 연결이 끊어지면 지수적 백오프로 재연결을 시도합니다:

- 1초 후 첫 재시도
- 2초 후 두 번째 재시도
- 4초 후 세 번째 재시도
- 8초 후 네 번째 재시도
- 16초 후 다섯 번째 재시도

최대 5회 재시도 후 `ConnectionError`가 발생합니다.

## 토큰 자동 갱신

토큰이 만료 5분 전이면 자동으로 갱신됩니다.

- 만료 10분 전: 갱신 없음
- 만료 4분 전: 자동 갱신

## 테스트

```bash
# 전체 테스트 실행
pytest

# 단위 테스트만
pytest tests/unit/

# 커버리지 확인
pytest --cov=src/stock_manager/adapters/broker --cov-report=html
```

## 모의 투자 vs 실전 투자

| 모드 | REST URL | WebSocket URL | 설명 |
|------|----------|---------------|------|
| PAPER | openapivts.koreainvestment.com:29443 | ops.koreainvestment.com:31000 | 모의 투자 (기본값) |
| LIVE | openapi.koreainvestment.com:9443 | ops.koreainvestment.com:21000 | 실전 투자 |

## 보안 주의사항

1. **API 키 관리**: `.env` 파일을 `.gitignore`에 추가하세요.
2. **TLS 버전**: TLS 1.2/1.3만 지원됩니다.
3. **Rate Limit**: 초당 5회 호출 제한을 준수하세요.
4. **로그 기록**: 민감 정보(앱키, 시크릿, 토큰)는 로그에서 제외됩니다.

## 라이선스

MIT

## 참고

- [한국투자증권 OpenAPI 개발가이드](https://apiportal.koreainvestment.com/)
- [KIS OpenAPI 문서](../../docs/kis-openapi/)
