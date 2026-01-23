"""
Order Service

주문 생성, 전송, 조회, 취소 및 체결 처리를 담당합니다.
"""

import logging
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from ..domain.order import (
    Order,
    Fill,
    OrderRequest,
    OrderStatus,
)
from ..adapters.broker.port import (
    BrokerPort,
    FillEvent as BrokerFillEvent,
    OrderSide,
    OrderType,
)

logger = logging.getLogger(__name__)


class IdempotencyConflictError(Exception):
    """idempotency key 중복 에러"""

    pass


class RiskViolationError(Exception):
    """리스크 위반 에러"""

    pass


class OrderStatusError(Exception):
    """주문 상태 에러"""

    pass


class RiskService:
    """리스크 서비스 (placeholder - SPEC-BACKEND-INFRA-003에서 구현될 것임)"""

    def __init__(self, db_connection):
        self.db = db_connection

    def validate_order(self, order: Order) -> bool:
        """주문 리스크 검증 (WT-003)

        Args:
            order: 주문 정보

        Returns:
            bool: 리스크 통과 여부

        Note:
            현재는 placeholder로 항상 True 반환
            실제 리스크 검증 로직은 SPEC-BACKEND-INFRA-003에서 구현
        """
        # TODO: SPEC-BACKEND-INFRA-003에서 리스크 검증 로직 구현
        return True


class OrderError(Exception):
    """주문 에러 기본 클래스"""

    pass


