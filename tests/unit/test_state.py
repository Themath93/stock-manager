"""Unit tests for state persistence."""

import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from stock_manager.persistence.state import (
    TradingState,
    _deserialize_order,
    _deserialize_position,
    _parse_decimal,
    _parse_dt,
    _serialize_order,
    _serialize_position,
    load_state,
    save_state_atomic,
)
from stock_manager.trading.models import Order, OrderStatus, Position, PositionStatus


class TestTradingState:
    """Test TradingState model serialization."""

    def test_default_state(self):
        """Test default state creation."""
        state = TradingState()
        assert state.positions == {}
        assert state.pending_orders == {}
        assert state.version == 4
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
        assert data["version"] == 4
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

    def test_from_dict_ignores_non_dict_risk_controls(self):
        state = TradingState.from_dict({"positions": {}, "pending_orders": {}, "risk_controls": []})
        assert state.risk_controls == {}


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
        assert data["version"] == 4

    def test_save_round_trip_preserves_order_resolution_metadata(self, tmp_path):
        state = TradingState(
            pending_orders={
                "ord-1": Order(
                    order_id="ord-1",
                    symbol="005930",
                    side="buy",
                    quantity=1,
                    price=70000,
                    status=OrderStatus.PARTIAL_FILL,
                    resolution_source="daily_order",
                    broker_last_seen_status="partial_fill",
                    last_reconciled_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
                    unresolved_reason="waiting_for_fill",
                )
            }
        )
        path = tmp_path / "state.json"

        save_state_atomic(state, path)
        loaded = load_state(path)

        assert loaded is not None
        order = loaded.pending_orders["ord-1"]
        assert order.resolution_source == "daily_order"
        assert order.broker_last_seen_status == "partial_fill"
        assert order.last_reconciled_at == datetime(2026, 3, 8, tzinfo=timezone.utc)
        assert order.unresolved_reason == "waiting_for_fill"

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


class TestStateHelpers:
    def test_parse_helpers_handle_invalid_and_naive_values(self):
        naive = _parse_dt("2024-01-01T00:00:00")
        assert naive == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert _parse_dt("") is None
        assert _parse_dt("not-a-datetime") is None

        assert _parse_decimal("12.5") == Decimal("12.5")
        assert _parse_decimal("") is None
        assert _parse_decimal("oops") is None

    def test_position_serialization_and_deserialization_cover_compatibility_paths(self):
        serialized = _serialize_position(
            "005930",
            {
                "quantity": 3,
                "entry_price": "70000",
                "current_price": "71000",
                "stop_loss": "68000",
                "take_profit": "73000",
                "unrealized_pnl": "3000",
                "status": "stale",
                "opened_at": "2024-01-01T00:00:00+00:00",
                "closed_at": "2024-01-02T00:00:00+00:00",
            },
        )
        assert serialized["symbol"] == "005930"
        assert serialized["status"] == "stale"

        with pytest.raises(TypeError):
            _serialize_position("005930", object())

        position = Position(symbol="005930", quantity=1, entry_price=Decimal("1"))
        assert _deserialize_position("005930", position) is position
        assert _deserialize_position("005930", "Position(...)") is None
        assert _deserialize_position("005930", 123) is None

        restored = _deserialize_position(
            "005930",
            {
                "quantity": 2,
                "entry_price": "70000",
                "status": "unknown-status",
                "opened_at": "2024-01-01T00:00:00+00:00",
            },
        )
        assert restored is not None
        assert restored.status == PositionStatus.OPEN

        assert _deserialize_position("005930", {"quantity": "bad"}) is None

    def test_order_serialization_and_deserialization_cover_compatibility_paths(self):
        serialized = _serialize_order(
            "ord-1",
            {
                "symbol": "005930",
                "side": "buy",
                "quantity": 2,
                "status": "submitted",
                "requested_stop_loss": 68000,
                "requested_take_profit": 72000,
                "exit_reason": "MANUAL",
                "position_quantity_at_submit": 2,
                "resolution_source": "daily_order",
                "broker_last_seen_status": "partial_fill",
                "last_reconciled_at": "2024-01-01T00:00:00+00:00",
                "unresolved_reason": "waiting_for_fill",
                "submission_attempts": 1,
                "filled_quantity": 1,
                "filled_avg_price": "70100",
            },
        )
        assert serialized["resolution_source"] == "daily_order"
        assert serialized["filled_avg_price"] == "70100"

        with pytest.raises(TypeError):
            _serialize_order("ord-1", object())

        order = Order(order_id="ord-1", symbol="005930", side="buy", quantity=1)
        assert _deserialize_order("ord-1", order) is order
        assert _deserialize_order("ord-1", "invalid") is None

        restored = _deserialize_order(
            "ord-1",
            {
                "symbol": "005930",
                "side": "sell",
                "quantity": 3,
                "status": "unknown-status",
                "requested_stop_loss": "68000",
                "requested_take_profit": "72000",
                "position_quantity_at_submit": "3",
                "resolution_source": "balance",
                "broker_last_seen_status": "submitted",
                "last_reconciled_at": "2024-01-01T00:00:00+00:00",
                "unresolved_reason": "awaiting_fill",
                "created_at": "2024-01-01T00:00:01+00:00",
                "filled_avg_price": "71000",
            },
        )
        assert restored is not None
        assert restored.status == OrderStatus.CREATED
        assert restored.requested_stop_loss == 68000
        assert restored.requested_take_profit == 72000
        assert restored.position_quantity_at_submit == 3
        assert restored.resolution_source == "balance"
        assert restored.last_reconciled_at == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert restored.filled_avg_price == Decimal("71000")

        assert _deserialize_order("ord-1", {"quantity": "bad"}) is None
