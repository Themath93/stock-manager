"""Unit tests for state persistence."""

import json
from datetime import datetime, timezone
from decimal import Decimal

from stock_manager.persistence.state import TradingState, load_state, save_state_atomic
from stock_manager.trading.models import Order, OrderStatus, Position, PositionStatus


class TestTradingState:
    """Test TradingState model serialization."""

    def test_default_state(self):
        """Test default state creation."""
        state = TradingState()
        assert state.positions == {}
        assert state.pending_orders == {}
        assert state.version == 2
        assert isinstance(state.last_updated, datetime)

    def test_to_dict_serializes_models(self):
        """Test v2 schema serialization from Position/Order models."""
        state = TradingState(
            positions={
                "005930": Position(
                    symbol="005930",
                    quantity=10,
                    entry_price=Decimal("70000"),
                    current_price=Decimal("71000"),
                    status=PositionStatus.OPEN,
                )
            },
            pending_orders={
                "ord-1": Order(
                    order_id="ord-1",
                    idempotency_key="idem-1",
                    symbol="005930",
                    side="buy",
                    quantity=10,
                    price=70000,
                    status=OrderStatus.SUBMITTED,
                )
            },
        )

        data = state.to_dict()
        assert data["version"] == 2
        assert data["positions"]["005930"]["entry_price"] == "70000"
        assert data["positions"]["005930"]["status"] == "open"
        assert data["pending_orders"]["ord-1"]["status"] == "submitted"

    def test_from_dict_v2_restores_models(self):
        """Test v2 schema is deserialized to typed models."""
        data = {
            "version": 2,
            "positions": {
                "005930": {
                    "symbol": "005930",
                    "quantity": 10,
                    "entry_price": "70000",
                    "current_price": "71000",
                    "stop_loss": "68000",
                    "take_profit": "75000",
                    "unrealized_pnl": "10000",
                    "status": "open",
                    "opened_at": "2024-01-01T00:00:00+00:00",
                    "closed_at": None,
                }
            },
            "pending_orders": {
                "ord-1": {
                    "order_id": "ord-1",
                    "idempotency_key": "idem-1",
                    "symbol": "005930",
                    "side": "buy",
                    "quantity": 10,
                    "price": 70000,
                    "order_type": "limit",
                    "status": "submitted",
                    "broker_order_id": None,
                    "submission_attempts": 1,
                    "max_attempts": 3,
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "submitted_at": "2024-01-01T00:00:01+00:00",
                    "filled_at": None,
                }
            },
            "last_updated": "2024-01-01T00:00:02+00:00",
        }
        state = TradingState.from_dict(data)

        assert isinstance(state.positions["005930"], Position)
        assert state.positions["005930"].entry_price == Decimal("70000")
        assert isinstance(state.pending_orders["ord-1"], Order)
        assert state.pending_orders["ord-1"].status == OrderStatus.SUBMITTED

    def test_from_dict_v1_legacy_dict_compatible(self):
        """Test legacy dict-based payloads are still loadable."""
        data = {
            "version": 1,
            "positions": {"005930": {"symbol": "005930", "quantity": 10, "entry_price": "50000"}},
            "pending_orders": {"ord-1": {"order_id": "ord-1", "symbol": "005930", "side": "buy"}},
            "last_updated": "2024-01-01T00:00:00",
        }

        state = TradingState.from_dict(data)
        assert isinstance(state.positions["005930"], Position)
        assert state.positions["005930"].quantity == 10
        assert isinstance(state.pending_orders["ord-1"], Order)

    def test_from_dict_skips_legacy_string_positions(self):
        """Test broken legacy stringified positions are skipped."""
        data = {
            "version": 1,
            "positions": {
                "005930": "Position(symbol='005930', quantity=10, ...)",
                "000660": {"symbol": "000660", "quantity": 5, "entry_price": "100000"},
            },
            "pending_orders": {},
            "last_updated": "2024-01-01T00:00:00+00:00",
        }
        state = TradingState.from_dict(data)
        assert "005930" not in state.positions
        assert "000660" in state.positions

    def test_risk_controls_round_trip(self):
        state = TradingState(
            risk_controls={
                "daily_kill_switch_active": True,
                "daily_pnl_date": "2026-02-15",
                "daily_baseline_equity": "1000000",
            }
        )

        data = state.to_dict()
        restored = TradingState.from_dict(data)

        assert restored.risk_controls["daily_kill_switch_active"] is True
        assert restored.risk_controls["daily_pnl_date"] == "2026-02-15"
        assert restored.risk_controls["daily_baseline_equity"] == "1000000"


