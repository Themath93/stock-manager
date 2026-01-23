"""
Domain model tests for Worker, StockLock, WorkerProcess, Candidate, DailySummary
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.stock_manager.domain.worker import (
    WorkerStatus,
    StockLock,
    WorkerProcess,
    Candidate,
    PositionSnapshot,
    DailySummary,
)


class TestWorkerStatus:
    """WorkerStatus Enum tests"""

    def test_worker_status_values(self):
        """WorkerStatus enum values"""
        assert WorkerStatus.IDLE.value == "IDLE"
        assert WorkerStatus.SCANNING.value == "SCANNING"
        assert WorkerStatus.HOLDING.value == "HOLDING"
        assert WorkerStatus.EXITING.value == "EXITING"


class TestStockLock:
    """StockLock dataclass tests"""

    def test_create_stock_lock(self):
        """Create a valid stock lock"""
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=5)

        lock = StockLock(
            id=1,
            symbol="005930",
            worker_id="worker-001",
            acquired_at=now,
            expires_at=expires_at,
            heartbeat_at=now,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )

        assert lock.symbol == "005930"
        assert lock.worker_id == "worker-001"
        assert lock.status == "ACTIVE"

    def test_is_valid_active_lock(self):
        """is_valid() returns True for active non-expired lock"""
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=5)

        lock = StockLock(
            id=1,
            symbol="005930",
            worker_id="worker-001",
            acquired_at=now,
            expires_at=expires_at,
            heartbeat_at=now,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )

        assert lock.is_valid() is True

    def test_is_valid_expired_lock(self):
        """is_valid() returns False for expired lock"""
        now = datetime.utcnow()
        expires_at = now - timedelta(minutes=1)  # Already expired

        lock = StockLock(
            id=1,
            symbol="005930",
            worker_id="worker-001",
            acquired_at=now,
            expires_at=expires_at,
            heartbeat_at=now,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )

        assert lock.is_valid() is False

    def test_is_valid_expired_status(self):
        """is_valid() returns False for EXPIRED status"""
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=5)

        lock = StockLock(
            id=1,
            symbol="005930",
            worker_id="worker-001",
            acquired_at=now,
            expires_at=expires_at,
            heartbeat_at=now,
            status="EXPIRED",
            created_at=now,
            updated_at=now,
        )

        assert lock.is_valid() is False

    def test_needs_renewal_soon(self):
        """needs_renewal() returns True when lock expires soon (< half TTL)"""
        ttl = timedelta(minutes=5)
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=2)  # < half of 5 minutes

        lock = StockLock(
            id=1,
            symbol="005930",
            worker_id="worker-001",
            acquired_at=now,
            expires_at=expires_at,
            heartbeat_at=now,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )

        assert lock.needs_renewal(ttl) is True

    def test_needs_renewal_later(self):
        """needs_renewal() returns False when lock expires later (>= half TTL)"""
        ttl = timedelta(minutes=5)
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=4)  # > half of 5 minutes

        lock = StockLock(
            id=1,
            symbol="005930",
            worker_id="worker-001",
            acquired_at=now,
            expires_at=expires_at,
            heartbeat_at=now,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )

        assert lock.needs_renewal(ttl) is False


class TestWorkerProcess:
    """WorkerProcess dataclass tests"""

    def test_create_worker_process(self):
        """Create a valid worker process"""
        now = datetime.utcnow()

        process = WorkerProcess(
            id=1,
            worker_id="worker-001",
            status=WorkerStatus.IDLE,
            current_symbol=None,
            started_at=now,
            last_heartbeat_at=now,
            heartbeat_interval=timedelta(seconds=30),
            created_at=now,
            updated_at=now,
        )

        assert process.worker_id == "worker-001"
        assert process.status == WorkerStatus.IDLE
        assert process.current_symbol is None

    def test_is_alive_recent_heartbeat(self):
        """is_alive() returns True for recent heartbeat"""
        ttl = timedelta(minutes=5)
        now = datetime.utcnow()
        last_heartbeat = now - timedelta(seconds=30)  # Within TTL * 3

        process = WorkerProcess(
            id=1,
            worker_id="worker-001",
            status=WorkerStatus.IDLE,
            current_symbol=None,
            started_at=now,
            last_heartbeat_at=last_heartbeat,
            heartbeat_interval=timedelta(seconds=30),
            created_at=now,
            updated_at=now,
        )

        assert process.is_alive(ttl) is True

    def test_is_alive_stale_heartbeat(self):
        """is_alive() returns False for stale heartbeat"""
        ttl = timedelta(minutes=5)
        now = datetime.utcnow()
        last_heartbeat = now - timedelta(minutes=20)  # Exceeds TTL * 3

        process = WorkerProcess(
            id=1,
            worker_id="worker-001",
            status=WorkerStatus.IDLE,
            current_symbol=None,
            started_at=now,
            last_heartbeat_at=last_heartbeat,
            heartbeat_interval=timedelta(seconds=30),
            created_at=now,
            updated_at=now,
        )

        assert process.is_alive(ttl) is False


class TestCandidate:
    """Candidate dataclass tests"""

    def test_create_candidate(self):
        """Create a valid candidate"""
        now = datetime.utcnow()

        candidate = Candidate(
            symbol="005930",
            name="삼성전자",
            current_price=Decimal("80000"),
            volume=1000000,
            change_percent=Decimal("2.5"),
            discovered_at=now,
            metadata={"change": Decimal("2000")},
        )

        assert candidate.symbol == "005930"
        assert candidate.name == "삼성전자"
        assert candidate.current_price == Decimal("80000")
        assert candidate.change_percent == Decimal("2.5")

    def test_to_dict(self):
        """Convert candidate to dictionary"""
        now = datetime.utcnow()

        candidate = Candidate(
            symbol="005930",
            name="삼성전자",
            current_price=Decimal("80000"),
            volume=1000000,
            change_percent=Decimal("2.5"),
            discovered_at=now,
            metadata={"change": Decimal("2000")},
        )

        result = candidate.to_dict()

        assert result["symbol"] == "005930"
        assert result["name"] == "삼성전자"
        assert result["current_price"] == 80000.0
        assert result["volume"] == 1000000
        assert result["change_percent"] == 2.5
        assert "discovered_at" in result
        assert result["metadata"]["change"] == 2000.0


class TestPositionSnapshot:
    """PositionSnapshot dataclass tests"""

    def test_create_position_snapshot(self):
        """Create a valid position snapshot"""
        now = datetime.utcnow()

        snapshot = PositionSnapshot(
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("80000"),
            current_price=Decimal("82000"),
            timestamp=now,
            realized_pnl=Decimal("50000"),
            metadata={},
        )

        assert snapshot.symbol == "005930"
        assert snapshot.qty == Decimal("100")
        assert snapshot.avg_price == Decimal("80000")
        assert snapshot.current_price == Decimal("82000")

    def test_calculate_unrealized_pnl_long(self):
        """Calculate unrealized PnL for long position"""
        now = datetime.utcnow()

        snapshot = PositionSnapshot(
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("80000"),
            current_price=Decimal("82000"),
            timestamp=now,
            realized_pnl=Decimal("0"),
            metadata={},
        )

        unrealized = snapshot.calculate_unrealized_pnl()
        expected = (Decimal("82000") - Decimal("80000")) * Decimal("100")
        assert unrealized == expected  # 200000

    def test_calculate_unrealized_pnl_short(self):
        """Calculate unrealized PnL for short position"""
        now = datetime.utcnow()

        snapshot = PositionSnapshot(
            symbol="005930",
            qty=Decimal("-100"),
            avg_price=Decimal("80000"),
            current_price=Decimal("78000"),
            timestamp=now,
            realized_pnl=Decimal("0"),
            metadata={},
        )

        unrealized = snapshot.calculate_unrealized_pnl()
        expected = (Decimal("78000") - Decimal("80000")) * Decimal("-100")
        assert unrealized == expected  # 200000

    def test_calculate_total_pnl(self):
        """Calculate total PnL (realized + unrealized)"""
        now = datetime.utcnow()

        snapshot = PositionSnapshot(
            symbol="005930",
            qty=Decimal("100"),
            avg_price=Decimal("80000"),
            current_price=Decimal("82000"),
            timestamp=now,
            realized_pnl=Decimal("50000"),
            metadata={},
        )

        total = snapshot.calculate_total_pnl()
        unrealized = snapshot.calculate_unrealized_pnl()
        expected = Decimal("50000") + unrealized
        assert total == expected


class TestDailySummary:
    """DailySummary dataclass tests"""

    def test_create_daily_summary(self):
        """Create a valid daily summary"""
        now = datetime.utcnow()

        summary = DailySummary(
            id=1,
            worker_id="worker-001",
            summary_date=datetime.utcnow().date(),
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            gross_profit=Decimal("50000"),
            gross_loss=Decimal("30000"),
            net_pnl=Decimal("20000"),
            unrealized_pnl=Decimal("10000"),
            max_drawdown=Decimal("0.15"),
            win_rate=Decimal("0.7"),
            profit_factor=Decimal("1.67"),
            created_at=now,
            updated_at=now,
        )

        assert summary.worker_id == "worker-001"
        assert summary.total_trades == 10
        assert summary.net_pnl == Decimal("20000")

    def test_calculate_win_rate(self):
        """Calculate win rate"""
        now = datetime.utcnow()

        summary = DailySummary(
            id=1,
            worker_id="worker-001",
            summary_date=datetime.utcnow().date(),
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            gross_profit=Decimal("50000"),
            gross_loss=Decimal("30000"),
            net_pnl=Decimal("20000"),
            unrealized_pnl=Decimal("10000"),
            max_drawdown=Decimal("0.15"),
            win_rate=Decimal("0.7"),
            profit_factor=Decimal("1.67"),
            created_at=now,
            updated_at=now,
        )

        win_rate = summary.calculate_win_rate()
        assert win_rate == Decimal("0.7")

    def test_calculate_win_rate_no_trades(self):
        """Calculate win rate with no trades returns 0"""
        now = datetime.utcnow()

        summary = DailySummary(
            id=1,
            worker_id="worker-001",
            summary_date=datetime.utcnow().date(),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            gross_profit=Decimal("0"),
            gross_loss=Decimal("0"),
            net_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            max_drawdown=Decimal("0"),
            win_rate=Decimal("0"),
            profit_factor=Decimal("0"),
            created_at=now,
            updated_at=now,
        )

        win_rate = summary.calculate_win_rate()
        assert win_rate == Decimal("0")

    def test_calculate_profit_factor(self):
        """Calculate profit factor"""
        now = datetime.utcnow()

        summary = DailySummary(
            id=1,
            worker_id="worker-001",
            summary_date=datetime.utcnow().date(),
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            gross_profit=Decimal("50000"),
            gross_loss=Decimal("30000"),
            net_pnl=Decimal("20000"),
            unrealized_pnl=Decimal("10000"),
            max_drawdown=Decimal("0.15"),
            win_rate=Decimal("0.7"),
            profit_factor=Decimal("1.67"),
            created_at=now,
            updated_at=now,
        )

        profit_factor = summary.calculate_profit_factor()
        expected = Decimal("50000") / Decimal("30000")
        assert abs(profit_factor - expected) < Decimal("0.01")

    def test_calculate_profit_factor_no_loss(self):
        """Calculate profit factor with no loss returns 999.99"""
        now = datetime.utcnow()

        summary = DailySummary(
            id=1,
            worker_id="worker-001",
            summary_date=datetime.utcnow().date(),
            total_trades=5,
            winning_trades=5,
            losing_trades=0,
            gross_profit=Decimal("50000"),
            gross_loss=Decimal("0"),
            net_pnl=Decimal("50000"),
            unrealized_pnl=Decimal("0"),
            max_drawdown=Decimal("0"),
            win_rate=Decimal("1.0"),
            profit_factor=Decimal("0"),
            created_at=now,
            updated_at=now,
        )

        profit_factor = summary.calculate_profit_factor()
        assert profit_factor == Decimal("999.99")
