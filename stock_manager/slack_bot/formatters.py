"""Slack Block Kit formatters for /sm command responses."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from stock_manager.engine import EngineStatus


def format_started(params_info: dict) -> dict:
    """Format session started response.

    params_info keys: strategy, symbols, mode ("MOCK" or "LIVE"), duration
    Returns: {"text": str, "blocks": list}
    """
    strategy = params_info.get("strategy", "N/A")
    symbols = params_info.get("symbols", "N/A")
    mode = params_info.get("mode", "N/A")
    duration = params_info.get("duration", "until stopped")

    if isinstance(symbols, list):
        symbols = ", ".join(symbols)

    return {
        "text": "Trading session started",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Trading Session Started", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Strategy:*\n{strategy}"},
                    {"type": "mrkdwn", "text": f"*Mode:*\n{mode}"},
                    {"type": "mrkdwn", "text": f"*Symbols:*\n{symbols}"},
                    {"type": "mrkdwn", "text": f"*Duration:*\n{duration}"},
                ],
            },
        ],
    }


def format_stopped(session_info: dict) -> dict:
    """Format session stopped response.

    session_info keys: uptime_str, state
    Returns: {"text": str, "blocks": list}
    """
    uptime_str = session_info.get("uptime_str", "N/A")
    state = session_info.get("state", "STOPPED")

    return {
        "text": "Trading session stopped",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Trading Session Stopped", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*State:*\n{state}"},
                    {"type": "mrkdwn", "text": f"*Uptime:*\n{uptime_str}"},
                ],
            },
        ],
    }


def format_status(status: "EngineStatus | None", session_info: dict) -> dict:
    """Format engine status response.

    session_info keys: state, strategy, symbols, mode, uptime_str
    Returns: {"text": str, "blocks": list}
    """
    state = session_info.get("state", "UNKNOWN")
    strategy = session_info.get("strategy", "N/A")
    symbols = session_info.get("symbols", "N/A")
    mode = session_info.get("mode", "N/A")
    uptime_str = session_info.get("uptime_str", "N/A")

    if isinstance(symbols, list):
        symbols = ", ".join(symbols)

    fields: list[dict] = [
        {"type": "mrkdwn", "text": f"*State:*\n{state}"},
        {"type": "mrkdwn", "text": f"*Uptime:*\n{uptime_str}"},
        {"type": "mrkdwn", "text": f"*Mode:*\n{mode}"},
        {"type": "mrkdwn", "text": f"*Strategy:*\n{strategy}"},
        {"type": "mrkdwn", "text": f"*Symbols:*\n{symbols}"},
    ]

    if status is not None:
        position_count = status.position_count
        price_monitor = "Active" if status.price_monitor_running else "Inactive"
        trading = "Enabled" if status.trading_enabled else "Disabled"
        fields.append({"type": "mrkdwn", "text": f"*Positions:*\n{position_count}"})
        fields.append({"type": "mrkdwn", "text": f"*Price Monitor:*\n{price_monitor}"})
        fields.append({"type": "mrkdwn", "text": f"*Trading:*\n{trading}"})

        if status.degraded_reason:
            fields.append({"type": "mrkdwn", "text": f"*Degraded Reason:*\n{status.degraded_reason}"})

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Engine Status", "emoji": True},
        },
        {
            "type": "section",
            "fields": fields,
        },
    ]

    return {
        "text": f"Engine Status: {state}",
        "blocks": blocks,
    }


def format_config(config_info: dict) -> dict:
    """Format config response.

    config_info keys: any key-value pairs to display
    Returns: {"text": str, "blocks": list}
    """
    fields = [
        {"type": "mrkdwn", "text": f"*{key}:*\n{value}"}
        for key, value in config_info.items()
    ]

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Current Configuration", "emoji": True},
        },
    ]

    if fields:
        blocks.append({"type": "section", "fields": fields})
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No configuration available._"},
        })

    return {
        "text": "Current configuration",
        "blocks": blocks,
    }


def format_error(message: str) -> dict:
    """Format error response.

    Returns: {"text": str, "blocks": list}
    """
    return {
        "text": f"Error: {message}",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":x: *Error:* {message}"},
            }
        ],
    }


def format_help() -> dict:
    """Format help message showing available /sm commands.

    Returns: {"text": str, "blocks": list}
    """
    commands = (
        "• `/sm start [--strategy NAME] [--symbols A,B] [--duration SEC] [--mock]`"
        " - Start trading session\n"
        "• `/sm stop` - Stop current trading session\n"
        "• `/sm status` - Show engine status\n"
        "• `/sm config` - Show current configuration"
    )

    return {
        "text": "Available /sm commands",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Stock Manager Bot", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Available Commands:*\n{commands}",
                },
            },
        ],
    }


def _format_uptime(seconds: float) -> str:
    """Format uptime seconds as '2h 15m 30s'."""
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)
