"""
Unit tests for SettlementService

Tests for daily settlement operations including position snapshots
and PnL calculations.
"""

import pytest
from datetime import datetime, date
from unittest.mock import Mock
from decimal import Decimal

from stock_manager.service_layer.settlement_service import (
    SettlementServiceImpl,
    SettlementError,
)
from stock_manager.domain.market_lifecycle import (
    DailySettlement,
    PositionSnapshot,
)
from stock_manager.domain.order import Position


@pytest.fixture
def mock_position_service():
    """Mock position service"""
    position_service = Mock()
    return position_service


@pytest.fixture
def mock_db_connection():
    """Mock database connection with proper context manager support"""
    from contextlib import contextmanager

    db = Mock()

    # Create cursor mock
    cursor_mock = Mock()
    cursor_mock.fetchone.return_value = None
    cursor_mock.fetchall.return_value = []

    # Create context manager that yields cursor_mock
    @contextmanager
    def mock_cursor_cm():
        yield cursor_mock

    # Make db.cursor() return the context manager
    db.cursor = mock_cursor_cm
    db.commit = Mock()

    return db


@pytest.fixture
def settlement_service(mock_position_service, mock_db_connection):
    """Settlement service fixture"""
    return SettlementServiceImpl(
        position_service=mock_position_service,
        db_connection=mock_db_connection,
    )


