"""Unit tests for Block Kit formatters."""

from stock_manager.slack_bot.formatters import (
    format_started,
    format_stopped,
    format_status,
    format_config,
    format_error,
    format_help,
    format_start_help,
    format_balance,
    format_orders,
    format_sell_all_preview,
    format_sell_all_result,
    _format_uptime,
    _format_currency,
)


class TestFormatUptime:
    def test_seconds_only(self):
        assert _format_uptime(45) == "45s"

    def test_zero_seconds(self):
        assert _format_uptime(0) == "0s"

    def test_minutes_and_seconds(self):
        result = _format_uptime(90)
        assert "1m" in result
        assert "30s" in result

    def test_hours_minutes_seconds(self):
        result = _format_uptime(3723)  # 1h 2m 3s
        assert "1h" in result
        assert "2m" in result
        assert "3s" in result

    def test_exact_hour(self):
        result = _format_uptime(3600)
        assert "1h" in result
        assert "0s" in result

    def test_exact_minute(self):
        result = _format_uptime(60)
        assert "1m" in result
        assert "0s" in result

    def test_float_truncated(self):
        # Fractional seconds are truncated to int
        result = _format_uptime(61.9)
        assert "1m" in result
        assert "1s" in result


class TestFormatStarted:
    def _base_info(self):
        return {
            "strategy": "consensus",
            "symbols": "005930, 000660",
            "mode": "MOCK",
            "duration": "until stopped",
            "llm_mode": "off",
        }

    def test_returns_text_and_blocks(self):
        result = format_started(self._base_info())
        assert "text" in result
        assert "blocks" in result
        assert isinstance(result["text"], str)
        assert isinstance(result["blocks"], list)
        assert len(result["blocks"]) > 0

    def test_text_contains_started(self):
        result = format_started(self._base_info())
        assert "시작" in result["text"]

    def test_strategy_in_blocks(self):
        result = format_started(self._base_info())
        blocks_text = str(result["blocks"])
        assert "consensus" in blocks_text

    def test_mode_in_blocks(self):
        result = format_started(self._base_info())
        blocks_text = str(result["blocks"])
        assert "모의투자" in blocks_text

    def test_symbols_list_joined(self):
        info = {"strategy": "s", "symbols": ["005930", "000660"], "mode": "MOCK", "duration": "1h"}
        result = format_started(info)
        blocks_text = str(result["blocks"])
        assert "005930" in blocks_text

    def test_missing_keys_use_defaults(self):
        # Should not raise even with empty dict
        result = format_started({})
        assert "text" in result
        assert "blocks" in result

    def test_llm_mode_included(self):
        result = format_started(
            {
                "strategy": "consensus",
                "symbols": "005930",
                "mode": "MOCK",
                "duration": "1h",
                "llm_mode": "selective",
            }
        )
        output = str(result["blocks"])
        assert "LLM 모드" in output
        assert "selective" in output


class TestFormatError:
    def test_returns_text_and_blocks(self):
        result = format_error("Something went wrong")
        assert "text" in result
        assert "blocks" in result

    def test_text_contains_error_prefix(self):
        result = format_error("Something went wrong")
        assert "오류:" in result["text"]
        assert "Something went wrong" in result["text"]

    def test_x_emoji_in_blocks(self):
        result = format_error("bad thing")
        blocks_text = str(result["blocks"])
        assert ":x:" in blocks_text

    def test_message_in_blocks(self):
        result = format_error("connection timeout")
        blocks_text = str(result["blocks"])
        assert "connection timeout" in blocks_text

    def test_blocks_is_list_with_one_item(self):
        result = format_error("oops")
        assert isinstance(result["blocks"], list)
        assert len(result["blocks"]) == 2


