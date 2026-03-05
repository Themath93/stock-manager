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
    "pipeline.consensus.buy": "📊",
    "pipeline.consensus.reject": "📉",
    "pipeline.buy_filled": "💰",
    "pipeline.position_summary": "📋",
    "pipeline.condition_warning": "⚠️",
    "pipeline.sell_triggered": "🔔",
    "pipeline.trade_profit": "🎉",
    "pipeline.trade_loss": "📛",
    "error.stop_loss_failed": "🚨",
    "error.take_profit_failed": "🚨",
    "error.state_persistence_failed": "💾",
    "error.buy_submission_failed": "🚨",
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
        "pipeline": format_pipeline_event,
        "consensus": format_consensus_event,
        "error": format_error_detail,
        "strategy": format_error_detail,
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
            _mrkdwn_field("*상태:*", "실행 중"),
            _mrkdwn_field(
                "*모드:*", "모의투자" if details.get("is_paper_trading") else "실전투자"
            ),
            _mrkdwn_field("*로딩된 포지션:*", str(details.get("position_count", 0))),
            _mrkdwn_field("*복구:*", str(details.get("recovery_result", "N/A"))),
        ]
    else:  # engine.stopped
        fields = [
            _mrkdwn_field("*상태:*", "중지"),
            _mrkdwn_field("*미체결 포지션:*", str(details.get("position_count", 0))),
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
            _mrkdwn_field("*종목:*", symbol),
            _mrkdwn_field("*매매 방향:*", f"{side_emoji} {str(side).upper()}"),
            _mrkdwn_field("*수량:*", str(quantity)),
            _mrkdwn_field("*가격:*", _format_currency(price) if price else "시장가"),
        ]
        broker_id = details.get("broker_order_id")
        if broker_id:
            fields.append(_mrkdwn_field("*브로커 주문 ID:*", str(broker_id)))
    else:  # order.rejected
        fields = [
            _mrkdwn_field("*종목:*", symbol),
            _mrkdwn_field("*매매 방향:*", f"{side_emoji} {str(side).upper()}"),
            _mrkdwn_field("*수량:*", str(quantity)),
            _mrkdwn_field("*사유:*", details.get("reason", "알 수 없음")),
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
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*매입가:*", _format_currency(entry_price) if entry_price else "N/A"),
        _mrkdwn_field(
            "*발동가:*", _format_currency(trigger_price) if trigger_price else "N/A"
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
            fields.append(_mrkdwn_field("*주당 손익:*", pnl_str))
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
        _mrkdwn_field("*상태:*", "불일치"),
        _mrkdwn_field("*고아 포지션:*", str(len(details.get("orphan_positions", [])))),
        _mrkdwn_field("*누락 포지션:*", str(len(details.get("missing_positions", [])))),
        _mrkdwn_field("*수량 불일치:*", str(len(details.get("quantity_mismatches", {})))),
    ]

    discrepancy_count = details.get("discrepancy_count", 0)
    text = f"{mode_prefix}{emoji} {event.title}: {discrepancy_count}건 불일치 발견"
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
            _mrkdwn_field("*결과:*", "조정 완료"),
            _mrkdwn_field("*고아 포지션:*", str(len(details.get("orphan_positions", [])))),
            _mrkdwn_field("*누락 포지션:*", str(len(details.get("missing_positions", [])))),
            _mrkdwn_field(
                "*수량 불일치:*", str(len(details.get("quantity_mismatches", {})))
            ),
        ]
    else:  # recovery.failed
        errors = details.get("errors", [])
        fields = [
            _mrkdwn_field("*결과:*", "실패"),
            _mrkdwn_field("*오류 수:*", str(len(errors))),
        ]
        if errors:
            error_text = "\n".join(f"- {e}" for e in errors[:5])
            fields.append(_mrkdwn_field("*오류 목록:*", error_text))

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


