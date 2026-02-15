"""Block Kit message formatters for Slack notifications.

All formatters are pure functions - no side effects, no external imports.
Each returns a dict with keys: text (fallback), blocks (Block Kit JSON), color (hex).
"""

from decimal import Decimal
from typing import Any

from stock_manager.notifications.models import NotificationEvent, NotificationLevel


SYMBOL_NAME_MAP: dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "035720": "카카오",
    "051910": "LG화학",
    "006400": "삼성SDI",
    "068270": "셀트리온",
    "005380": "현대차",
    "207940": "삼성바이오로직스",
}


EVENT_EMOJI_MAP: dict[str, str] = {
    "engine.started": "🚀",
    "engine.stopped": "🛑",
    "order.filled": "✅",
    "order.rejected": "❌",
    "order.canceled": "↩️",
    "order.created": "📝",
    "position.stop_loss": "🛡️",
    "position.take_profit": "💰",
    "reconciliation.discrepancy": "🔍",
    "recovery.reconciled": "♻️",
    "recovery.failed": "🚨",
}


def format_notification(event: NotificationEvent) -> dict[str, Any]:
    """Dispatch to specific formatter based on event_type prefix.

    Args:
        event: Notification event to format

    Returns:
        Dict with text (fallback), blocks (Block Kit JSON), color (hex string)
    """
    prefix = event.event_type.split(".")[0] if "." in event.event_type else ""

    dispatchers = {
        "engine": format_engine_event,
        "order": format_order_event,
        "position": format_position_event,
        "reconciliation": format_reconciliation_event,
        "recovery": format_recovery_event,
    }

    formatter = dispatchers.get(prefix, _format_generic_event)
    return formatter(event)


def format_engine_event(event: NotificationEvent) -> dict[str, Any]:
    """Format engine lifecycle events (engine.started, engine.stopped)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    if event.event_type == "engine.started":
        fields = [
            _mrkdwn_field("*Status:*", "Running"),
            _mrkdwn_field(
                "*Mode:*", "Paper Trading" if details.get("is_paper_trading") else "Live Trading"
            ),
            _mrkdwn_field("*Positions Loaded:*", str(details.get("position_count", 0))),
            _mrkdwn_field("*Recovery:*", str(details.get("recovery_result", "N/A"))),
        ]
    else:  # engine.stopped
        fields = [
            _mrkdwn_field("*Status:*", "Stopped"),
            _mrkdwn_field("*Open Positions:*", str(details.get("position_count", 0))),
        ]

    text = f"{mode_prefix}{emoji} {event.title}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def format_order_event(event: NotificationEvent) -> dict[str, Any]:
    """Format order events (order.filled, order.rejected)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    symbol = _format_symbol_label(details)
    side = details.get("side", "N/A")
    side_emoji = _side_to_emoji(side)
    quantity = details.get("quantity", 0)
    price = details.get("price")

    if event.event_type == "order.filled":
        fields = [
            _mrkdwn_field("*Symbol:*", symbol),
            _mrkdwn_field("*Side:*", f"{side_emoji} {str(side).upper()}"),
            _mrkdwn_field("*Quantity:*", str(quantity)),
            _mrkdwn_field("*Price:*", _format_currency(price) if price else "Market"),
        ]
        broker_id = details.get("broker_order_id")
        if broker_id:
            fields.append(_mrkdwn_field("*Broker Order ID:*", str(broker_id)))
    else:  # order.rejected
        fields = [
            _mrkdwn_field("*Symbol:*", symbol),
            _mrkdwn_field("*Side:*", f"{side_emoji} {str(side).upper()}"),
            _mrkdwn_field("*Quantity:*", str(quantity)),
            _mrkdwn_field("*Reason:*", details.get("reason", "Unknown")),
        ]

    text = f"{mode_prefix}{emoji} {event.title}: {side_emoji} {side} {quantity}x {symbol}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def format_position_event(event: NotificationEvent) -> dict[str, Any]:
    """Format position events (position.stop_loss, position.take_profit)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    symbol = _format_symbol_label(details)
    entry_price = details.get("entry_price")
    trigger_price = details.get("trigger_price")

    fields = [
        _mrkdwn_field("*Symbol:*", symbol),
        _mrkdwn_field("*Entry Price:*", _format_currency(entry_price) if entry_price else "N/A"),
        _mrkdwn_field(
            "*Trigger Price:*", _format_currency(trigger_price) if trigger_price else "N/A"
        ),
    ]

    # Add P&L info if available
    if entry_price and trigger_price:
        try:
            entry = Decimal(str(entry_price))
            trigger = Decimal(str(trigger_price))
            diff = trigger - entry
            pct = (diff / entry * 100) if entry else Decimal("0")
            pnl_str = f"{'+' if diff >= 0 else ''}{_format_currency(int(diff))} ({pct:+.1f}%)"
            fields.append(_mrkdwn_field("*P&L per share:*", pnl_str))
        except (ValueError, ArithmeticError):
            pass

    text = f"{mode_prefix}{emoji} {event.title}: {symbol}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def format_reconciliation_event(event: NotificationEvent) -> dict[str, Any]:
    """Format reconciliation events (reconciliation.discrepancy)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    fields = [
        _mrkdwn_field("*Status:*", "DIRTY"),
        _mrkdwn_field("*Orphan Positions:*", str(len(details.get("orphan_positions", [])))),
        _mrkdwn_field("*Missing Positions:*", str(len(details.get("missing_positions", [])))),
        _mrkdwn_field("*Quantity Mismatches:*", str(len(details.get("quantity_mismatches", {})))),
    ]

    discrepancy_count = details.get("discrepancy_count", 0)
    text = f"{mode_prefix}{emoji} {event.title}: {discrepancy_count} discrepancies found"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def format_recovery_event(event: NotificationEvent) -> dict[str, Any]:
    """Format recovery events (recovery.reconciled, recovery.failed)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    if event.event_type == "recovery.reconciled":
        fields = [
            _mrkdwn_field("*Result:*", "RECONCILED"),
            _mrkdwn_field("*Orphan Positions:*", str(len(details.get("orphan_positions", [])))),
            _mrkdwn_field("*Missing Positions:*", str(len(details.get("missing_positions", [])))),
            _mrkdwn_field(
                "*Quantity Mismatches:*", str(len(details.get("quantity_mismatches", {})))
            ),
        ]
    else:  # recovery.failed
        errors = details.get("errors", [])
        fields = [
            _mrkdwn_field("*Result:*", "FAILED"),
            _mrkdwn_field("*Error Count:*", str(len(errors))),
        ]
        if errors:
            error_text = "\n".join(f"- {e}" for e in errors[:5])
            fields.append(_mrkdwn_field("*Errors:*", error_text))

    text = f"{mode_prefix}{emoji} {event.title}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def _format_generic_event(event: NotificationEvent) -> dict[str, Any]:
    """Format unknown event types with a generic layout."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)

    fields = [_mrkdwn_field(f"*{k}:*", str(v)) for k, v in list(event.details.items())[:8]]

    text = f"{mode_prefix}{emoji} {event.title} ({event.event_type})"
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
    ]
    if fields:
        blocks.append({"type": "section", "fields": fields})
    blocks.append(_context_block(event))

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