class TestFormatStatus:
    def test_no_session_stopped(self):
        result = format_status(None, {"state": "STOPPED"})
        assert "text" in result
        assert "blocks" in result
        assert isinstance(result["blocks"], list)

    def test_state_in_text(self):
        result = format_status(None, {"state": "RUNNING"})
        assert "RUNNING" in result["text"]

    def test_running_state_in_blocks(self):
        result = format_status(None, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "RUNNING" in output

    def test_with_uptime(self):
        result = format_status(None, {"state": "RUNNING", "uptime_str": "1h 30m 0s"})
        output = str(result["blocks"])
        assert "1h 30m 0s" in output

    def test_with_engine_status(self):
        from unittest.mock import MagicMock

        mock_status = MagicMock()
        mock_status.position_count = 3
        mock_status.price_monitor_running = True
        mock_status.trading_enabled = True
        mock_status.degraded_reason = None

        result = format_status(mock_status, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "3" in output
        assert "활성" in output
        assert "활성" in output

    def test_with_degraded_engine(self):
        from unittest.mock import MagicMock

        mock_status = MagicMock()
        mock_status.position_count = 0
        mock_status.price_monitor_running = False
        mock_status.trading_enabled = False
        mock_status.degraded_reason = "API error"

        result = format_status(mock_status, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "API error" in output

    def test_symbols_list_joined(self):
        result = format_status(None, {"state": "STOPPED", "symbols": ["005930", "000660"]})
        output = str(result["blocks"])
        assert "005930" in output

    def test_missing_keys_use_defaults(self):
        result = format_status(None, {})
        assert "text" in result
        assert "UNKNOWN" in result["text"]


class TestFormatHelp:
    def test_returns_text_and_blocks(self):
        result = format_help()
        assert "text" in result
        assert "blocks" in result

    def test_contains_commands(self):
        result = format_help()
        text = str(result)
        assert "start" in text.lower()
        assert "stop" in text.lower()
        assert "status" in text.lower()

    def test_blocks_has_header_and_section(self):
        result = format_help()
        types = [b["type"] for b in result["blocks"]]
        assert "header" in types
        assert "section" in types

    def test_text_field_is_string(self):
        result = format_help()
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0

    def test_mentions_start_help_command(self):
        result = format_help()
        assert "start help" in str(result["blocks"]).lower()


class TestFormatStopped:
    def test_returns_text_and_blocks(self):
        result = format_stopped({"state": "STOPPED", "uptime_str": "30m 0s"})
        assert "text" in result
        assert "blocks" in result

    def test_stop_in_text(self):
        result = format_stopped({"state": "STOPPED", "uptime_str": "30m 0s"})
        assert "종료" in result["text"]

    def test_uptime_in_blocks(self):
        result = format_stopped({"state": "STOPPED", "uptime_str": "30m 0s"})
        output = str(result["blocks"])
        assert "30m 0s" in output

    def test_missing_keys_use_defaults(self):
        result = format_stopped({})
        assert "text" in result
        assert "blocks" in result


class TestFormatConfig:
    def test_returns_text_and_blocks(self):
        result = format_config({"slack_enabled": True, "default_channel": "#trading"})
        assert "text" in result
        assert "blocks" in result

    def test_config_keys_in_blocks(self):
        result = format_config({"slack_enabled": True, "default_channel": "#trading"})
        output = str(result["blocks"])
        assert "알림 활성" in output
        assert "#trading" in output

    def test_empty_config_shows_no_config_message(self):
        result = format_config({})
        output = str(result["blocks"])
        assert "설정 정보가 없습니다" in output

    def test_text_field_is_string(self):
        result = format_config({"key": "value"})
        assert isinstance(result["text"], str)


class TestFormatHelpUX:
    """Test help redesign with sections and flags."""

    def test_help_has_dividers(self):
        result = format_help()
        types = [b["type"] for b in result["blocks"]]
        assert types.count("divider") >= 2

    def test_help_has_all_flags(self):
        result = format_help()
        all_text = str(result["blocks"])
        for flag in [
            "--strategy",
            "--symbols",
            "--duration",
            "--mock",
            "--no-mock",
            "--order-quantity",
            "--run-interval",
            "--auto-discover",
            "--discovery-limit",
            "--fallback-symbols",
            "--llm-mode",
        ]:
            assert flag in all_text, f"Missing flag: {flag}"

    def test_help_has_examples(self):
        result = format_help()
        all_text = str(result["blocks"])
        assert "예시" in all_text

    def test_help_has_sections(self):
        result = format_help()
        all_text = str(result["blocks"])
        assert "세션 관리" in all_text
        assert "조회" in all_text


class TestFormatStartHelp:
    def test_returns_text_and_blocks(self):
        result = format_start_help()
        assert "text" in result
        assert "blocks" in result

    def test_contains_all_supported_strategies(self):
        result = format_start_help()
        all_text = str(result["blocks"]).lower()
        assert "graham" in all_text
        assert "consensus" in all_text

    def test_contains_example_commands(self):
        result = format_start_help()
        all_text = str(result["blocks"])
        assert "/sm start --strategy graham" in all_text
        assert "/sm start --strategy consensus" in all_text
        assert "--auto-discover" in all_text
        assert "--llm-mode selective" in all_text

    def test_mentions_live_gate_caution(self):
        result = format_start_help()
        assert "promotion gate" in str(result["blocks"]).lower()


class TestFormatStatusUX:
    """Test status redesign with 3-section layout."""

    def test_status_has_state_emoji(self):
        result = format_status(None, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "🟢" in output

    def test_status_stopped_emoji(self):
        result = format_status(None, {"state": "STOPPED"})
        output = str(result["blocks"])
        assert "🔴" in output

    def test_status_reads_nested_params(self):
        """Bug fix: strategy/symbols/mode read from params dict."""
        session_info = {
            "state": "RUNNING",
            "params": {
                "strategy": "consensus",
                "symbols": ["005930"],
                "mode": "MOCK",
                "llm_mode": "selective",
            },
            "uptime_sec": 120,
        }
        result = format_status(None, session_info)
        output = str(result["blocks"])
        assert "consensus" in output
        assert "005930" in output
        assert "LLM 모드" in output
        assert "selective" in output

    def test_status_shows_auto_discovery_when_symbols_empty(self):
        session_info = {
            "state": "RUNNING",
            "params": {
                "strategy": "consensus",
                "symbols": [],
                "is_mock": True,
                "strategy_auto_discover": True,
                "strategy_discovery_limit": 7,
                "strategy_discovery_fallback_symbols": ["005930", "000660"],
            },
            "uptime_sec": 120,
        }
        result = format_status(None, session_info)
        output = str(result["blocks"])
        assert "자동 탐색 (limit=7, fallback=005930, 000660)" in output
        assert "MOCK" in output

    def test_status_with_engine_has_divider(self):
        from unittest.mock import MagicMock
        mock_status = MagicMock()
        mock_status.position_count = 2
        mock_status.price_monitor_running = True
        mock_status.trading_enabled = True
        mock_status.degraded_reason = None
        result = format_status(mock_status, {"state": "RUNNING"})
        types = [b["type"] for b in result["blocks"]]
        assert "divider" in types

    def test_status_degraded_shows_warning(self):
        from unittest.mock import MagicMock
        mock_status = MagicMock()
        mock_status.position_count = 0
        mock_status.price_monitor_running = False
        mock_status.trading_enabled = False
        mock_status.degraded_reason = "startup_recovery_failed"
        result = format_status(mock_status, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "저하 원인" in output
        assert "startup_recovery_failed" in output

    def test_status_with_engine_shows_discovery_runtime_fields(self):
        from unittest.mock import MagicMock

        mock_status = MagicMock()
        mock_status.position_count = 0
        mock_status.price_monitor_running = False
        mock_status.trading_enabled = True
        mock_status.degraded_reason = None
        mock_status.strategy_discovery_source = "mock_fallback"
        mock_status.strategy_discovery_symbols = ("005930", "000660")
        mock_status.strategy_discovery_updated_at = "2026-03-05T15:00:00+00:00"
        mock_status.strategy_discovery_reason = "paper_trading_mode"

        result = format_status(mock_status, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "탐색 소스" in output
        assert "mock_fallback" in output
        assert "탐색 종목" in output
        assert "005930, 000660" in output
        assert "최근 탐색" in output
        assert "탐색 사유" in output
        assert "paper_trading_mode" in output

    def test_status_with_engine_handles_empty_discovery_fields(self):
        from unittest.mock import MagicMock

        mock_status = MagicMock()
        mock_status.position_count = 0
        mock_status.price_monitor_running = False
        mock_status.trading_enabled = True
        mock_status.degraded_reason = None
        mock_status.strategy_discovery_source = None
        mock_status.strategy_discovery_symbols = ()
        mock_status.strategy_discovery_updated_at = None
        mock_status.strategy_discovery_reason = None

        result = format_status(mock_status, {"state": "RUNNING"})
        output = str(result["blocks"])
        assert "탐색 소스" in output
        assert "N/A" in output
        assert "탐색 종목" in output
        assert "(없음)" in output
        assert "탐색 사유" not in output


class TestFormatConfigUX:
    """Test config redesign with trading settings."""

    def test_config_with_trading_params(self):
        config_info = {
            "slack_enabled": True,
            "default_channel": "#trading",
            "session_state": "RUNNING",
            "strategy": "consensus",
            "symbols": ["005930", "000660"],
            "mode": "MOCK",
            "order_quantity": 5,
            "run_interval_sec": 15.0,
            "strategy_auto_discover": True,
            "strategy_discovery_limit": 7,
            "strategy_discovery_fallback_symbols": ["005930", "000660"],
            "llm_mode": "selective",
        }
        result = format_config(config_info)
        output = str(result["blocks"])
        assert "전략" in output
        assert "consensus" in output
        assert "주문 수량" in output
        assert "자동탐색" in output
        assert "탐색 limit" in output
        assert "fallback 종목" in output
        assert "LLM 모드" in output
        assert "selective" in output
        types = [b["type"] for b in result["blocks"]]
        assert "divider" in types

    def test_config_without_trading_params(self):
        config_info = {
            "slack_enabled": True,
            "default_channel": "#alerts",
            "session_state": "STOPPED",
        }
        result = format_config(config_info)
        types = [b["type"] for b in result["blocks"]]
        assert "divider" not in types


class TestFormatStartedMode:
    """Test started mode emoji."""

    def test_mock_mode_shows_emoji(self):
        result = format_started({"strategy": "s", "symbols": "005930", "mode": "MOCK", "duration": "1h"})
        output = str(result["blocks"])
        assert "🧪" in output
        assert "모의투자" in output

    def test_live_mode_shows_emoji(self):
        result = format_started({"strategy": "s", "symbols": "005930", "mode": "LIVE", "duration": "1h"})
        output = str(result["blocks"])
        assert "🔴" in output
        assert "실전투자" in output


class TestFormatErrorHint:
    """Test error message help hint."""

    def test_error_has_help_hint(self):
        result = format_error("test error")
        all_text = str(result["blocks"])
        assert "/sm help" in all_text
        assert "사용법" in all_text


class TestFormatCurrency:
    def test_integer_string(self):
        assert _format_currency("70000") == "70,000원"

    def test_decimal_string(self):
        assert _format_currency("70000.50") == "70,000원"

    def test_zero(self):
        assert _format_currency("0") == "0원"

    def test_invalid_fallback(self):
        assert _format_currency("N/A") == "N/A원"


class TestFormatBalance:
    def _sample_data(self):
        return {
            "output1": [
                {
                    "prdt_name": "삼성전자",
                    "pdno": "005930",
                    "hldg_qty": "10",
                    "pchs_avg_pric": "70000.00",
                    "prpr": "72000",
                    "evlu_pfls_amt": "20000",
                    "evlu_pfls_rt": "2.86",
                }
            ],
            "output2": [
                {
                    "dnca_tot_amt": "1000000",
                    "tot_evlu_amt": "1720000",
                    "nass_amt": "1720000",
                    "pchs_amt_smtl_amt": "700000",
                }
            ],
        }

    def test_returns_text_and_blocks(self):
        result = format_balance(self._sample_data())
        assert "text" in result
        assert "blocks" in result
        assert isinstance(result["blocks"], list)

    def test_text_contains_balance(self):
        result = format_balance(self._sample_data())
        assert "잔고" in result["text"]

    def test_holdings_displayed(self):
        result = format_balance(self._sample_data())
        output = str(result["blocks"])
        assert "삼성전자" in output
        assert "005930" in output
        assert "10" in output

    def test_summary_fields(self):
        result = format_balance(self._sample_data())
        output = str(result["blocks"])
        assert "예수금" in output
        assert "총평가" in output
        assert "순자산" in output
        assert "총매입" in output

    def test_empty_holdings(self):
        data = {"output1": [], "output2": [{"dnca_tot_amt": "500000", "tot_evlu_amt": "500000", "nass_amt": "500000", "pchs_amt_smtl_amt": "0"}]}
        result = format_balance(data)
        output = str(result["blocks"])
        assert "보유 종목이 없습니다" in output

    def test_empty_data(self):
        result = format_balance({})
        assert "text" in result
        assert "blocks" in result


class TestFormatOrders:
    def _sample_data(self):
        return {
            "output1": [
                {
                    "prdt_name": "삼성전자",
                    "sll_buy_dvsn_cd": "02",
                    "ord_qty": "10",
                    "tot_ccld_qty": "10",
                    "avg_prvs": "70000",
                }
            ]
        }

    def test_returns_text_and_blocks(self):
        result = format_orders(self._sample_data())
        assert "text" in result
        assert "blocks" in result

    def test_text_contains_orders(self):
        result = format_orders(self._sample_data())
        assert "주문" in result["text"]

    def test_order_displayed(self):
        result = format_orders(self._sample_data())
        output = str(result["blocks"])
        assert "삼성전자" in output
        assert "매수" in output

    def test_sell_label(self):
        data = {"output1": [{"prdt_name": "SK하이닉스", "sll_buy_dvsn_cd": "01", "ord_qty": "5", "tot_ccld_qty": "5", "avg_prvs": "150000"}]}
        result = format_orders(data)
        output = str(result["blocks"])
        assert "매도" in output

    def test_empty_orders(self):
        result = format_orders({"output1": []})
        output = str(result["blocks"])
        assert "당일 주문 내역이 없습니다" in output

    def test_has_timestamp_context(self):
        result = format_orders(self._sample_data())
        output = str(result["blocks"])
        assert "조회 시각" in output


class TestFormatSellAllPreview:
    def _sample_positions(self):
        return {
            "005930": {"symbol": "005930", "quantity": 10, "entry_price": 70000, "status": "open"},
            "000660": {"symbol": "000660", "quantity": 5, "entry_price": 150000, "status": "open_reconciled"},
        }

    def test_returns_text_and_blocks(self):
        result = format_sell_all_preview(self._sample_positions())
        assert "text" in result
        assert "blocks" in result

    def test_text_contains_preview(self):
        result = format_sell_all_preview(self._sample_positions())
        assert "미리보기" in result["text"]

    def test_positions_displayed(self):
        result = format_sell_all_preview(self._sample_positions())
        output = str(result["blocks"])
        assert "005930" in output
        assert "000660" in output

    def test_confirm_hint(self):
        result = format_sell_all_preview(self._sample_positions())
        output = str(result["blocks"])
        assert "/sm sell-all --confirm" in output

    def test_empty_positions(self):
        result = format_sell_all_preview({})
        output = str(result["blocks"])
        assert "매도할 포지션이 없습니다" in output

    def test_closed_positions_excluded(self):
        positions = {
            "005930": {"symbol": "005930", "quantity": 10, "entry_price": 70000, "status": "closed"},
        }
        result = format_sell_all_preview(positions)
        output = str(result["blocks"])
        assert "매도할 포지션이 없습니다" in output


class TestFormatSellAllResult:
    def _sample_results(self):
        return [
            {"symbol": "005930", "quantity": 10, "entry_price": 70000, "success": True, "message": "", "broker_order_id": "ORD001"},
            {"symbol": "000660", "quantity": 5, "entry_price": 150000, "success": False, "message": "rejected", "broker_order_id": None},
        ]

    def test_returns_text_and_blocks(self):
        result = format_sell_all_result(self._sample_results())
        assert "text" in result
        assert "blocks" in result

    def test_text_contains_complete(self):
        result = format_sell_all_result(self._sample_results())
        assert "완료" in result["text"]

    def test_success_count(self):
        result = format_sell_all_result(self._sample_results())
        output = str(result["blocks"])
        assert "성공 1건" in output
        assert "실패 1건" in output

    def test_success_emoji(self):
        results = [{"symbol": "005930", "quantity": 10, "entry_price": 70000, "success": True, "message": "", "broker_order_id": "ORD001"}]
        result = format_sell_all_result(results)
        output = str(result["blocks"])
        assert ":white_check_mark:" in output

    def test_failure_emoji(self):
        results = [{"symbol": "005930", "quantity": 10, "entry_price": 70000, "success": False, "message": "err", "broker_order_id": None}]
        result = format_sell_all_result(results)
        output = str(result["blocks"])
        assert ":x:" in output

    def test_broker_order_id_shown(self):
        results = [{"symbol": "005930", "quantity": 10, "entry_price": 70000, "success": True, "message": "", "broker_order_id": "ORD999"}]
        result = format_sell_all_result(results)
        output = str(result["blocks"])
        assert "ORD999" in output


class TestFormatHelpNewCommands:
    """Test that help includes balance, orders, sell-all."""

    def test_help_contains_balance(self):
        result = format_help()
        output = str(result["blocks"])
        assert "balance" in output

    def test_help_contains_orders(self):
        result = format_help()
        output = str(result["blocks"])
        assert "orders" in output

    def test_help_contains_sell_all(self):
        result = format_help()
        output = str(result["blocks"])
        assert "sell-all" in output

    def test_help_has_emergency_section(self):
        result = format_help()
        output = str(result["blocks"])
        assert "긴급" in output
