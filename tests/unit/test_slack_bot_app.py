from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from stock_manager.slack_bot import app as slack_app
from stock_manager.slack_bot.command_parser import ParsedCommand


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache() -> None:
    slack_app._rate_limit_cache.clear()


def test_get_allowed_user_ids_none_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLACK_ALLOWED_USER_IDS", raising=False)
    assert slack_app._get_allowed_user_ids() is None


def test_get_allowed_user_ids_parses_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_ALLOWED_USER_IDS", "U1, U2 ,U3")
    assert slack_app._get_allowed_user_ids() == {"U1", "U2", "U3"}


def test_check_user_allowed_respects_allow_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_ALLOWED_USER_IDS", "U1,U2")
    assert slack_app._check_user_allowed("U1") is True
    assert slack_app._check_user_allowed("U9") is False


def test_check_rate_limit_blocks_second_immediate_call() -> None:
    assert slack_app._check_rate_limit("U1") is True
    assert slack_app._check_rate_limit("U1") is False


def test_dispatch_command_help_path(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()

    monkeypatch.setattr(
        "stock_manager.slack_bot.command_parser.parse_command",
        lambda _text: ParsedCommand(subcommand="help"),
    )

    slack_app._dispatch_command(
        text="help",
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
    )

    respond.assert_called_once()
    kwargs = respond.call_args.kwargs
    assert kwargs["response_type"] == "ephemeral"


def test_dispatch_command_start_help_path(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()

    monkeypatch.setattr(
        "stock_manager.slack_bot.command_parser.parse_command",
        lambda _text: ParsedCommand(subcommand="start-help"),
    )

    slack_app._dispatch_command(
        text="start help",
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
    )

    respond.assert_called_once()
    kwargs = respond.call_args.kwargs
    assert kwargs["response_type"] == "ephemeral"
    assert "전략" in kwargs["text"]


def test_dispatch_command_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()

    monkeypatch.setattr(
        "stock_manager.slack_bot.command_parser.parse_command",
        lambda _text: ParsedCommand(subcommand="start", error="bad input"),
    )

    slack_app._dispatch_command(
        text="start",
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
    )

    respond.assert_called_once()
    assert "오류" in respond.call_args.kwargs["text"]


def test_dispatch_command_unknown_subcommand(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()

    monkeypatch.setattr(
        "stock_manager.slack_bot.command_parser.parse_command",
        lambda _text: ParsedCommand(subcommand="unknown"),
    )

    slack_app._dispatch_command(
        text="unknown",
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
    )

    respond.assert_called_once()
    assert "알 수 없는 명령어" in str(respond.call_args.kwargs)


def test_handle_start_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    cmd = ParsedCommand(subcommand="start")

    monkeypatch.setattr(slack_app, "_check_rate_limit", lambda _user_id: False)

    slack_app._handle_start(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_started=lambda payload: {"text": str(payload), "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    session_manager.start_session.assert_not_called()


def test_handle_start_handles_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.start_session.side_effect = RuntimeError("already running")
    cmd = ParsedCommand(subcommand="start", is_mock=True)

    monkeypatch.setattr(slack_app, "_check_rate_limit", lambda _user_id: True)

    slack_app._handle_start(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_started=lambda payload: {"text": str(payload), "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    assert "already running" in respond.call_args.kwargs["text"]


def test_handle_start_success(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    captured_payload: dict[str, object] = {}
    cmd = ParsedCommand(
        subcommand="start",
        strategy="consensus",
        symbols=("005930", "000660"),
        duration_sec=120,
        is_mock=False,
        order_quantity=2,
        run_interval_sec=15.0,
        llm_mode="off",
    )

    monkeypatch.setattr(slack_app, "_check_rate_limit", lambda _user_id: True)

    def _format_started(payload: dict[str, object]) -> dict[str, object]:
        captured_payload.update(payload)
        return {"text": str(payload), "blocks": []}

    slack_app._handle_start(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_started=_format_started,
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    session_manager.start_session.assert_called_once()
    params = session_manager.start_session.call_args.args[0]
    assert params.strategy_auto_discover is False
    assert params.strategy_discovery_limit == 20
    assert params.strategy_discovery_fallback_symbols == ()
    assert params.llm_mode == "off"
    respond.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "in_channel"
    assert captured_payload["mode"] == "LIVE"
    assert captured_payload["symbols"] == "005930, 000660"
    assert captured_payload["llm_mode"] == "off"


def test_handle_start_auto_discover_updates_symbols_display(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    captured_payload: dict[str, object] = {}
    cmd = ParsedCommand(
        subcommand="start",
        strategy="consensus",
        symbols=(),
        is_mock=True,
        strategy_auto_discover=True,
        strategy_discovery_limit=7,
        strategy_discovery_fallback_symbols=("005930", "000660"),
        llm_mode="selective",
    )

    monkeypatch.setattr(slack_app, "_check_rate_limit", lambda _user_id: True)

    def _format_started(payload: dict[str, object]) -> dict[str, object]:
        captured_payload.update(payload)
        return {"text": str(payload), "blocks": []}

    slack_app._handle_start(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_started=_format_started,
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    session_manager.start_session.assert_called_once()
    params = session_manager.start_session.call_args.args[0]
    assert params.strategy_auto_discover is True
    assert params.strategy_discovery_limit == 7
    assert params.strategy_discovery_fallback_symbols == ("005930", "000660")
    assert params.llm_mode == "selective"
    assert "자동 탐색 (limit=7, fallback=005930, 000660)" == captured_payload["symbols"]
    assert captured_payload["llm_mode"] == "selective"


def test_handle_start_no_symbols_auto_discover_off_display(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    captured_payload: dict[str, object] = {}
    cmd = ParsedCommand(
        subcommand="start",
        strategy="consensus",
        symbols=(),
        is_mock=True,
        strategy_auto_discover=False,
    )

    monkeypatch.setattr(slack_app, "_check_rate_limit", lambda _user_id: True)

    def _format_started(payload: dict[str, object]) -> dict[str, object]:
        captured_payload.update(payload)
        return {"text": str(payload), "blocks": []}

    slack_app._handle_start(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_started=_format_started,
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    assert captured_payload["symbols"] == "미지정 (자동 탐색 OFF)"


def test_handle_start_mode_defaults_to_env_when_is_mock_unspecified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    captured_payload: dict[str, object] = {}
    cmd = ParsedCommand(subcommand="start", is_mock=None)

    monkeypatch.setattr(slack_app, "_check_rate_limit", lambda _user_id: True)

    def _format_started(payload: dict[str, object]) -> dict[str, object]:
        captured_payload.update(payload)
        return {"text": str(payload), "blocks": []}

    monkeypatch.setattr("stock_manager.adapters.broker.kis.config.KISConfig", lambda: SimpleNamespace(use_mock=False))

    slack_app._handle_start(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_started=_format_started,
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    session_manager.start_session.assert_called_once()
    assert captured_payload["mode"] == "LIVE"


def test_handle_stop_paths() -> None:
    respond = MagicMock()

    stopped_manager = MagicMock()
    stopped_manager.is_running = False
    slack_app._handle_stop(
        respond=respond,
        session_manager=stopped_manager,
        format_stopped=lambda payload: {"text": str(payload), "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )
    assert "활성 트레이딩 세션이 없습니다" in respond.call_args.kwargs["text"]

    respond.reset_mock()
    running_manager = MagicMock()
    running_manager.is_running = True
    running_manager.get_session_info.return_value = {"state": "STOPPED"}
    slack_app._handle_stop(
        respond=respond,
        session_manager=running_manager,
        format_stopped=lambda payload: {"text": str(payload), "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )
    running_manager.stop_session.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "in_channel"


def test_handle_status_calls_formatter() -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.get_status.return_value = {"status": "ok"}
    session_manager.get_session_info.return_value = {"state": "RUNNING"}

    slack_app._handle_status(
        respond=respond,
        session_manager=session_manager,
        format_status=lambda status, info: {"text": f"{status}:{info}", "blocks": []},
    )

    respond.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "ephemeral"


def test_handle_config_uses_slack_config(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.get_session_info.return_value = {"state": "RUNNING"}

    fake_config = SimpleNamespace(enabled=True, default_channel="#alerts")
    monkeypatch.setattr("stock_manager.notifications.config.SlackConfig", lambda: fake_config)

    slack_app._handle_config(
        respond=respond,
        session_manager=session_manager,
        format_config=lambda payload: {"text": str(payload), "blocks": []},
    )

    respond.assert_called_once()
    assert "#alerts" in respond.call_args.kwargs["text"]


def test_create_slack_app_registers_handler_and_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApp:
        def __init__(self, token: str) -> None:
            self.token = token
            self.command_handler = None
            self.error_handler = None

        def command(self, _name: str):
            def decorator(func):
                self.command_handler = func
                return func

            return decorator

        def error(self, func):
            self.error_handler = func
            return func

    fake_slack_module = SimpleNamespace(App=FakeApp)
    monkeypatch.setitem(sys.modules, "slack_bolt", fake_slack_module)

    fake_config = SimpleNamespace(bot_token=SimpleNamespace(get_secret_value=lambda: "xoxb-token"))
    monkeypatch.setattr("stock_manager.notifications.config.SlackConfig", lambda: fake_config)

    dispatched: list[str] = []

    def fake_dispatch(*, text: str, user_id: str, respond, session_manager) -> None:
        dispatched.append(f"{user_id}:{text}")

    monkeypatch.setattr(slack_app, "_dispatch_command", fake_dispatch)
    monkeypatch.setattr(slack_app, "_check_user_allowed", lambda _uid: True)

    manager = MagicMock()
    app = slack_app.create_slack_app(manager)

    ack = MagicMock()
    respond = MagicMock()
    command = {"user_id": "U1", "text": "status"}
    app.command_handler(ack=ack, respond=respond, command=command, client=MagicMock())

    ack.assert_called_once()
    assert dispatched == ["U1:status"]

    err_logger = MagicMock()
    app.error_handler(RuntimeError("boom"), {}, err_logger)
    err_logger.error.assert_called_once()


def test_create_slack_app_handles_unauthorized_user(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApp:
        def __init__(self, token: str) -> None:
            self.command_handler = None

        def command(self, _name: str):
            def decorator(func):
                self.command_handler = func
                return func

            return decorator

        def error(self, func):
            return func

    monkeypatch.setitem(sys.modules, "slack_bolt", SimpleNamespace(App=FakeApp))
    monkeypatch.setattr(
        "stock_manager.notifications.config.SlackConfig",
        lambda: SimpleNamespace(bot_token=SimpleNamespace(get_secret_value=lambda: "xoxb-token")),
    )
    monkeypatch.setattr(slack_app, "_check_user_allowed", lambda _uid: False)

    app = slack_app.create_slack_app(MagicMock())
    ack = MagicMock()
    respond = MagicMock()
    app.command_handler(
        ack=ack,
        respond=respond,
        command={"user_id": "U9", "text": "status"},
        client=MagicMock(),
    )

    ack.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "ephemeral"


def test_handle_config_includes_trading_params(monkeypatch: pytest.MonkeyPatch) -> None:
    """_handle_config passes trading params from session_info to format_config."""
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.get_session_info.return_value = {
        "state": "RUNNING",
        "params": {
            "strategy": "consensus",
            "symbols": ["005930"],
            "mode": "MOCK",
            "order_quantity": 5,
            "run_interval_sec": 15.0,
            "strategy_auto_discover": True,
            "strategy_discovery_limit": 7,
            "strategy_discovery_fallback_symbols": ["005930", "000660"],
            "llm_mode": "selective",
        },
    }

    fake_config = SimpleNamespace(enabled=True, default_channel="#alerts")
    monkeypatch.setattr("stock_manager.notifications.config.SlackConfig", lambda: fake_config)

    captured = {}

    def capture_config(payload):
        captured.update(payload)
        return {"text": str(payload), "blocks": []}

    slack_app._handle_config(
        respond=respond,
        session_manager=session_manager,
        format_config=capture_config,
    )

    assert captured["strategy"] == "consensus"
    assert captured["symbols"] == ["005930"]
    assert captured["mode"] == "MOCK"
    assert captured["order_quantity"] == 5
    assert captured["strategy_auto_discover"] is True
    assert captured["strategy_discovery_limit"] == 7
    assert captured["strategy_discovery_fallback_symbols"] == ["005930", "000660"]
    assert captured["llm_mode"] == "selective"


def test_handle_config_derives_mode_from_is_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.get_session_info.return_value = {
        "state": "RUNNING",
        "params": {
            "strategy": "consensus",
            "symbols": ["005930"],
            "is_mock": True,
        },
    }

    fake_config = SimpleNamespace(enabled=True, default_channel="#alerts")
    monkeypatch.setattr("stock_manager.notifications.config.SlackConfig", lambda: fake_config)

    captured: dict[str, object] = {}

    def capture_config(payload):
        captured.update(payload)
        return {"text": str(payload), "blocks": []}

    slack_app._handle_config(
        respond=respond,
        session_manager=session_manager,
        format_config=capture_config,
    )

    assert captured["mode"] == "MOCK"


# --- balance tests ---


def test_handle_balance_requires_session() -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = False
    session_manager.get_balance.return_value = {"output1": [], "output2": []}

    slack_app._handle_balance(
        respond=respond,
        session_manager=session_manager,
        format_balance=lambda d: {"text": str(d), "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "ephemeral"
    session_manager.get_balance.assert_called_once()


def test_handle_balance_returns_ephemeral() -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = True
    session_manager.get_balance.return_value = {"output1": [], "output2": []}

    slack_app._handle_balance(
        respond=respond,
        session_manager=session_manager,
        format_balance=lambda d: {"text": "ok", "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "ephemeral"


# --- orders tests ---


def test_handle_orders_requires_session() -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = False
    session_manager.get_daily_orders.return_value = {"output1": []}

    slack_app._handle_orders(
        respond=respond,
        session_manager=session_manager,
        format_orders=lambda d: {"text": str(d), "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "ephemeral"
    session_manager.get_daily_orders.assert_called_once()


def test_handle_orders_returns_ephemeral() -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = True
    session_manager.get_daily_orders.return_value = {"output1": []}

    slack_app._handle_orders(
        respond=respond,
        session_manager=session_manager,
        format_orders=lambda d: {"text": "ok", "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "ephemeral"


# --- sell-all tests ---


def test_handle_sell_all_requires_session() -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = False
    cmd = ParsedCommand(subcommand="sell-all")

    slack_app._handle_sell_all(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_sell_all_preview=lambda d: {"text": str(d), "blocks": []},
        format_sell_all_result=lambda d: {"text": str(d), "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    assert "활성 트레이딩 세션이 없습니다" in respond.call_args.kwargs["text"]


def test_handle_sell_all_without_confirm_shows_preview() -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = True
    session_manager.get_positions.return_value = {"005930": {"symbol": "005930", "quantity": 10, "entry_price": 70000, "status": "open"}}
    cmd = ParsedCommand(subcommand="sell-all", confirm=False)

    slack_app._handle_sell_all(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_sell_all_preview=lambda d: {"text": "preview", "blocks": []},
        format_sell_all_result=lambda d: {"text": str(d), "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "ephemeral"
    assert respond.call_args.kwargs["text"] == "preview"
    session_manager.liquidate_all.assert_not_called()


def test_handle_sell_all_with_confirm_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = True
    session_manager.liquidate_all.return_value = [
        {"symbol": "005930", "quantity": 10, "entry_price": 70000, "success": True, "message": "", "broker_order_id": "ORD1"}
    ]
    cmd = ParsedCommand(subcommand="sell-all", confirm=True)

    monkeypatch.setattr(slack_app, "_check_rate_limit", lambda _uid: True)

    slack_app._handle_sell_all(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_sell_all_preview=lambda d: {"text": str(d), "blocks": []},
        format_sell_all_result=lambda d: {"text": "done", "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    assert respond.call_args.kwargs["response_type"] == "in_channel"
    session_manager.liquidate_all.assert_called_once()


def test_handle_sell_all_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = True
    cmd = ParsedCommand(subcommand="sell-all", confirm=True)

    monkeypatch.setattr(slack_app, "_check_rate_limit", lambda _uid: False)

    slack_app._handle_sell_all(
        cmd=cmd,
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
        format_sell_all_preview=lambda d: {"text": str(d), "blocks": []},
        format_sell_all_result=lambda d: {"text": str(d), "blocks": []},
        format_error=lambda msg: {"text": msg, "blocks": []},
    )

    respond.assert_called_once()
    session_manager.liquidate_all.assert_not_called()


# --- dispatch routing tests ---


def test_dispatch_routes_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = True
    session_manager.get_balance.return_value = {"output1": [], "output2": []}

    slack_app._dispatch_command(
        text="balance",
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
    )

    respond.assert_called_once()


def test_dispatch_routes_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = True
    session_manager.get_daily_orders.return_value = {"output1": []}

    slack_app._dispatch_command(
        text="orders",
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
    )

    respond.assert_called_once()


def test_dispatch_routes_sell_all(monkeypatch: pytest.MonkeyPatch) -> None:
    respond = MagicMock()
    session_manager = MagicMock()
    session_manager.is_running = True
    session_manager.get_positions.return_value = {}

    slack_app._dispatch_command(
        text="sell-all",
        user_id="U1",
        respond=respond,
        session_manager=session_manager,
    )

    respond.assert_called_once()