class OrderService:
    """주문 서비스"""

    def __init__(self, broker: BrokerPort, db_connection):
        self.broker = broker
        self.db = db_connection
        self.risk_service = RiskService(db_connection)  # 리스크 서비스 초기화

    def create_order(self, request: OrderRequest) -> Order:
        """주문 생성 (idempotency key 중복 검사 + 리스크 검증 포함)

        Args:
            request: 주문 요청

        Returns:
            Order: 생성된 주문

        Raises:
            IdempotencyConflictError: idempotency key 중복 시
            RiskViolationError: 리스크 위반 시 (WT-003)
        """
        # idempotency key 중복 검사 (WT-001)
        existing_order = self._find_order_by_idempotency_key(request.idempotency_key)
        if existing_order:
            logger.warning(
                f"Duplicate idempotency_key: {request.idempotency_key}, returning existing order"
            )
            # IdempotencyConflictEvent 로깅
            self._log_event(
                level="WARN",
                message="Idempotency conflict detected",
                payload={
                    "idempotency_key": request.idempotency_key,
                    "existing_order_id": existing_order.id,
                },
            )
            return existing_order

        # 새 주문 생성
        order_id = self._create_order_in_db(request)
        logger.info(f"Order created: {order_id} with idempotency_key: {request.idempotency_key}")

        # OrderCreatedEvent 로깅
        self._log_event(
            level="INFO",
            message="Order created",
            payload={
                "order_id": order_id,
                "idempotency_key": request.idempotency_key,
                "symbol": request.symbol,
                "side": request.side,
                "order_type": request.order_type,
                "qty": str(request.qty),
            },
        )

        # 주문 조회
        order = self._get_order_from_db(order_id)

        # 리스크 검증 (WT-003)
        if not self.risk_service.validate_order(order):
            logger.warning(f"Risk validation failed for order {order_id}")
            # 주문 상태 REJECTED로 설정
            self._update_order_status(order_id, OrderStatus.REJECTED, None)

            # RiskViolationEvent 로깅 (WARN 레벨)
            self._log_event(
                level="WARN",
                message="Risk violation detected",
                payload={
                    "order_id": order_id,
                    "symbol": order.symbol,
                    "side": order.side,
                },
            )

            raise RiskViolationError(f"Order {order_id} rejected due to risk violation")

        return order

    def send_order(self, order_id: int) -> bool:
        """주문 전송

        Args:
            order_id: 주문 ID

        Returns:
            bool: 전송 성공 여부
        """
        order = self._get_order_from_db(order_id)
        if not order:
            raise OrderError(f"Order not found: {order_id}")

        # 상태 체크: NEW 상태만 전송 가능
        if order.status != OrderStatus.NEW:
            raise OrderStatusError(
                f"Cannot send order with status {order.status.value}, expected NEW"
            )

        # BrokerPort를 통한 주문 전송
        broker_order_request = self._to_broker_order_request(order)
        broker_order_id = self.broker.place_order(broker_order_request)

        # 주문 상태 업데이트 (NEW → SENT)
        self._update_order_status(order_id, OrderStatus.SENT, broker_order_id)
        logger.info(f"Order {order_id} sent to broker, broker_order_id: {broker_order_id}")

        # OrderSentEvent 로깅
        self._log_event(
            level="INFO",
            message="Order sent to broker",
            payload={
                "order_id": order_id,
                "broker_order_id": broker_order_id,
                "symbol": order.symbol,
            },
        )

        return True

    def cancel_order(self, order_id: int) -> bool:
        """주문 취소

        Args:
            order_id: 주문 ID

        Returns:
            bool: 취소 성공 여부
        """
        order = self._get_order_from_db(order_id)
        if not order:
            raise OrderError(f"Order not found: {order_id}")

        # 상태 체크: SENT, PARTIAL 상태만 취소 가능
        if order.status not in [OrderStatus.SENT, OrderStatus.PARTIAL]:
            raise OrderStatusError(
                f"Cannot cancel order with status {order.status.value}, expected SENT or PARTIAL"
            )

        # BrokerPort를 통한 주문 취소
        success = self.broker.cancel_order(order.broker_order_id)

        if success:
            # 주문 상태 업데이트 (SENT/PARTIAL → CANCELED)
            self._update_order_status(order_id, OrderStatus.CANCELED, None)
            logger.info(f"Order {order_id} canceled")

            # OrderCanceledEvent 로깅
            self._log_event(
                level="INFO",
                message="Order canceled",
                payload={
                    "order_id": order_id,
                    "broker_order_id": order.broker_order_id,
                },
            )

        return success

    def get_order(self, order_id: int) -> Optional[Order]:
        """주문 조회

        Args:
            order_id: 주문 ID

        Returns:
            Optional[Order]: 주문 정보 (없으면 None)
        """
        return self._get_order_from_db(order_id)

    def get_pending_orders(self) -> List[Order]:
        """미체결 주문 조회

        Returns:
            List[Order]: 미체결 주문 목록 (status: SENT, PARTIAL)
        """
        query = """
        SELECT id, broker_order_id, idempotency_key, symbol, side, order_type,
               qty, price, status, filled_qty, avg_fill_price,
               requested_at, created_at, updated_at
        FROM orders
        WHERE status IN ('SENT', 'PARTIAL')
        ORDER BY created_at DESC
        """

        with self.db.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        orders = []
        for row in rows:
            orders.append(self._row_to_order(row))

        return orders

    def process_fill(self, fill_event: BrokerFillEvent) -> Fill:
        """체결 이벤트 처리 (ED-003)

        Args:
            fill_event: 브로커 체결 이벤트

        Returns:
            Fill: 생성된 체결 레코드
        """
        # 주문 조회
        order = self._find_order_by_broker_order_id(fill_event.broker_order_id)
        if not order:
            logger.warning(f"Order not found for broker_order_id: {fill_event.broker_order_id}")
            raise OrderError(f"Order not found: {fill_event.broker_order_id}")

        # 체결 레코드 생성 (append-only)
        fill_id = self._create_fill_in_db(order.id, fill_event)

        # 체결 누적 계산
        filled_qty = self._calculate_cumulative_filled_qty(order.id)
        new_status = OrderStatus.PARTIAL

        # 모든 수량이 체결되었으면 FILLED로 변경 (WT-002)
        if filled_qty >= order.qty:
            new_status = OrderStatus.FILLED
            self._update_order_status(order.id, new_status, None)
            logger.info(f"Order {order.id} fully filled, status changed to FILLED")
        else:
            self._update_order_status(order.id, new_status, None)

        # OrderFilledEvent 또는 FillRecordedEvent 로깅
        self._log_event(
            level="INFO",
            message="Fill recorded",
            payload={
                "order_id": order.id,
                "fill_id": fill_id,
                "filled_qty": str(filled_qty),
                "order_qty": str(order.qty),
                "status": new_status.value,
            },
        )

        return self._get_fill_from_db(fill_id)

    def _find_order_by_idempotency_key(self, idempotency_key: str) -> Optional[Order]:
        """idempotency key로 주문 조회"""
        query = """
        SELECT id, broker_order_id, idempotency_key, symbol, side, order_type,
               qty, price, status, filled_qty, avg_fill_price,
               requested_at, created_at, updated_at
        FROM orders
        WHERE idempotency_key = %s
        """

        with self.db.cursor() as cursor:
            cursor.execute(query, (idempotency_key,))
            row = cursor.fetchone()

        if row:
            return self._row_to_order(row)
        return None

    def _find_order_by_broker_order_id(self, broker_order_id: str) -> Optional[Order]:
        """브로커 주문 ID로 주문 조회"""
        query = """
        SELECT id, broker_order_id, idempotency_key, symbol, side, order_type,
               qty, price, status, filled_qty, avg_fill_price,
               requested_at, created_at, updated_at
        FROM orders
        WHERE broker_order_id = %s
        """

        with self.db.cursor() as cursor:
            cursor.execute(query, (broker_order_id,))
            row = cursor.fetchone()

        if row:
            return self._row_to_order(row)
        return None

    def _create_order_in_db(self, request: OrderRequest) -> int:
        """DB에 새 주문 생성"""
        query = """
        INSERT INTO orders (symbol, side, order_type, qty, price, idempotency_key, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'NEW')
        RETURNING id
        """

        with self.db.cursor() as cursor:
            cursor.execute(
                query,
                (
                    request.symbol,
                    request.side,
                    request.order_type,
                    str(request.qty),
                    str(request.price) if request.price else None,
                    request.idempotency_key,
                ),
            )
            order_id = cursor.fetchone()[0]
            self.db.commit()

        return order_id

    def _update_order_status(
        self, order_id: int, status: OrderStatus, broker_order_id: Optional[str] = None
    ) -> None:
        """주문 상태 업데이트 (UB-001: 단방향 전이 규칙)"""
        # 상태 전이 규칙 체크
        order = self._get_order_from_db(order_id)
        if order:
            if not self._is_valid_transition(order.status, status):
                raise OrderStatusError(
                    f"Invalid status transition: {order.status.value} → {status.value}"
                )

        query = "UPDATE orders SET status = %s WHERE id = %s"
        params = [status.value, order_id]

        if broker_order_id:
            query = "UPDATE orders SET status = %s, broker_order_id = %s WHERE id = %s"
            params = [status.value, broker_order_id, order_id]

        with self.db.cursor() as cursor:
            cursor.execute(query, params)
            self.db.commit()

    def _is_valid_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """상태 전이 유효성 검사 (UB-001)

        유효한 전이:
        - NEW → SENT
        - SENT → PARTIAL, FILLED, CANCELED, REJECTED, ERROR
        - PARTIAL → FILLED, CANCELED, REJECTED, ERROR

        유효하지 않은 전이:
        - 상태 되돌리기 (예: FILLED → PARTIAL)
        - NEW → PARTIAL/FILLED (반드시 SENT 거쳐야 함)
        """
        # 유효한 전이 규칙
        valid_transitions = {
            OrderStatus.NEW: [OrderStatus.SENT],
            OrderStatus.SENT: [
                OrderStatus.PARTIAL,
                OrderStatus.FILLED,
                OrderStatus.CANCELED,
                OrderStatus.REJECTED,
                OrderStatus.ERROR,
            ],
            OrderStatus.PARTIAL: [
                OrderStatus.FILLED,
                OrderStatus.CANCELED,
                OrderStatus.REJECTED,
                OrderStatus.ERROR,
            ],
        }

        # 유효하지 않은 전이 체크
        invalid_transitions = [
            (OrderStatus.FILLED, OrderStatus.PARTIAL),  # 되돌리기 방지
        ]

        for from_status, to_statuses in valid_transitions.items():
            if current_status == from_status:
                return new_status in to_statuses

        # 유효하지 않은 전이 명시적 거부
        if (current_status, new_status) in invalid_transitions:
            return False

        return False

    def _create_fill_in_db(self, order_id: int, fill_event: BrokerFillEvent) -> int:
        """DB에 체결 레코드 생성"""
        query = """
        INSERT INTO fills (order_id, broker_fill_id, symbol, side, qty, price, filled_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        with self.db.cursor() as cursor:
            cursor.execute(
                query,
                (
                    order_id,
                    fill_event.broker_order_id,
                    fill_event.symbol,
                    fill_event.side.value,
                    str(fill_event.qty),
                    str(fill_event.price),
                    fill_event.filled_at,
                ),
            )
            fill_id = cursor.fetchone()[0]
            self.db.commit()

        return fill_id

    def _calculate_cumulative_filled_qty(self, order_id: int) -> Decimal:
        """누적 체결 수량 계산"""
        query = "SELECT SUM(qty) FROM fills WHERE order_id = %s"

        with self.db.cursor() as cursor:
            cursor.execute(query, (order_id,))
            result = cursor.fetchone()
            return Decimal(result[0]) if result[0] else Decimal("0")

    def _get_order_from_db(self, order_id: int) -> Order:
        """DB에서 주문 조회"""
        query = """
        SELECT id, broker_order_id, idempotency_key, symbol, side, order_type,
               qty, price, status, filled_qty, avg_fill_price,
               requested_at, created_at, updated_at
        FROM orders
        WHERE id = %s
        """

        with self.db.cursor() as cursor:
            cursor.execute(query, (order_id,))
            row = cursor.fetchone()

        if not row:
            raise OrderError(f"Order not found: {order_id}")

        return self._row_to_order(row)

    def _get_fill_from_db(self, fill_id: int) -> Fill:
        """DB에서 체결 조회"""
        query = """
        SELECT id, order_id, broker_fill_id, symbol, side, qty, price, filled_at, created_at, updated_at
        FROM fills
        WHERE id = %s
        """

        with self.db.cursor() as cursor:
            cursor.execute(query, (fill_id,))
            row = cursor.fetchone()

        if not row:
            raise OrderError(f"Fill not found: {fill_id}")

        return self._row_to_fill(row)

    def _log_event(self, level: str, message: str, payload: dict = None) -> None:
        """이벤트 로깅"""
        query = """
        INSERT INTO events (level, message, payload)
        VALUES (%s, %s, %s)
        """

        with self.db.cursor() as cursor:
            cursor.execute(
                query,
                (level, message, payload if payload else None),
            )
            self.db.commit()

    def _to_broker_order_request(self, order: Order):
        """Order를 BrokerPort.OrderRequest로 변환"""
        # BrokerPort에서 OrderSide/OrderType import
        from ..adapters.broker.port import OrderSide, OrderType

        return OrderRequest(
            account_id="0000000000",  # TODO: 실제 계좌 ID
            symbol=order.symbol,
            side=OrderSide(order.side),
            order_type=OrderType(order.order_type),
            qty=order.qty,
            price=order.price,
            idempotency_key=order.idempotency_key,
        )

    def _row_to_order(self, row: tuple) -> Order:
        """DB row를 Order 객체로 변환"""
        return Order(
            id=row[0],
            broker_order_id=row[1],
            idempotency_key=row[2],
            symbol=row[3],
            side=row[4],
            order_type=row[5],
            qty=Decimal(row[6]),
            price=Decimal(row[7]) if row[7] else None,
            status=OrderStatus(row[8]),
            filled_qty=Decimal(row[9]) if row[9] else Decimal("0"),
            avg_fill_price=Decimal(row[10]) if row[10] else None,
            requested_at=row[11],
            created_at=row[12],
            updated_at=row[13],
        )

    def _row_to_fill(self, row: tuple) -> Fill:
        """DB row를 Fill 객체로 변환"""
        return Fill(
            id=row[0],
            order_id=row[1],
            broker_fill_id=row[2],
            symbol=row[3],
            side=row[4],
            qty=Decimal(row[5]),
            price=Decimal(row[6]),
            filled_at=row[7],
            created_at=row[8],
            updated_at=row[9],
        )

    def sync_order_status(self) -> int:
        """브로커/DB 상태 동기화 (WT-005)

        Returns:
            int: 동기화된 주문 수
        """
        # 모든 SENT, PARTIAL 상태 주문 조회
        orders = self.get_pending_orders()
        synced_count = 0

        for order in orders:
            try:
                # 브로커에서 주문 상태 조회
                broker_orders = self.broker.get_orders(
                    account_id="0000000000"
                )  # TODO: 실제 계좌 ID
                broker_order_map = {
                    o.broker_order_id: o for o in broker_orders if o.broker_order_id
                }

                if order.broker_order_id in broker_order_map:
                    broker_order = broker_order_map[order.broker_order_id]
                    # 브로커 상태를 DB 상태로 변환
                    broker_status = self._broker_status_to_order_status(broker_order.status)

                    # 상태 불일치 감지
                    if broker_status != order.status:
                        logger.warning(
                            f"Status mismatch detected for order {order.id}: "
                            f"DB={order.status.value}, Broker={broker_order.status}, syncing to broker state"
                        )

                        # DB 상태를 브로커 상태로 동기화
                        self._update_order_status(order.id, broker_status, order.broker_order_id)

                        # StateSyncEvent 로깅 (INFO 레벨)
                        self._log_event(
                            level="INFO",
                            message="Order status synchronized",
                            payload={
                                "order_id": order.id,
                                "broker_order_id": order.broker_order_id,
                                "db_status": order.status.value,
                                "broker_status": broker_order.status,
                            },
                        )

                        synced_count += 1
                else:
                    logger.warning(
                        f"Order {order.id} not found in broker, status: {order.status.value}"
                    )
            except Exception as e:
                logger.error(f"Error syncing order {order.id}: {e}")
                # DatabaseError 로깅 (ERROR 레벨)
                self._log_event(
                    level="ERROR",
                    message=f"Order sync error: {str(e)}",
                    payload={
                        "order_id": order.id,
                        "broker_order_id": order.broker_order_id,
                    },
                )

        logger.info(f"Status synchronization completed: {synced_count} orders synced")

        return synced_count

    def _broker_status_to_order_status(self, broker_status: str) -> OrderStatus:
        """브로커 상태를 OrderStatus로 변환"""
        status_map = {
            "접수": OrderStatus.NEW,
            "주문중": OrderStatus.SENT,
            "체결": OrderStatus.PARTIAL,
            "체결완료": OrderStatus.FILLED,
            "주문취소": OrderStatus.CANCELED,
            "주문거부": OrderStatus.REJECTED,
        }

        return status_map.get(broker_status, OrderStatus.ERROR)
