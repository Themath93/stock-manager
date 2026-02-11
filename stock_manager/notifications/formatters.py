"""Block Kit message formatters for Slack notifications.

All formatters are pure functions - no side effects, no external imports.
Each returns a dict with keys: text (fallback), blocks (Block Kit JSON), color (hex).
"""

from decimal import Decimal
from typing import Any

from stock_manager.notifications.models import NotificationEvent, NotificationLevel


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
    emoji = _level_to_emoji(event.level)
    details = event.details

    if event.event_type == "engine.started":
        fields = [
            _mrkdwn_field("*Status:*", "Running"),
            _mrkdwn_field("*Mode:*", "Paper Trading" if details.get("is_paper_trading") else "Live Trading"),
            _mrkdwn_field("*Positions Loaded:*", str(details.get("position_count", 0))),
            _mrkdwn_field("*Recovery:*", str(details.get("recovery_result", "N/A"))),
        ]
    else:  # engine.stopped
        fields = [
            _mrkdwn_field("*Status:*", "Stopped"),
            _mrkdwn_field("*Open Positions:*", str(details.get("position_count", 0))),
        ]

    text = f"{emoji} {event.title}"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} {event.title}"}},
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def format_order_event(event: NotificationEvent) -> dict[str, Any]:
    """Format order events (order.filled, order.rejected)."""
    emoji = _level_to_emoji(event.level)
    details = event.details

    symbol = details.get("symbol", "N/A")
    side = details.get("side", "N/A")
    quantity = details.get("quantity", 0)
    price = details.get("price")

    if event.event_type == "order.filled":
        fields = [
            _mrkdwn_field("*Symbol:*", symbol),
            _mrkdwn_field("*Side:*", str(side).upper()),
            _mrkdwn_field("*Quantity:*", str(quantity)),
            _mrkdwn_field("*Price:*", _format_currency(price) if price else "Market"),
        ]
        broker_id = details.get("broker_order_id")
        if broker_id:
            fields.append(_mrkdwn_field("*Broker Order ID:*", str(broker_id)))
    else:  # order.rejected
        fields = [
            _mrkdwn_field("*Symbol:*", symbol),
            _mrkdwn_field("*Side:*", str(side).upper()),
            _mrkdwn_field("*Quantity:*", str(quantity)),
            _mrkdwn_field("*Reason:*", details.get("reason", "Unknown")),
        ]

    text = f"{emoji} {event.title}: {side} {quantity}x {symbol}"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} {event.title}"}},
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def format_position_event(event: NotificationEvent) -> dict[str, Any]:
    """Format position events (position.stop_loss, position.take_profit)."""
    emoji = _level_to_emoji(event.level)
    details = event.details

    symbol = details.get("symbol", "N/A")
    entry_price = details.get("entry_price")
    trigger_price = details.get("trigger_price")

    fields = [
        _mrkdwn_field("*Symbol:*", symbol),
        _mrkdwn_field("*Entry Price:*", _format_currency(entry_price) if entry_price else "N/A"),
        _mrkdwn_field("*Trigger Price:*", _format_currency(trigger_price) if trigger_price else "N/A"),
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

    text = f"{emoji} {event.title}: {symbol}"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} {event.title}"}},
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def format_reconciliation_event(event: NotificationEvent) -> dict[str, Any]:
    """Format reconciliation events (reconciliation.discrepancy)."""
    emoji = _level_to_emoji(event.level)
    details = event.details

    fields = [
        _mrkdwn_field("*Status:*", "DIRTY"),
        _mrkdwn_field("*Orphan Positions:*", str(len(details.get("orphan_positions", [])))),
        _mrkdwn_field("*Missing Positions:*", str(len(details.get("missing_positions", [])))),
        _mrkdwn_field("*Quantity Mismatches:*", str(len(details.get("quantity_mismatches", {})))),
    ]

    discrepancy_count = details.get("discrepancy_count", 0)
    text = f"{emoji} {event.title}: {discrepancy_count} discrepancies found"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} {event.title}"}},
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def format_recovery_event(event: NotificationEvent) -> dict[str, Any]:
    """Format recovery events (recovery.reconciled, recovery.failed)."""
    emoji = _level_to_emoji(event.level)
    details = event.details

    if event.event_type == "recovery.reconciled":
        fields = [
            _mrkdwn_field("*Result:*", "RECONCILED"),
            _mrkdwn_field("*Orphan Positions:*", str(len(details.get("orphan_positions", [])))),
            _mrkdwn_field("*Missing Positions:*", str(len(details.get("missing_positions", [])))),
            _mrkdwn_field("*Quantity Mismatches:*", str(len(details.get("quantity_mismatches", {})))),
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

    text = f"{emoji} {event.title}"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} {event.title}"}},
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def _format_generic_event(event: NotificationEvent) -> dict[str, Any]:
    """Format unknown event types with a generic layout."""
    emoji = _level_to_emoji(event.level)

    fields = [_mrkdwn_field(f"*{k}:*", str(v)) for k, v in list(event.details.items())[:8]]

    text = f"{emoji} {event.title} ({event.event_type})"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} {event.title}"}},
    ]
    if fields:
        blocks.append({"type": "section", "fields": fields})
    blocks.append(_context_block(event))

    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


# --- Helper functions ---


def _level_to_color(level: NotificationLevel) -> str:
    """Map notification level to Slack attachment color (hex)."""
    colors = {
        NotificationLevel.INFO: "#36a64f",      # green
        NotificationLevel.WARNING: "#ECB22E",    # yellow
        NotificationLevel.ERROR: "#E01E5A",      # red
        NotificationLevel.CRITICAL: "#E01E5A",   # red
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
        "elements": [
            {"type": "mrkdwn", "text": f"{ts} | `{event.event_type}`"}
        ],
    }