class TestSettlementService:
    """SettlementService tests"""

    def test_initialization(self, settlement_service: SettlementServiceImpl):
        """Test service initialization"""
        assert settlement_service.position_service is not None
        assert settlement_service.db is not None

    def test_create_daily_settlement_success(
        self, settlement_service: SettlementServiceImpl
    ):
        """Test successful daily settlement creation (WT-004)"""
        trade_date = date(2026, 1, 25)

        # Mock: No positions
        settlement_service.position_service.get_all_positions.return_value = []

        # Mock: Save settlement returns ID
        # Get the cursor mock from the fixture
        with settlement_service.db.cursor() as cursor:
            cursor.fetchone.return_value = [1]

        # Create settlement
        settlement = settlement_service.create_daily_settlement(trade_date)

        # Verify result
        assert settlement.trade_date == trade_date
        assert settlement.realized_pnl == Decimal("0")
        assert settlement.unrealized_pnl == Decimal("0")
        assert settlement.total_pnl == Decimal("0")
        assert settlement.id == 1

    def test_create_daily_settlement_with_positions(
        self, settlement_service: SettlementServiceImpl
    ):
        """Test daily settlement with open positions"""
        trade_date = date(2026, 1, 25)

        # Mock: Has positions
        position = Position(
            id=1,
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("50000"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        settlement_service.position_service.get_all_positions.return_value = [position]

        # Mock: Save settlement returns ID
        with settlement_service.db.cursor() as cursor:
            cursor.fetchone.return_value = [1]

        # Create settlement
        settlement = settlement_service.create_daily_settlement(trade_date)

        # Verify position snapshot was created
        assert len(settlement.positions_snapshot["snapshots"]) == 1
        assert settlement.positions_snapshot["snapshots"][0]["symbol"] == "005930"

    def test_create_position_snapshots(
        self, settlement_service: SettlementServiceImpl
    ):
        """Test position snapshot creation"""
        # Mock: Has positions
        position = Position(
            id=1,
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("50000"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        settlement_service.position_service.get_all_positions.return_value = [position]

        # Create snapshots
        snapshots = settlement_service.create_position_snapshots()

        # Verify
        assert len(snapshots) == 1
        assert snapshots[0].symbol == "005930"
        assert snapshots[0].qty == Decimal("100")
        assert snapshots[0].avg_price == Decimal("50000")
        assert isinstance(snapshots[0], PositionSnapshot)

    def test_calculate_realized_pnl_no_fills(
        self, settlement_service: SettlementServiceImpl
    ):
        """Test realized PnL with no fills"""
        trade_date = date(2026, 1, 25)

        # Mock: No fills (already set in fixture)
        # Calculate
        pnl = settlement_service.calculate_realized_pnl(trade_date)

        # Verify
        assert pnl == Decimal("0")

    def test_calculate_realized_pnl_with_fills(
        self, settlement_service: SettlementServiceImpl
    ):
        """Test realized PnL with buy/sell fills"""
        trade_date = date(2026, 1, 25)

        # Mock: Has fills (buy 100 @ 50000, sell 100 @ 51000)
        # Need to set up cursor mock before calling calculate_realized_pnl
        with settlement_service.db.cursor() as cursor:
            cursor.fetchall.return_value = [
                ("005930", "BUY", "100", "50000", datetime.now()),
                ("005930", "SELL", "100", "51000", datetime.now()),
            ]

        # Calculate
        pnl = settlement_service.calculate_realized_pnl(trade_date)

        # Verify: (51000 - 50000) * 100 = 100000
        assert pnl == Decimal("100000")

    def test_calculate_unrealized_pnl_no_positions(
        self, settlement_service: SettlementServiceImpl
    ):
        """Test unrealized PnL with no positions"""
        # Mock: No positions
        settlement_service.position_service.get_all_positions.return_value = []

        # Calculate
        pnl = settlement_service.calculate_unrealized_pnl([])

        # Verify
        assert pnl == Decimal("0")

    def test_calculate_unrealized_pnl_with_positions(
        self, settlement_service: SettlementServiceImpl
    ):
        """Test unrealized PnL calculation"""
        # Mock: Has position
        position = Position(
            id=1,
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("50000"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        settlement_service.position_service.get_all_positions.return_value = [position]

        # Calculate
        pnl = settlement_service.calculate_unrealized_pnl([position])

        # Verify: With current_price = avg_price (placeholder), unrealized_pnl = 0
        assert pnl == Decimal("0")

    def test_get_daily_settlement_exists(
        self, settlement_service: SettlementServiceImpl
    ):
        """Test getting existing daily settlement"""
        trade_date = date(2026, 1, 25)

        # Mock: Settlement exists
        with settlement_service.db.cursor() as cursor:
            cursor.fetchone.return_value = [
                1,
                trade_date,
                "100000",
                "50000",
                "150000",
                {},
                datetime.now(),
                None,
            ]

        # Get settlement
        settlement = settlement_service.get_daily_settlement(trade_date)

        # Verify
        assert settlement is not None
        assert settlement.id == 1
        assert settlement.trade_date == trade_date
        assert settlement.realized_pnl == Decimal("100000")

    def test_get_daily_settlement_not_exists(
        self, settlement_service: SettlementServiceImpl
    ):
        """Test getting non-existent daily settlement"""
        trade_date = date(2026, 1, 25)

        # Mock: No settlement (already set in fixture)

        # Get settlement
        settlement = settlement_service.get_daily_settlement(trade_date)

        # Verify
        assert settlement is None


class TestPositionSnapshot:
    """PositionSnapshot domain model tests"""

    def test_create_position_snapshot(self):
        """Test creating position snapshot"""
        snapshot = PositionSnapshot(
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("50000"),
            current_price=Decimal("51000"),
            timestamp=datetime.now(),
            realized_pnl=Decimal("100000"),
        )

        assert snapshot.symbol == "005930"
        assert snapshot.qty == Decimal("100")
        assert snapshot.avg_price == Decimal("50000")
        assert snapshot.current_price == Decimal("51000")

    def test_calculate_unrealized_pnl(self):
        """Test unrealized PnL calculation"""
        snapshot = PositionSnapshot(
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("50000"),
            current_price=Decimal("51000"),
            timestamp=datetime.now(),
            realized_pnl=Decimal("100000"),
        )

        # (51000 - 50000) * 100 = 100000
        unrealized_pnl = snapshot.calculate_unrealized_pnl()

        assert unrealized_pnl == Decimal("100000")

    def test_calculate_total_pnl(self):
        """Test total PnL calculation"""
        snapshot = PositionSnapshot(
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("50000"),
            current_price=Decimal("51000"),
            timestamp=datetime.now(),
            realized_pnl=Decimal("100000"),
        )

        # total = realized + unrealized = 100000 + 100000 = 200000
        total_pnl = snapshot.calculate_total_pnl()

        assert total_pnl == Decimal("200000")

    def test_to_dict(self):
        """Test converting snapshot to dictionary"""
        snapshot = PositionSnapshot(
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("50000"),
            current_price=Decimal("51000"),
            timestamp=datetime.now(),
            realized_pnl=Decimal("100000"),
        )

        snapshot_dict = snapshot.to_dict()

        assert snapshot_dict["symbol"] == "005930"
        assert snapshot_dict["qty"] == "100"
        assert snapshot_dict["avg_price"] == "50000"
        assert "unrealized_pnl" in snapshot_dict
        assert "total_pnl" in snapshot_dict
