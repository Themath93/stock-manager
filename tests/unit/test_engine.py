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
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from stock_manager.engine import TradingEngine, EngineStatus
from stock_manager.trading import (
    TradingConfig,
    Order,
    OrderStatus,
    Position,
    PositionStatus,
    OrderResult,
    RiskCheckResult,
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
        return_value={
            "rt_cd": "0",
            "msg_cd": "0",
            "output": {"stck_prpr": "70000"},
            "output2": [{"dnca_tot_amt": "10000000"}],
        }
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
        market_hours_enabled=False,
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

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_seeds_executor_idempotency_from_pending_orders(
        self, mock_reconcile, mock_load, engine
    ):
        pending_order = Order(
            order_id="OID-1",
            idempotency_key="persisted-key",
            symbol="005930",
            side="buy",
            quantity=1,
            price=70000,
            status=OrderStatus.PENDING_BROKER,
        )
        mock_state = TradingState(
            pending_orders={pending_order.order_id: pending_order},
            last_updated=datetime.now(timezone.utc),
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

        assert "persisted-key" in engine._executor._submitted_keys

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
    def test_start_enters_degraded_mode_when_recovery_failed(
        self, mock_reconcile, mock_load, mock_client, trading_config, tmp_path
    ):
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.FAILED,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=["Broker unavailable"],
        )
        engine = TradingEngine(
            client=mock_client,
            config=trading_config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=False,
        )

        with patch.object(engine._price_monitor, "start") as mock_price_start:
            with patch.object(engine._reconciler, "start") as mock_reconciler_start:
                engine.start()

        assert engine._running is True
        assert engine._trading_enabled is False
        assert engine._degraded_reason == "startup_recovery_failed"
        mock_price_start.assert_not_called()
        mock_reconciler_start.assert_called_once()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_blocks_live_trading_when_pending_orders_remain(
        self, mock_reconcile, mock_load, mock_client, trading_config, tmp_path
    ):
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.RECONCILED,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=["ord-1"],
            errors=[],
        )
        engine = TradingEngine(
            client=mock_client,
            config=trading_config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=False,
        )

        engine.start()

        assert engine._running is True
        assert engine._trading_enabled is False
        assert engine._degraded_reason == "startup_recovery_unresolved_orders"

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_keeps_mock_trading_enabled_when_pending_orders_remain(
        self, mock_reconcile, mock_load, engine
    ):
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.RECONCILED,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=["ord-1"],
            errors=[],
        )

        engine.start()

        assert engine._trading_enabled is True
        assert engine._degraded_reason is None

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_allows_live_override_when_pending_orders_remain(
        self, mock_reconcile, mock_load, mock_client, tmp_path
    ):
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.RECONCILED,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=["ord-1"],
            errors=[],
        )
        config = TradingConfig(market_hours_enabled=False, allow_unsafe_trading=True)
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=False,
        )

        engine.start()

        assert engine._trading_enabled is True
        assert engine._degraded_reason is None

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_enters_reduce_only_when_execution_stream_unavailable_at_startup(
        self, mock_reconcile, mock_load, mock_client, tmp_path
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
            market_hours_enabled=False,
            websocket_monitoring_enabled=True,
            websocket_execution_notice_enabled=True,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=False,
        )
        engine.notifier = MagicMock()

        with patch.object(
            engine,
            "_start_realtime_streams",
            return_value=SimpleNamespace(
                quote_stream_active=False,
                should_block_trading=True,
                degraded_reason="execution_stream_unavailable",
            ),
        ):
            engine.start()

        assert engine._running is True
        assert engine._operational_state == "degraded_reduce_only"
        assert engine._trading_enabled is False
        assert engine._degraded_reason == "execution_stream_unavailable"
        event_types = [call[0][0].event_type for call in engine.notifier.notify.call_args_list]
        assert "error.execution_stream_unavailable" in event_types


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


