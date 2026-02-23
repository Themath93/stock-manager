"""Unit tests for pipeline Slack channel routing in SlackConfig and CHANNEL_MAP.

Tests:
  - SlackConfig has 5 pipeline-specific channel fields
  - CHANNEL_MAP routes event types to the correct channel field names
  - get_channel_for_event returns the correct channel string
  - Unknown event types fall back to default_channel
"""


from stock_manager.notifications.config import CHANNEL_MAP, SlackConfig


# ---------------------------------------------------------------------------
# SlackConfig pipeline channel fields
# ---------------------------------------------------------------------------

class TestSlackConfigPipelineChannels:
    """SlackConfig must expose the 5 pipeline-specific channel fields."""

    def test_has_analysis_channel_field(self):
        """SlackConfig has an analysis_channel field."""
        config = SlackConfig(_env_file=None)
        assert hasattr(config, "analysis_channel")

    def test_has_orders_channel_field(self):
        """SlackConfig has an orders_channel field."""
        config = SlackConfig(_env_file=None)
        assert hasattr(config, "orders_channel")

    def test_has_positions_channel_field(self):
        """SlackConfig has a positions_channel field."""
        config = SlackConfig(_env_file=None)
        assert hasattr(config, "positions_channel")

    def test_has_alerts_channel_field(self):
        """SlackConfig has an alerts_channel field."""
        config = SlackConfig(_env_file=None)
        assert hasattr(config, "alerts_channel")

    def test_has_results_channel_field(self):
        """SlackConfig has a results_channel field."""
        config = SlackConfig(_env_file=None)
        assert hasattr(config, "results_channel")

    def test_pipeline_channels_default_to_empty_string(self):
        """All 5 pipeline channel fields default to empty string."""
        config = SlackConfig(_env_file=None)
        assert config.analysis_channel == ""
        assert config.orders_channel == ""
        assert config.positions_channel == ""
        assert config.alerts_channel == ""
        assert config.results_channel == ""

    def test_pipeline_channels_loaded_from_env(self, monkeypatch):
        """Pipeline channel fields load from SLACK_*_CHANNEL environment variables."""
        monkeypatch.setenv("SLACK_ANALYSIS_CHANNEL", "#trading-analysis")
        monkeypatch.setenv("SLACK_ORDERS_CHANNEL", "#trading-orders")
        monkeypatch.setenv("SLACK_POSITIONS_CHANNEL", "#trading-positions")
        monkeypatch.setenv("SLACK_ALERTS_CHANNEL", "#trading-alerts")
        monkeypatch.setenv("SLACK_RESULTS_CHANNEL", "#trading-results")

        config = SlackConfig(_env_file=None)
        assert config.analysis_channel == "#trading-analysis"
        assert config.orders_channel == "#trading-orders"
        assert config.positions_channel == "#trading-positions"
        assert config.alerts_channel == "#trading-alerts"
        assert config.results_channel == "#trading-results"

    def test_has_exactly_five_pipeline_channel_fields(self):
        """SlackConfig has exactly the 5 expected pipeline channel fields."""
        pipeline_fields = {
            "analysis_channel",
            "orders_channel",
            "positions_channel",
            "alerts_channel",
            "results_channel",
        }
        config = SlackConfig(_env_file=None)
        for field in pipeline_fields:
            assert hasattr(config, field), f"Missing field: {field}"


# ---------------------------------------------------------------------------
# CHANNEL_MAP structure
# ---------------------------------------------------------------------------

class TestChannelMap:
    """Tests for the CHANNEL_MAP dict that maps event types to field names."""

    def test_channel_map_is_dict(self):
        """CHANNEL_MAP is a dict."""
        assert isinstance(CHANNEL_MAP, dict)

    def test_analysis_events_map_to_analysis_channel(self):
        """Screening and consensus analysis events route to analysis_channel."""
        assert CHANNEL_MAP["screening_complete"] == "analysis_channel"
        assert CHANNEL_MAP["agent_vote"] == "analysis_channel"
        assert CHANNEL_MAP["advisory_vote"] == "analysis_channel"
        assert CHANNEL_MAP["consensus_result"] == "analysis_channel"

    def test_order_events_map_to_orders_channel(self):
        """Buy decision and order executed events route to orders_channel."""
        assert CHANNEL_MAP["buy_decision"] == "orders_channel"
        assert CHANNEL_MAP["order_executed"] == "orders_channel"

    def test_position_events_map_to_positions_channel(self):
        """State change and condition check events route to positions_channel."""
        assert CHANNEL_MAP["state_change"] == "positions_channel"
        assert CHANNEL_MAP["condition_check"] == "positions_channel"

    def test_alert_events_map_to_alerts_channel(self):
        """Warning, sell trigger, and error events route to alerts_channel."""
        assert CHANNEL_MAP["condition_warning"] == "alerts_channel"
        assert CHANNEL_MAP["sell_trigger"] == "alerts_channel"
        assert CHANNEL_MAP["error"] == "alerts_channel"

    def test_result_events_map_to_results_channel(self):
        """Trade complete events route to results_channel."""
        assert CHANNEL_MAP["trade_complete"] == "results_channel"

    def test_all_channel_map_values_are_valid_field_names(self):
        """Every value in CHANNEL_MAP is a valid SlackConfig field name."""
        config = SlackConfig(_env_file=None)
        for event_type, field_name in CHANNEL_MAP.items():
            assert hasattr(config, field_name), (
                f"CHANNEL_MAP['{event_type}'] = '{field_name}' is not a SlackConfig field"
            )


