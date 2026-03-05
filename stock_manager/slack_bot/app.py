"""Slack Bolt application factory for /sm slash command."""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

# Rate limiting state: user_id -> last_start_timestamp
_rate_limit_cache: dict[str, float] = {}
_rate_limit_lock = threading.Lock()
_RATE_LIMIT_COOLDOWN_SEC = 10.0


def _get_allowed_user_ids() -> set[str] | None:
    """Return set of allowed user IDs, or None if all users allowed."""
    value = os.environ.get("SLACK_ALLOWED_USER_IDS", "").strip()
    if not value:
        return None
    return {uid.strip() for uid in value.split(",") if uid.strip()}


def _check_user_allowed(user_id: str) -> bool:
    """Return True if user is allowed to use bot."""
    allowed = _get_allowed_user_ids()
    if allowed is None:
        return True
    return user_id in allowed


def _check_rate_limit(user_id: str) -> bool:
    """Return True if user is within rate limit (can proceed)."""
    now = time.monotonic()
    with _rate_limit_lock:
        last = _rate_limit_cache.get(user_id, 0.0)
        if now - last < _RATE_LIMIT_COOLDOWN_SEC:
            return False
        _rate_limit_cache[user_id] = now
        return True


def create_slack_app(session_manager) -> Any:
    """Create and configure Slack Bolt App with /sm command handler.

    Args:
        session_manager: SessionManager instance

    Returns:
        Configured Bolt App instance
    """
    from slack_bolt import App

    # Get bot token from env - SlackConfig handles SLACK_BOT_TOKEN
    from stock_manager.notifications.config import SlackConfig
    slack_config = SlackConfig()

    # Socket Mode: token only, no signing_secret or process_before_response needed
    app = App(
        token=slack_config.bot_token.get_secret_value() if slack_config.bot_token else "",
    )

    @app.command("/sm")
    def handle_sm_command(ack, respond, command, client):
        """Main /sm command handler.

        Pattern: ack() immediately, then dispatch synchronously (respond() has no timeout after ack).
        """
        from stock_manager.slack_bot.formatters import format_error

        # Always ack immediately (Slack 3-second requirement)
        ack()

        user_id = command.get("user_id", "")
        text = (command.get("text") or "").strip()

        # Auth check
        if not _check_user_allowed(user_id):
            respond(
                response_type="ephemeral",
                **format_error("이 봇을 사용할 권한이 없습니다. 관리자에게 문의하세요.")
            )
            return

        # Process synchronously — ack() already sent, no 3s constraint on respond()
        try:
            _dispatch_command(
                text=text,
                user_id=user_id,
                respond=respond,
                session_manager=session_manager,
            )
        except Exception as exc:
            logger.error("Unhandled error in /sm: %s", exc, exc_info=True)
            try:
                respond(response_type="ephemeral", **format_error(f"내부 오류: {exc}"))
            except Exception:
                pass

    @app.error
    def handle_error(error, body, logger):
        logger.error(f"Slack Bolt error: {error}", exc_info=True)

    return app


def _dispatch_command(*, text: str, user_id: str, respond, session_manager) -> None:
    """Dispatch /sm subcommand to appropriate handler."""
    from stock_manager.slack_bot.command_parser import parse_command
    from stock_manager.slack_bot.formatters import (
        format_started, format_stopped, format_status,
        format_config, format_error, format_help,
        format_balance, format_orders,
        format_sell_all_preview, format_sell_all_result,
    )

    cmd = parse_command(text)

    if cmd.error:
        respond(response_type="ephemeral", **format_error(cmd.error))
        return

    if cmd.subcommand == "help" or cmd.subcommand == "":
        respond(response_type="ephemeral", **format_help())
        return

    if cmd.subcommand == "start":
        _handle_start(
            cmd=cmd,
            user_id=user_id,
            respond=respond,
            session_manager=session_manager,
            format_started=format_started,
            format_error=format_error,
        )
    elif cmd.subcommand == "stop":
        _handle_stop(
            respond=respond,
            session_manager=session_manager,
            format_stopped=format_stopped,
            format_error=format_error,
        )
    elif cmd.subcommand == "status":
        _handle_status(
            respond=respond,
            session_manager=session_manager,
            format_status=format_status,
        )
    elif cmd.subcommand == "config":
        _handle_config(
            respond=respond,
            session_manager=session_manager,
            format_config=format_config,
        )
    elif cmd.subcommand == "balance":
        _handle_balance(
            respond=respond,
            session_manager=session_manager,
            format_balance=format_balance,
            format_error=format_error,
        )
    elif cmd.subcommand == "orders":
        _handle_orders(
            respond=respond,
            session_manager=session_manager,
            format_orders=format_orders,
            format_error=format_error,
        )
    elif cmd.subcommand == "sell-all":
        _handle_sell_all(
            cmd=cmd,
            user_id=user_id,
            respond=respond,
            session_manager=session_manager,
            format_sell_all_preview=format_sell_all_preview,
            format_sell_all_result=format_sell_all_result,
            format_error=format_error,
        )
    else:
        respond(response_type="ephemeral", **format_error(f"알 수 없는 명령어: {cmd.subcommand}. /sm help를 입력하세요"))


