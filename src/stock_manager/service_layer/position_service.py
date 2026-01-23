"""
Position Service

포지션 계산 및 업데이트를 담당합니다.
"""

import logging
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from ..domain.order import Fill, Position

logger = logging.getLogger(__name__)


class PositionService:
    """포지션 서비스"""

    def __init__(self, db_connection):
        self.db = db_connection

    def calculate_position(self, symbol: str) -> Position:
        """포지션 계산

        Args:
            symbol: 종목 코드

        Returns:
            Position: 계산된 포지션
        """
        # 모든 체결 기록 조회
        fills = self._get_fills_by_symbol(symbol)

        if not fills:
            # 체결 기록이 없으면 포지션 초기화
            return self._initialize_position(symbol)

        # 수량 계산 (BUY: +, SELL: -)
        total_qty = Decimal("0")
        total_value = Decimal("0")

        for fill in fills:
            if fill.side == "BUY":
                total_qty += fill.qty
                total_value += fill.qty * fill.price
            else:  # SELL
                total_qty -= fill.qty
                total_value -= fill.qty * fill.price

        # 평균 단가 계산
        if total_qty != Decimal("0"):
            avg_price = total_value / total_qty
        else:
            avg_price = Decimal("0")

        logger.info(f"Position calculated for {symbol}: qty={total_qty}, avg_price={avg_price}")

        return Position(
            symbol=symbol,
            qty=total_qty,
            avg_price=avg_price,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def update_position(self, fill: Fill) -> Position:
        """체결로 포지션 업데이트 (ED-004)

        Args:
            fill: 체결 정보

        Returns:
            Position: 업데이트된 포지션
        """
        # 포지션 계산
        position = self.calculate_position(fill.symbol)

        # DB에 upsert
        self._upsert_position(position)

        # PositionUpdatedEvent 로깅
        self._log_event(
            level="INFO",
            message="Position updated",
            payload={
                "symbol": position.symbol,
                "qty": str(position.qty),
                "avg_price": str(position.avg_price),
                "fill_id": fill.id,
            },
        )

        logger.info(
            f"Position updated for {position.symbol}: "
            f"qty={position.qty}, avg_price={position.avg_price}"
        )

        return position

    def get_position(self, symbol: str) -> Optional[Position]:
        """포지션 조회

        Args:
            symbol: 종목 코드

        Returns:
            Optional[Position]: 포지션 정보 (없으면 None)
        """
        return self._get_position_from_db(symbol)

    def get_all_positions(self) -> List[Position]:
        """모든 포지션 조회

        Returns:
            List[Position]: 포지션 목록
        """
        query = """
        SELECT id, symbol, qty, avg_price, created_at, updated_at
        FROM positions
        ORDER BY symbol
        """

        with self.db.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        positions = []
        for row in rows:
            positions.append(self._row_to_position(row))

        return positions

    def _get_fills_by_symbol(self, symbol: str) -> List[Fill]:
        """종목별 체결 기록 조회"""
        query = """
        SELECT id, order_id, broker_fill_id, symbol, side, qty, price, filled_at, created_at, updated_at
        FROM fills
        WHERE symbol = %s
        ORDER BY filled_at
        """

        with self.db.cursor() as cursor:
            cursor.execute(query, (symbol,))
            rows = cursor.fetchall()

        fills = []
        for row in rows:
            fills.append(self._row_to_fill(row))

        return fills

    def _initialize_position(self, symbol: str) -> Position:
        """포지션 초기화 (빈 포지션 생성)"""
        return Position(
            symbol=symbol,
            qty=Decimal("0"),
            avg_price=Decimal("0"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def _upsert_position(self, position: Position) -> None:
        """포지션 upsert (INSERT ON CONFLICT UPDATE)"""
        query = """
        INSERT INTO positions (symbol, qty, avg_price)
        VALUES (%s, %s, %s)
        ON CONFLICT (symbol)
        DO UPDATE SET
            qty = EXCLUDED.qty,
            avg_price = EXCLUDED.avg_price,
            updated_at = NOW()
        """

        with self.db.cursor() as cursor:
            cursor.execute(
                query,
                (
                    position.symbol,
                    str(position.qty),
                    str(position.avg_price),
                ),
            )
            self.db.commit()

    def _get_position_from_db(self, symbol: str) -> Optional[Position]:
        """DB에서 포지션 조회"""
        query = """
        SELECT id, symbol, qty, avg_price, created_at, updated_at
        FROM positions
        WHERE symbol = %s
        """

        with self.db.cursor() as cursor:
            cursor.execute(query, (symbol,))
            row = cursor.fetchone()

        if row:
            return self._row_to_position(row)
        return None

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

    def _row_to_position(self, row: tuple) -> Position:
        """DB row를 Position 객체로 변환"""
        return Position(
            id=row[0],
            symbol=row[1],
            qty=Decimal(row[2]),
            avg_price=Decimal(row[3]),
            created_at=row[4],
            updated_at=row[5],
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