# ---------------------------------------------------------------------------
# get_channel_for_event
# ---------------------------------------------------------------------------

class TestGetChannelForEvent:
    """Tests for SlackConfig.get_channel_for_event method."""

    def test_returns_analysis_channel_for_screening_complete(self, monkeypatch):
        """screening_complete routes to analysis_channel value."""
        monkeypatch.setenv("SLACK_ANALYSIS_CHANNEL", "#trading-analysis")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("screening_complete") == "#trading-analysis"

    def test_returns_analysis_channel_for_consensus_result(self, monkeypatch):
        """consensus_result routes to analysis_channel value."""
        monkeypatch.setenv("SLACK_ANALYSIS_CHANNEL", "#trading-analysis")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("consensus_result") == "#trading-analysis"

    def test_returns_orders_channel_for_buy_decision(self, monkeypatch):
        """buy_decision routes to orders_channel value."""
        monkeypatch.setenv("SLACK_ORDERS_CHANNEL", "#trading-orders")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("buy_decision") == "#trading-orders"

    def test_returns_orders_channel_for_order_executed(self, monkeypatch):
        """order_executed routes to orders_channel value."""
        monkeypatch.setenv("SLACK_ORDERS_CHANNEL", "#trading-orders")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("order_executed") == "#trading-orders"

    def test_returns_positions_channel_for_state_change(self, monkeypatch):
        """state_change routes to positions_channel value."""
        monkeypatch.setenv("SLACK_POSITIONS_CHANNEL", "#trading-positions")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("state_change") == "#trading-positions"

    def test_returns_alerts_channel_for_condition_warning(self, monkeypatch):
        """condition_warning routes to alerts_channel value."""
        monkeypatch.setenv("SLACK_ALERTS_CHANNEL", "#trading-alerts")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("condition_warning") == "#trading-alerts"

    def test_returns_alerts_channel_for_sell_trigger(self, monkeypatch):
        """sell_trigger routes to alerts_channel value."""
        monkeypatch.setenv("SLACK_ALERTS_CHANNEL", "#trading-alerts")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("sell_trigger") == "#trading-alerts"

    def test_returns_alerts_channel_for_error(self, monkeypatch):
        """error event routes to alerts_channel value."""
        monkeypatch.setenv("SLACK_ALERTS_CHANNEL", "#trading-alerts")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("error") == "#trading-alerts"

    def test_returns_results_channel_for_trade_complete(self, monkeypatch):
        """trade_complete routes to results_channel value."""
        monkeypatch.setenv("SLACK_RESULTS_CHANNEL", "#trading-results")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("trade_complete") == "#trading-results"

    def test_unknown_event_falls_back_to_default_channel(self, monkeypatch):
        """Unknown event type returns default_channel value."""
        monkeypatch.setenv("SLACK_DEFAULT_CHANNEL", "#trading-general")
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("unknown_event_type") == "#trading-general"

    def test_unknown_event_returns_empty_when_no_default(self):
        """Unknown event with no default channel configured returns empty string."""
        config = SlackConfig(_env_file=None)
        result = config.get_channel_for_event("completely_unknown")
        assert result == ""

    def test_empty_channel_field_falls_back_to_default(self, monkeypatch):
        """When the mapped channel field is empty, falls back to default_channel."""
        # Set default but not the specific pipeline channel
        monkeypatch.setenv("SLACK_DEFAULT_CHANNEL", "#fallback")
        # analysis_channel not set, so screening_complete should fall back
        config = SlackConfig(_env_file=None)
        assert config.get_channel_for_event("screening_complete") == "#fallback"

    def test_all_mapped_event_types_resolve(self, monkeypatch):
        """Every event type in CHANNEL_MAP resolves without error."""
        monkeypatch.setenv("SLACK_ANALYSIS_CHANNEL", "#analysis")
        monkeypatch.setenv("SLACK_ORDERS_CHANNEL", "#orders")
        monkeypatch.setenv("SLACK_POSITIONS_CHANNEL", "#positions")
        monkeypatch.setenv("SLACK_ALERTS_CHANNEL", "#alerts")
        monkeypatch.setenv("SLACK_RESULTS_CHANNEL", "#results")

        config = SlackConfig(_env_file=None)
        for event_type in CHANNEL_MAP:
            result = config.get_channel_for_event(event_type)
            assert isinstance(result, str)
            assert len(result) > 0, f"Event '{event_type}' resolved to empty channel"

    def test_returns_string_type_always(self):
        """get_channel_for_event always returns a str, never None."""
        config = SlackConfig(_env_file=None)
        result = config.get_channel_for_event("state_change")
        assert isinstance(result, str)