def format_consensus_buy_signal(event: NotificationEvent) -> dict[str, Any]:
    """Format consensus buy signal events (pipeline.consensus.buy)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    symbol = _format_symbol_label(details)
    buy_votes = details.get("buy_votes", "N/A")
    total_votes = details.get("total_votes", "N/A")
    avg_conviction = details.get("avg_conviction", None)
    categories = details.get("categories", [])

    votes_str = f"{buy_votes}/{total_votes}" if buy_votes != "N/A" else "N/A"
    conviction_str = f"{avg_conviction:.2f}" if avg_conviction is not None else "N/A"
    categories_str = ", ".join(categories) if categories else "N/A"

    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*매수 투표:*", votes_str),
        _mrkdwn_field("*평균 확신도:*", conviction_str),
        _mrkdwn_field("*카테고리:*", categories_str),
    ]

    # Build per-persona vote lines
    persona_votes = details.get("persona_votes", {})
    persona_lines = []
    for persona, vote_info in persona_votes.items():
        vote = vote_info.get("vote", "N/A")
        conviction = vote_info.get("conviction", 0.0)
        filled = int(conviction * 10)
        bar = "█" * filled + "░" * (10 - filled)
        persona_lines.append(f"{persona}: {vote} ({conviction:.1f}) {bar}")

    text = f"{mode_prefix}{emoji} {event.title}: {symbol} {votes_str} votes"
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
    ]

    if persona_lines:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(persona_lines)},
            }
        )

    advisory_vote = details.get("advisory_vote")
    if advisory_vote:
        disruption = advisory_vote.get("disruption_assessment", "N/A")
        innovation = advisory_vote.get("innovation_score", "N/A")
        innovation_str = f"{innovation:.2f}" if isinstance(innovation, float) else str(innovation)
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"💡 Wood Advisory: {disruption} (innovation: {innovation_str})",
                    }
                ],
            }
        )

    blocks.append(_context_block(event))

    return {"text": text, "blocks": blocks, "color": "#36a64f"}


def format_buy_filled(event: NotificationEvent) -> dict[str, Any]:
    """Format buy order filled events (pipeline.buy_filled)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    symbol = _format_symbol_label(details)
    quantity = details.get("quantity", "N/A")
    price = details.get("executed_price") or details.get("price")
    conviction = details.get("conviction_score", None)

    conviction_str = f"{conviction:.2f}" if conviction is not None else "N/A"

    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*수량:*", str(quantity)),
        _mrkdwn_field("*체결가:*", _format_currency(price) if price else "N/A"),
        _mrkdwn_field("*확신도:*", conviction_str),
    ]

    text = f"{mode_prefix}{emoji} {event.title}: {symbol} {quantity}x @ {_format_currency(price) if price else 'N/A'}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": "#36a64f"}


def format_position_summary(event: NotificationEvent) -> dict[str, Any]:
    """Format periodic position summary events (pipeline.position_summary)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    positions = details.get("positions", [])
    total_pnl = details.get("total_pnl", 0)
    color = "#36a64f" if total_pnl >= 0 else "#E01E5A"

    position_lines = []
    for pos in positions:
        sym = _format_symbol_label(pos) if isinstance(pos, dict) else str(pos)
        entry = pos.get("entry_price") if isinstance(pos, dict) else None
        current = pos.get("current_price") if isinstance(pos, dict) else None
        holding_days = pos.get("holding_days", "N/A") if isinstance(pos, dict) else "N/A"
        pnl_pct_str = "N/A"
        if entry and current:
            try:
                entry_d = Decimal(str(entry))
                current_d = Decimal(str(current))
                pct = (current_d - entry_d) / entry_d * 100 if entry_d else Decimal("0")
                pnl_pct_str = f"{pct:+.1f}%"
            except (ValueError, ArithmeticError):
                pass
        entry_str = _format_currency(entry) if entry else "N/A"
        current_str = _format_currency(current) if current else "N/A"
        position_lines.append(
            f"*{sym}* | 매입: {entry_str} | 현재: {current_str} | 손익: {pnl_pct_str} | 보유일: {holding_days}"
        )

    text = f"{mode_prefix}{emoji} {event.title}: {len(positions)} positions"
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
    ]

    if position_lines:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(position_lines)},
            }
        )
    else:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_보유 포지션 없음._"},
            }
        )

    blocks.append(_context_block(event))

    return {"text": text, "blocks": blocks, "color": color}


def format_condition_warning(event: NotificationEvent) -> dict[str, Any]:
    """Format condition warning events (pipeline.condition_warning)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    symbol = _format_symbol_label(details)
    condition = details.get("condition", "N/A")
    progress = details.get("progress", None)
    threshold = details.get("threshold", "N/A")

    progress_str = f"{progress:.0%}" if isinstance(progress, float) else str(progress) if progress is not None else "N/A"

    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*조건:*", str(condition)),
        _mrkdwn_field("*진행도:*", progress_str),
        _mrkdwn_field("*기준값:*", str(threshold)),
    ]

    text = f"{mode_prefix}{emoji} {event.title}: {symbol} - {condition}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": "#ECB22E"}


