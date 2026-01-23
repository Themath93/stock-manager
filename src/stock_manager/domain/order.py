"""
Order Domain Model
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderStatus(Enum):
    """주문 상태"""

    NEW = "NEW"
    SENT = "SENT"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


@dataclass
class Order:
    """주문 도메인 모델"""

    id: int
    broker_order_id: str | None
    idempotency_key: str
    symbol: str
    side: str  # OrderSide.BUY or SELL
    order_type: str  # OrderType.MARKET or LIMIT
    qty: Decimal
    price: Decimal | None  # 필수 for LIMIT
    status: OrderStatus
    filled_qty: Decimal  # 체결 누적 수량
    avg_fill_price: Decimal | None  # 평균 체결가
    requested_at: datetime
    created_at: datetime
    updated_at: datetime


@dataclass
class Fill:
    """체결 도메인 모델"""

    id: int
    order_id: int  # orders.id 참조
    broker_fill_id: str | None
    symbol: str
    side: str  # OrderSide.BUY or SELL
    qty: Decimal
    price: Decimal
    filled_at: datetime
    created_at: datetime
    updated_at: datetime


@dataclass
class Position:
    """포지션 도메인 모델"""

    id: int
    symbol: str
    qty: Decimal  # 보유 수량 (양수: 롱, 음수: 숏)
    avg_price: Decimal  # 평균 단가
    created_at: datetime
    updated_at: datetime


@dataclass
class OrderRequest:
    """주문 요청 DTO"""

    symbol: str
    side: str  # OrderSide.BUY or SELL
    order_type: str  # OrderType.MARKET or LIMIT
    qty: Decimal
    price: Decimal | None
    idempotency_key: str
