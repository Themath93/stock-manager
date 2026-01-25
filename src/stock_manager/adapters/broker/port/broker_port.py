"""
Broker Port Interface

브로커 어댑터의 추상 인터페이스를 정의합니다.
Port/Adapter 패턴에 따라 외부 브로커 시스템과의 통신을 추상화합니다.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, List, Optional


class OrderSide(Enum):
    """주문 방향"""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """주문 유형"""

    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass
class AuthenticationToken:
    """인증 토큰"""

    access_token: str
    token_type: str
    expires_in: int  # seconds
    expires_at: datetime  # calculated timestamp


@dataclass
class OrderRequest:
    """주문 요청"""

    account_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    price: Optional[Decimal] = None  # 필수 for LIMIT
    idempotency_key: str = ""


@dataclass
class Order:
    """주문"""

    broker_order_id: str
    account_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    price: Optional[Decimal]
    status: str
    created_at: datetime


@dataclass
class FillEvent:
    """체결 이벤트"""

    broker_order_id: str
    symbol: str
    side: OrderSide
    qty: Decimal
    price: Decimal
    filled_at: datetime


@dataclass
class QuoteEvent:
    """호가 이벤트"""

    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    bid_qty: Decimal
    ask_qty: Decimal
    timestamp: datetime


class BrokerPort(ABC):
    """브로커 포트 인터페이스

    모든 브로커 어댑터는 이 인터페이스를 구현해야 합니다.
    """

    @abstractmethod
    def authenticate(self) -> AuthenticationToken:
        """인증 토큰 발급

        Returns:
            AuthenticationToken: 발급된 인증 토큰

        Raises:
            AuthenticationError: 인증 실패 시
        """
        pass

    @abstractmethod
    def place_order(self, order: OrderRequest) -> str:
        """주문 전송

        Args:
            order: 주문 요청

        Returns:
            str: 브로커 주문 ID

        Raises:
            APIError: 주문 실패 시
            RateLimitError: Rate Limit 초과 시
        """
        pass

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> bool:
        """주문 취소

        Args:
            broker_order_id: 취소할 주문 ID

        Returns:
            bool: 취소 성공 여부

        Raises:
            APIError: 취소 실패 시
        """
        pass

    @abstractmethod
    def get_orders(self, account_id: str) -> List[Order]:
        """주문 목록 조회

        Args:
            account_id: 계좌 ID

        Returns:
            List[Order]: 주문 목록

        Raises:
            APIError: 조회 실패 시
        """
        pass

    @abstractmethod
    def get_cash(self, account_id: str) -> Decimal:
        """예수금 조회

        Args:
            account_id: 계좌 ID

        Returns:
            Decimal: 예수금

        Raises:
            APIError: 조회 실패 시
        """
        pass

    @abstractmethod
    def get_stock_balance(self, account_id: str) -> list[dict]:
        """주식잔고 조회

        Args:
            account_id: 계좌 ID

        Returns:
            list[dict]: 종목별 잔고 정보
                [
                    {
                        "pdno": "005930",           # 종목코드
                        "prdt_name": "삼성전자",      # 종목명
                        "hldg_qty": "1657",          # 보유수량
                        "pchs_avg_pric": "135440.25", # 매입평균가격
                        "pchs_amt": "224424497",     # 매입금액
                        "prpr": "0",                # 현재가
                        "evlu_amt": "0",             # 평가금액
                        "evlu_pfls_amt": "0",       # 평가손익금액
                        "evlu_pfls_rt": "0.00",     # 평가손익율
                    },
                    ...
                ]

        Raises:
            APIError: 조회 실패 시
        """
        pass

    @abstractmethod
    def subscribe_quotes(self, symbols: List[str], callback: Callable[[QuoteEvent], None]):
        """호가 구독

        Args:
            symbols: 구독할 종목 코드 목록
            callback: 호가 이벤트 수신 콜백

        Raises:
            ConnectionError: WebSocket 연결 실패 시
        """
        pass

    @abstractmethod
    def subscribe_executions(self, callback: Callable[[FillEvent], None]):
        """체결 구독

        Args:
            callback: 체결 이벤트 수신 콜백

        Raises:
            ConnectionError: WebSocket 연결 실패 시
        """
        pass

    @abstractmethod
    def connect_websocket(self):
        """WebSocket 연결

        Raises:
            ConnectionError: 연결 실패 시
        """
        pass

    @abstractmethod
    def disconnect_websocket(self):
        """WebSocket 연결 종료"""
        pass


# Custom Exceptions
class BrokerError(Exception):
    """브로커 에러 기본 클래스"""

    pass


class AuthenticationError(BrokerError):
    """인증 에러"""

    pass


class ConnectionError(BrokerError):
    """연결 에러"""

    pass


class APIError(BrokerError):
    """API 에러"""

    pass


class RateLimitError(BrokerError):
    """Rate Limit 에러"""

    pass
