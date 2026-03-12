"""Slack Block Kit formatters for /sm command responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    llm_mode = params_info.get("llm_mode", "off")

    if isinstance(symbols, list):
        symbols = ", ".join(symbols)

    mode_display = "🧪 모의투자" if mode == "MOCK" else "🔴 실전투자" if mode == "LIVE" else mode

    return {
        "text": "트레이딩 세션 시작",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "트레이딩 세션 시작", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*전략:*\n{strategy}"},
                    {"type": "mrkdwn", "text": f"*모드:*\n{mode_display}"},
                    {"type": "mrkdwn", "text": f"*종목:*\n{symbols}"},
                    {"type": "mrkdwn", "text": f"*실행 시간:*\n{duration}"},
                    {"type": "mrkdwn", "text": f"*LLM 모드:*\n{llm_mode}"},
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
        "text": "트레이딩 세션 종료",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "트레이딩 세션 종료", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*상태:*\n{state}"},
                    {"type": "mrkdwn", "text": f"*가동 시간:*\n{uptime_str}"},
                ],
            },
        ],
    }


def format_status(status: "EngineStatus | None", session_info: dict) -> dict:
    """Format engine status response.

    session_info keys: state, params (nested: strategy, symbols, mode), uptime_sec
    Returns: {"text": str, "blocks": list}
    """
    state = session_info.get("state", "UNKNOWN")
    # BUG FIX: read from nested params dict
    params = session_info.get("params", {})
    strategy = params.get("strategy") or session_info.get("strategy", "N/A")
    if "symbols" in params:
        symbols = params.get("symbols")
    else:
        symbols = session_info.get("symbols", "N/A")
    mode = params.get("mode") or session_info.get("mode", "N/A")
    if mode == "N/A":
        is_mock = params.get("is_mock")
        if isinstance(is_mock, bool):
            mode = "MOCK" if is_mock else "LIVE"
    auto_discover = bool(params.get("strategy_auto_discover", False))
    discovery_limit = params.get("strategy_discovery_limit", "N/A")
    fallback_symbols = params.get("strategy_discovery_fallback_symbols", [])
    llm_mode = params.get("llm_mode", "off")
    uptime_sec = session_info.get("uptime_sec", 0)
    uptime_str = _format_uptime(uptime_sec) if uptime_sec else session_info.get("uptime_str", "N/A")

    if isinstance(symbols, list):
        if symbols:
            symbols = ", ".join(symbols)
        elif auto_discover:
            fallback_joined = ", ".join(fallback_symbols) if fallback_symbols else ""
            if fallback_joined:
                symbols = f"자동 탐색 (limit={discovery_limit}, fallback={fallback_joined})"
            else:
                symbols = f"자동 탐색 (limit={discovery_limit})"
        else:
            symbols = "미지정 (자동 탐색 OFF)"

    state_emoji = "🟢" if state == "RUNNING" else "🔴"

    # Section 1: Session info
    session_fields: list[dict] = [
        {"type": "mrkdwn", "text": f"*상태:*\n{state_emoji} {state}"},
        {"type": "mrkdwn", "text": f"*가동 시간:*\n{uptime_str}"},
        {"type": "mrkdwn", "text": f"*전략:*\n{strategy}"},
        {"type": "mrkdwn", "text": f"*모드:*\n{mode}"},
        {"type": "mrkdwn", "text": f"*종목:*\n{symbols}"},
        {"type": "mrkdwn", "text": f"*LLM 모드:*\n{llm_mode}"},
    ]

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "엔진 상태", "emoji": True},
        },
        {"type": "section", "fields": session_fields},
    ]

    # Section 2: Runtime status (only when engine status available)
    if status is not None:
        position_count = status.position_count
        buying_enabled = getattr(status, "buying_enabled", status.trading_enabled)
        runtime_mode = (
            "🟢 활성"
            if buying_enabled
            else "🟠 risk-reduction-only"
            if getattr(status, "running", True)
            else "🔴 비활성"
        )
        price_monitor = status.price_monitor_running
        source_raw = getattr(status, "strategy_discovery_source", None)
        symbols_raw = getattr(status, "strategy_discovery_symbols", ())
        reason_raw = getattr(status, "strategy_discovery_reason", None)
        updated_at_raw = getattr(status, "strategy_discovery_updated_at", None)

        discovery_source = source_raw if isinstance(source_raw, str) and source_raw else "N/A"
        if isinstance(symbols_raw, tuple):
            discovery_symbols = symbols_raw
        elif isinstance(symbols_raw, list):
            discovery_symbols = tuple(symbols_raw)
        else:
            discovery_symbols = ()
        discovery_symbols_text = ", ".join(discovery_symbols) if discovery_symbols else "(없음)"
        discovery_updated_at = (
            updated_at_raw if isinstance(updated_at_raw, str) and updated_at_raw else "N/A"
        )
        discovery_reason = reason_raw if isinstance(reason_raw, str) and reason_raw else None

        runtime_fields: list[dict] = [
            {"type": "mrkdwn", "text": f"*보유종목:*\n{position_count}"},
            {"type": "mrkdwn", "text": f"*매매:*\n{runtime_mode}"},
            {"type": "mrkdwn", "text": f"*가격 모니터:*\n{'🟢 활성' if price_monitor else '🔴 비활성'}"},
            {"type": "mrkdwn", "text": f"*탐색 소스:*\n{discovery_source}"},
            {"type": "mrkdwn", "text": f"*탐색 종목:*\n{discovery_symbols_text}"},
            {"type": "mrkdwn", "text": f"*최근 탐색:*\n{discovery_updated_at}"},
        ]
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "fields": runtime_fields})

        if discovery_reason:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"ℹ️ *탐색 사유:* {discovery_reason}"},
            })

        # Section 3: Health (only if degraded)
        if status.degraded_reason:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"⚠️ *저하 원인:* {status.degraded_reason}"},
            })

    return {
        "text": f"엔진 상태: {state}",
        "blocks": blocks,
    }


def format_config(config_info: dict) -> dict:
    """Format config response.

    config_info keys: slack_enabled, default_channel, session_state, plus optional
    trading params: strategy, symbols, mode, order_quantity, run_interval_sec
    Returns: {"text": str, "blocks": list}
    """
    # Section 1: Slack settings
    slack_fields = [
        {"type": "mrkdwn", "text": f"*알림 활성:*\n{config_info.get('slack_enabled', 'N/A')}"},
        {"type": "mrkdwn", "text": f"*기본 채널:*\n{config_info.get('default_channel', 'N/A')}"},
        {"type": "mrkdwn", "text": f"*세션 상태:*\n{config_info.get('session_state', 'N/A')}"},
    ]

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "현재 설정", "emoji": True},
        },
        {"type": "section", "fields": slack_fields},
    ]

    # Section 2: Trading settings (if available)
    trading_keys = [
        "strategy",
        "symbols",
        "mode",
        "order_quantity",
        "run_interval_sec",
        "strategy_auto_discover",
        "strategy_discovery_limit",
        "strategy_discovery_fallback_symbols",
        "llm_mode",
    ]
    has_trading = any(config_info.get(k) for k in trading_keys)
    if has_trading:
        symbols = config_info.get("symbols", "N/A")
        if isinstance(symbols, list):
            symbols = ", ".join(symbols)
        fallback_symbols = config_info.get("strategy_discovery_fallback_symbols", [])
        if isinstance(fallback_symbols, list):
            fallback_symbols = ", ".join(fallback_symbols) if fallback_symbols else "(없음)"
        trading_fields = [
            {"type": "mrkdwn", "text": f"*전략:*\n{config_info.get('strategy', 'N/A')}"},
            {"type": "mrkdwn", "text": f"*종목:*\n{symbols}"},
            {"type": "mrkdwn", "text": f"*모드:*\n{config_info.get('mode', 'N/A')}"},
            {"type": "mrkdwn", "text": f"*주문 수량:*\n{config_info.get('order_quantity', 'N/A')}"},
            {"type": "mrkdwn", "text": f"*실행 간격:*\n{config_info.get('run_interval_sec', 'N/A')}"},
            {
                "type": "mrkdwn",
                "text": (
                    "*자동탐색:*\n"
                    f"{'ON' if config_info.get('strategy_auto_discover', False) else 'OFF'}"
                ),
            },
            {
                "type": "mrkdwn",
                "text": f"*탐색 limit:*\n{config_info.get('strategy_discovery_limit', 'N/A')}",
            },
            {
                "type": "mrkdwn",
                "text": f"*fallback 종목:*\n{fallback_symbols}",
            },
            {
                "type": "mrkdwn",
                "text": f"*LLM 모드:*\n{config_info.get('llm_mode', 'off')}",
            },
        ]
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "fields": trading_fields})
    elif not any(config_info.values()):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_설정 정보가 없습니다._"},
        })

    return {
        "text": "현재 설정",
        "blocks": blocks,
    }


def format_error(message: str) -> dict:
    """Format error response.

    Returns: {"text": str, "blocks": list}
    """
    return {
        "text": f"오류: {message}",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":x: *오류:* {message}"},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "💡 `/sm help`로 사용법을 확인하세요."}
                ],
            },
        ],
    }


def format_help() -> dict:
    """Format help message showing available /sm commands.

    Returns: {"text": str, "blocks": list}
    """
    return {
        "text": "/sm 명령어 안내",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Stock Manager 봇", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*세션 관리*\n"
                        "• `/sm start` - 트레이딩 세션 시작\n"
                        "• `/sm start help` - 시작 가능한 전략/예시 명령 안내\n"
                        "  `--strategy NAME` 전략 지정\n"
                        "  `--symbols A,B` 종목 지정\n"
                        "  `--duration SEC` 실행 시간(초)\n"
                        "  `--mock` 모의투자 모드\n"
                        "  `--no-mock` 실전투자 모드\n"
                        "  `--order-quantity N` 주문 수량\n"
                        "  `--run-interval SEC` 실행 간격(초)\n"
                        "  `--auto-discover` 종목 자동 탐색 사용\n"
                        "  `--discovery-limit N` 자동 탐색 최대 종목 수\n"
                        "  `--fallback-symbols A,B` 자동 탐색 실패 시 대체 종목\n"
                        "  `--llm-mode off|selective` LLM 평가 모드\n"
                        "• `/sm stop` - 현재 세션 종료",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*조회*\n"
                        "• `/sm status` - 엔진 상태 조회\n"
                        "• `/sm config` - 현재 설정 조회\n"
                        "• `/sm balance` - 계좌 잔고 조회\n"
                        "• `/sm orders` - 당일 주문 내역 조회\n"
                        "• `/sm help` - 이 도움말 표시",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*긴급*\n"
                        "• `/sm sell-all` - 보유 포지션 미리보기\n"
                        "• `/sm sell-all --confirm` - 모든 포지션 시장가 매도",
                },
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "예시: `/sm start --strategy consensus --symbols 005930,000660 --mock`\n"
                            "예시: `/sm start --strategy consensus --auto-discover --discovery-limit 7 --fallback-symbols 005930,000660 --mock`\n"
                            "예시: `/sm start --strategy consensus --auto-discover --discovery-limit 7 --fallback-symbols 005930,000660 --llm-mode selective --mock`\n"
                            "예시: `/sm start --duration 3600 --order-quantity 5`",
                    }
                ],
            },
        ],
    }


def format_start_help() -> dict:
    """Format `/sm start help` response with strategy guide and example commands."""
    return {
        "text": "/sm start 전략 안내",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "시작 전략 가이드", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*지원 전략*\n"
                    "• `graham` - 벤저민 그레이엄 스타일 가치 스크리너입니다. "
                    "명시한 종목을 보수적으로 점검할 때 적합합니다.\n"
                    "• `consensus` - 10개 투자 페르소나 + advisory를 조합한 합의형 전략입니다. "
                    "자동 탐색과 `--llm-mode selective`를 함께 쓰려면 이 전략을 사용해야 합니다.",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*전략 선택 기준*\n"
                    "• 명시 종목을 빠르게 보수적으로 돌리고 싶으면 `graham`\n"
                    "• 자동 탐색, 합의 투표, selective LLM 보강이 필요하면 `consensus`\n"
                    "• `--llm-mode selective`는 `consensus`에서만 허용됩니다.",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*예시 명령*\n"
                    "• Graham mock:\n"
                    "`/sm start --strategy graham --symbols 005930,000660 --duration 1800 --mock`\n"
                    "• Consensus mock:\n"
                    "`/sm start --strategy consensus --symbols 005930,000660 --duration 1800 --mock`\n"
                    "• Consensus auto-discover mock:\n"
                    "`/sm start --strategy consensus --auto-discover --discovery-limit 7 --fallback-symbols 005930,000660 --mock`\n"
                    "• Consensus selective LLM mock:\n"
                    "`/sm start --strategy consensus --auto-discover --discovery-limit 7 --fallback-symbols 005930,000660 --llm-mode selective --mock`\n"
                    "• Consensus live:\n"
                    "`/sm start --strategy consensus --symbols 005930,000660 --duration 1800 --no-mock`",
                },
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "실전(`--no-mock`)은 promotion gate를 통과해야 시작됩니다.",
                    }
                ],
            },
        ],
    }


def format_balance(balance_data: dict) -> dict:
    """Format account balance response.

    balance_data: KIS inquire_balance response with output1[] (holdings) and output2[] (summary).
    Returns: {"text": str, "blocks": list}
    """
    output1 = balance_data.get("output1", [])
    output2 = balance_data.get("output2", [])

    summary = output2[0] if output2 else {}

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "계좌 잔고", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*예수금:*\n{_format_currency(summary.get('dnca_tot_amt', '0'))}"},
                {"type": "mrkdwn", "text": f"*총평가:*\n{_format_currency(summary.get('tot_evlu_amt', '0'))}"},
                {"type": "mrkdwn", "text": f"*순자산:*\n{_format_currency(summary.get('nass_amt', '0'))}"},
                {"type": "mrkdwn", "text": f"*총매입:*\n{_format_currency(summary.get('pchs_amt_smtl_amt', '0'))}"},
            ],
        },
    ]

    if output1:
        blocks.append({"type": "divider"})
        for item in output1:
            pnl_amt = item.get("evlu_pfls_amt", "0")
            pnl_rt = item.get("evlu_pfls_rt", "0")
            pnl_sign = "+" if not pnl_amt.startswith("-") and pnl_amt != "0" else ""
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{item.get('prdt_name', 'N/A')}* (`{item.get('pdno', '')}`)\n보유: {item.get('hldg_qty', '0')}주"},
                    {"type": "mrkdwn", "text": f"매입가: {_format_currency(item.get('pchs_avg_pric', '0'))}\n현재가: {_format_currency(item.get('prpr', '0'))}"},
                    {"type": "mrkdwn", "text": f"평가손익: {pnl_sign}{_format_currency(pnl_amt)} ({pnl_sign}{pnl_rt}%)"},
                ],
            })
    else:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_보유 종목이 없습니다._"},
        })

    return {"text": "계좌 잔고", "blocks": blocks}


def format_orders(orders_data: dict) -> dict:
    """Format daily order history response.

    orders_data: KIS inquire_daily_ccld response with output1[] (orders).
    Returns: {"text": str, "blocks": list}
    """
    from datetime import datetime, timezone

    output1 = orders_data.get("output1", [])

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "당일 주문 내역", "emoji": True},
        },
    ]

    if output1:
        for item in output1:
            side_code = item.get("sll_buy_dvsn_cd", "")
            side_label = "매도" if side_code == "01" else "매수" if side_code == "02" else side_code
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{item.get('prdt_name', 'N/A')}* | {side_label}"},
                    {"type": "mrkdwn", "text": f"주문: {item.get('ord_qty', '0')}주 | 체결: {item.get('tot_ccld_qty', '0')}주 | 체결가: {_format_currency(item.get('avg_prvs', '0'))}"},
                ],
            })
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_당일 주문 내역이 없습니다._"},
        })

    now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"조회 시각: {now_str}"}],
    })

    return {"text": "당일 주문 내역", "blocks": blocks}


def format_sell_all_preview(positions: dict) -> dict:
    """Format sell-all preview (without --confirm).

    positions: {symbol: {symbol, quantity, entry_price, status}} from SessionManager.
    Returns: {"text": str, "blocks": list}
    """
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "시장가 일괄 매도 미리보기", "emoji": True},
        },
    ]

    items = [v for v in positions.values() if v.get("status") in ("open", "open_reconciled")] if positions else []

    if items:
        for pos in items:
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{pos['symbol']}*\n수량: {pos['quantity']}주"},
                    {"type": "mrkdwn", "text": f"매입가: {_format_currency(str(pos['entry_price']))}"},
                ],
            })
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "실행하려면 `/sm sell-all --confirm`을 입력하세요."}],
        })
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_매도할 포지션이 없습니다._"},
        })

    return {"text": "시장가 일괄 매도 미리보기", "blocks": blocks}


def format_sell_all_result(results: list[dict]) -> dict:
    """Format sell-all execution result.

    results: list of {symbol, quantity, entry_price, success, message, broker_order_id}.
    Returns: {"text": str, "blocks": list}
    """
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "시장가 일괄 매도 완료", "emoji": True},
        },
    ]

    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count

    for r in results:
        emoji = ":white_check_mark:" if r["success"] else ":x:"
        order_id = r.get("broker_order_id") or "N/A"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{r['symbol']}* {r['quantity']}주 — 주문번호: `{order_id}`",
            },
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"성공 {success_count}건 / 실패 {fail_count}건"}],
    })

    return {"text": "시장가 일괄 매도 완료", "blocks": blocks}


def _format_currency(value: str) -> str:
    """Format numeric string as KRW currency with comma separators."""
    try:
        # Handle decimal strings like "70000.00"
        num = int(float(value))
        return f"{num:,}원"
    except (ValueError, TypeError):
        return f"{value}원"


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
