"""Unit tests for crash recovery."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from stock_manager.persistence.recovery import (
    startup_reconciliation,
    RecoveryResult,
    RecoveryReport,
    _extract_daily_filled_qty,
    _find_daily_order,
    _get_local_qty,
    _looks_rejected_or_cancelled,
    _mark_local_position_stale,
    _recover_pending_orders,
    _set_local_qty,
    _to_decimal,
    _upsert_local_position,
)
from stock_manager.persistence.state import TradingState
from stock_manager.trading.models import Order, OrderStatus, Position, PositionStatus


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
        local_state.positions = {"005930": {"symbol": "005930", "quantity": 10}}

        client = Mock()
        inquire_balance = Mock(
            return_value={"rt_cd": "0", "output1": [{"pdno": "005930", "hldg_qty": "10"}]}
        )
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
        inquire_balance = Mock(return_value={"rt_cd": "0", "output1": []})
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
        inquire_balance = Mock(
            return_value={"rt_cd": "0", "output1": [{"pdno": "005930", "hldg_qty": "10"}]}
        )
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        assert report.result == RecoveryResult.RECONCILED
        assert "005930" in report.orphan_positions
        assert len(report.missing_positions) == 0

        # Verify orphan was added to local state
        assert "005930" in local_state.positions
        position = local_state.positions["005930"]
        assert isinstance(position, Position)
        assert position.quantity == 10
        assert position.status == PositionStatus.OPEN_RECONCILED

    def test_reconciled_when_multiple_orphans(self):
        """Test reconciliation with multiple orphan positions."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(
            return_value={
                "rt_cd": "0",
                "output1": [
                    {"pdno": "005930", "hldg_qty": "10"},
                    {"pdno": "000660", "hldg_qty": "5"},
                ],
            }
        )
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
        local_state.positions = {"005930": {"symbol": "005930", "quantity": 10}}

        client = Mock()
        inquire_balance = Mock(return_value={"rt_cd": "0", "output1": []})
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
        local_state.positions = {"005930": {"symbol": "005930", "quantity": 10}}

        client = Mock()
        inquire_balance = Mock(
            return_value={"rt_cd": "0", "output1": [{"pdno": "005930", "hldg_qty": "15"}]}
        )
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
            "000660": {"symbol": "000660", "quantity": 5},  # Missing at broker
        }

        client = Mock()
        inquire_balance = Mock(
            return_value={
                "rt_cd": "0",
                "output1": [
                    {"pdno": "005930", "hldg_qty": "15"},  # Quantity mismatch
                    {"pdno": "035720", "hldg_qty": "20"},  # Orphan
                ],
            }
        )
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
        inquire_balance = Mock(return_value={"rt_cd": "1", "msg1": "API Error"})
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
        local_state.positions = {"005930": {"symbol": "005930", "quantity": 100}}

        client = Mock()
        inquire_balance = Mock(
            return_value={"rt_cd": "0", "output1": [{"pdno": "005930", "hldg_qty": "1"}]}
        )
        save_state = Mock()

        startup_reconciliation(local_state, client, inquire_balance, save_state, "state.json")

        # Even with large difference, broker wins
        assert local_state.positions["005930"]["quantity"] == 1

    def test_zero_quantity_at_broker(self):
        """Test handling of zero quantity at broker."""
        local_state = TradingState()
        local_state.positions = {"005930": {"symbol": "005930", "quantity": 10}}

        client = Mock()
        inquire_balance = Mock(
            return_value={"rt_cd": "0", "output1": [{"pdno": "005930", "hldg_qty": "0"}]}
        )
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
        inquire_balance = Mock(
            return_value={"rt_cd": "0", "output1": [{"pdno": "005930", "hldg_qty": "10"}]}
        )
        save_state = Mock()

        startup_reconciliation(local_state, client, inquire_balance, save_state, "state.json")

        # Verify save was called with correct arguments
        save_state.assert_called_once_with(local_state, "state.json")

    def test_inquire_balance_called_with_client(self):
        """Test that inquire_balance is called with the client."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(return_value={"rt_cd": "0", "output1": []})
        save_state = Mock()

        startup_reconciliation(local_state, client, inquire_balance, save_state, "state.json")

        inquire_balance.assert_called_once_with(client)

    def test_handles_missing_hldg_qty_field(self):
        """Test handling of missing hldg_qty field."""
        local_state = TradingState()

        client = Mock()
        inquire_balance = Mock(
            return_value={
                "rt_cd": "0",
                "output1": [{"pdno": "005930"}],  # Missing hldg_qty
            }
        )
        save_state = Mock()

        report = startup_reconciliation(
            local_state, client, inquire_balance, save_state, "state.json"
        )

        # Should handle gracefully, treating as 0
        assert report.result == RecoveryResult.RECONCILED
        assert "005930" in local_state.positions
        position = local_state.positions["005930"]
        assert isinstance(position, Position)
        assert position.quantity == 0

    def test_records_daily_order_query_error_and_continues(self):
        local_state = TradingState()
        client = Mock()
        inquire_balance = Mock(return_value={"rt_cd": "0", "output1": []})
        save_state = Mock()

        report = startup_reconciliation(
            local_state,
            client,
            inquire_balance,
            save_state,
            "state.json",
            inquire_daily_orders_func=Mock(side_effect=RuntimeError("daily orders unavailable")),
        )

        assert report.result == RecoveryResult.CLEAN
        assert report.errors == ["Failed to query daily orders: daily orders unavailable"]
        save_state.assert_called_once_with(local_state, "state.json")


class TestPendingOrderRecovery:
    def test_recover_pending_buy_from_daily_order_fill(self):
        order = Order(
            order_id="ord-1",
            symbol="005930",
            side="buy",
            quantity=3,
            status=OrderStatus.SUBMITTED,
            broker_order_id="12345",
        )
        pending_orders = {"ord-1": order}
        report = RecoveryReport()

        _recover_pending_orders(
            pending_orders=pending_orders,
            broker_positions=[],
            daily_orders_response={
                "output1": [{"odno": "12345", "tot_ccld_qty": "3", "avg_prvs": "70100"}]
            },
            report=report,
        )

        assert report.pending_orders == []
        assert order.status == OrderStatus.FILLED
        assert order.resolution_source == "daily_order"
        assert order.filled_quantity == 3
        assert order.filled_avg_price == Decimal("70100")
        assert order.filled_at is not None

    def test_recover_pending_buy_from_balance_when_daily_order_missing(self):
        order = Order(
            order_id="ord-1",
            symbol="005930",
            side="buy",
            quantity=2,
            status=OrderStatus.SUBMITTED,
        )
        report = RecoveryReport()

        _recover_pending_orders(
            pending_orders={"ord-1": order},
            broker_positions=[{"pdno": "005930", "hldg_qty": "2", "pchs_avg_pric": "72000"}],
            daily_orders_response={"output1": []},
            report=report,
        )

        assert report.pending_orders == []
        assert order.status == OrderStatus.FILLED
        assert order.resolution_source == "balance"
        assert order.filled_quantity == 2
        assert order.filled_avg_price == Decimal("72000")
        assert order.filled_at is not None

    def test_recover_pending_order_marks_rejected_from_cancel_payload(self):
        order = Order(
            order_id="ord-1",
            symbol="005930",
            side="buy",
            quantity=1,
            status=OrderStatus.SUBMITTED,
            broker_order_id="12345",
        )
        report = RecoveryReport()

        _recover_pending_orders(
            pending_orders={"ord-1": order},
            broker_positions=[],
            daily_orders_response={"output1": [{"odno": "12345", "msg1": "주문 거부"}]},
            report=report,
        )

        assert report.pending_orders == []
        assert order.status == OrderStatus.REJECTED
        assert order.unresolved_reason is None
        assert order.last_event_at is not None

    def test_recover_pending_sell_from_daily_order_fill(self):
        order = Order(
            order_id="ord-1",
            symbol="005930",
            side="sell",
            quantity=4,
            status=OrderStatus.SUBMITTED,
            broker_order_id="54321",
        )
        report = RecoveryReport()

        _recover_pending_orders(
            pending_orders={"ord-1": order},
            broker_positions=[],
            daily_orders_response={"output1": [{"odno": "54321", "tot_ccld_qty": "4"}]},
            report=report,
        )

        assert report.pending_orders == []
        assert order.status == OrderStatus.FILLED
        assert order.resolution_source == "daily_order"
        assert order.filled_quantity == 4
        assert order.filled_at is not None

    def test_recover_pending_order_marks_ambiguous_daily_order_unresolved(self):
        order = Order(
            order_id="ord-1",
            symbol="005930",
            side="buy",
            quantity=1,
            status=OrderStatus.SUBMITTED,
        )
        report = RecoveryReport()

        _recover_pending_orders(
            pending_orders={"ord-1": order},
            broker_positions=[],
            daily_orders_response={
                "output1": [
                    {"pdno": "005930", "sll_buy_dvsn_cd": "02"},
                    {"pdno": "005930", "sll_buy_dvsn_cd": "02"},
                ]
            },
            report=report,
        )

        assert report.pending_orders == ["ord-1"]
        assert order.status == OrderStatus.SUBMITTED
        assert order.unresolved_reason == "ambiguous_daily_order_match"
        assert order.last_reconciled_at is not None


class TestRecoveryHelpers:
    def test_find_daily_order_prefers_broker_order_id_and_single_candidate(self):
        order = Order(
            order_id="ord-1",
            symbol="005930",
            side="buy",
            quantity=1,
            broker_order_id="A-1",
        )
        matched, reason = _find_daily_order(
            [
                {"odno": "A-1", "pdno": "000660", "sll_buy_dvsn_cd": "01"},
                {"pdno": "005930", "sll_buy_dvsn_cd": "02"},
            ],
            order,
        )
        assert matched == {"odno": "A-1", "pdno": "000660", "sll_buy_dvsn_cd": "01"}
        assert reason is None

        order.broker_order_id = None
        matched, reason = _find_daily_order([{"pdno": "005930", "sll_buy_dvsn_cd": "02"}], order)
        assert matched == {"pdno": "005930", "sll_buy_dvsn_cd": "02"}
        assert reason is None

        matched, reason = _find_daily_order([], order)
        assert matched is None
        assert reason == "no_daily_order_match"

    def test_find_daily_order_skips_invalid_candidates_and_non_list_daily_orders(self):
        order = Order(
            order_id="ord-1",
            symbol="005930",
            side="buy",
            quantity=1,
            status=OrderStatus.SUBMITTED,
        )
        matched, reason = _find_daily_order(
            [
                None,
                {"pdno": "000660", "sll_buy_dvsn_cd": "02"},
                {"pdno": "005930"},
                {"pdno": "005930", "sll_buy_dvsn_cd": "99"},
            ],
            order,
        )
        assert matched is None
        assert reason == "no_daily_order_match"

        report = RecoveryReport()
        _recover_pending_orders(
            pending_orders={"ord-1": order, "done": Order(status=OrderStatus.FILLED)},
            broker_positions=[],
            daily_orders_response={"output1": "not-a-list"},
            report=report,
        )
        assert report.pending_orders == ["ord-1"]
        assert order.unresolved_reason == "no_daily_order_match"

    def test_helper_branches_cover_fallback_and_parsing_paths(self):
        typed_position = Position(symbol="005930", quantity=3, entry_price=Decimal("100"))
        assert _get_local_qty(typed_position) == 3
        assert _get_local_qty(SimpleNamespace(quantity=7)) == 7

        _set_local_qty({"005930": typed_position}, "005930", 8)
        assert typed_position.quantity == 8

        _mark_local_position_stale({"005930": typed_position}, "005930")
        assert typed_position.status == PositionStatus.STALE

        positions: dict[str, object] = {}
        _set_local_qty(positions, "005930", 5)
        assert positions["005930"] == {
            "symbol": "005930",
            "quantity": 5,
            "status": PositionStatus.OPEN_RECONCILED.value,
        }

        _mark_local_position_stale(positions, "000660")
        assert positions["000660"] == {
            "symbol": "000660",
            "quantity": 0,
            "status": PositionStatus.STALE.value,
        }

        existing = {"035720": {"symbol": "035720", "quantity": 1}}
        _upsert_local_position(existing, "035720", 9)
        assert existing["035720"]["quantity"] == 9

        created: dict[str, object] = {}
        _upsert_local_position(created, "251340", 4)
        assert isinstance(created["251340"], Position)
        assert created["251340"].status == PositionStatus.OPEN_RECONCILED

        assert _extract_daily_filled_qty({"tot_ccld_qty": "bad", "CCLD_QTY": "2"}) == 2
        assert _extract_daily_filled_qty({"tot_ccld_qty": ""}) == 0
        assert _looks_rejected_or_cancelled({"msg1": "주문 취소"}) is True
        assert _looks_rejected_or_cancelled({"msg1": "filled"}) is False
        assert _to_decimal("-") is None
        assert _to_decimal("oops") is None
        assert _to_decimal("12.5") == Decimal("12.5")
