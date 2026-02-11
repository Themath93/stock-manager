"""Unit tests for crash recovery."""
from unittest.mock import Mock
from stock_manager.persistence.recovery import (
    startup_reconciliation, RecoveryResult, RecoveryReport
)
from stock_manager.persistence.state import TradingState


class TestRecoveryReport:
    """Test RecoveryReport model."""

    def test_default_report(self):
        """Test default recovery report."""
        report = RecoveryReport()
        assert report.result == RecoveryResult.CLEAN
        assert report.orphan_positions == []
        assert report.missing_positions == []
        assert report.quantity_mismatches == {}
        assert report.pending_orders == []
        assert report.errors == []


class TestStartupReconciliation:
    """Test startup reconciliation logic."""

    def test_clean_state_when_matching(self):
        """Test clean state when local matches broker."""
        local_state = TradingState()
        local_state.positions = {
            "005930": {"symbol": "005930", "quantity": 10}
        }

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": [{"pdno": "005930", "hldg_qty": "10"}]
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.CLEAN
        assert len(report.orphan_positions) == 0
        assert len(report.missing_positions) == 0
        assert len(report.quantity_mismatches) == 0
        save_state.assert_called_once()

    def test_clean_state_when_both_empty(self):
        """Test clean state when both local and broker are empty."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": []
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.CLEAN
        assert len(report.orphan_positions) == 0
        assert len(report.missing_positions) == 0

    def test_reconciled_when_orphan_found(self):
        """Test reconciliation when broker has positions not in local state."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": [{"pdno": "005930", "hldg_qty": "10"}]
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.RECONCILED
        assert "005930" in report.orphan_positions
        assert len(report.missing_positions) == 0

        # Verify orphan was added to local state
        assert "005930" in local_state.positions
        assert local_state.positions["005930"]["quantity"] == 10
        assert local_state.positions["005930"]["status"] == "open_reconciled"

    def test_reconciled_when_multiple_orphans(self):
        """Test reconciliation with multiple orphan positions."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": [
                {"pdno": "005930", "hldg_qty": "10"},
                {"pdno": "000660", "hldg_qty": "5"}
            ]
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.RECONCILED
        assert len(report.orphan_positions) == 2
        assert "005930" in report.orphan_positions
        assert "000660" in report.orphan_positions

    def test_reconciled_when_missing_position(self):
        """Test reconciliation when local has positions not at broker."""
        local_state = TradingState()
        local_state.positions = {
            "005930": {"symbol": "005930", "quantity": 10}
        }

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": []
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.RECONCILED
        assert "005930" in report.missing_positions
        assert len(report.orphan_positions) == 0

        # Verify missing position was marked stale
        assert local_state.positions["005930"]["status"] == "stale"

    def test_reconciled_when_quantity_mismatch(self):
        """Test reconciliation when quantities don't match."""
        local_state = TradingState()
        local_state.positions = {
            "005930": {"symbol": "005930", "quantity": 10}
        }

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": [{"pdno": "005930", "hldg_qty": "15"}]
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.RECONCILED
        assert "005930" in report.quantity_mismatches
        assert report.quantity_mismatches["005930"] == (10, 15)

        # Verify broker quantity is source of truth
        assert local_state.positions["005930"]["quantity"] == 15

    def test_reconciled_with_mixed_issues(self):
        """Test reconciliation with multiple types of issues."""
        local_state = TradingState()
        local_state.positions = {
            "005930": {"symbol": "005930", "quantity": 10},  # Mismatch
            "000660": {"symbol": "000660", "quantity": 5}    # Missing at broker
        }

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": [
                {"pdno": "005930", "hldg_qty": "15"},  # Quantity mismatch
                {"pdno": "035720", "hldg_qty": "20"}   # Orphan
            ]
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.RECONCILED
        assert "035720" in report.orphan_positions
        assert "000660" in report.missing_positions
        assert "005930" in report.quantity_mismatches
        assert report.quantity_mismatches["005930"] == (10, 15)

    def test_failed_when_broker_api_error(self):
        """Test failed reconciliation when broker API returns error."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "1",
            "msg1": "API Error"
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.FAILED
        assert len(report.errors) > 0
        assert "Failed to query broker" in report.errors[0]

    def test_failed_when_exception_raised(self):
        """Test failed reconciliation when exception is raised."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(side_effect=Exception("Connection error"))
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.FAILED
        assert len(report.errors) > 0
        assert "Connection error" in report.errors[0]

    def test_broker_is_source_of_truth(self):
        """Test that broker positions always override local state."""
        local_state = TradingState()
        local_state.positions = {
            "005930": {"symbol": "005930", "quantity": 100}
        }

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": [{"pdno": "005930", "hldg_qty": "1"}]
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        # Even with large difference, broker wins
        assert local_state.positions["005930"]["quantity"] == 1

    def test_zero_quantity_at_broker(self):
        """Test handling of zero quantity at broker."""
        local_state = TradingState()
        local_state.positions = {
            "005930": {"symbol": "005930", "quantity": 10}
        }

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": [{"pdno": "005930", "hldg_qty": "0"}]
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        # Zero quantity means broker has it but quantity is 0
        assert report.result == RecoveryResult.RECONCILED
        assert local_state.positions["005930"]["quantity"] == 0

    def test_save_state_called_after_reconciliation(self):
        """Test that state is saved after reconciliation."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": [{"pdno": "005930", "hldg_qty": "10"}]
        })
        save_state = Mock()

        startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        # Verify save was called with correct arguments
        save_state.assert_called_once_with(local_state, "state.json")

    def test_inquire_balance_called_with_client(self):
        """Test that inquire_balance is called with the client."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": []
        })
        save_state = Mock()

        startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        inquire_balance.assert_called_once_with(client)

    def test_handles_missing_hldg_qty_field(self):
        """Test handling of missing hldg_qty field."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(return_value={
            "rt_cd": "0",
            "output1": [{"pdno": "005930"}]  # Missing hldg_qty
        })
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        # Should handle gracefully, treating as 0
        assert report.result == RecoveryResult.RECONCILED
        assert "005930" in local_state.positions
        assert local_state.positions["005930"]["quantity"] == 0
