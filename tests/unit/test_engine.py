"""Tests for TradingEngine facade.

Kent Beck TDD Style:
- RED: Write failing test that documents expected behavior
- GREEN: Make tests pass with minimal implementation
- REFACTOR: Improve code while keeping tests green

This module tests the TradingEngine class with comprehensive coverage
including lifecycle management, trading operations, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
import logging

from stock_manager.engine import TradingEngine, EngineStatus
from stock_manager.trading import (
    TradingConfig,
    Order,
    OrderStatus,
    Position,
    PositionStatus,
    OrderResult,
)
from stock_manager.persistence import TradingState
from stock_manager.persistence.recovery import RecoveryReport, RecoveryResult
from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.trading.strategies.base import Strategy, StrategyScore


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Provide mock KIS client."""
    client = MagicMock(spec=KISRestClient)
    client.make_request = MagicMock(
        return_value={"rt_cd": "0", "msg_cd": "0", "output": {"stck_prpr": "70000"}}
    )
    return client


@pytest.fixture
def trading_config():
    """Provide trading configuration."""
    return TradingConfig(
        max_positions=5,
        polling_interval_sec=2.0,
        rate_limit_per_sec=20,
        max_position_size_pct=Decimal("0.10"),
        default_stop_loss_pct=Decimal("0.05"),
        default_take_profit_pct=Decimal("0.10"),
    )


@pytest.fixture
def engine(mock_client, trading_config, tmp_path):
    """Provide TradingEngine instance."""
    state_path = tmp_path / "test_state.json"
    return TradingEngine(
        client=mock_client,
        config=trading_config,
        account_number="12345678",
        account_product_code="01",
        state_path=state_path,
        is_paper_trading=True,
    )


@pytest.fixture
def mock_position():
    """Provide mock position."""
    return Position(
        symbol="005930",
        quantity=10,
        entry_price=Decimal("70000"),
        current_price=Decimal("75000"),
        status=PositionStatus.OPEN,
        opened_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_order():
    """Provide mock order."""
    return Order(
        order_id="TEST123",
        symbol="005930",
        side="buy",
        quantity=10,
        price=70000,
        status=OrderStatus.FILLED,
        created_at=datetime.now(timezone.utc),
    )


# =============================================================================
# Initialization Tests
# =============================================================================


class TestEngineInitialization:
    """Test engine initialization and component setup."""

    def test_engine_initialization_creates_components(self, engine):
        """Test that __post_init__ creates all required components."""
        assert engine._rate_limiter is not None
        assert engine._position_manager is not None
        assert engine._risk_manager is not None
        assert engine._executor is not None
        assert engine._price_monitor is not None
        assert engine._reconciler is not None
        assert engine._state is not None
        assert not engine._running

    def test_engine_has_correct_configuration(self, engine, trading_config):
        """Test that engine stores configuration correctly."""
        assert engine.config == trading_config
        assert engine.account_number == "12345678"
        assert engine.account_product_code == "01"
        assert engine.is_paper_trading is True

    def test_engine_creates_state_directory(self, tmp_path):
        """Test that engine creates state directory if it doesn't exist."""
        state_path = tmp_path / "nested" / "dir" / "state.json"
        engine = TradingEngine(
            client=MagicMock(),
            config=TradingConfig(),
            account_number="12345678",
            state_path=state_path,
            is_paper_trading=True,
        )
        assert engine.state_path == state_path


# =============================================================================
# Lifecycle Tests
# =============================================================================


class TestEngineLifecycle:
    """Test engine lifecycle management."""

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_initializes_engine(self, mock_reconcile, mock_load, engine):
        """Test that start() initializes engine correctly."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        report = engine.start()

        assert engine._running is True
        assert isinstance(report, RecoveryReport)
        mock_load.assert_called_once_with(engine.state_path)
        mock_reconcile.assert_called_once()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_loads_existing_state(self, mock_reconcile, mock_load, engine, mock_position):
        """Test that start() loads and restores positions from state."""
        mock_state = TradingState(
            positions={"005930": mock_position}, last_updated=datetime.now(timezone.utc)
        )
        mock_load.return_value = mock_state
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        engine.start()

        # Verify position was restored
        position = engine.get_position("005930")
        assert position is not None
        assert position.symbol == "005930"

    def test_start_raises_if_already_running(self, engine):
        """Test that start() raises error if engine already running."""
        engine._running = True

        with pytest.raises(RuntimeError, match="already running"):
            engine.start()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_stop_gracefully_shuts_down(self, mock_reconcile, mock_load, engine):
        """Test that stop() gracefully shuts down engine."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        engine.start()
        engine.stop()

        assert engine._running is False

    def test_stop_raises_if_not_running(self, engine):
        """Test that stop() raises error if engine not running."""
        with pytest.raises(RuntimeError, match="not running"):
            engine.stop()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_context_manager_starts_and_stops(self, mock_reconcile, mock_load, engine):
        """Test that context manager properly starts and stops engine."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        with engine as eng:
            assert eng._running is True
            assert eng is engine

        assert engine._running is False

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_fails_fast_when_recovery_failed(self, mock_reconcile, mock_load, engine):
        """Test that start() raises and keeps engine stopped on recovery failure."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.FAILED,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=["Broker unavailable"],
        )

        with patch.object(engine._price_monitor, "start") as mock_price_start:
            with patch.object(engine._reconciler, "start") as mock_reconciler_start:
                with pytest.raises(RuntimeError, match="Startup reconciliation failed"):
                    engine.start()

        assert engine._running is False
        mock_price_start.assert_not_called()
        mock_reconciler_start.assert_not_called()