def format_sell_triggered(event: NotificationEvent) -> dict[str, Any]:
    """Format sell triggered events (pipeline.sell_triggered)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    symbol = _format_symbol_label(details)
    exit_reason = details.get("exit_reason", "N/A")
    trigger_value = details.get("trigger_value", None)
    current_pnl = details.get("current_pnl", None)

    trigger_str = _format_currency(trigger_value) if trigger_value is not None else "N/A"
    pnl_str = _format_currency(current_pnl) if current_pnl is not None else "N/A"

    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*매도 사유:*", str(exit_reason)),
        _mrkdwn_field("*발동값:*", trigger_str),
        _mrkdwn_field("*현재 손익:*", pnl_str),
    ]

    text = f"{mode_prefix}{emoji} {event.title}: {symbol} - {exit_reason}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": "#FFD700"}


def format_trade_profit(event: NotificationEvent) -> dict[str, Any]:
    """Format trade complete - profit events (pipeline.trade_profit)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    symbol = _format_symbol_label(details)
    entry_price = details.get("entry_price")
    exit_price = details.get("exit_price")
    pnl = details.get("pnl", None)
    return_pct = details.get("return_pct", None)
    holding_days = details.get("holding_days", "N/A")

    return_str = f"{return_pct:+.1f}%" if return_pct is not None else "N/A"

    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*매입가:*", _format_currency(entry_price) if entry_price else "N/A"),
        _mrkdwn_field("*매도가:*", _format_currency(exit_price) if exit_price else "N/A"),
        _mrkdwn_field("*손익:*", _format_currency(pnl) if pnl is not None else "N/A"),
        _mrkdwn_field("*수익률:*", return_str),
        _mrkdwn_field("*보유일:*", str(holding_days)),
    ]

    text = f"{mode_prefix}{emoji} {event.title}: {symbol} {return_str}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": "#36a64f"}