class _ScreeningStrategy(Strategy):
    def __init__(self, scores: dict[str, bool]) -> None:
        self.scores = scores
        self.screened_symbols: list[str] = []

    def screen(self, symbols: list[str]) -> list[StrategyScore]:
        self.screened_symbols = list(symbols)
        return [
            _DummyScore(symbol=symbol, passes=self.scores.get(symbol, True)) for symbol in symbols
        ]

    def evaluate(self, symbol: str) -> _DummyScore | None:
        return _DummyScore(symbol=symbol, passes=self.scores.get(symbol, True))


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

        engine.buy.assert_called_once_with("005930", 1, 70000, origin="strategy")
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

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_strategy_max_symbols_per_cycle_truncates_screened_list(
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

        symbols = ("005930", "000660", "035720", "051910", "035420")
        strategy = _ScreeningStrategy({symbol: True for symbol in symbols})

        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=symbols,
            strategy_order_quantity=1,
            strategy_max_symbols_per_cycle=3,
            strategy_max_buys_per_cycle=10,
            strategy_run_interval_sec=0.0,
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

        assert strategy.screened_symbols == ["005930", "000660", "035720"]
        assert engine.buy.call_count == 3
        assert [call.args[0] for call in engine.buy.call_args_list] == [
            "005930",
            "000660",
            "035720",
        ]
        engine.stop()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_strategy_max_buys_per_cycle_limits_submissions(
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

        symbols = ("005930", "000660", "035720", "051910")
        strategy = _ScreeningStrategy({symbol: True for symbol in symbols})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=symbols,
            strategy_order_quantity=1,
            strategy_max_symbols_per_cycle=10,
            strategy_max_buys_per_cycle=2,
            strategy_run_interval_sec=0.0,
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

        assert engine.buy.call_count == 2
        assert [call.args[0] for call in engine.buy.call_args_list] == ["005930", "000660"]
        engine.stop()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    @pytest.mark.parametrize("order_quantity", [0, -1])
    def test_strategy_order_quantity_le_zero_skips_buys(
        self,
        mock_reconcile,
        mock_load,
        mock_client,
        tmp_path,
        order_quantity,
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

        strategy = _ScreeningStrategy({"005930": True, "000660": True})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=("005930", "000660"),
            strategy_order_quantity=order_quantity,
            strategy_max_symbols_per_cycle=10,
            strategy_max_buys_per_cycle=10,
            strategy_run_interval_sec=0.0,
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

        engine.start()

        engine.buy.assert_not_called()
        engine.stop()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_strategy_cycle_skips_existing_positions(
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

        strategy = _ScreeningStrategy({"005930": True, "000660": True, "035720": True})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=("005930", "000660", "035720"),
            strategy_order_quantity=1,
            strategy_max_symbols_per_cycle=10,
            strategy_max_buys_per_cycle=10,
            strategy_run_interval_sec=0.0,
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
        engine._position_manager.get_position = MagicMock(
            side_effect=lambda symbol: True if symbol == "005930" else None
        )

        engine.start()

        assert engine.buy.call_count == 2
        assert [call.args[0] for call in engine.buy.call_args_list] == ["000660", "035720"]
        engine.stop()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_strategy_skips_non_passing_scores(
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

        strategy = _ScreeningStrategy({"005930": True, "000660": False, "035720": True})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=("005930", "000660", "035720"),
            strategy_order_quantity=1,
            strategy_max_symbols_per_cycle=10,
            strategy_max_buys_per_cycle=10,
            strategy_run_interval_sec=0.0,
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

        assert engine.buy.call_count == 2
        assert [call.args[0] for call in engine.buy.call_args_list] == ["005930", "035720"]
        engine.stop()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_strategy_auto_discover_uses_mock_fallback_symbols(
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

        strategy = _ScreeningStrategy({"005930": True, "000660": True})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=(),
            strategy_order_quantity=1,
            strategy_max_symbols_per_cycle=10,
            strategy_max_buys_per_cycle=10,
            strategy_auto_discover=True,
            strategy_discovery_limit=2,
            strategy_discovery_fallback_symbols=("005930", "000660", "035720"),
            strategy_run_interval_sec=0.0,
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

        assert strategy.screened_symbols == ["005930", "000660"]
        assert engine.buy.call_count == 2
        engine.stop()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_strategy_auto_discover_uses_volume_rank_in_real_mode(
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

        strategy = _ScreeningStrategy({"005930": True, "000660": True})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=(),
            strategy_order_quantity=1,
            strategy_max_buys_per_cycle=10,
            strategy_auto_discover=True,
            strategy_discovery_limit=2,
            strategy_run_interval_sec=0.0,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=False,
        )
        engine._get_current_price = MagicMock(return_value=70000)
        engine.buy = MagicMock(return_value=OrderResult(success=True, order_id="OID"))

        with patch(
            "stock_manager.adapters.broker.kis.apis.domestic_stock.ranking.get_volume_rank",
            return_value={
                "rt_cd": "0",
                "output": [
                    {"stck_shrn_iscd": "005930"},
                    {"mksc_shrn_iscd": "000660"},
                ],
            },
        ):
            engine.start()

        assert strategy.screened_symbols == ["005930", "000660"]
        assert engine.buy.call_count == 2
        engine.stop()

    def test_strategy_auto_discover_status_tracks_mock_fallback_symbols(
        self,
        mock_client,
        tmp_path,
    ):
        strategy = _ScreeningStrategy({"005930": True, "000660": True})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=(),
            strategy_order_quantity=1,
            strategy_max_symbols_per_cycle=10,
            strategy_max_buys_per_cycle=0,
            strategy_auto_discover=True,
            strategy_discovery_limit=2,
            strategy_discovery_fallback_symbols=("005930", "000660", "035720"),
            strategy_run_interval_sec=0.0,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=True,
        )

        engine._run_strategy_cycle()
        status = engine.get_status()

        assert status.strategy_discovery_source == "mock_fallback"
        assert status.strategy_discovery_symbols == ("005930", "000660")
        assert status.strategy_discovery_reason == "paper_trading_mode"
        assert status.strategy_discovery_updated_at is not None

    def test_strategy_auto_discover_status_tracks_volume_rank_source(
        self,
        mock_client,
        tmp_path,
    ):
        strategy = _ScreeningStrategy({"005930": True, "000660": True})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=(),
            strategy_order_quantity=1,
            strategy_max_symbols_per_cycle=10,
            strategy_max_buys_per_cycle=0,
            strategy_auto_discover=True,
            strategy_discovery_limit=2,
            strategy_discovery_fallback_symbols=("005930",),
            strategy_run_interval_sec=0.0,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=False,
        )

        with patch(
            "stock_manager.adapters.broker.kis.apis.domestic_stock.ranking.get_volume_rank",
            return_value={
                "rt_cd": "0",
                "output": [
                    {"stck_shrn_iscd": "005930"},
                    {"mksc_shrn_iscd": "000660"},
                ],
            },
        ):
            engine._run_strategy_cycle()

        status = engine.get_status()
        assert status.strategy_discovery_source == "volume_rank"
        assert status.strategy_discovery_symbols == ("005930", "000660")
        assert status.strategy_discovery_reason is None
        assert status.strategy_discovery_updated_at is not None

    def test_strategy_auto_discover_status_tracks_fallback_reason_when_rank_fails(
        self,
        mock_client,
        tmp_path,
    ):
        strategy = _ScreeningStrategy({"005930": True, "000660": True})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=(),
            strategy_order_quantity=1,
            strategy_max_symbols_per_cycle=10,
            strategy_max_buys_per_cycle=0,
            strategy_auto_discover=True,
            strategy_discovery_limit=2,
            strategy_discovery_fallback_symbols=("005930", "000660"),
            strategy_run_interval_sec=0.0,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=False,
        )

        with patch(
            "stock_manager.adapters.broker.kis.apis.domestic_stock.ranking.get_volume_rank",
            side_effect=RuntimeError("rank failed"),
        ):
            engine._run_strategy_cycle()

        status = engine.get_status()
        assert status.strategy_discovery_source == "fallback"
        assert status.strategy_discovery_symbols == ("005930", "000660")
        assert status.strategy_discovery_reason == "volume_rank_request_failed"
        assert status.strategy_discovery_updated_at is not None

    def test_strategy_cycle_skips_when_buying_is_blocked(self, mock_client, tmp_path):
        strategy = _ScreeningStrategy({"005930": True})
        config = TradingConfig(
            strategy=strategy,
            strategy_symbols=("005930",),
            strategy_order_quantity=1,
            strategy_max_buys_per_cycle=1,
            strategy_run_interval_sec=0.0,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        engine._running = True
        engine._set_operational_state(
            operational_state="degraded_reduce_only",
            degraded_reason="runtime_reconciliation_drift",
        )
        engine.buy = MagicMock(return_value=OrderResult(success=False, order_id="OID"))
        engine._get_current_price = MagicMock(return_value=70000)

        engine._run_strategy_cycle()

        engine.buy.assert_not_called()
        engine._get_current_price.assert_not_called()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_strategy_orchestration_starts_background_thread_when_interval_positive(
        self, mock_reconcile, mock_load, mock_client, tmp_path
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
            strategy=_DummyStrategy(passing_symbols={"005930"}),
            strategy_symbols=("005930",),
            strategy_order_quantity=1,
            strategy_max_buys_per_cycle=10,
            strategy_run_interval_sec=0.05,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=True,
        )

        engine._run_strategy_cycle = MagicMock()
        engine._get_current_price = MagicMock(return_value=70000)
        engine.buy = MagicMock(return_value=OrderResult(success=True, order_id="OID"))

        with (
            patch.object(
                engine,
                "_start_realtime_streams",
                return_value=SimpleNamespace(
                    quote_stream_active=False,
                    should_block_trading=False,
                    degraded_reason=None,
                ),
            ),
            patch("stock_manager.engine.load_state", return_value=None),
            patch(
                "stock_manager.engine.startup_reconciliation",
                return_value=mock_reconcile.return_value,
            ),
        ):
            engine.start()

        assert engine._strategy_thread is not None
        assert engine._strategy_thread.name == "StrategyOrchestrator"

        engine.stop()

        assert engine._strategy_thread is None

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_strategy_orchestration_does_not_create_duplicate_thread_when_already_running(
        self, mock_reconcile, mock_load, mock_client, tmp_path
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
            strategy=_DummyStrategy(passing_symbols={"005930"}),
            strategy_symbols=("005930",),
            strategy_order_quantity=1,
            strategy_max_buys_per_cycle=10,
            strategy_run_interval_sec=0.05,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=True,
        )

        engine._run_strategy_cycle = MagicMock()

        with (
            patch.object(
                engine,
                "_start_realtime_streams",
                return_value=SimpleNamespace(
                    quote_stream_active=False,
                    should_block_trading=False,
                    degraded_reason=None,
                ),
            ),
            patch("stock_manager.engine.load_state", return_value=None),
            patch(
                "stock_manager.engine.startup_reconciliation",
                return_value=mock_reconcile.return_value,
            ),
        ):
            engine.start()

        first_thread = engine._strategy_thread
        engine._start_strategy_orchestration()

        assert engine._strategy_thread is first_thread
        assert first_thread is not None

        engine.stop()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_strategy_orchestration_skips_thread_when_interval_is_zero(
        self, mock_reconcile, mock_load, mock_client, tmp_path
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
            strategy=_DummyStrategy(passing_symbols={"005930"}),
            strategy_symbols=("005930",),
            strategy_order_quantity=1,
            strategy_max_buys_per_cycle=10,
            strategy_run_interval_sec=0.0,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=True,
        )

        engine._run_strategy_cycle = MagicMock()

        engine._start_strategy_orchestration()

        assert engine._strategy_thread is None
        assert engine._run_strategy_cycle.call_count >= 1


class TestRealtimeBridge:
    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_uses_websocket_streams_when_enabled(
        self,
        mock_reconcile,
        mock_load,
        mock_client,
        tmp_path,
        mock_position,
    ):
        mock_load.return_value = TradingState(
            positions={"005930": mock_position},
            last_updated=datetime.now(timezone.utc),
        )
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        broker_adapter = MagicMock()
        config = TradingConfig(
            websocket_monitoring_enabled=True,
            websocket_execution_notice_enabled=True,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=True,
            broker_adapter=broker_adapter,
        )

        engine.start()
        engine.stop()

        broker_adapter.subscribe_quotes.assert_called_once()
        broker_adapter.subscribe_executions.assert_called_once()
        broker_adapter.disconnect_websocket.assert_called_once()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_with_stop_loss_subscribes_symbol_to_websocket_after_fill(
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

        broker_adapter = MagicMock()
        config = TradingConfig(websocket_monitoring_enabled=True, max_positions=5, market_hours_enabled=False)
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=True,
            broker_adapter=broker_adapter,
        )
        engine.start()

        engine._executor.buy = MagicMock(return_value=OrderResult(success=True, order_id="BUY123"))

        result = engine.buy("005930", 1, 70000, stop_loss=65000)

        assert result.success is True
        broker_adapter.subscribe_quotes.assert_not_called()

        event = SimpleNamespace(
            symbol="005930",
            order_id="BUY123",
            side="buy",
            executed_price=Decimal("70000"),
            executed_quantity=Decimal("1"),
            timestamp="2026-03-08T00:00:00+00:00",
        )
        engine._apply_execution_event(event)

        broker_adapter.subscribe_quotes.assert_called_with(
            symbols=["005930"],
            callback=engine._on_websocket_quote,
        )
        position = engine.get_position("005930")
        assert position is not None
        assert position.stop_loss == Decimal("65000")
        engine.stop()

    def test_websocket_execution_notice_triggers_reconciliation(self, engine):
        engine._reconciler.reconcile_now = MagicMock(
            return_value=SimpleNamespace(is_clean=True, discrepancies=[])
        )
        engine._notify = MagicMock()
        engine._apply_execution_event = MagicMock()

        event = SimpleNamespace(
            symbol="005930",
            order_id="ORD-1",
            side="buy",
            price=Decimal("70000"),
            quantity=Decimal("1"),
        )
        engine._on_websocket_execution(event)

        engine._notify.assert_called_once()
        engine._apply_execution_event.assert_called_once_with(event)
        engine._reconciler.reconcile_now.assert_called_once()

    def test_websocket_execution_notice_payload_is_emitted_in_notification(self, engine):
        engine._reconciler.reconcile_now = MagicMock(
            return_value=SimpleNamespace(is_clean=True, discrepancies=[])
        )
        engine.notifier = MagicMock()
        engine._update_state = MagicMock()
        engine._persist_state = MagicMock()

        event = SimpleNamespace(
            symbol="005930",
            order_id="ORD-1",
            side="buy",
            price=Decimal("70000"),
            quantity=Decimal("1"),
        )

        engine._on_websocket_execution(event)

        engine._reconciler.reconcile_now.assert_called_once()
        engine._update_state.assert_not_called()
        engine._persist_state.assert_not_called()

        event_arg = engine.notifier.notify.call_args_list[0][0][0]
        assert event_arg.event_type == "order.execution_notice"
        assert event_arg.details["symbol"] == "005930"
        assert event_arg.details["order_id"] == "ORD-1"
        assert event_arg.details["side"] == "buy"
        assert event_arg.details["price"] == "70000"
        assert event_arg.details["quantity"] == "1"
        assert event_arg.details["is_paper_trading"] is True

    def test_reconciliation_cycle_handles_discrepancy(self, engine):
        reconciler_result = SimpleNamespace(
            is_clean=False,
            discrepancies=[{"symbol": "005930"}],
            orphan_positions=["000660"],
            missing_positions=[],
            quantity_mismatches={"005930": (10, 9)},
            broker_positions={},
            local_positions={},
        )
        engine._handle_discrepancy = MagicMock()
        engine._update_state = MagicMock()
        engine._persist_state = MagicMock()
        engine._sync_pending_orders_from_broker = MagicMock()
        engine._apply_reconciled_positions = MagicMock()

        engine._on_reconciliation_cycle(reconciler_result)

        engine._handle_discrepancy.assert_called_once_with(reconciler_result)
        engine._sync_pending_orders_from_broker.assert_called_once_with(reconciler_result, [])
        engine._apply_reconciled_positions.assert_called_once_with({})
        engine._persist_state.assert_called_once()

    def test_reconciliation_cycle_latches_live_trading_when_drift_detected(
        self, mock_client, tmp_path
    ):
        engine = TradingEngine(
            client=mock_client,
            config=TradingConfig(market_hours_enabled=False),
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        engine._running = True
        engine._set_operational_state(operational_state="normal", degraded_reason=None)
        engine.notifier = MagicMock()
        engine._persist_state = MagicMock()
        engine._sync_pending_orders_from_broker = MagicMock()
        engine._apply_reconciled_positions = MagicMock()

        reconciler_result = SimpleNamespace(
            is_clean=False,
            discrepancies=["Missing at broker: 005930"],
            orphan_positions=[],
            missing_positions=["005930"],
            quantity_mismatches={},
            broker_positions={},
            local_positions={},
        )

        engine._on_reconciliation_cycle(reconciler_result)

        assert engine._trading_enabled is False
        assert engine._degraded_reason == "runtime_reconciliation_drift"
        events = [call[0][0].event_type for call in engine.notifier.notify.call_args_list]
        assert "error.runtime_reconciliation_drift" in events

    def test_reconciliation_cycle_does_not_auto_clear_runtime_drift(self, mock_client, tmp_path):
        engine = TradingEngine(
            client=mock_client,
            config=TradingConfig(market_hours_enabled=False),
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        engine._running = True
        engine._set_operational_state(
            operational_state="degraded_reduce_only",
            degraded_reason="runtime_reconciliation_drift",
        )
        engine._persist_state = MagicMock()
        engine._sync_pending_orders_from_broker = MagicMock()
        engine._apply_reconciled_positions = MagicMock()

        clean_result = SimpleNamespace(
            is_clean=True,
            discrepancies=[],
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            broker_positions={},
            local_positions={},
        )

        engine._on_reconciliation_cycle(clean_result)

        assert engine._trading_enabled is False
        assert engine._degraded_reason == "runtime_reconciliation_drift"

    def test_websocket_execution_notice_swallow_reconcile_exception(self, engine):
        engine._reconciler.reconcile_now = MagicMock(side_effect=RuntimeError("reconcile failed"))
        engine._update_state = MagicMock()
        engine._persist_state = MagicMock()
        engine.notifier = MagicMock()

        event = SimpleNamespace(
            symbol="005930",
            order_id="ORD-1",
            side="buy",
            price=Decimal("70000"),
            quantity=Decimal("1"),
        )

        engine._on_websocket_execution(event)

    def test_websocket_reconnect_exhausted_starts_polling_fallback_and_blocks_live_trading(
        self, mock_client, tmp_path, mock_position
    ):
        config = TradingConfig(
            market_hours_enabled=False,
            websocket_monitoring_enabled=True,
            websocket_execution_notice_enabled=True,
        )
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        engine._running = True
        engine._set_operational_state(operational_state="normal", degraded_reason=None)
        engine.notifier = MagicMock()
        engine._position_manager.open_position(mock_position)

        with patch.object(engine._price_monitor, "start") as mock_price_start:
            event = SimpleNamespace(status="reconnect_exhausted", reconnect_attempts=5)
            engine._on_websocket_lifecycle(event)
            engine._on_websocket_lifecycle(event)

        mock_price_start.assert_called_once_with(["005930"], engine._on_price_update)
        assert engine._trading_enabled is False
        assert engine._degraded_reason == "execution_stream_unavailable"
        event_types = [call[0][0].event_type for call in engine.notifier.notify.call_args_list]
        assert event_types.count("error.execution_stream_unavailable") == 1


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
        assert result.order_id in engine._state.pending_orders
        call_kwargs = engine._executor.buy.call_args.kwargs
        assert call_kwargs["symbol"] == "005930"
        assert call_kwargs["quantity"] == 10
        assert call_kwargs["price"] == 70000
        assert call_kwargs["idempotency_key"] == result.order_id

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_persists_created_intent_before_executor_submission(
        self, mock_reconcile, mock_load, engine
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

        observed: dict[str, object] = {}
        engine.start()

        def _submit(**kwargs):
            assert len(engine._state.pending_orders) == 1
            staged_order = next(iter(engine._state.pending_orders.values()))
            observed["status"] = staged_order.status
            observed["order_id"] = staged_order.order_id
            observed["idempotency_key"] = kwargs["idempotency_key"]
            return OrderResult(success=True, order_id="broker-return")

        engine._executor.buy = MagicMock(side_effect=_submit)

        result = engine.buy("005930", 1, 70000)

        assert result.success is True
        assert observed["status"] == OrderStatus.CREATED
        assert observed["order_id"] == observed["idempotency_key"]

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_rejects_when_risk_manager_disapproves(
        self, mock_reconcile, mock_load, mock_client, tmp_path
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

        config = TradingConfig(risk_enforcement_mode="enforce", market_hours_enabled=False)
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
        )
        engine.start()
        engine._risk_manager.validate_order = MagicMock(
            return_value=RiskCheckResult(approved=False, reason="risk rejected")
        )
        engine._executor.buy = MagicMock(return_value=OrderResult(success=True, order_id="TEST123"))

        result = engine.buy("005930", 10, 70000)

        assert result.success is False
        assert "risk rejected" in result.message
        engine._executor.buy.assert_not_called()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_uses_risk_adjusted_quantity(self, mock_reconcile, mock_load, engine):
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
        engine._risk_manager.validate_order = MagicMock(
            return_value=RiskCheckResult(approved=True, reason="adjusted", adjusted_quantity=3)
        )
        engine._executor.buy = MagicMock(return_value=OrderResult(success=True, order_id="TEST123"))

        result = engine.buy("005930", 10, 70000)

        assert result.success is True
        call_kwargs = engine._executor.buy.call_args.kwargs
        assert call_kwargs["symbol"] == "005930"
        assert call_kwargs["quantity"] == 3
        assert call_kwargs["price"] == 70000
        assert call_kwargs["idempotency_key"] == result.order_id

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_with_stop_loss(self, mock_reconcile, mock_load, engine, mock_order, mock_position):
        """Test that buy() stores stop-loss target until broker fill confirms the position."""
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

        result = engine.buy("005930", 10, 70000, stop_loss=65000)

        assert result.success is True
        pending_order = engine._state.pending_orders[result.order_id]
        assert pending_order.requested_stop_loss == 65000
        assert engine.get_position("005930") is None

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_with_take_profit(
        self, mock_reconcile, mock_load, engine, mock_order, mock_position
    ):
        """Test that buy() stores take-profit target until broker fill confirms the position."""
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

        result = engine.buy("005930", 10, 70000, take_profit=80000)

        assert result.success is True
        pending_order = engine._state.pending_orders[result.order_id]
        assert pending_order.requested_take_profit == 80000
        assert engine.get_position("005930") is None

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_records_submit_position_baseline(
        self, mock_reconcile, mock_load, engine, mock_position
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

        engine.start()
        engine._position_manager.open_position(mock_position)
        engine._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="TEST123", broker_order_id="B-1")
        )

        result = engine.buy("005930", 2, 70000)

        assert result.success is True
        pending_order = engine._state.pending_orders[result.order_id]
        assert pending_order.position_quantity_at_submit == 10

    def test_buy_raises_if_not_running(self, engine):
        """Test that buy() raises error if engine not running."""
        with pytest.raises(RuntimeError, match="not running"):
            engine.buy("005930", 10, 70000)

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_rejected_when_startup_guard_blocks_but_sell_allowed(
        self, mock_reconcile, mock_load, mock_client, tmp_path
    ):
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.RECONCILED,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=["ord-1"],
            errors=[],
        )

        engine = TradingEngine(
            client=mock_client,
            config=TradingConfig(market_hours_enabled=False),
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        engine.start()
        engine._position_manager.open_position(
            Position(symbol="005930", quantity=10, entry_price=Decimal("70000"))
        )
        engine._executor.sell = MagicMock(return_value=OrderResult(success=True, order_id="SELL-1"))

        buy_result = engine.buy("000660", 1, 70000)
        sell_result = engine.sell("005930", 10, 70000)

        assert buy_result.success is False
        assert buy_result.message == "startup_recovery_unresolved_orders"
        assert sell_result.success is True

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_sell_closes_position(self, mock_reconcile, mock_load, engine, mock_order):
        """Test that sell() submits a pending exit order against an open position."""
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
        engine._position_manager.open_position(
            Position(symbol="005930", quantity=10, entry_price=Decimal("70000"))
        )
        mock_result = OrderResult(success=True, order_id="TEST123")
        engine._executor.sell = MagicMock(return_value=mock_result)

        result = engine.sell("005930", 10, 75000)

        assert result.success is True
        assert result.order_id in engine._state.pending_orders
        call_kwargs = engine._executor.sell.call_args.kwargs
        assert call_kwargs["symbol"] == "005930"
        assert call_kwargs["quantity"] == 10
        assert call_kwargs["price"] == 75000
        assert call_kwargs["idempotency_key"] == result.order_id
        assert engine.get_position("005930") is not None

    def test_sell_raises_if_not_running(self, engine):
        """Test that sell() raises error if engine not running."""
        with pytest.raises(RuntimeError, match="not running"):
            engine.sell("005930", 10, 75000)

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_sell_rejects_when_quantity_exceeds_position(
        self, mock_reconcile, mock_load, engine
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

        engine.start()
        engine._position_manager.open_position(
            Position(symbol="005930", quantity=10, entry_price=Decimal("70000"))
        )
        engine._executor.sell = MagicMock(return_value=OrderResult(success=True, order_id="SELL123"))

        result = engine.sell("005930", 11, 70000)

        assert result.success is False
        assert result.message == "sell_quantity_exceeds_position"
        engine._executor.sell.assert_not_called()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_rejected_when_daily_loss_killswitch_active(
        self, mock_reconcile, mock_load, engine
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

        engine.start()
        engine._daily_kill_switch_active = True
        engine._executor.buy = MagicMock(return_value=OrderResult(success=True, order_id="TEST123"))

        result = engine.buy("005930", 10, 70000)

        assert result.success is False
        assert "daily_loss_killswitch" in result.message
        engine._executor.buy.assert_not_called()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_sell_allowed_when_daily_loss_killswitch_active(
        self, mock_reconcile, mock_load, engine
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

        engine.start()
        engine._position_manager.open_position(
            Position(symbol="005930", quantity=10, entry_price=Decimal("70000"))
        )
        engine._daily_kill_switch_active = True
        engine._executor.sell = MagicMock(
            return_value=OrderResult(success=True, order_id="SELL123")
        )

        result = engine.sell("005930", 10, 70000)

        assert result.success is True
        call_kwargs = engine._executor.sell.call_args.kwargs
        assert call_kwargs["symbol"] == "005930"
        assert call_kwargs["quantity"] == 10
        assert call_kwargs["price"] == 70000
        assert call_kwargs["idempotency_key"] == result.order_id

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_latches_runtime_balance_unavailable_but_sell_still_allowed(
        self, mock_reconcile, mock_load, mock_client, tmp_path
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
        engine = TradingEngine(
            client=mock_client,
            config=TradingConfig(market_hours_enabled=False),
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        engine.start()
        engine._last_reconciliation_success_at = datetime.now(timezone.utc)
        engine._inquire_balance = MagicMock(side_effect=RuntimeError("balance down"))
        engine._executor.buy = MagicMock(return_value=OrderResult(success=True, order_id="BUY123"))
        engine._position_manager.open_position(
            Position(symbol="005930", quantity=10, entry_price=Decimal("70000"))
        )
        engine._last_market_data_success_at = datetime.now(timezone.utc)
        engine._executor.sell = MagicMock(return_value=OrderResult(success=True, order_id="SELL123"))

        buy_result = engine.buy("000660", 1, 70000)
        sell_result = engine.sell("005930", 10, 70000)

        assert buy_result.success is False
        assert buy_result.message == "runtime_balance_unavailable"
        assert engine._buying_enabled is False
        assert sell_result.success is True

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_latches_market_data_stale_with_open_positions(
        self, mock_reconcile, mock_load, mock_client, tmp_path
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
        engine = TradingEngine(
            client=mock_client,
            config=TradingConfig(market_hours_enabled=False, quote_staleness_sec=5.0),
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        engine.start()
        engine._position_manager.open_position(
            Position(symbol="005930", quantity=10, entry_price=Decimal("70000"))
        )
        engine._last_reconciliation_success_at = datetime.now(timezone.utc)
        engine._last_market_data_success_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        engine._executor.buy = MagicMock(return_value=OrderResult(success=True, order_id="BUY123"))

        result = engine.buy("000660", 1, 70000)

        assert result.success is False
        assert result.message == "market_data_stale"
        assert engine._buying_enabled is False
        engine._executor.buy.assert_not_called()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_ambiguous_submission_marks_pending_broker_and_latches_buy_guard(
        self, mock_reconcile, mock_load, mock_client, tmp_path
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
        engine = TradingEngine(
            client=mock_client,
            config=TradingConfig(market_hours_enabled=False),
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        engine.start()
        engine._last_reconciliation_success_at = datetime.now(timezone.utc)
        engine._executor.buy = MagicMock(
            return_value=OrderResult(
                success=False,
                order_id="ignored",
                message="timeout",
                submission_unknown=True,
            )
        )

        result = engine.buy("005930", 1, 70000)

        assert result.success is False
        assert result.message == "timeout"
        pending_order = engine._state.pending_orders[result.order_id]
        assert pending_order.status == OrderStatus.PENDING_BROKER
        assert pending_order.unresolved_reason == "submission_result_unknown"
        assert engine._buying_enabled is False
        assert engine._buy_blocked_reason == "submission_result_unknown"

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_daily_loss_killswitch_triggers_and_emits_critical_notification(
        self, mock_reconcile, mock_load, engine
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

        engine.start()
        engine.notifier = MagicMock()
        engine._daily_pnl_date = datetime.now(timezone.utc).date().isoformat()
        engine._daily_baseline_equity = Decimal("1000000")
        engine._daily_realized_pnl = Decimal("-6000")

        engine._evaluate_daily_loss_killswitch(unrealized_pnl=Decimal("-5000"))

        assert engine._daily_kill_switch_active is True
        calls = engine.notifier.notify.call_args_list
        events = [
            call[0][0] for call in calls if call[0][0].event_type == "risk.killswitch.triggered"
        ]
        assert len(events) == 1
        event = events[0]
        assert event.level.name == "CRITICAL"
        assert event.details.get("threshold_pct") == "0.01"

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_daily_loss_killswitch_resets_on_day_rollover(self, mock_reconcile, mock_load, engine):
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
        engine._daily_kill_switch_active = True
        engine._daily_pnl_date = "2000-01-01"
        engine._daily_baseline_equity = Decimal("1000000")
        engine._daily_realized_pnl = Decimal("-5000")
        engine._degraded_reason = "daily_loss_killswitch"

        engine._rollover_daily_metrics_if_needed(now=datetime.now(timezone.utc))

        assert engine._daily_kill_switch_active is False
        assert engine._daily_realized_pnl == Decimal("0")
        assert engine._degraded_reason is None


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
        assert status.operational_state == engine._operational_state
        assert status.buying_enabled is engine._buying_enabled
        assert status.buy_blocked_reason == engine._buy_blocked_reason
        assert str(engine.state_path) in status.state_path

    def test_get_status_prefers_client_global_rate_limiter(self, engine):
        """Status should report client-level limiter availability when exposed."""
        engine._running = True
        engine.client.request_rate_limiter_available = 3

        status = engine.get_status()

        assert status.rate_limiter_available == 3

    def test_is_healthy_returns_true_when_healthy(self, engine):
        """Test that is_healthy() returns True when engine is healthy."""
        engine._running = True
        engine._last_reconciliation_success_at = datetime.now(timezone.utc)
        # Mock price monitor is_running property and rate limiter available property
        with patch.object(type(engine._price_monitor), "is_running", property(lambda self: True)):
            with patch.object(type(engine._rate_limiter), "available", property(lambda self: 5)):
                assert engine.is_healthy() is True

    def test_is_healthy_returns_false_when_not_running(self, engine):
        """Test that is_healthy() returns False when engine not running."""
        engine._running = False

        assert engine.is_healthy() is False

    def test_is_healthy_returns_true_when_no_positions_even_if_monitor_stopped(self, engine):
        """No-position sessions can be healthy without the polling monitor."""
        engine._running = True
        engine._last_reconciliation_success_at = datetime.now(timezone.utc)
        with patch.object(type(engine._price_monitor), "is_running", property(lambda self: False)):
            with patch.object(type(engine._rate_limiter), "available", property(lambda self: 5)):
                assert engine.is_healthy() is True

    def test_is_healthy_returns_false_when_monitors_stopped_with_open_positions(
        self, engine, mock_position
    ):
        """With open positions, monitor/realtime stream must be active."""
        engine._running = True
        engine._position_manager.open_position(mock_position)
        # Mock price monitor as not running
        with patch.object(type(engine._price_monitor), "is_running", property(lambda self: False)):
            with patch.object(type(engine._rate_limiter), "available", property(lambda self: 5)):
                engine._broker_adapter = None
                engine.config = SimpleNamespace(websocket_monitoring_enabled=False)
                assert engine.is_healthy() is False

    def test_is_healthy_returns_true_with_open_positions_when_websocket_connected(
        self, engine, mock_position
    ):
        """WebSocket quote stream is a valid monitoring path when polling is disabled."""
        engine._running = True
        engine._last_reconciliation_success_at = datetime.now(timezone.utc)
        engine._last_market_data_success_at = datetime.now(timezone.utc)
        engine._position_manager.open_position(mock_position)
        engine._broker_adapter = SimpleNamespace(websocket_connected=True)
        engine.config = SimpleNamespace(websocket_monitoring_enabled=True)
        with patch.object(type(engine._price_monitor), "is_running", property(lambda self: False)):
            with patch.object(type(engine._rate_limiter), "available", property(lambda self: 5)):
                assert engine.is_healthy() is True

    def test_is_healthy_returns_false_when_reconciliation_is_stale(self, engine):
        engine._running = True
        engine._last_reconciliation_success_at = datetime(2000, 1, 1, tzinfo=timezone.utc)

        with patch.object(type(engine._rate_limiter), "available", property(lambda self: 5)):
            assert engine.is_healthy() is False

    def test_is_healthy_returns_false_when_market_data_is_stale(self, engine, mock_position):
        engine._running = True
        engine._position_manager.open_position(mock_position)
        engine._last_reconciliation_success_at = datetime.now(timezone.utc)
        engine._last_market_data_success_at = datetime(2000, 1, 1, tzinfo=timezone.utc)

        with patch.object(type(engine._price_monitor), "is_running", property(lambda self: True)):
            with patch.object(type(engine._rate_limiter), "available", property(lambda self: 5)):
                assert engine.is_healthy() is False

    def test_get_operability_requires_stop_when_degraded_and_flat(self, engine):
        engine._running = True
        engine._set_operational_state(
            operational_state="degraded_reduce_only",
            degraded_reason="execution_stream_unavailable",
        )
        engine._last_reconciliation_success_at = datetime.now(timezone.utc)

        with patch.object(type(engine._rate_limiter), "available", property(lambda self: 5)):
            decision = engine.get_operability()

        assert decision.is_healthy is True
        assert decision.is_ready_for_new_orders is False
        assert decision.should_keep_session_running is False

    def test_get_operability_keeps_session_running_when_degraded_with_position(
        self, engine, mock_position
    ):
        engine._running = True
        engine._set_operational_state(
            operational_state="degraded_reduce_only",
            degraded_reason="runtime_reconciliation_drift",
        )
        engine._position_manager.open_position(mock_position)
        engine._last_reconciliation_success_at = datetime.now(timezone.utc)
        engine._last_market_data_success_at = datetime.now(timezone.utc)

        with patch.object(type(engine._price_monitor), "is_running", property(lambda self: True)):
            with patch.object(type(engine._rate_limiter), "available", property(lambda self: 5)):
                decision = engine.get_operability()

        assert decision.is_healthy is True
        assert decision.is_ready_for_new_orders is False
        assert decision.should_keep_session_running is True


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

        call_kwargs = engine._executor.sell.call_args.kwargs
        assert call_kwargs["symbol"] == "005930"
        assert call_kwargs["quantity"] == 10
        assert call_kwargs["price"] is None

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_registers_position_callbacks(self, mock_reconcile, mock_load, engine):
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

        stop_cb = engine._position_manager._on_stop_loss
        tp_cb = engine._position_manager._on_take_profit
        assert stop_cb is not None
        assert tp_cb is not None
        assert stop_cb.__self__ is engine
        assert tp_cb.__self__ is engine
        assert stop_cb.__func__ is engine._handle_stop_loss.__func__
        assert tp_cb.__func__ is engine._handle_take_profit.__func__

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_auto_exit_dedupes_stop_loss_within_cooldown(
        self, mock_reconcile, mock_load, mock_client, tmp_path, mock_position
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

        config = TradingConfig(auto_exit_cooldown_sec=60.0)
        engine = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            account_product_code="01",
            state_path=tmp_path / "test_state.json",
            is_paper_trading=True,
        )

        engine.start()
        engine._position_manager.open_position(mock_position)
        engine.sell = MagicMock(
            return_value=OrderResult(success=False, order_id="FAILED", message="x")
        )
        engine._get_current_price = MagicMock(return_value=70000)

        engine._handle_stop_loss("005930")
        engine._handle_stop_loss("005930")

        engine.sell.assert_called_once_with(
            symbol="005930",
            quantity=10,
            price=None,
            origin="stop_loss",
            exit_reason="STOP_LOSS",
        )

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


# =============================================================================
# Market Hours Tests
# =============================================================================


class TestMarketHours:
    """Test market hours trading restriction."""

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_rejected_outside_market_hours(
        self, mock_reconcile, mock_load, mock_client, tmp_path
    ):
        """Live buy orders must be rejected on weekends and outside 09:00-15:20 KST."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )
        config = TradingConfig(market_hours_enabled=True)
        eng = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        eng.start()
        eng._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="TEST123")
        )

        # Saturday 10:00 KST
        saturday = datetime(2026, 3, 7, 10, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with patch("stock_manager.engine.datetime") as mock_dt:
            mock_dt.now = MagicMock(return_value=saturday)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = eng.buy("005930", 10, 70000)

        assert result.success is False
        assert "Market is closed" in result.message
        eng._executor.buy.assert_not_called()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_not_blocked_outside_market_hours_in_mock_when_enabled(
        self, mock_reconcile, mock_load, mock_client, tmp_path
    ):
        """Mock buy orders should continue outside market hours when checks are enabled."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )
        config = TradingConfig(market_hours_enabled=True)
        eng = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
        )
        eng.start()
        eng._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="TEST123")
        )

        # Saturday 10:00 KST
        saturday = datetime(2026, 3, 7, 10, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with patch("stock_manager.engine.datetime") as mock_dt:
            mock_dt.now = MagicMock(return_value=saturday)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = eng.buy("005930", 10, 70000)

        assert result.success is True
        call_kwargs = eng._executor.buy.call_args.kwargs
        assert call_kwargs["symbol"] == "005930"
        assert call_kwargs["quantity"] == 10
        assert call_kwargs["price"] == 70000

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_buy_allowed_during_market_hours(
        self, mock_reconcile, mock_load, mock_client, tmp_path
    ):
        """Live buy orders should succeed during weekday 09:00-15:20 KST."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )
        config = TradingConfig(market_hours_enabled=True)
        eng = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )
        eng.start()
        eng._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="TEST123")
        )

        # Wednesday 10:00 KST
        wednesday = datetime(2026, 3, 4, 10, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with patch("stock_manager.engine.datetime") as mock_dt:
            mock_dt.now = MagicMock(return_value=wednesday)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = eng.buy("005930", 10, 70000)

        assert result.success is True

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_sell_allowed_outside_market_hours(self, mock_reconcile, mock_load, engine):
        """Sell (stop-loss) must work at any time."""
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
        engine._position_manager.open_position(
            Position(symbol="005930", quantity=10, entry_price=Decimal("70000"))
        )
        engine._executor.sell = MagicMock(
            return_value=OrderResult(success=True, order_id="SELL123")
        )

        # Saturday 22:00 KST - sell should still work
        saturday_night = datetime(2026, 3, 7, 22, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with patch("stock_manager.engine.datetime") as mock_dt:
            mock_dt.now = MagicMock(return_value=saturday_night)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = engine.sell("005930", 10, 70000)

        assert result.success is True

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_market_hours_disabled_allows_anytime(
        self, mock_reconcile, mock_load, mock_client, tmp_path
    ):
        """When market_hours_enabled=False, buy orders pass at any time."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )
        config = TradingConfig(market_hours_enabled=False)
        eng = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
        )
        eng.start()
        eng._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="TEST123")
        )

        # Saturday - should still work because market_hours_enabled=False
        saturday = datetime(2026, 3, 7, 10, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with patch("stock_manager.engine.datetime") as mock_dt:
            mock_dt.now = MagicMock(return_value=saturday)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = eng.buy("005930", 10, 70000)

        assert result.success is True


# =============================================================================
# Risk Enforcement Mode Tests
# =============================================================================


class TestRiskEnforcementMode:
    """Test risk_enforcement_mode behavior in buy()."""

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_risk_enforce_mode_blocks_order(self, mock_reconcile, mock_load, mock_client, tmp_path):
        """enforce mode: risk check failure blocks the order."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )
        config = TradingConfig(risk_enforcement_mode="enforce", market_hours_enabled=False)
        eng = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
        )
        eng.start()
        eng._risk_manager.validate_order = MagicMock(
            return_value=RiskCheckResult(approved=False, reason="position too large")
        )
        eng._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="TEST123")
        )

        result = eng.buy("005930", 10, 70000)

        assert result.success is False
        assert "position too large" in result.message
        eng._executor.buy.assert_not_called()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_risk_warn_mode_allows_with_warning(self, mock_reconcile, mock_load, mock_client, tmp_path):
        """warn mode: risk check failure logs warning but allows order."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )
        config = TradingConfig(risk_enforcement_mode="warn", market_hours_enabled=False)
        eng = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
        )
        eng.start()
        eng._risk_manager.validate_order = MagicMock(
            return_value=RiskCheckResult(approved=False, reason="position too large")
        )
        eng._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="TEST123")
        )

        result = eng.buy("005930", 10, 70000)

        assert result.success is True
        eng._executor.buy.assert_called_once()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_risk_off_mode_skips_check(self, mock_reconcile, mock_load, mock_client, tmp_path):
        """off mode: risk check is skipped entirely."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )
        config = TradingConfig(risk_enforcement_mode="off", market_hours_enabled=False)
        eng = TradingEngine(
            client=mock_client,
            config=config,
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
        )
        eng.start()
        eng._risk_manager.validate_order = MagicMock(
            return_value=RiskCheckResult(approved=False, reason="should be skipped")
        )
        eng._executor.buy = MagicMock(
            return_value=OrderResult(success=True, order_id="TEST123")
        )

        result = eng.buy("005930", 10, 70000)

        assert result.success is True
        eng._executor.buy.assert_called_once()


# =============================================================================
# Preflight Checks Tests
# =============================================================================


class TestPreflightChecks:
    """Test engine start() preflight validation."""

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_fails_when_balance_inquiry_fails(
        self, mock_reconcile, mock_load, mock_client, tmp_path
    ):
        """Engine must not start if balance inquiry fails."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        # Make _inquire_balance fail
        mock_client.make_request.side_effect = Exception("Connection refused")

        eng = TradingEngine(
            client=mock_client,
            config=TradingConfig(),
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
        )

        with pytest.raises(RuntimeError, match="Preflight checks failed"):
            eng.start()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_sets_portfolio_value_from_balance(
        self, mock_reconcile, mock_load, mock_client, tmp_path
    ):
        """Engine should auto-set portfolio_value from balance inquiry."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        mock_client.make_request.return_value = {
            "rt_cd": "0",
            "output2": [{"dnca_tot_amt": "50000000"}],
        }

        eng = TradingEngine(
            client=mock_client,
            config=TradingConfig(),
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
        )
        eng.start()

        assert eng._risk_manager.portfolio_value == Decimal("50000000")

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_fails_when_slack_health_check_fails(
        self, mock_reconcile, mock_load, mock_client, tmp_path
    ):
        """Engine must not start if Slack health check fails."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        mock_notifier = MagicMock()
        mock_notifier.health_check.return_value = False

        eng = TradingEngine(
            client=mock_client,
            config=TradingConfig(),
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
            notifier=mock_notifier,
        )

        with pytest.raises(RuntimeError, match="Slack notification health check failed"):
            eng.start()

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_warns_outside_market_hours_in_live_mode(
        self, mock_reconcile, mock_load, mock_client, tmp_path, caplog
    ):
        """Live engine should warn that buy orders will be blocked outside market hours."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        eng = TradingEngine(
            client=mock_client,
            config=TradingConfig(market_hours_enabled=True),
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=False,
        )

        # Simulate starting on a Saturday
        saturday = datetime(2026, 3, 7, 10, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with patch("stock_manager.engine.datetime") as mock_dt:
            mock_dt.now = MagicMock(return_value=saturday)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with caplog.at_level(logging.WARNING):
                eng.start()

        assert "buy orders will be blocked" in caplog.text

    @patch("stock_manager.engine.load_state")
    @patch("stock_manager.engine.startup_reconciliation")
    def test_start_logs_mock_market_hours_override(
        self, mock_reconcile, mock_load, mock_client, tmp_path, caplog
    ):
        """Mock engine should log that local market-hours blocking is disabled."""
        mock_load.return_value = None
        mock_reconcile.return_value = RecoveryReport(
            result=RecoveryResult.CLEAN,
            orphan_positions=[],
            missing_positions=[],
            quantity_mismatches={},
            pending_orders=[],
            errors=[],
        )

        eng = TradingEngine(
            client=mock_client,
            config=TradingConfig(market_hours_enabled=True),
            account_number="12345678",
            state_path=tmp_path / "state.json",
            is_paper_trading=True,
        )

        saturday = datetime(2026, 3, 7, 10, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with patch("stock_manager.engine.datetime") as mock_dt:
            mock_dt.now = MagicMock(return_value=saturday)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            with caplog.at_level(logging.INFO):
                eng.start()

        assert "buy orders will be blocked" not in caplog.text
        assert "mock mode: local market-hours block disabled" in caplog.text