@dataclass
class _DummyScore(StrategyScore):
    symbol: str
    passes: bool

    @property
    def passes_all(self) -> bool:
        return self.passes

    @property
    def criteria_passed(self) -> int:
        return 1 if self.passes else 0


class _DummyStrategy(Strategy):
    def __init__(self, *, passing_symbols: set[str]):
        self._passing_symbols = passing_symbols

    def evaluate(self, symbol: str) -> _DummyScore | None:
        return _DummyScore(symbol=symbol, passes=(symbol in self._passing_symbols))


class _RaisingStrategy(Strategy):
    def evaluate(self, symbol: str) -> StrategyScore | None:
        raise RuntimeError("boom")


class TestStrategyOrchestration:
    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_triggers_buy_only_for_passing_symbols(
        self,
        mock_reconcile,
        mock_load,
        mock_client,
        tmp_path,
    ):
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        config = TradingConfig(
            max_positions=5,
            polling_interval_sec=2.0,
            rate_limit_per_sec=20,
            max_position_size_pct=Decimal("0.10"),
            default_stop_loss_pct=Decimal("0.05"),
            default_take_profit_pct=Decimal("0.10"),
            strategy=_DummyStrategy(passing_symbols={"005930"}),
            strategy_symbols=("005930", "000660"),
            strategy_order_quantity=1,
            strategy_max_buys_per_cycle=10,
        )

        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=True,
        )

        engine._get_current_price = MagicMock(return_value=70000)
        engine.buy = MagicMock(return_value=OrderResult(success=True, order_id="OID"))

        engine.start()

        engine.buy.assert_called_once_with("005930", 1, 70000)
        engine.stop()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_strategy_failure_is_isolated_and_does_not_submit_orders(
        self,
        mock_reconcile,
        mock_load,
        mock_client,
        tmp_path,
        caplog,
    ):
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        config = TradingConfig(
            strategy=_RaisingStrategy(),
            strategy_symbols=("005930",),
            strategy_order_quantity=1,
        )

        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=True,
        )
        engine.buy = MagicMock(return_value=OrderResult(success=True, order_id="OID"))

        caplog.set_level(logging.ERROR, logger="stock_manager.engine")

        engine.start()

        assert engine._running is True
        engine.buy.assert_not_called()
        assert "strategy" in caplog.text.lower()

        engine.stop()


# =============================================================================
# Trading Operation Tests
# =============================================================================