def format_trade_loss(event: NotificationEvent) -> dict[str, Any]:
    """Format trade complete - loss events (pipeline.trade_loss)."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    symbol = _format_symbol_label(details)
    entry_price = details.get("entry_price")
    exit_price = details.get("exit_price")
    pnl = details.get("pnl", None)
    return_pct = details.get("return_pct", None)
    holding_days = details.get("holding_days", "N/A")

    return_str = f"{return_pct:+.1f}%" if return_pct is not None else "N/A"

    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*매입가:*", _format_currency(entry_price) if entry_price else "N/A"),
        _mrkdwn_field("*매도가:*", _format_currency(exit_price) if exit_price else "N/A"),
        _mrkdwn_field("*손익:*", _format_currency(pnl) if pnl is not None else "N/A"),
        _mrkdwn_field("*수익률:*", return_str),
        _mrkdwn_field("*보유일:*", str(holding_days)),
    ]

    text = f"{mode_prefix}{emoji} {event.title}: {symbol} {return_str}"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{mode_prefix}{emoji} {event.title}"},
        },
        {"type": "section", "fields": fields},
        _context_block(event),
    ]

    return {"text": text, "blocks": blocks, "color": "#E01E5A"}


def format_error_detail(event: NotificationEvent) -> dict[str, Any]:
    """Format detailed error events with traceback and recovery info."""
    emoji = _event_to_emoji(event)
    mode_prefix = _mock_prefix(event)
    details = event.details

    symbol = _format_symbol_label(details) if details.get("symbol") else None
    error_type = details.get("error_type", "Exception")
    error_category = details.get("error_category", "시스템")
    operation = details.get("operation", "")
    recoverable = details.get("recoverable", False)
    error_message = details.get("error_message", "")
    tb = details.get("traceback", "")
    recovery_suggestion = details.get("recovery_suggestion", "")
    session_uptime = details.get("session_uptime_sec")

    # Section 1: Header
    title_text = f"{mode_prefix}{emoji} {event.title}"
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": title_text},
        },
    ]

    # Section 2: Key fields
    fields = []
    if symbol:
        fields.append(_mrkdwn_field("*종목:*", symbol))
    fields.append(_mrkdwn_field("*오류 유형:*", f"`{error_type}`"))
    fields.append(_mrkdwn_field("*오류 분류:*", error_category))
    if operation:
        fields.append(_mrkdwn_field("*작업:*", operation))
    fields.append(_mrkdwn_field("*재시도 가능:*", "예" if recoverable else "아니오"))

    # Position info if available
    entry_price = details.get("entry_price")
    quantity = details.get("quantity")
    if entry_price and quantity:
        fields.append(_mrkdwn_field("*포지션:*", f"{quantity}주 @ {entry_price} KRW"))

    blocks.append({"type": "section", "fields": fields})

    # Section 3: Error message
    if error_message:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{error_message}```"},
        })

    # Section 4: Traceback (truncated to 1500 chars)
    if tb:
        tb_display = tb[:1500] if len(tb) > 1500 else tb
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{tb_display}```"},
        })

    # Section 5: Recovery suggestion
    if recovery_suggestion:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"💡 *조치 방안:* {recovery_suggestion}"}],
        })

    # Section 6: Timestamp + uptime
    ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    uptime_str = ""
    if session_uptime is not None:
        hours, rem = divmod(int(session_uptime), 3600)
        mins, secs = divmod(rem, 60)
        parts = []
        if hours:
            parts.append(f"{hours}h")
        if mins:
            parts.append(f"{mins}m")
        parts.append(f"{secs}s")
        uptime_str = f" | 세션 가동: {' '.join(parts)}"
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"{ts} | `{event.event_type}`{uptime_str}"}],
    })

    text = f"{mode_prefix}{emoji} {event.title}"
    return {"text": text, "blocks": blocks, "color": _level_to_color(event.level)}


def format_pipeline_event(event: NotificationEvent) -> dict[str, Any]:
    """Dispatch pipeline sub-events."""
    sub_dispatchers = {
        "pipeline.consensus.buy": format_consensus_buy_signal,
        "pipeline.buy_filled": format_buy_filled,
        "pipeline.position_summary": format_position_summary,
        "pipeline.condition_warning": format_condition_warning,
        "pipeline.sell_triggered": format_sell_triggered,
        "pipeline.trade_profit": format_trade_profit,
        "pipeline.trade_loss": format_trade_loss,
    }
    formatter = sub_dispatchers.get(event.event_type, _format_generic_event)
    return formatter(event)


def format_consensus_event(event: NotificationEvent) -> dict[str, Any]:
    """Dispatch consensus sub-events."""
    if "buy" in event.event_type:
        return format_consensus_buy_signal(event)
    return _format_generic_event(event)


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


# ---------------------------------------------------------------------------
# Pipeline-specific standalone formatters (keyword-arg interface)
# ---------------------------------------------------------------------------


def format_pipeline_state_change(
    symbol: str,
    from_state: str,
    to_state: str,
    reason: str,
    **kwargs: Any,
) -> list[dict]:
    """Format a pipeline state transition as Block Kit blocks.

    Args:
        symbol: Stock symbol.
        from_state: Previous pipeline state.
        to_state: New pipeline state.
        reason: Human-readable reason for the transition.
        **kwargs: Extra fields are accepted and ignored.

    Returns:
        List of Block Kit block dicts.
    """
    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*이전:*", from_state),
        _mrkdwn_field("*이후:*", to_state),
        _mrkdwn_field("*사유:*", reason),
    ]
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"파이프라인 상태 변경: {symbol}"},
        },
        {"type": "section", "fields": fields},
    ]


def format_consensus_result(
    symbol: str,
    passed: bool,
    buy_count: int,
    total_count: int,
    avg_conviction: float,
    categories: dict[str, int],
    **kwargs: Any,
) -> list[dict]:
    """Format a consensus voting result as Block Kit blocks.

    Args:
        symbol: Stock symbol.
        passed: Whether consensus threshold was met.
        buy_count: Number of buy votes.
        total_count: Total votes cast.
        avg_conviction: Average conviction score (0.0–1.0).
        categories: Vote category breakdown.
        **kwargs: Extra fields are accepted and ignored.

    Returns:
        List of Block Kit block dicts.
    """
    verdict = "통과" if passed else "거부"
    emoji = "📊" if passed else "📉"
    votes_str = f"{buy_count}/{total_count}"
    conviction_str = f"{avg_conviction:.2f}"
    categories_str = ", ".join(f"{k}:{v}" for k, v in categories.items()) or "N/A"

    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*판정:*", verdict),
        _mrkdwn_field("*매수 투표:*", votes_str),
        _mrkdwn_field("*평균 확신도:*", conviction_str),
        _mrkdwn_field("*카테고리:*", categories_str),
    ]
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} 합의 결과: {symbol}"},
        },
        {"type": "section", "fields": fields},
    ]


def format_buy_executed(
    symbol: str,
    price: int | float | Decimal,
    quantity: int,
    order_type: str,
    **kwargs: Any,
) -> list[dict]:
    """Format a buy order execution as Block Kit blocks.

    Args:
        symbol: Stock symbol.
        price: Executed price.
        quantity: Number of shares bought.
        order_type: Order type string (e.g. "LIMIT", "MARKET").
        **kwargs: Extra fields are accepted and ignored.

    Returns:
        List of Block Kit block dicts.
    """
    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*가격:*", _format_currency(price)),
        _mrkdwn_field("*수량:*", str(quantity)),
        _mrkdwn_field("*주문 유형:*", order_type),
    ]
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"💰 매수 체결: {symbol}"},
        },
        {"type": "section", "fields": fields},
    ]


def format_sell_executed(
    symbol: str,
    reason: str,
    price: int | float | Decimal,
    pnl: int | float | Decimal,
    return_pct: float,
    **kwargs: Any,
) -> list[dict]:
    """Format a sell order execution as Block Kit blocks.

    Args:
        symbol: Stock symbol.
        reason: Sell trigger reason (e.g. "stop_loss", "take_profit").
        price: Executed sell price.
        pnl: Realised profit/loss.
        return_pct: Return as a percentage (e.g. -10.0 for -10%).
        **kwargs: Extra fields are accepted and ignored.

    Returns:
        List of Block Kit block dicts.
    """
    return_str = f"{return_pct:+.1f}%"
    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*사유:*", reason),
        _mrkdwn_field("*가격:*", _format_currency(price)),
        _mrkdwn_field("*손익:*", _format_currency(pnl)),
        _mrkdwn_field("*수익률:*", return_str),
    ]
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🔔 매도 체결: {symbol}"},
        },
        {"type": "section", "fields": fields},
    ]


def format_pipeline_error(
    symbol: str,
    error_type: str,
    error_message: str,
    state: str,
    **kwargs: Any,
) -> list[dict]:
    """Format a pipeline error event as Block Kit blocks.

    Args:
        symbol: Stock symbol where the error occurred.
        error_type: Exception class name (e.g. "ConnectionError").
        error_message: Human-readable error description.
        state: Pipeline state at the time of the error.
        **kwargs: Extra fields are accepted and ignored.

    Returns:
        List of Block Kit block dicts.
    """
    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*오류 유형:*", error_type),
        _mrkdwn_field("*메시지:*", error_message),
        _mrkdwn_field("*상태:*", state),
    ]
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🚨 파이프라인 오류: {symbol}"},
        },
        {"type": "section", "fields": fields},
    ]

    # Optional enrichment from error context
    traceback_str = kwargs.get("traceback")
    recovery = kwargs.get("recovery_suggestion")
    if traceback_str:
        tb_display = traceback_str[:1500] if len(traceback_str) > 1500 else traceback_str
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{tb_display}```"},
        })
    if recovery:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"💡 *조치 방안:* {recovery}"}],
        })

    return blocks


def format_daily_summary(
    date: str,
    total_trades: int,
    winning_trades: int,
    total_pnl: int | float | Decimal,
    **kwargs: Any,
) -> list[dict]:
    """Format a daily trading summary as Block Kit blocks.

    Args:
        date: Date string for the summary (e.g. "2026-02-22").
        total_trades: Total number of completed trades.
        winning_trades: Number of profitable trades.
        total_pnl: Aggregate profit/loss across all trades.
        **kwargs: Extra fields are accepted and ignored.

    Returns:
        List of Block Kit block dicts.
    """
    losing_trades = total_trades - winning_trades
    win_rate = f"{winning_trades / total_trades:.0%}" if total_trades > 0 else "N/A"
    fields = [
        _mrkdwn_field("*날짜:*", date),
        _mrkdwn_field("*총 거래:*", str(total_trades)),
        _mrkdwn_field("*수익:*", str(winning_trades)),
        _mrkdwn_field("*손실:*", str(losing_trades)),
        _mrkdwn_field("*승률:*", win_rate),
        _mrkdwn_field("*총 손익:*", _format_currency(total_pnl)),
    ]
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📋 일일 요약: {date}"},
        },
        {"type": "section", "fields": fields},
    ]


def format_trade_complete(
    symbol: str,
    entry_price: int | float | Decimal,
    exit_price: int | float | Decimal,
    pnl: int | float | Decimal,
    holding_days: int,
    return_pct: float,
    **kwargs: Any,
) -> list[dict]:
    """Format a completed trade summary as Block Kit blocks.

    Args:
        symbol: Stock symbol.
        entry_price: Price at which the position was opened.
        exit_price: Price at which the position was closed.
        pnl: Realised profit/loss.
        holding_days: Number of days the position was held.
        return_pct: Return as a percentage.
        **kwargs: Extra fields are accepted and ignored.

    Returns:
        List of Block Kit block dicts.
    """
    return_str = f"{return_pct:+.1f}%"
    emoji = "🎉" if return_pct >= 0 else "📛"
    fields = [
        _mrkdwn_field("*종목:*", symbol),
        _mrkdwn_field("*매입가:*", _format_currency(entry_price)),
        _mrkdwn_field("*매도가:*", _format_currency(exit_price)),
        _mrkdwn_field("*손익:*", _format_currency(pnl)),
        _mrkdwn_field("*수익률:*", return_str),
        _mrkdwn_field("*보유일:*", str(holding_days)),
    ]
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} 거래 완료: {symbol}"},
        },
        {"type": "section", "fields": fields},
    ]


# ---------------------------------------------------------------------------
# Pipeline event dispatchers (keyword-arg interface)
# ---------------------------------------------------------------------------

_PIPELINE_FORMATTERS: dict[str, Any] = {
    "state_change": format_pipeline_state_change,
    "buy_decision": format_buy_executed,
    "order_executed": format_buy_executed,
    "sell_trigger": format_sell_executed,
    "trade_complete": format_trade_complete,
    "error": format_pipeline_error,
    "daily_summary": format_daily_summary,
    "screening_complete": lambda **kw: [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*스크리닝 완료:* {kw.get('symbol', 'N/A')}"},
        }
    ],
}

_CONSENSUS_FORMATTERS: dict[str, Any] = {
    "consensus_result": format_consensus_result,
    "consensus_passed": format_consensus_result,
    "consensus_rejected": format_consensus_result,
}


def dispatch_pipeline_event(event_type: str, **kwargs: Any) -> list[dict]:
    """Route a pipeline event type to the correct Block Kit formatter.

    Args:
        event_type: Pipeline event type string (e.g. "state_change", "trade_complete").
        **kwargs: Event-specific keyword arguments forwarded to the formatter.

    Returns:
        List of Block Kit block dicts. Falls back to a generic single-section
        block for unknown event types.
    """
    formatter = _PIPELINE_FORMATTERS.get(event_type)
    if formatter is not None:
        return formatter(**kwargs)
    # Generic fallback
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*파이프라인 이벤트:* `{event_type}` — {kwargs.get('symbol', 'N/A')}",
            },
        }
    ]


def dispatch_consensus_event(event_type: str, **kwargs: Any) -> list[dict]:
    """Route a consensus event type to the correct Block Kit formatter.

    Args:
        event_type: Consensus event type string (e.g. "consensus_result").
        **kwargs: Event-specific keyword arguments forwarded to the formatter.

    Returns:
        List of Block Kit block dicts. Falls back to a generic single-section
        block for unknown event types.
    """
    formatter = _CONSENSUS_FORMATTERS.get(event_type)
    if formatter is not None:
        return formatter(**kwargs)
    # Generic fallback
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*합의 이벤트:* `{event_type}` — {kwargs.get('symbol', 'N/A')}",
            },
        }
    ]
