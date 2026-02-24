"""Unit tests for command_parser module."""
import pytest
from stock_manager.slack_bot.command_parser import parse_command, ParsedCommand


class TestParseCommand:
    def test_empty_text_returns_help(self):
        result = parse_command("")
        assert result.subcommand == "help"
        assert result.error is None

    def test_whitespace_only_returns_help(self):
        result = parse_command("   ")
        assert result.subcommand == "help"

    def test_start_no_args(self):
        result = parse_command("start")
        assert result.subcommand == "start"
        assert result.strategy is None
        assert result.symbols == ()
        assert result.error is None

    def test_start_with_strategy(self):
        result = parse_command("start --strategy consensus")
        assert result.subcommand == "start"
        assert result.strategy == "consensus"

    def test_start_with_symbols_uppercased(self):
        result = parse_command("start --symbols 005930,000660,035420")
        assert result.symbols == ("005930", "000660", "035420")

    def test_start_with_symbols_whitespace_quoted(self):
        # Spaces around commas require quoting; shlex splits on whitespace otherwise
        result = parse_command('start --symbols "005930, 000660"')
        assert result.symbols == ("005930", "000660")

    def test_start_with_symbols_unquoted_space_is_error(self):
        # Without quotes, "000660" becomes an unknown flag token
        result = parse_command("start --symbols 005930, 000660")
        assert result.error is not None

    def test_start_with_duration(self):
        result = parse_command("start --duration 3600")
        assert result.duration_sec == 3600

    def test_start_mock_flag(self):
        result = parse_command("start --mock")
        assert result.is_mock is True

    def test_start_no_mock_flag(self):
        result = parse_command("start --no-mock")
        assert result.is_mock is False

    def test_start_full_options(self):
        result = parse_command(
            "start --strategy consensus --symbols 005930,000660 --duration 7200 --mock"
        )
        assert result.subcommand == "start"
        assert result.strategy == "consensus"
        assert result.symbols == ("005930", "000660")
        assert result.duration_sec == 7200
        assert result.is_mock is True
        assert result.error is None

    def test_stop(self):
        result = parse_command("stop")
        assert result.subcommand == "stop"
        assert result.error is None

    def test_status(self):
        result = parse_command("status")
        assert result.subcommand == "status"
        assert result.error is None

    def test_config(self):
        result = parse_command("config")
        assert result.subcommand == "config"
        assert result.error is None

    def test_help_explicit(self):
        result = parse_command("help")
        assert result.subcommand == "help"
        assert result.error is None

    def test_unknown_subcommand(self):
        result = parse_command("unknown")
        assert result.subcommand == "unknown"
        assert result.error is not None
        assert "unknown" in result.error.lower()

    def test_unknown_flag(self):
        result = parse_command("start --invalid-flag")
        assert result.error is not None

    def test_strategy_missing_value(self):
        result = parse_command("start --strategy")
        assert result.error is not None

    def test_duration_invalid(self):
        result = parse_command("start --duration abc")
        assert result.error is not None

    def test_case_insensitive_subcommand(self):
        result = parse_command("START")
        assert result.subcommand == "start"

    def test_order_quantity_parsed(self):
        result = parse_command("start --order-quantity 5")
        assert result.order_quantity == 5
        assert result.error is None

    def test_order_quantity_invalid(self):
        result = parse_command("start --order-quantity xyz")
        assert result.error is not None

    def test_run_interval_parsed(self):
        result = parse_command("start --run-interval 30.5")
        assert result.run_interval_sec == 30.5
        assert result.error is None

    def test_run_interval_invalid(self):
        result = parse_command("start --run-interval notanumber")
        assert result.error is not None

    def test_default_values(self):
        result = parse_command("start")
        assert result.duration_sec == 0
        assert result.order_quantity == 1
        assert result.run_interval_sec == 60.0
        assert result.is_mock is None

    def test_symbols_missing_value(self):
        result = parse_command("start --symbols")
        assert result.error is not None

    def test_duration_missing_value(self):
        result = parse_command("start --duration")
        assert result.error is not None
