"""Unit tests for trading models."""
from decimal import Decimal
from stock_manager.trading.models import (
    Order, OrderStatus, Position, PositionStatus, TradingConfig
)


class TestOrder:
    """Test Order model."""

    def test_order_creation_generates_ids(self):
        """Test that order creation generates unique IDs."""
        order = Order(symbol="005930", side="buy", quantity=10)
        assert order.order_id is not None
        assert order.idempotency_key is not None
        assert order.order_id != order.idempotency_key

    def test_order_ids_are_unique(self):
        """Test that multiple orders get different IDs."""
        order1 = Order(symbol="005930", side="buy", quantity=10)
        order2 = Order(symbol="005930", side="buy", quantity=10)
        assert order1.order_id != order2.order_id
        assert order1.idempotency_key != order2.idempotency_key

    def test_can_retry_when_created(self):
        """Test that new orders can be retried."""
        order = Order(symbol="005930", side="buy", quantity=10)
        assert order.can_retry() is True

    def test_can_retry_when_submitted(self):
        """Test that submitted orders can be retried."""
        order = Order(
            symbol="005930",
            side="buy",
            quantity=10,
            status=OrderStatus.SUBMITTED
        )
        assert order.can_retry() is True

    def test_can_retry_false_after_max_attempts(self):
        """Test that orders cannot retry after max attempts."""
        order = Order(
            symbol="005930",
            side="buy",
            quantity=10,
            submission_attempts=3
        )
        assert order.can_retry() is False

    def test_can_retry_false_when_filled(self):
        """Test that filled orders cannot be retried."""
        order = Order(
            symbol="005930",
            side="buy",
            quantity=10,
            status=OrderStatus.FILLED
        )
        assert order.can_retry() is False

    def test_can_retry_false_when_rejected(self):
        """Test that rejected orders cannot be retried."""
        order = Order(
            symbol="005930",
            side="buy",
            quantity=10,
            status=OrderStatus.REJECTED
        )
        assert order.can_retry() is False

    def test_can_retry_false_when_cancelled(self):
        """Test that cancelled orders cannot be retried."""
        order = Order(
            symbol="005930",
            side="buy",
            quantity=10,
            status=OrderStatus.CANCELLED
        )
        assert order.can_retry() is False

    def test_order_defaults(self):
        """Test order default values."""
        order = Order(symbol="005930", side="buy", quantity=10)
        assert order.status == OrderStatus.CREATED
        assert order.order_type == "limit"
        assert order.submission_attempts == 0
        assert order.max_attempts == 3
        assert order.broker_order_id is None
        assert order.submitted_at is None
        assert order.filled_at is None

    def test_market_order(self):
        """Test market order creation."""
        order = Order(
            symbol="005930",
            side="buy",
            quantity=10,
            order_type="market",
            price=None
        )
        assert order.order_type == "market"
        assert order.price is None

    def test_limit_order(self):
        """Test limit order creation."""
        order = Order(
            symbol="005930",
            side="buy",
            quantity=10,
            order_type="limit",
            price=50000
        )
        assert order.order_type == "limit"
        assert order.price == 50000


class TestPosition:
    """Test Position model."""

    def test_position_creation(self):
        """Test basic position creation."""
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        assert pos.symbol == "005930"
        assert pos.quantity == 10
        assert pos.entry_price == Decimal("50000")
        assert pos.status == PositionStatus.OPEN
        assert pos.unrealized_pnl == Decimal("0")

    def test_position_defaults(self):
        """Test position default values."""
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000")
        )
        assert pos.current_price is None
        assert pos.stop_loss is None
        assert pos.take_profit is None
        assert pos.unrealized_pnl == Decimal("0")
        assert pos.status == PositionStatus.OPEN
        assert pos.closed_at is None

    def test_position_with_stop_loss(self):
        """Test position with stop loss."""
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            stop_loss=Decimal("47500")
        )
        assert pos.stop_loss == Decimal("47500")

    def test_position_with_take_profit(self):
        """Test position with take profit."""
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            take_profit=Decimal("55000")
        )
        assert pos.take_profit == Decimal("55000")

    def test_position_with_current_price(self):
        """Test position with current price."""
        pos = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            current_price=Decimal("52000")
        )
        assert pos.current_price == Decimal("52000")

    def test_position_status_options(self):
        """Test different position statuses."""
        pos_open = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            status=PositionStatus.OPEN
        )
        assert pos_open.status == PositionStatus.OPEN

        pos_reconciled = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            status=PositionStatus.OPEN_RECONCILED
        )
        assert pos_reconciled.status == PositionStatus.OPEN_RECONCILED

        pos_closed = Position(
            symbol="005930",
            quantity=10,
            entry_price=Decimal("50000"),
            status=PositionStatus.CLOSED
        )
        assert pos_closed.status == PositionStatus.CLOSED


class TestTradingConfig:
    """Test TradingConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TradingConfig()
        assert config.max_positions == 1
        assert config.polling_interval_sec == 2.0
        assert config.rate_limit_per_sec == 20
        assert config.max_position_size_pct == Decimal("0.10")
        assert config.default_stop_loss_pct == Decimal("0.05")
        assert config.default_take_profit_pct == Decimal("0.10")
        assert config.recovery_mode == "block"
        assert config.allow_unsafe_trading is False
        assert config.risk_enforcement_mode == "warn"
        assert config.portfolio_value == Decimal("0")

    def test_custom_values(self):
        """Test custom configuration values."""
        config = TradingConfig(
            max_positions=5,
            polling_interval_sec=1.0,
            rate_limit_per_sec=10,
            max_position_size_pct=Decimal("0.20"),
            default_stop_loss_pct=Decimal("0.03"),
            default_take_profit_pct=Decimal("0.15"),
            recovery_mode="warn",
            allow_unsafe_trading=True,
            risk_enforcement_mode="enforce",
            portfolio_value=Decimal("1000000"),
        )
        assert config.max_positions == 5
        assert config.polling_interval_sec == 1.0
        assert config.rate_limit_per_sec == 10
        assert config.max_position_size_pct == Decimal("0.20")
        assert config.default_stop_loss_pct == Decimal("0.03")
        assert config.default_take_profit_pct == Decimal("0.15")
        assert config.recovery_mode == "warn"
        assert config.allow_unsafe_trading is True
        assert config.risk_enforcement_mode == "enforce"
        assert config.portfolio_value == Decimal("1000000")

    def test_decimal_precision(self):
        """Test that decimal values maintain precision."""
        config = TradingConfig(
            max_position_size_pct=Decimal("0.123456"),
            default_stop_loss_pct=Decimal("0.054321")
        )
        assert config.max_position_size_pct == Decimal("0.123456")
        assert config.default_stop_loss_pct == Decimal("0.054321")
