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

        Pattern: ack() immediately, process in background, respond() with result.
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
                **format_error("You are not authorized to use this bot. Contact the admin.")
            )
            return

        # Process in background to avoid blocking Bolt's main loop
        def _process():
            _dispatch_command(
                text=text,
                user_id=user_id,
                respond=respond,
                session_manager=session_manager,
            )

        thread = threading.Thread(target=_process, daemon=True)
        thread.start()

    @app.error
    def handle_error(error, body, logger):
        logger.error(f"Slack Bolt error: {error}", exc_info=True)

    return app


def _dispatch_command(*, text: str, user_id: str, respond, session_manager) -> None:
    """Dispatch /sm subcommand to appropriate handler."""
    from stock_manager.slack_bot.command_parser import parse_command
    from stock_manager.slack_bot.formatters import (
        format_started, format_stopped, format_status,
        format_config, format_error, format_help
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
    else:
        respond(response_type="ephemeral", **format_error(f"Unknown subcommand: {cmd.subcommand}. Try /sm help"))


def _handle_start(*, cmd, user_id, respond, session_manager, format_started, format_error):
    """Handle /sm start command."""
    # Rate limit check
    if not _check_rate_limit(user_id):
        respond(
            response_type="ephemeral",
            **format_error(f"Please wait {int(_RATE_LIMIT_COOLDOWN_SEC)} seconds before starting again.")
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
        respond(response_type="ephemeral", **format_error(f"Blocked: {e}"))
        return
    except Exception as e:
        respond(response_type="ephemeral", **format_error(f"Failed to start session: {e}"))
        return

    # Build params_info for formatter
    mode = "MOCK" if (cmd.is_mock is True or (cmd.is_mock is None)) else "LIVE"
    params_info = {
        "strategy": cmd.strategy or "default",
        "symbols": ", ".join(cmd.symbols) if cmd.symbols else "auto-discover",
        "mode": mode,
        "duration": f"{cmd.duration_sec}s" if cmd.duration_sec > 0 else "until stopped",
    }
    respond(response_type="in_channel", **format_started(params_info))


def _handle_stop(*, respond, session_manager, format_stopped, format_error):
    """Handle /sm stop command."""
    if not session_manager.is_running:
        respond(response_type="ephemeral", **format_error("No active trading session."))
        return

    try:
        session_manager.stop_session()
    except Exception as e:
        respond(response_type="ephemeral", **format_error(f"Failed to stop session: {e}"))
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
    config_info = {
        "slack_enabled": slack_config.enabled,
        "default_channel": slack_config.default_channel or "(not set)",
        "session_state": session_info.get("state", "STOPPED"),
    }
    respond(response_type="ephemeral", **format_config(config_info))
