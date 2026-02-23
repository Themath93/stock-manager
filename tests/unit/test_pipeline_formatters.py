"""Unit tests for pipeline-specific Slack Block Kit formatter functions.

Tests the new pipeline formatter functions added to
stock_manager/notifications/formatters.py:
  - format_pipeline_state_change
  - format_consensus_result
  - format_buy_executed
  - format_sell_executed
  - format_pipeline_error
  - format_daily_summary
  - format_trade_complete
  - dispatch_pipeline_event
  - dispatch_consensus_event
"""


from stock_manager.notifications.formatters import (
    dispatch_consensus_event,
    dispatch_pipeline_event,
    format_buy_executed,
    format_consensus_result,
    format_daily_summary,
    format_pipeline_error,
    format_pipeline_state_change,
    format_sell_executed,
    format_trade_complete,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _block_types(blocks: list[dict]) -> list[str]:
    """Return list of block type strings from a blocks list."""
    return [b["type"] for b in blocks]


def _all_text(blocks: list[dict]) -> str:
    """Concatenate all text values found anywhere in blocks (for string assertions)."""
    parts: list[str] = []

    def _extract(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "text" and isinstance(v, str):
                    parts.append(v)
                else:
                    _extract(v)
        elif isinstance(obj, list):
            for item in obj:
                _extract(item)

    _extract(blocks)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# format_pipeline_state_change
# ---------------------------------------------------------------------------

class TestFormatPipelineStateChange:
    """Tests for format_pipeline_state_change."""

    def test_returns_list_of_dicts(self):
        """Return value is a non-empty list of dicts (Block Kit blocks)."""
        result = format_pipeline_state_change(
            symbol="005930",
            from_state="IDLE",
            to_state="SCREENING",
            reason="market open",
        )
        assert isinstance(result, list)
        assert len(result) > 0
        for block in result:
            assert isinstance(block, dict)

    def test_contains_symbol(self):
        """Symbol appears somewhere in the rendered blocks."""
        result = format_pipeline_state_change(
            symbol="005930",
            from_state="IDLE",
            to_state="SCREENING",
            reason="market open",
        )
        text = _all_text(result)
        assert "005930" in text

    def test_contains_state_transition(self):
        """from_state and to_state both appear in the rendered blocks."""
        result = format_pipeline_state_change(
            symbol="005930",
            from_state="IDLE",
            to_state="SCREENING",
            reason="market open",
        )
        text = _all_text(result)
        assert "IDLE" in text
        assert "SCREENING" in text

    def test_contains_reason(self):
        """Reason string appears somewhere in the rendered blocks."""
        result = format_pipeline_state_change(
            symbol="005930",
            from_state="IDLE",
            to_state="SCREENING",
            reason="daily trigger",
        )
        text = _all_text(result)
        assert "daily trigger" in text

    def test_has_header_block(self):
        """Result includes at least one header or section block."""
        result = format_pipeline_state_change(
            symbol="005930",
            from_state="IDLE",
            to_state="CONSENSUS",
            reason="screened",
        )
        types = _block_types(result)
        assert "header" in types or "section" in types

    def test_accepts_extra_kwargs(self):
        """Extra keyword arguments are silently accepted (no TypeError)."""
        result = format_pipeline_state_change(
            symbol="005930",
            from_state="IDLE",
            to_state="SCREENING",
            reason="start",
            extra_field="ignored",
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# format_consensus_result
# ---------------------------------------------------------------------------

class TestFormatConsensusResult:
    """Tests for format_consensus_result."""

    def test_returns_list_of_dicts(self):
        """Return value is a non-empty list of dicts."""
        result = format_consensus_result(
            symbol="005930",
            passed=True,
            buy_count=3,
            total_count=4,
            avg_conviction=0.82,
            categories={"value": 2, "growth": 1},
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_passed_true_shows_buy_counts(self):
        """Buy count and total count appear in blocks for a passing consensus."""
        result = format_consensus_result(
            symbol="005930",
            passed=True,
            buy_count=3,
            total_count=4,
            avg_conviction=0.82,
            categories={"value": 2},
        )
        text = _all_text(result)
        # 3 and 4 should appear somewhere
        assert "3" in text
        assert "4" in text

    def test_passed_false_represented(self):
        """A rejected consensus is represented distinctively in blocks."""
        result = format_consensus_result(
            symbol="000660",
            passed=False,
            buy_count=1,
            total_count=4,
            avg_conviction=0.35,
            categories={"value": 1},
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_symbol_in_blocks(self):
        """Symbol appears in blocks."""
        result = format_consensus_result(
            symbol="035420",
            passed=True,
            buy_count=3,
            total_count=4,
            avg_conviction=0.75,
            categories={},
        )
        text = _all_text(result)
        assert "035420" in text

    def test_avg_conviction_in_blocks(self):
        """avg_conviction value is rendered somewhere in blocks."""
        result = format_consensus_result(
            symbol="005930",
            passed=True,
            buy_count=3,
            total_count=4,
            avg_conviction=0.82,
            categories={},
        )
        text = _all_text(result)
        # Conviction formatted as decimal, e.g. "0.82" or "82"
        assert "0.82" in text or "82" in text

    def test_accepts_extra_kwargs(self):
        """Extra keyword arguments are silently accepted."""
        result = format_consensus_result(
            symbol="005930",
            passed=True,
            buy_count=3,
            total_count=4,
            avg_conviction=0.8,
            categories={},
            ignored_field="x",
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# format_buy_executed
# ---------------------------------------------------------------------------

class TestFormatBuyExecuted:
    """Tests for format_buy_executed."""

    def test_returns_list_of_dicts(self):
        """Return value is a non-empty list of dicts."""
        result = format_buy_executed(
            symbol="005930",
            price=70000,
            quantity=10,
            order_type="LIMIT",
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_symbol_in_blocks(self):
        """Symbol appears in rendered blocks."""
        result = format_buy_executed(
            symbol="005930",
            price=70000,
            quantity=10,
            order_type="LIMIT",
        )
        text = _all_text(result)
        assert "005930" in text

    def test_price_in_blocks(self):
        """Price value appears in rendered blocks."""
        result = format_buy_executed(
            symbol="005930",
            price=70000,
            quantity=10,
            order_type="LIMIT",
        )
        text = _all_text(result)
        assert "70000" in text or "70,000" in text

    def test_quantity_in_blocks(self):
        """Quantity appears in rendered blocks."""
        result = format_buy_executed(
            symbol="005930",
            price=70000,
            quantity=10,
            order_type="LIMIT",
        )
        text = _all_text(result)
        assert "10" in text

    def test_order_type_in_blocks(self):
        """Order type appears in rendered blocks."""
        result = format_buy_executed(
            symbol="005930",
            price=70000,
            quantity=10,
            order_type="MARKET",
        )
        text = _all_text(result)
        assert "MARKET" in text

    def test_accepts_extra_kwargs(self):
        """Extra keyword arguments are silently accepted."""
        result = format_buy_executed(
            symbol="005930",
            price=70000,
            quantity=5,
            order_type="LIMIT",
            stop_loss=63000,
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# format_sell_executed
# ---------------------------------------------------------------------------

class TestFormatSellExecuted:
    """Tests for format_sell_executed."""

    def test_returns_list_of_dicts(self):
        """Return value is a non-empty list of dicts."""
        result = format_sell_executed(
            symbol="005930",
            reason="stop_loss",
            price=63000,
            pnl=-7000,
            return_pct=-10.0,
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_symbol_in_blocks(self):
        """Symbol appears in rendered blocks."""
        result = format_sell_executed(
            symbol="005930",
            reason="take_profit",
            price=77000,
            pnl=7000,
            return_pct=10.0,
        )
        text = _all_text(result)
        assert "005930" in text

    def test_pnl_in_blocks(self):
        """PnL value appears in rendered blocks."""
        result = format_sell_executed(
            symbol="005930",
            reason="stop_loss",
            price=63000,
            pnl=-7000,
            return_pct=-10.0,
        )
        text = _all_text(result)
        assert "7000" in text or "7,000" in text

    def test_return_pct_in_blocks(self):
        """Return percentage appears in rendered blocks."""
        result = format_sell_executed(
            symbol="005930",
            reason="stop_loss",
            price=63000,
            pnl=-7000,
            return_pct=-10.0,
        )
        text = _all_text(result)
        assert "10" in text

    def test_reason_in_blocks(self):
        """Sell reason appears in rendered blocks."""
        result = format_sell_executed(
            symbol="005930",
            reason="max_holding_days",
            price=70000,
            pnl=0,
            return_pct=0.0,
        )
        text = _all_text(result)
        assert "max_holding_days" in text

    def test_accepts_extra_kwargs(self):
        """Extra keyword arguments are silently accepted."""
        result = format_sell_executed(
            symbol="005930",
            reason="stop_loss",
            price=63000,
            pnl=-7000,
            return_pct=-10.0,
            holding_days=5,
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# format_pipeline_error
# ---------------------------------------------------------------------------

class TestFormatPipelineError:
    """Tests for format_pipeline_error."""

    def test_returns_list_of_dicts(self):
        """Return value is a non-empty list of dicts."""
        result = format_pipeline_error(
            symbol="005930",
            error_type="ConnectionError",
            error_message="KIS API unreachable",
            state="SCREENING",
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_symbol_in_blocks(self):
        """Symbol appears in rendered blocks."""
        result = format_pipeline_error(
            symbol="005930",
            error_type="TimeoutError",
            error_message="request timed out",
            state="BUYING",
        )
        text = _all_text(result)
        assert "005930" in text

    def test_error_type_in_blocks(self):
        """Error type appears in rendered blocks."""
        result = format_pipeline_error(
            symbol="005930",
            error_type="ValueError",
            error_message="invalid price",
            state="SCREENING",
        )
        text = _all_text(result)
        assert "ValueError" in text

    def test_error_message_in_blocks(self):
        """Error message appears in rendered blocks."""
        result = format_pipeline_error(
            symbol="005930",
            error_type="RuntimeError",
            error_message="unexpected shutdown",
            state="SCREENING",
        )
        text = _all_text(result)
        assert "unexpected shutdown" in text

    def test_state_in_blocks(self):
        """Pipeline state at time of error appears in rendered blocks."""
        result = format_pipeline_error(
            symbol="005930",
            error_type="RuntimeError",
            error_message="crash",
            state="CONSENSUS",
        )
        text = _all_text(result)
        assert "CONSENSUS" in text

    def test_accepts_extra_kwargs(self):
        """Extra keyword arguments are silently accepted."""
        result = format_pipeline_error(
            symbol="005930",
            error_type="OSError",
            error_message="file not found",
            state="IDLE",
            context={"retry": 3},
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# format_daily_summary
# ---------------------------------------------------------------------------

class TestFormatDailySummary:
    """Tests for format_daily_summary."""

    def test_returns_list_of_dicts(self):
        """Return value is a non-empty list of dicts."""
        result = format_daily_summary(
            date="2026-02-22",
            total_trades=5,
            winning_trades=3,
            total_pnl=25000,
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_date_in_blocks(self):
        """Date appears somewhere in rendered blocks."""
        result = format_daily_summary(
            date="2026-02-22",
            total_trades=5,
            winning_trades=3,
            total_pnl=25000,
        )
        text = _all_text(result)
        assert "2026-02-22" in text or "2026" in text

    def test_total_trades_in_blocks(self):
        """Total trades count appears in rendered blocks."""
        result = format_daily_summary(
            date="2026-02-22",
            total_trades=5,
            winning_trades=3,
            total_pnl=25000,
        )
        text = _all_text(result)
        assert "5" in text

    def test_winning_trades_in_blocks(self):
        """Winning trades count appears in rendered blocks."""
        result = format_daily_summary(
            date="2026-02-22",
            total_trades=5,
            winning_trades=3,
            total_pnl=25000,
        )
        text = _all_text(result)
        assert "3" in text

    def test_total_pnl_in_blocks(self):
        """Total PnL appears in rendered blocks."""
        result = format_daily_summary(
            date="2026-02-22",
            total_trades=5,
            winning_trades=3,
            total_pnl=25000,
        )
        text = _all_text(result)
        assert "25000" in text or "25,000" in text

    def test_zero_trades_does_not_crash(self):
        """Zero trades day renders without error."""
        result = format_daily_summary(
            date="2026-02-22",
            total_trades=0,
            winning_trades=0,
            total_pnl=0,
        )
        assert isinstance(result, list)

    def test_accepts_extra_kwargs(self):
        """Extra keyword arguments are silently accepted."""
        result = format_daily_summary(
            date="2026-02-22",
            total_trades=2,
            winning_trades=1,
            total_pnl=5000,
            losing_trades=1,
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# format_trade_complete
# ---------------------------------------------------------------------------

class TestFormatTradeComplete:
    """Tests for format_trade_complete (standalone pipeline version)."""

    def test_returns_list_of_dicts(self):
        """Return value is a non-empty list of dicts."""
        result = format_trade_complete(
            symbol="005930",
            entry_price=70000,
            exit_price=77000,
            pnl=70000,
            holding_days=10,
            return_pct=10.0,
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_symbol_in_blocks(self):
        """Symbol appears in rendered blocks."""
        result = format_trade_complete(
            symbol="005930",
            entry_price=70000,
            exit_price=77000,
            pnl=70000,
            holding_days=10,
            return_pct=10.0,
        )
        text = _all_text(result)
        assert "005930" in text

    def test_entry_and_exit_price_in_blocks(self):
        """Entry and exit prices appear in rendered blocks."""
        result = format_trade_complete(
            symbol="005930",
            entry_price=70000,
            exit_price=77000,
            pnl=70000,
            holding_days=10,
            return_pct=10.0,
        )
        text = _all_text(result)
        assert "70000" in text or "70,000" in text
        assert "77000" in text or "77,000" in text

    def test_pnl_in_blocks(self):
        """PnL value appears in rendered blocks."""
        result = format_trade_complete(
            symbol="005930",
            entry_price=70000,
            exit_price=77000,
            pnl=70000,
            holding_days=10,
            return_pct=10.0,
        )
        text = _all_text(result)
        assert "70000" in text or "70,000" in text

    def test_holding_days_in_blocks(self):
        """Holding days appears in rendered blocks."""
        result = format_trade_complete(
            symbol="005930",
            entry_price=70000,
            exit_price=77000,
            pnl=70000,
            holding_days=10,
            return_pct=10.0,
        )
        text = _all_text(result)
        assert "10" in text

    def test_return_pct_in_blocks(self):
        """Return percentage appears in rendered blocks."""
        result = format_trade_complete(
            symbol="005930",
            entry_price=70000,
            exit_price=77000,
            pnl=70000,
            holding_days=10,
            return_pct=10.0,
        )
        text = _all_text(result)
        assert "10" in text

    def test_accepts_extra_kwargs(self):
        """Extra keyword arguments are silently accepted."""
        result = format_trade_complete(
            symbol="005930",
            entry_price=70000,
            exit_price=63000,
            pnl=-7000,
            holding_days=5,
            return_pct=-10.0,
            broker_order_id="ORD123",
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# dispatch_pipeline_event
# ---------------------------------------------------------------------------

class TestDispatchPipelineEvent:
    """Tests for dispatch_pipeline_event routing."""

    def test_routes_state_change(self):
        """dispatch_pipeline_event routes 'state_change' to correct formatter."""
        result = dispatch_pipeline_event(
            "state_change",
            symbol="005930",
            from_state="IDLE",
            to_state="SCREENING",
            reason="start",
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_routes_buy_decision(self):
        """dispatch_pipeline_event routes 'buy_decision' to correct formatter."""
        result = dispatch_pipeline_event(
            "buy_decision",
            symbol="005930",
            price=70000,
            quantity=10,
            order_type="LIMIT",
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_routes_sell_trigger(self):
        """dispatch_pipeline_event routes 'sell_trigger' to correct formatter."""
        result = dispatch_pipeline_event(
            "sell_trigger",
            symbol="005930",
            reason="stop_loss",
            price=63000,
            pnl=-7000,
            return_pct=-10.0,
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_routes_trade_complete(self):
        """dispatch_pipeline_event routes 'trade_complete' to correct formatter."""
        result = dispatch_pipeline_event(
            "trade_complete",
            symbol="005930",
            entry_price=70000,
            exit_price=77000,
            pnl=70000,
            holding_days=10,
            return_pct=10.0,
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_routes_error(self):
        """dispatch_pipeline_event routes 'error' to correct formatter."""
        result = dispatch_pipeline_event(
            "error",
            symbol="005930",
            error_type="RuntimeError",
            error_message="crash",
            state="SCREENING",
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_routes_daily_summary(self):
        """dispatch_pipeline_event routes 'daily_summary' to correct formatter."""
        result = dispatch_pipeline_event(
            "daily_summary",
            date="2026-02-22",
            total_trades=5,
            winning_trades=3,
            total_pnl=25000,
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_unknown_event_type_returns_list(self):
        """dispatch_pipeline_event returns a list for unknown event types."""
        result = dispatch_pipeline_event("unknown_event", symbol="005930")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# dispatch_consensus_event
# ---------------------------------------------------------------------------

class TestDispatchConsensusEvent:
    """Tests for dispatch_consensus_event routing."""

    def test_routes_consensus_result(self):
        """dispatch_consensus_event routes 'consensus_result' to correct formatter."""
        result = dispatch_consensus_event(
            "consensus_result",
            symbol="005930",
            passed=True,
            buy_count=3,
            total_count=4,
            avg_conviction=0.82,
            categories={"value": 2},
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_routes_consensus_passed(self):
        """dispatch_consensus_event routes passing consensus events."""
        result = dispatch_consensus_event(
            "consensus_passed",
            symbol="005930",
            passed=True,
            buy_count=3,
            total_count=4,
            avg_conviction=0.8,
            categories={},
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_routes_consensus_rejected(self):
        """dispatch_consensus_event routes rejected consensus events."""
        result = dispatch_consensus_event(
            "consensus_rejected",
            symbol="000660",
            passed=False,
            buy_count=1,
            total_count=4,
            avg_conviction=0.3,
            categories={},
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_symbol_present_in_result(self):
        """Symbol is present in the formatted blocks for consensus events."""
        result = dispatch_consensus_event(
            "consensus_result",
            symbol="035420",
            passed=True,
            buy_count=3,
            total_count=4,
            avg_conviction=0.8,
            categories={},
        )
        text = _all_text(result)
        assert "035420" in text

    def test_unknown_consensus_event_returns_list(self):
        """dispatch_consensus_event returns a list for unknown event types."""
        result = dispatch_consensus_event("consensus_unknown", symbol="005930")
        assert isinstance(result, list)