class TestStatePersistence:
    """Test atomic state persistence."""

    def test_save_and_load_state_round_trip(self, tmp_path):
        """Test round-trip persistence with typed models."""
        state = TradingState(
            positions={
                "005930": Position(symbol="005930", quantity=10, entry_price=Decimal("50000"))
            },
            pending_orders={
                "ord-1": Order(
                    order_id="ord-1",
                    idempotency_key="idem-1",
                    symbol="005930",
                    side="buy",
                    quantity=10,
                    price=50000,
                )
            },
        )
        path = tmp_path / "state.json"
        save_state_atomic(state, path)
        loaded = load_state(path)

        assert loaded is not None
        assert isinstance(loaded.positions["005930"], Position)
        assert loaded.positions["005930"].entry_price == Decimal("50000")
        assert isinstance(loaded.pending_orders["ord-1"], Order)

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directories."""
        state = TradingState()
        path = tmp_path / "subdir" / "state.json"
        save_state_atomic(state, path)

        assert path.exists()
        assert path.parent.exists()

    def test_atomic_write_creates_no_temp_file(self, tmp_path):
        """Test that atomic write leaves no temporary files."""
        state = TradingState()
        path = tmp_path / "state.json"
        save_state_atomic(state, path)

        tmp_file = tmp_path / ".state.json.tmp"
        assert not tmp_file.exists()
        assert list(tmp_path.iterdir())[0].name == "state.json"

    def test_atomic_write_overwrites_existing(self, tmp_path):
        """Test that atomic write overwrites existing state."""
        path = tmp_path / "state.json"
        state1 = TradingState(
            positions={"005930": Position(symbol="005930", quantity=10, entry_price=Decimal("1"))}
        )
        state2 = TradingState(
            positions={"005930": Position(symbol="005930", quantity=20, entry_price=Decimal("2"))}
        )

        save_state_atomic(state1, path)
        save_state_atomic(state2, path)
        loaded = load_state(path)
        assert loaded is not None
        assert loaded.positions["005930"].quantity == 20

    def test_load_nonexistent_returns_none(self, tmp_path):
        """Test loading non-existent file returns None."""
        path = tmp_path / "nonexistent.json"
        result = load_state(path)
        assert result is None

    def test_save_preserves_json_format(self, tmp_path):
        """Test that saved state is valid JSON."""
        state = TradingState(
            positions={
                "005930": Position(symbol="005930", quantity=10, entry_price=Decimal("50000"))
            }
        )
        path = tmp_path / "state.json"
        save_state_atomic(state, path)

        with open(path, "r") as f:
            data = json.load(f)

        assert "positions" in data
        assert data["positions"]["005930"]["quantity"] == 10
        assert data["version"] == 2

    def test_save_includes_timestamp(self, tmp_path):
        """Test that saved state includes timestamp."""
        state = TradingState()
        path = tmp_path / "state.json"
        save_state_atomic(state, path)

        with open(path, "r") as f:
            data = json.load(f)

        assert isinstance(data["last_updated"], str)
        datetime.fromisoformat(data["last_updated"])

    def test_path_as_string(self, tmp_path):
        """Test that save/load work with string paths."""
        state = TradingState(
            positions={
                "005930": Position(symbol="005930", quantity=10, entry_price=Decimal("50000"))
            }
        )
        path_str = str(tmp_path / "state.json")
        save_state_atomic(state, path_str)
        loaded = load_state(path_str)

        assert loaded is not None
        assert "005930" in loaded.positions

    def test_backward_compatibility_reads_v1_file(self, tmp_path):
        """Test v1 persisted file can still be loaded."""
        path = tmp_path / "legacy_state.json"
        path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "positions": {
                        "005930": {"symbol": "005930", "quantity": 10, "entry_price": "50000"}
                    },
                    "pending_orders": {},
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        loaded = load_state(path)

        assert loaded is not None
        assert isinstance(loaded.positions["005930"], Position)
