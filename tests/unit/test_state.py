"""Unit tests for state persistence."""
import json
from datetime import datetime
from stock_manager.persistence.state import (
    TradingState, save_state_atomic, load_state
)


class TestTradingState:
    """Test TradingState model."""

    def test_default_state(self):
        """Test default state creation."""
        state = TradingState()
        assert state.positions == {}
        assert state.pending_orders == {}
        assert state.version == 1
        assert isinstance(state.last_updated, datetime)

    def test_to_dict(self):
        """Test state serialization to dict."""
        state = TradingState()
        state.positions["005930"] = {"symbol": "005930", "quantity": 10}
        state.pending_orders["order1"] = {"order_id": "order1", "symbol": "005930"}

        data = state.to_dict()

        assert "positions" in data
        assert "pending_orders" in data
        assert "last_updated" in data
        assert "version" in data
        assert data["positions"]["005930"]["quantity"] == 10
        assert data["pending_orders"]["order1"]["order_id"] == "order1"

    def test_from_dict(self):
        """Test state deserialization from dict."""
        data = {
            "positions": {"005930": {"symbol": "005930", "quantity": 10}},
            "pending_orders": {"order1": {"order_id": "order1"}},
            "last_updated": "2024-01-01T12:00:00",
            "version": 1
        }

        state = TradingState.from_dict(data)

        assert "005930" in state.positions
        assert state.positions["005930"]["quantity"] == 10
        assert "order1" in state.pending_orders
        assert state.version == 1

    def test_from_dict_with_missing_fields(self):
        """Test state deserialization handles missing fields."""
        data = {}
        state = TradingState.from_dict(data)

        assert state.positions == {}
        assert state.pending_orders == {}
        assert state.version == 1


class TestStatePersistence:
    """Test atomic state persistence."""

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading state."""
        state = TradingState()
        state.positions["005930"] = {"symbol": "005930", "quantity": 10}
        state.pending_orders["order1"] = {"order_id": "order1", "symbol": "005930"}

        path = tmp_path / "state.json"
        save_state_atomic(state, path)

        # Verify file exists
        assert path.exists()

        # Load and verify
        loaded = load_state(path)
        assert loaded is not None
        assert "005930" in loaded.positions
        assert loaded.positions["005930"]["quantity"] == 10
        assert "order1" in loaded.pending_orders

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

        # No .tmp file should remain
        tmp_file = tmp_path / ".state.json.tmp"
        assert not tmp_file.exists()

        # Only the final file should exist
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "state.json"

    def test_atomic_write_overwrites_existing(self, tmp_path):
        """Test that atomic write overwrites existing state."""
        state1 = TradingState()
        state1.positions["005930"] = {"quantity": 10}

        state2 = TradingState()
        state2.positions["005930"] = {"quantity": 20}

        path = tmp_path / "state.json"

        # Save first state
        save_state_atomic(state1, path)
        loaded1 = load_state(path)
        assert loaded1.positions["005930"]["quantity"] == 10

        # Overwrite with second state
        save_state_atomic(state2, path)
        loaded2 = load_state(path)
        assert loaded2.positions["005930"]["quantity"] == 20

    def test_load_nonexistent_returns_none(self, tmp_path):
        """Test loading non-existent file returns None."""
        path = tmp_path / "nonexistent.json"
        result = load_state(path)
        assert result is None

    def test_save_preserves_json_format(self, tmp_path):
        """Test that saved state is valid JSON."""
        state = TradingState()
        state.positions["005930"] = {
            "symbol": "005930",
            "quantity": 10,
            "entry_price": "50000"
        }

        path = tmp_path / "state.json"
        save_state_atomic(state, path)

        # Verify it's valid JSON by loading with json module
        with open(path, 'r') as f:
            data = json.load(f)

        assert "positions" in data
        assert "005930" in data["positions"]
        assert data["positions"]["005930"]["quantity"] == 10

    def test_save_includes_timestamp(self, tmp_path):
        """Test that saved state includes timestamp."""
        state = TradingState()
        path = tmp_path / "state.json"

        save_state_atomic(state, path)

        with open(path, 'r') as f:
            data = json.load(f)

        assert "last_updated" in data
        assert isinstance(data["last_updated"], str)
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(data["last_updated"])

    def test_save_empty_state(self, tmp_path):
        """Test saving empty state."""
        state = TradingState()
        path = tmp_path / "state.json"

        save_state_atomic(state, path)

        loaded = load_state(path)
        assert loaded is not None
        assert loaded.positions == {}
        assert loaded.pending_orders == {}

    def test_save_complex_state(self, tmp_path):
        """Test saving state with complex data."""
        state = TradingState()
        state.positions["005930"] = {
            "symbol": "005930",
            "quantity": 10,
            "entry_price": "50000",
            "current_price": "52000",
            "stop_loss": "47500",
            "take_profit": "55000",
            "unrealized_pnl": "20000",
            "status": "open"
        }
        state.pending_orders["order1"] = {
            "order_id": "order1",
            "symbol": "005930",
            "side": "buy",
            "quantity": 10,
            "price": 50000,
            "status": "submitted"
        }

        path = tmp_path / "state.json"
        save_state_atomic(state, path)

        loaded = load_state(path)
        assert loaded is not None
        assert loaded.positions["005930"]["entry_price"] == "50000"
        assert loaded.positions["005930"]["unrealized_pnl"] == "20000"
        assert loaded.pending_orders["order1"]["price"] == 50000

    def test_multiple_saves_are_independent(self, tmp_path):
        """Test that multiple saves to different files don't interfere."""
        state1 = TradingState()
        state1.positions["005930"] = {"quantity": 10}

        state2 = TradingState()
        state2.positions["000660"] = {"quantity": 20}

        path1 = tmp_path / "state1.json"
        path2 = tmp_path / "state2.json"

        save_state_atomic(state1, path1)
        save_state_atomic(state2, path2)

        loaded1 = load_state(path1)
        loaded2 = load_state(path2)

        assert "005930" in loaded1.positions
        assert "000660" not in loaded1.positions
        assert "000660" in loaded2.positions
        assert "005930" not in loaded2.positions

    def test_state_file_is_readable(self, tmp_path):
        """Test that state file is human-readable JSON."""
        state = TradingState()
        state.positions["005930"] = {"symbol": "005930", "quantity": 10}

        path = tmp_path / "state.json"
        save_state_atomic(state, path)

        # Read file as text
        content = path.read_text()

        # Should be formatted JSON (has newlines)
        assert "\n" in content
        assert '"positions"' in content
        assert '"005930"' in content

    def test_path_as_string(self, tmp_path):
        """Test that save/load work with string paths."""
        state = TradingState()
        state.positions["005930"] = {"quantity": 10}

        path_str = str(tmp_path / "state.json")
        save_state_atomic(state, path_str)

        loaded = load_state(path_str)
        assert loaded is not None
        assert "005930" in loaded.positions