# --- Helper functions ---


def _level_to_color(level: NotificationLevel) -> str:
    """Map notification level to Slack attachment color (hex)."""
    colors = {
        NotificationLevel.INFO: "#36a64f",  # green
        NotificationLevel.WARNING: "#ECB22E",  # yellow
        NotificationLevel.ERROR: "#E01E5A",  # red
        NotificationLevel.CRITICAL: "#E01E5A",  # red
    }
    return colors.get(level, "#36a64f")


def _level_to_emoji(level: NotificationLevel) -> str:
    """Map notification level to Slack emoji."""
    emojis = {
        NotificationLevel.INFO: ":white_check_mark:",
        NotificationLevel.WARNING: ":warning:",
        NotificationLevel.ERROR: ":x:",
        NotificationLevel.CRITICAL: ":rotating_light:",
    }
    return emojis.get(level, ":bell:")


def _event_to_emoji(event: NotificationEvent) -> str:
    """Map event type to an explicit emoji, fallback to level emoji."""
    return EVENT_EMOJI_MAP.get(event.event_type, _level_to_emoji(event.level))


def _mock_prefix(event: NotificationEvent) -> str:
    """Return title/text prefix for mock-trading events."""
    raw = event.details.get("is_paper_trading")
    if isinstance(raw, bool):
        return "[MOCK] " if raw else ""
    return "[MOCK] " if str(raw).strip().lower() in {"1", "true", "yes", "y"} else ""


def _side_to_emoji(side: Any) -> str:
    """Map side to emoji for quick visual scan."""
    side_str = str(side).upper()
    if side_str == "BUY":
        return "🟢"
    if side_str == "SELL":
        return "🔴"
    return "⚪"


def _format_symbol_label(details: dict[str, Any]) -> str:
    """Format symbol label with name when available.

    Priority:
      1) symbol_name / prdt_name / name in event details
      2) built-in SYMBOL_NAME_MAP by symbol code
      3) raw symbol
    """
    symbol = str(details.get("symbol", "N/A"))
    symbol_name = details.get("symbol_name") or details.get("prdt_name") or details.get("name")
    if not symbol_name and symbol != "N/A":
        symbol_name = SYMBOL_NAME_MAP.get(symbol)

    if symbol_name and symbol and symbol != "N/A":
        return f"{symbol_name}({symbol})"
    if symbol_name:
        return str(symbol_name)
    return symbol


def _format_currency(value: int | float | Decimal | None) -> str:
    """Format a numeric value as KRW currency with comma separators."""
    if value is None:
        return "N/A"
    try:
        return f"{int(value):,} KRW"
    except (ValueError, TypeError):
        return str(value)


def _mrkdwn_field(label: str, value: str) -> dict[str, str]:
    """Create a Block Kit mrkdwn field."""
    return {"type": "mrkdwn", "text": f"{label}\n{value}"}


def _context_block(event: NotificationEvent) -> dict[str, Any]:
    """Create a Block Kit context block with timestamp and event type."""
    ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"{ts} | `{event.event_type}`"}],
    }