def _handle_start(*, cmd, user_id, respond, session_manager, format_started, format_error):
    """Handle /sm start command."""
    # Rate limit check
    if not _check_rate_limit(user_id):
        respond(
            response_type="ephemeral",
            **format_error(f"다시 시작하려면 {int(_RATE_LIMIT_COOLDOWN_SEC)}초 후에 시도하세요.")
        )
        return

    from stock_manager.slack_bot.session_manager import SessionParams

    params = SessionParams(
        strategy=cmd.strategy,
        symbols=cmd.symbols,
        duration_sec=cmd.duration_sec,
        is_mock=cmd.is_mock,
        order_quantity=cmd.order_quantity,
        run_interval_sec=cmd.run_interval_sec,
    )

    try:
        session_manager.start_session(params)
    except RuntimeError as e:
        respond(response_type="ephemeral", **format_error(str(e)))
        return
    except ValueError as e:
        respond(response_type="ephemeral", **format_error(f"차단됨: {e}"))
        return
    except Exception as e:
        respond(response_type="ephemeral", **format_error(f"세션 시작 실패: {e}"))
        return

    # Build params_info for formatter
    mode = "MOCK" if (cmd.is_mock is True or (cmd.is_mock is None)) else "LIVE"
    params_info = {
        "strategy": cmd.strategy or "default",
        "symbols": ", ".join(cmd.symbols) if cmd.symbols else "자동 탐색",
        "mode": mode,
        "duration": f"{cmd.duration_sec}s" if cmd.duration_sec > 0 else "수동 종료까지",
    }
    respond(response_type="in_channel", **format_started(params_info))


def _handle_stop(*, respond, session_manager, format_stopped, format_error):
    """Handle /sm stop command."""
    if not session_manager.is_running:
        respond(response_type="ephemeral", **format_error("활성 트레이딩 세션이 없습니다."))
        return

    try:
        session_manager.stop_session()
    except Exception as e:
        respond(response_type="ephemeral", **format_error(f"세션 종료 실패: {e}"))
        return

    session_info = session_manager.get_session_info()
    respond(response_type="in_channel", **format_stopped(session_info))


def _handle_status(*, respond, session_manager, format_status):
    """Handle /sm status command."""
    status = session_manager.get_status()
    session_info = session_manager.get_session_info()
    respond(response_type="ephemeral", **format_status(status, session_info))


def _handle_config(*, respond, session_manager, format_config):
    """Handle /sm config command."""
    from stock_manager.notifications.config import SlackConfig
    slack_config = SlackConfig()

    session_info = session_manager.get_session_info()
    params = session_info.get("params", {})
    config_info = {
        "slack_enabled": slack_config.enabled,
        "default_channel": slack_config.default_channel or "(미설정)",
        "session_state": session_info.get("state", "STOPPED"),
        "strategy": params.get("strategy", "N/A"),
        "symbols": params.get("symbols", "N/A"),
        "mode": params.get("mode", "N/A"),
        "order_quantity": params.get("order_quantity", "N/A"),
        "run_interval_sec": params.get("run_interval_sec", "N/A"),
    }
    respond(response_type="ephemeral", **format_config(config_info))


def _handle_balance(*, respond, session_manager, format_balance, format_error):
    """Handle /sm balance command."""
    if not session_manager.is_running:
        respond(response_type="ephemeral", **format_error("활성 트레이딩 세션이 없습니다."))
        return

    balance_data = session_manager.get_balance()
    if balance_data is None:
        respond(response_type="ephemeral", **format_error("잔고 조회에 실패했습니다."))
        return

    respond(response_type="ephemeral", **format_balance(balance_data))


def _handle_orders(*, respond, session_manager, format_orders, format_error):
    """Handle /sm orders command."""
    if not session_manager.is_running:
        respond(response_type="ephemeral", **format_error("활성 트레이딩 세션이 없습니다."))
        return

    orders_data = session_manager.get_daily_orders()
    if orders_data is None:
        respond(response_type="ephemeral", **format_error("주문 내역 조회에 실패했습니다."))
        return

    respond(response_type="ephemeral", **format_orders(orders_data))


def _handle_sell_all(
    *, cmd, user_id, respond, session_manager,
    format_sell_all_preview, format_sell_all_result, format_error,
):
    """Handle /sm sell-all command."""
    if not session_manager.is_running:
        respond(response_type="ephemeral", **format_error("활성 트레이딩 세션이 없습니다."))
        return

    if not cmd.confirm:
        # Preview mode
        positions = session_manager.get_positions()
        if positions is None:
            respond(response_type="ephemeral", **format_error("포지션 조회에 실패했습니다."))
            return
        respond(response_type="ephemeral", **format_sell_all_preview(positions))
        return

    # Execution mode — rate limit check
    if not _check_rate_limit(user_id):
        respond(
            response_type="ephemeral",
            **format_error(f"다시 시도하려면 {int(_RATE_LIMIT_COOLDOWN_SEC)}초 후에 시도하세요.")
        )
        return

    try:
        results = session_manager.liquidate_all()
        if results is None:
            respond(response_type="ephemeral", **format_error("일괄 매도에 실패했습니다."))
            return
        respond(response_type="in_channel", **format_sell_all_result(results))
    except Exception as exc:
        respond(response_type="ephemeral", **format_error(f"일괄 매도 오류: {exc}"))