class TestTradingOperations:
    """Test buy and sell operations."""

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_places_order(self, mock_reconcile, mock_load, engine, mock_order):
        """Test that buy() places order through executor."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        # Mock executor buy
        engine.start()
        mock_result = OrderResult(success=True, order_id="TEST123")
        engine._executor.buy = MagicMock(return_value=mock_result)

        result = engine.buy("005930", 10, 70000)

        assert result.success is True
        assert result.order_id == "TEST123"
        engine._executor.buy.assert_called_once_with(symbol="005930", quantity=10, price=70000)

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_with_stop_loss(self, mock_reconcile, mock_load, engine, mock_order, mock_position):
        """Test that buy() sets stop-loss alert."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        engine.start()
        mock_result = OrderResult(success=True, order_id="TEST123")
        engine._executor.buy = MagicMock(return_value=mock_result)
        engine._position_manager.get_position = MagicMock(return_value=mock_position)

        result = engine.buy("005930", 10, 70000, stop_loss=65000)

        assert result.success is True
        assert mock_position.stop_loss == Decimal("65000")

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_with_take_profit(
        self, mock_reconcile, mock_load, engine, mock_order, mock_position
    ):
        """Test that buy() sets take-profit alert."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        engine.start()
        mock_result = OrderResult(success=True, order_id="TEST123")
        engine._executor.buy = MagicMock(return_value=mock_result)
        engine._position_manager.get_position = MagicMock(return_value=mock_position)

        result = engine.buy("005930", 10, 70000, take_profit=80000)

        assert result.success is True
        assert mock_position.take_profit == Decimal("80000")

    def test_buy_raises_if_not_running(self, engine):
        """Test that buy() raises error if engine not running."""
        with pytest.raises(RuntimeError, match="not running"):
            engine.buy("005930", 10, 70000)

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_sell_closes_position(self, mock_reconcile, mock_load, engine, mock_order):
        """Test that sell() places sell order through executor."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        engine.start()
        mock_result = OrderResult(success=True, order_id="TEST123")
        engine._executor.sell = MagicMock(return_value=mock_result)

        result = engine.sell("005930", 10, 75000)

        assert result.success is True
        assert result.order_id == "TEST123"
        engine._executor.sell.assert_called_once_with(symbol="005930", quantity=10, price=75000)

    def test_sell_raises_if_not_running(self, engine):
        """Test that sell() raises error if engine not running."""
        with pytest.raises(RuntimeError, match="not running"):
            engine.sell("005930", 10, 75000)


# =============================================================================
# Position Query Tests
# =============================================================================


class TestPositionQueries:
    """Test position query methods."""

    def test_get_positions_returns_all_positions(self, engine, mock_position):
        """Test that get_positions() returns all positions."""
        engine._position_manager.open_position(mock_position)

        positions = engine.get_positions()

        assert len(positions) == 1
        assert "005930" in positions
        assert positions["005930"].symbol == "005930"

    def test_get_position_returns_specific_position(self, engine, mock_position):
        """Test that get_position() returns specific position."""
        engine._position_manager.open_position(mock_position)

        position = engine.get_position("005930")

        assert position is not None
        assert position.symbol == "005930"

    def test_get_position_returns_none_if_not_found(self, engine):
        """Test that get_position() returns None if position doesn't exist."""
        position = engine.get_position("999999")

        assert position is None


# =============================================================================
# Status and Health Tests
# =============================================================================


class TestStatusAndHealth:
    """Test engine status and health checks."""

    def test_get_status_returns_correct_info(self, engine, mock_position):
        """Test that get_status() returns accurate engine status."""
        engine._position_manager.open_position(mock_position)
        engine._running = True

        status = engine.get_status()

        assert isinstance(status, EngineStatus)
        assert status.running is True
        assert status.position_count == 1
        assert status.is_paper_trading is True
        assert str(engine.state_path) in status.state_path

    def test_is_healthy_returns_true_when_healthy(self, engine):
        """Test that is_healthy() returns True when engine is healthy."""
        engine._running = True
        # Mock price monitor is_running property and rate limiter available property
        with patch.object(type(engine._price_monitor), "is_running", property(lambda self: True)):
            with patch.object(type(engine._rate_limiter), "available", property(lambda self: 5)):
                assert engine.is_healthy() is True

    def test_is_healthy_returns_false_when_not_running(self, engine):
        """Test that is_healthy() returns False when engine not running."""
        engine._running = False

        assert engine.is_healthy() is False

    def test_is_healthy_returns_false_when_monitors_stopped(self, engine):
        """Test that is_healthy() returns False when monitors stopped."""
        engine._running = True
        # Mock price monitor as not running
        with patch.object(type(engine._price_monitor), "is_running", property(lambda self: False)):
            assert engine.is_healthy() is False


# =============================================================================
# Internal Helper Tests
# =============================================================================


