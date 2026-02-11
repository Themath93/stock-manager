"""Unit tests for PositionManager with thread safety."""
import pytest
import threading
import time
from decimal import Decimal
from stock_manager.trading.positions import (
    PositionManager,
    calculate_unrealized_pnl,
    is_stop_loss_triggered,
    is_take_profit_triggered,
)
from stock_manager.trading.models import Position, PositionStatus


class TestPositionManager:
    """Test PositionManager thread-safe operations."""

    def test_open_and_get_position(self):
        """Test opening and retrieving a position."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        manager.open_position(pos)

        result = manager.get_position("005930")
        assert result is not None
        assert result.symbol == "005930"
        assert result.quantity == 10
        assert result.entry_price == Decimal("50000")

    def test_open_duplicate_position_raises_error(self):
        """Test that opening duplicate position raises ValueError."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        manager.open_position(pos)

        # Try to open duplicate
        with pytest.raises(ValueError, match="Position already exists"):
            manager.open_position(pos)

    def test_get_nonexistent_position(self):
        """Test getting a position that doesn't exist."""
        manager = PositionManager()
        result = manager.get_position("005930")
        assert result is None

    def test_update_price_calculates_pnl(self):
        """Test that price updates calculate unrealized P&L."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        manager.open_position(pos)

        manager.update_price("005930", Decimal("55000"))

        result = manager.get_position("005930")
        assert result.current_price == Decimal("55000")
        # (55000 - 50000) * 10 = 50000
        assert result.unrealized_pnl == Decimal("50000")

    def test_update_price_negative_pnl(self):
        """Test that price updates handle negative P&L."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        manager.open_position(pos)

        manager.update_price("005930", Decimal("45000"))

        result = manager.get_position("005930")
        assert result.current_price == Decimal("45000")
        # (45000 - 50000) * 10 = -50000
        assert result.unrealized_pnl == Decimal("-50000")

    def test_close_position(self):
        """Test closing a position."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        manager.open_position(pos)

        closed = manager.close_position("005930")

        assert closed is not None
        assert closed.status == PositionStatus.CLOSED
        assert closed.closed_at is not None
        assert manager.get_position("005930") is None

    def test_close_nonexistent_position(self):
        """Test closing a position that doesn't exist."""
        manager = PositionManager()
        closed = manager.close_position("005930")
        assert closed is None

    def test_get_all_positions(self):
        """Test getting all positions."""
        manager = PositionManager()
        pos1 = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        pos2 = Position(
            symbol="000660",
            quantity=5,
            entry_price=Decimal("100000")
        )
        manager.open_position(pos1)
        manager.open_position(pos2)

        all_positions = manager.get_all_positions()

        assert len(all_positions) == 2
        assert "005930" in all_positions
        assert "000660" in all_positions

    def test_position_count(self):
        """Test position count property."""
        manager = PositionManager()
        assert manager.position_count == 0

        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        manager.open_position(pos)
        assert manager.position_count == 1

        manager.close_position("005930")
        assert manager.position_count == 0

    def test_symbols_property(self):
        """Test symbols property."""
        manager = PositionManager()
        assert manager.symbols == []

        pos1 = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        pos2 = Position(
            symbol="000660",
            quantity=5,
            entry_price=Decimal("100000")
        )
        manager.open_position(pos1)
        manager.open_position(pos2)

        symbols = manager.symbols
        assert len(symbols) == 2
        assert "005930" in symbols
        assert "000660" in symbols

    def test_check_stop_loss_not_triggered(self):
        """Test stop loss check when not triggered."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            stop_loss=Decimal("47500")
        )
        manager.open_position(pos)

        manager.update_price("005930", Decimal("48000"))
        assert manager.check_stop_loss("005930") is False

    def test_check_stop_loss_triggered(self):
        """Test stop loss check when triggered."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            stop_loss=Decimal("47500")
        )
        manager.open_position(pos)

        manager.update_price("005930", Decimal("47000"))
        assert manager.check_stop_loss("005930") is True

    def test_check_stop_loss_at_exact_price(self):
        """Test stop loss check at exact stop loss price."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            stop_loss=Decimal("47500")
        )
        manager.open_position(pos)

        manager.update_price("005930", Decimal("47500"))
        assert manager.check_stop_loss("005930") is True

    def test_check_take_profit_not_triggered(self):
        """Test take profit check when not triggered."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            take_profit=Decimal("55000")
        )
        manager.open_position(pos)

        manager.update_price("005930", Decimal("54000"))
        assert manager.check_take_profit("005930") is False

    def test_check_take_profit_triggered(self):
        """Test take profit check when triggered."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            take_profit=Decimal("55000")
        )
        manager.open_position(pos)

        manager.update_price("005930", Decimal("56000"))
        assert manager.check_take_profit("005930") is True

    def test_set_callbacks(self):
        """Test setting stop loss and take profit callbacks."""
        manager = PositionManager()

        stop_loss_triggered = []
        take_profit_triggered = []

        def on_stop_loss(symbol):
            stop_loss_triggered.append(symbol)

        def on_take_profit(symbol):
            take_profit_triggered.append(symbol)

        manager.set_callbacks(
            on_stop_loss=on_stop_loss,
            on_take_profit=on_take_profit
        )

        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            stop_loss=Decimal("47500"),
            take_profit=Decimal("55000")
        )
        manager.open_position(pos)

        # Trigger stop loss
        manager.update_price("005930", Decimal("47000"))
        assert "005930" in stop_loss_triggered

        # Reset and trigger take profit
        stop_loss_triggered.clear()
        manager.close_position("005930")
        pos2 = Position(
            symbol="000660",
            quantity=10,
            entry_price=Decimal("50000"),
            stop_loss=Decimal("47500"),
            take_profit=Decimal("55000")
        )
        manager.open_position(pos2)
        manager.update_price("000660", Decimal("56000"))
        assert "000660" in take_profit_triggered

    def test_thread_safety_concurrent_updates(self):
        """Test thread safety with concurrent price updates."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        manager.open_position(pos)

        errors = []

        def update_thread(price):
            try:
                for _ in range(100):
                    manager.update_price("005930", price)
            except Exception as e:
                errors.append(e)

        # Create multiple threads updating price
        threads = [
            threading.Thread(target=update_thread, args=(Decimal("55000"),)),
            threading.Thread(target=update_thread, args=(Decimal("45000"),)),
            threading.Thread(target=update_thread, args=(Decimal("52000"),)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # Position should still be valid
        result = manager.get_position("005930")
        assert result is not None
        assert result.current_price in [
            Decimal("55000"),
            Decimal("45000"),
            Decimal("52000")
        ]

    def test_thread_safety_concurrent_read_write(self):
        """Test thread safety with concurrent reads and writes."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        manager.open_position(pos)

        errors = []
        results = []

        def writer_thread():
            try:
                for i in range(50):
                    price = Decimal(str(50000 + i * 100))
                    manager.update_price("005930", price)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def reader_thread():
            try:
                for _ in range(50):
                    pos = manager.get_position("005930")
                    if pos:
                        results.append(pos.current_price)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer_thread),
            threading.Thread(target=reader_thread),
            threading.Thread(target=reader_thread),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) > 0

    def test_to_dict_serialization(self):
        """Test position serialization to dict."""
        manager = PositionManager()
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            stop_loss=Decimal("47500"),
            take_profit=Decimal("55000")
        )
        manager.open_position(pos)
        manager.update_price("005930", Decimal("52000"))

        data = manager.to_dict()

        assert "005930" in data
        assert data["005930"]["symbol"] == "005930"
        assert data["005930"]["quantity"] == 10
        assert data["005930"]["entry_price"] == "50000"
        assert data["005930"]["current_price"] == "52000"
        assert data["005930"]["stop_loss"] == "47500"
        assert data["005930"]["take_profit"] == "55000"
        assert data["005930"]["status"] == "open"


class TestPureFunctions:
    """Unit tests for pure functions extracted from PositionManager."""

    def test_calculate_unrealized_pnl_profit(self):
        """Test P&L calculation with profit."""
        result = calculate_unrealized_pnl(
            current_price=Decimal("55000"),
            entry_price=Decimal("50000"),
            quantity=10
        )
        assert result == Decimal("50000")

    def test_calculate_unrealized_pnl_loss(self):
        """Test P&L calculation with loss."""
        result = calculate_unrealized_pnl(
            current_price=Decimal("45000"),
            entry_price=Decimal("50000"),
            quantity=10
        )
        assert result == Decimal("-50000")

    def test_calculate_unrealized_pnl_zero(self):
        """Test P&L calculation at breakeven."""
        result = calculate_unrealized_pnl(
            current_price=Decimal("50000"),
            entry_price=Decimal("50000"),
            quantity=10
        )
        assert result == Decimal("0")

    def test_calculate_unrealized_pnl_fractional_prices(self):
        """Test P&L calculation with fractional prices."""
        result = calculate_unrealized_pnl(
            current_price=Decimal("50.75"),
            entry_price=Decimal("50.25"),
            quantity=100
        )
        assert result == Decimal("50.00")

    def test_is_stop_loss_triggered_below(self):
        """Test stop loss trigger when price drops below level."""
        assert is_stop_loss_triggered(
            current_price=Decimal("47000"),
            stop_loss=Decimal("47500")
        ) is True

    def test_is_stop_loss_triggered_at_level(self):
        """Test stop loss trigger at exact level."""
        assert is_stop_loss_triggered(
            current_price=Decimal("47500"),
            stop_loss=Decimal("47500")
        ) is True

    def test_is_stop_loss_not_triggered(self):
        """Test stop loss not triggered when price above level."""
        assert is_stop_loss_triggered(
            current_price=Decimal("48000"),
            stop_loss=Decimal("47500")
        ) is False

    def test_is_stop_loss_triggered_none_price(self):
        """Test stop loss not triggered when price is None."""
        assert is_stop_loss_triggered(
            current_price=None,
            stop_loss=Decimal("47500")
        ) is False

    def test_is_stop_loss_triggered_none_stop_loss(self):
        """Test stop loss not triggered when stop loss is None."""
        assert is_stop_loss_triggered(
            current_price=Decimal("47000"),
            stop_loss=None
        ) is False

    def test_is_take_profit_triggered_above(self):
        """Test take profit trigger when price rises above level."""
        assert is_take_profit_triggered(
            current_price=Decimal("56000"),
            take_profit=Decimal("55000")
        ) is True

    def test_is_take_profit_triggered_at_level(self):
        """Test take profit trigger at exact level."""
        assert is_take_profit_triggered(
            current_price=Decimal("55000"),
            take_profit=Decimal("55000")
        ) is True

    def test_is_take_profit_not_triggered(self):
        """Test take profit not triggered when price below level."""
        assert is_take_profit_triggered(
            current_price=Decimal("54000"),
            take_profit=Decimal("55000")
        ) is False

    def test_is_take_profit_triggered_none_price(self):
        """Test take profit not triggered when price is None."""
        assert is_take_profit_triggered(
            current_price=None,
            take_profit=Decimal("55000")
        ) is False

    def test_is_take_profit_triggered_none_take_profit(self):
        """Test take profit not triggered when take profit is None."""
        assert is_take_profit_triggered(
            current_price=Decimal("56000"),
            take_profit=None
        ) is False