class TestInternalHelpers:
    """Test internal helper methods."""

    @patch("stock_manager.engine.save_state_atomic")
    def test_persist_state_saves_atomically(self, mock_save, engine):
        """Test that _persist_state() saves state atomically."""
        engine._persist_state()

        mock_save.assert_called_once_with(engine._state, engine.state_path)

    def test_update_state_syncs_positions(self, engine, mock_position):
        """Test that _update_state() syncs positions to state."""
        engine._position_manager.open_position(mock_position)

        engine._update_state()

        assert "005930" in engine._state.positions
        assert engine._state.positions["005930"].symbol == "005930"

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_handle_stop_loss_executes_sell(self, mock_reconcile, mock_load, engine, mock_position):
        """Test that _handle_stop_loss() executes sell order."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        engine.start()
        engine._position_manager.open_position(mock_position)
        engine._executor.sell = MagicMock(
            return_value=OrderResult(success=True, order_id="SELL123")
        )

        engine._handle_stop_loss("005930")

        engine._executor.sell.assert_called_once()

    def test_get_current_price_fetches_from_broker(self, engine, mock_client):
        """Test that _get_current_price() fetches price from broker."""
        mock_client.make_request.return_value = {"output": {"stck_prpr": "70000"}}

        price = engine._get_current_price("005930")

        assert price == 70000
        mock_client.make_request.assert_called_once()

    def test_inquire_balance_uses_client_make_request(self, engine, mock_client):
        """Test that _inquire_balance() uses client.make_request() correctly."""
        mock_client.make_request.return_value = {"output1": [{"pdno": "005930", "hldg_qty": "10"}]}

        result = engine._inquire_balance()

        assert "output1" in result
        mock_client.make_request.assert_called_once()
        # Verify it's using make_request with correct parameters
        call_args = mock_client.make_request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert "tr_id" in call_args.kwargs["headers"]
        params = call_args.kwargs["params"]
        assert params["AFHR_FLPR_YN"] == "N"
        assert params["INQR_DVSN"] == "01"
        assert params["UNPR_DVSN"] == "01"
        assert params["FUND_STTL_ICLD_YN"] == "N"
        assert params["FNCG_AMT_AUTO_RDPT_YN"] == "N"
        assert params["PRCS_DVSN"] == "00"


class TestSupportCoverage:
    def test_rate_limiter_try_acquire_and_reset(self):
        from stock_manager.trading.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests=2, window_seconds=10.0)
        assert limiter.available == 2
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False
        assert limiter.available == 0
        limiter.reset()
        assert limiter.available == 2

    def test_rate_limiter_acquire_timeout(self):
        from stock_manager.trading.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests=1, window_seconds=10.0)
        assert limiter.acquire(timeout=0.1) is True
        assert limiter.acquire(timeout=0.0) is False

    def test_risk_manager_sell_is_always_approved(self):
        from stock_manager.trading.risk import RiskManager

        mgr = RiskManager()
        result = mgr.validate_order(
            symbol="005930",
            quantity=10,
            price=Decimal("70000"),
            side="sell",
        )
        assert result.approved is True

    def test_risk_manager_rejects_when_portfolio_not_set(self):
        from stock_manager.trading.risk import RiskManager

        mgr = RiskManager()
        mgr.update_portfolio(Decimal("0"), Decimal("0"), 0)
        result = mgr.validate_order(
            symbol="005930",
            quantity=1,
            price=Decimal("70000"),
            side="buy",
        )
        assert result.approved is False
        assert "portfolio" in result.reason.lower()

    def test_risk_manager_adjusts_quantity_when_order_too_large(self):
        from stock_manager.trading.risk import RiskManager, RiskLimits

        limits = RiskLimits(max_position_size_pct=Decimal("0.10"), max_positions=5)
        mgr = RiskManager(limits=limits)
        mgr.update_portfolio(Decimal("1000000"), Decimal("0"), 0)
        result = mgr.validate_order(
            symbol="005930",
            quantity=100,
            price=Decimal("10000"),
            side="buy",
        )
        assert result.approved is True
        assert result.adjusted_quantity is not None
        assert result.adjusted_quantity < 100

    def test_risk_manager_suggests_stop_loss_and_take_profit_defaults(self):
        from stock_manager.trading.risk import RiskManager

        mgr = RiskManager()
        mgr.update_portfolio(Decimal("1000000"), Decimal("0"), 0)
        result = mgr.validate_order(
            symbol="005930",
            quantity=1,
            price=Decimal("100"),
            side="buy",
            stop_loss=None,
            take_profit=None,
        )
        assert result.approved is True
        assert result.suggested_stop_loss is not None
        assert result.suggested_take_profit is not None

    def test_calculate_kelly_position_size_handles_invalid_portfolio(self):
        from stock_manager.trading.risk import calculate_kelly_position_size

        assert (
            calculate_kelly_position_size(
                portfolio_value=Decimal("0"),
                price=Decimal("100"),
                risk_per_trade_pct=Decimal("0.02"),
                stop_loss_pct=Decimal("0.05"),
                max_position_size_pct=Decimal("0.10"),
            )
            == 0
        )

    def test_startup_reconciliation_reconciles_orphan_missing_and_qty_mismatch(self, tmp_path):
        from stock_manager.persistence.recovery import startup_reconciliation, RecoveryResult
        from stock_manager.persistence.state import TradingState

        local = TradingState(
            positions={
                "AAA": {"symbol": "AAA", "quantity": 1, "status": "open"},
                "CCC": {"symbol": "CCC", "quantity": 1, "status": "open"},
            }
        )
        saved: list[TradingState] = []

        def _save(state, _path):
            saved.append(state)

        def _inquire(_client):
            return {
                "rt_cd": "0",
                "output1": [
                    {"pdno": "BBB", "hldg_qty": "10"},
                    {"pdno": "CCC", "hldg_qty": "2"},
                ],
            }

        report = startup_reconciliation(
            local_state=local,
            client=object(),
            inquire_balance_func=_inquire,
            save_state_func=_save,
            state_path=tmp_path / "state.json",
        )

        assert report.result == RecoveryResult.RECONCILED
        assert "BBB" in report.orphan_positions
        assert "AAA" in report.missing_positions
        assert report.quantity_mismatches.get("CCC") == (1, 2)
        assert local.positions["CCC"]["quantity"] == 2
        assert saved

    def test_startup_reconciliation_fails_when_broker_unavailable(self, tmp_path):
        from stock_manager.persistence.recovery import startup_reconciliation, RecoveryResult
        from stock_manager.persistence.state import TradingState

        local = TradingState(positions={})

        def _save(_state, _path):
            raise AssertionError("save_state should not be called")

        def _inquire(_client):
            return {"rt_cd": "1", "msg1": "down"}

        report = startup_reconciliation(
            local_state=local,
            client=object(),
            inquire_balance_func=_inquire,
            save_state_func=_save,
            state_path=tmp_path / "state.json",
        )
        assert report.result == RecoveryResult.FAILED
        assert report.errors

    def test_position_reconciler_detects_orphan_and_missing(self):
        from stock_manager.monitoring.reconciler import PositionReconciler

        position_manager = MagicMock()
        position_manager.get_all_positions.return_value = {
            "AAA": {"quantity": 1},
        }

        def _inquire():
            return {
                "rt_cd": "0",
                "output1": [{"pdno": "BBB", "hldg_qty": "2"}],
            }

        reconciler = PositionReconciler(
            position_manager=position_manager, inquire_balance_func=_inquire
        )
        result = reconciler.reconcile_now()
        assert result.is_clean is False
        assert "AAA" in result.missing_positions
        assert "BBB" in result.orphan_positions

    def test_order_executor_buy_success_and_duplicate_detection(self, mock_client):
        from stock_manager.trading.executor import OrderExecutor

        executor = OrderExecutor(
            client=mock_client,
            account_number="12345678",
            account_product_code="01",
            is_paper_trading=True,
        )

        with patch(
            "stock_manager.adapters.broker.kis.apis.domestic_stock.orders.cash_order"
        ) as mock_cash_order:
            mock_cash_order.return_value = {
                "url_path": "/uapi/test",
                "params": {"x": 1},
                "tr_id": "T123",
            }
            mock_client.make_request.return_value = {
                "rt_cd": "0",
                "output": {"ODNO": "B123"},
                "msg1": "OK",
            }

            result = executor.buy(
                symbol="005930",
                quantity=1,
                price=70000,
                idempotency_key="K",
            )
            assert result.success is True
            assert result.broker_order_id == "B123"

            dup = executor.buy(
                symbol="005930",
                quantity=1,
                price=70000,
                idempotency_key="K",
            )
            assert dup.success is False

    def test_order_executor_handles_broker_failure(self, mock_client):
        from stock_manager.trading.executor import OrderExecutor

        executor = OrderExecutor(client=mock_client, account_number="12345678")

        with patch(
            "stock_manager.adapters.broker.kis.apis.domestic_stock.orders.cash_order"
        ) as mock_cash_order:
            mock_cash_order.return_value = {
                "url_path": "/uapi/test",
                "params": {"x": 1},
                "tr_id": "T123",
            }
            mock_client.make_request.return_value = {"rt_cd": "1", "msg1": "NO"}
            result = executor.buy(symbol="005930", quantity=1, price=70000, idempotency_key="K2")
            assert result.success is False
            assert result.message

    def test_order_executor_execute_with_retry_succeeds_after_retry(self):
        from stock_manager.trading.executor import OrderExecutor
        from stock_manager.trading.models import Order

        executor = OrderExecutor(client=MagicMock(), account_number="12345678")
        order = Order(symbol="005930", side="buy", quantity=1, price=70000)

        executor.buy = MagicMock(
            side_effect=[
                OrderResult(success=False, order_id=order.idempotency_key, message="fail"),
                OrderResult(success=True, order_id=order.idempotency_key, broker_order_id="B1"),
            ]
        )

        with patch("time.sleep", return_value=None):
            result = executor.execute_with_retry(order, max_attempts=2)

        assert result.success is True
        assert order.broker_order_id == "B1"
