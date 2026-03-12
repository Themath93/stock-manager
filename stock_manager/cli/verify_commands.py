from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import typer

from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import inquire_current_price
from stock_manager.adapters.broker.kis.apis.domestic_stock.orders import (
    get_default_inquire_balance_params,
    inquire_balance,
)
from stock_manager.cli.doctor import run_doctor
from stock_manager.cli.trading_commands import (
    RuntimeContext,
    _build_runtime_context,
    _enforce_live_promotion_gate,
    _request_balance_with_mock_retry,
)
from stock_manager.config.logging_config import setup_logging
from stock_manager.engine import TradingEngine
from stock_manager.notifications import NoOpNotifier, NotificationEvent, NotificationLevel
from stock_manager.persistence.recovery import RecoveryResult, startup_reconciliation
from stock_manager.persistence.state import TradingState, load_state, save_state_atomic
from stock_manager.trading import TradingConfig

DEFAULT_VERIFY_ARTIFACT_ROOT = Path(".sisyphus/evidence/live-roundtrip")


class LiveRoundTripProbeError(RuntimeError):
    """Raised when live round-trip verification cannot complete safely."""


@dataclass(frozen=True)
class LiveRoundTripProbeConfig:
    symbol: str
    quantity: int
    max_notional: int
    buy_fill_timeout_sec: float = 120.0
    sell_fill_timeout_sec: float = 120.0
    quote_wait_timeout_sec: float = 10.0
    poll_interval_sec: float = 0.5


@dataclass
class LiveRoundTripProbeResult:
    artifact_dir: Path
    current_price: int
    notional: int
    buy_order_id: str | None
    sell_order_id: str | None
    final_reconciliation: str
    startup_recovery: str
    captured_quote_count: int = 0
    captured_execution_count: int = 0


@dataclass
class _ArtifactRecorder:
    artifact_dir: Path
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.payload = {
            "started_at": _utc_now().isoformat(),
            "phases": [],
            "captures": {
                "quotes": [],
                "executions": [],
                "balance": [],
                "daily_orders": [],
            },
        }

    def add_phase(self, name: str, status: str, **details: Any) -> None:
        self.payload["phases"].append(
            {
                "name": name,
                "status": status,
                "timestamp": _utc_now().isoformat(),
                "details": _json_safe(details),
            }
        )

    def set_metadata(self, **metadata: Any) -> None:
        self.payload.update(_json_safe(metadata))

    def capture(self, bucket: str, value: Any) -> None:
        captures = self.payload.setdefault("captures", {})
        bucket_values = captures.setdefault(bucket, [])
        if isinstance(bucket_values, list):
            bucket_values.append(_json_safe(value))

    def write(self) -> None:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        payload = dict(self.payload)
        payload["finished_at"] = _utc_now().isoformat()
        (self.artifact_dir / "probe.json").write_text(
            json.dumps(_json_safe(payload), indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _extract_current_price(response: dict[str, Any]) -> int:
    output = response.get("output", {})
    if not isinstance(output, dict):
        raise LiveRoundTripProbeError("price response payload is missing output")
    value = output.get("stck_prpr")
    try:
        return int(str(value))
    except Exception as exc:
        raise LiveRoundTripProbeError("price response payload is missing stck_prpr") from exc


def _extract_open_holdings(balance_response: dict[str, Any]) -> list[str]:
    holdings = balance_response.get("output1", [])
    if not isinstance(holdings, list):
        return []

    symbols: list[str] = []
    for item in holdings:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("pdno") or item.get("PDNO") or "").strip().upper()
        qty_raw = item.get("hldg_qty") or item.get("HLDG_QTY") or "0"
        try:
            quantity = int(str(qty_raw).replace(",", ""))
        except Exception:
            quantity = 0
        if symbol and quantity > 0:
            symbols.append(symbol)
    return symbols


def _extract_daily_orders(response: dict[str, Any]) -> list[dict[str, Any]]:
    output = response.get("output1", [])
    if isinstance(output, list):
        return [item for item in output if isinstance(item, dict)]
    return []


def _wait_until(
    predicate: Any,
    *,
    timeout_sec: float,
    poll_interval_sec: float,
    on_poll: Any | None = None,
) -> bool:
    deadline = time.monotonic() + max(timeout_sec, 0.1)
    while time.monotonic() < deadline:
        if predicate():
            return True
        if on_poll is not None:
            on_poll()
        time.sleep(max(0.05, poll_interval_sec))
    return predicate()


def _notify_probe_event(event_type: str, title: str, **details: Any) -> None:
    NoOpNotifier().notify(
        NotificationEvent(
            event_type=event_type,
            level=NotificationLevel.INFO
            if event_type.endswith(".started") or event_type.endswith(".succeeded")
            else NotificationLevel.CRITICAL,
            title=title,
            details=_json_safe(details),
        )
    )


def _artifact_dir_for(symbol: str, *, root: Path = DEFAULT_VERIFY_ARTIFACT_ROOT) -> Path:
    timestamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    return root / f"{timestamp}-{symbol}"


def _require_live_runtime(runtime: RuntimeContext) -> None:
    if runtime.config.use_mock:
        raise LiveRoundTripProbeError(
            "verify live-roundtrip requires KIS_USE_MOCK=false and live account credentials."
        )


def _probe_notional_guard(current_price: int, quantity: int, max_notional: int) -> int:
    notional = current_price * quantity
    if notional > max_notional:
        raise LiveRoundTripProbeError(
            f"Probe notional {notional:,} exceeds --max-notional {max_notional:,}."
        )
    return notional


def _quote_monitoring_active(engine: TradingEngine, symbol: str) -> bool:
    adapter = getattr(engine, "_broker_adapter", None)
    websocket_client = getattr(adapter, "websocket_client", None) if adapter is not None else None
    quote_subscriptions = getattr(websocket_client, "_quote_subscriptions", {})
    if isinstance(quote_subscriptions, dict) and symbol in quote_subscriptions:
        return True
    monitor_symbols = getattr(engine._price_monitor, "_symbols", [])
    return symbol in monitor_symbols


def _build_probe_engine(runtime: RuntimeContext, *, state_path: Path) -> TradingEngine:
    return TradingEngine(
        client=runtime.client,
        config=TradingConfig(
            polling_interval_sec=2.0,
            market_hours_enabled=True,
            websocket_monitoring_enabled=True,
            websocket_execution_notice_enabled=True,
        ),
        account_number=runtime.account_number,
        account_product_code=runtime.account_product_code,
        state_path=state_path,
        is_paper_trading=False,
        notifier=NoOpNotifier(),
    )


def _run_live_roundtrip_probe(config: LiveRoundTripProbeConfig) -> LiveRoundTripProbeResult:
    artifact_dir = _artifact_dir_for(config.symbol)
    recorder = _ArtifactRecorder(artifact_dir=artifact_dir)
    recorder.set_metadata(
        probe={
            "symbol": config.symbol,
            "quantity": config.quantity,
            "max_notional": config.max_notional,
            "buy_fill_timeout_sec": config.buy_fill_timeout_sec,
            "sell_fill_timeout_sec": config.sell_fill_timeout_sec,
        }
    )
    _notify_probe_event("probe.live_roundtrip.started", "Live Roundtrip Started", symbol=config.symbol)

    runtime: RuntimeContext | None = None
    engine: TradingEngine | None = None

    try:
        recorder.add_phase("doctor", "started")
        doctor_result = run_doctor(verbose=False)
        if not doctor_result.ok:
            raise LiveRoundTripProbeError("doctor failed; fix configuration before live verification.")
        recorder.add_phase("doctor", "succeeded", env_path=doctor_result.env_path)

        recorder.add_phase("runtime_setup", "started")
        runtime = _build_runtime_context(use_mock_override=False)
        _require_live_runtime(runtime)
        _enforce_live_promotion_gate(use_mock=runtime.config.use_mock)
        recorder.add_phase("runtime_setup", "succeeded")

        recorder.add_phase("auth", "started")
        token = runtime.client.authenticate(force_refresh=True)
        recorder.add_phase(
            "auth",
            "succeeded",
            token_expires_at=runtime.client.state.access_token_expires_at,
            token_expires_in=token.expires_in,
        )

        recorder.add_phase("read_only_smoke", "started")
        price_response = inquire_current_price(
            client=runtime.client,
            stock_code=config.symbol,
            is_paper_trading=False,
        )
        current_price = _extract_current_price(price_response)
        notional = _probe_notional_guard(current_price, config.quantity, config.max_notional)

        balance_request = inquire_balance(
            cano=runtime.account_number,
            acnt_prdt_cd=runtime.account_product_code,
            is_paper_trading=False,
            **get_default_inquire_balance_params(),
        )
        balance_response = _request_balance_with_mock_retry(
            runtime=runtime,
            balance_request=balance_request,
        )
        recorder.capture("balance", balance_response)

        open_holdings = _extract_open_holdings(balance_response)
        if open_holdings:
            raise LiveRoundTripProbeError(
                "live roundtrip requires a clean account with no open holdings; "
                f"found holdings in: {', '.join(open_holdings[:5])}"
            )
        recorder.add_phase(
            "read_only_smoke",
            "succeeded",
            current_price=current_price,
            notional=notional,
            holdings_count=len(open_holdings),
        )

        engine = _build_probe_engine(runtime, state_path=artifact_dir / "probe-state.json")
        recorder.add_phase("engine_start", "started")
        engine.start()
        recorder.add_phase("engine_start", "succeeded")

        adapter = getattr(engine, "_broker_adapter", None)
        websocket_client = getattr(adapter, "websocket_client", None) if adapter is not None else None
        if adapter is None or websocket_client is None or not getattr(adapter, "websocket_connected", False):
            raise LiveRoundTripProbeError("live websocket streams did not connect cleanly.")

        websocket_client.register_quote_callback(
            lambda event: recorder.capture("quotes", getattr(event, "raw_payload", {}))
        )
        websocket_client.register_execution_callback(
            lambda event: recorder.capture("executions", getattr(event, "raw_payload", {}))
        )
        adapter.subscribe_quotes(symbols=[config.symbol], callback=engine._on_websocket_quote)

        quote_received = _wait_until(
            lambda: bool(recorder.payload["captures"]["quotes"]),
            timeout_sec=config.quote_wait_timeout_sec,
            poll_interval_sec=config.poll_interval_sec,
        )

        daily_orders_response = engine.get_daily_orders()
        recorder.capture("daily_orders", daily_orders_response)
        recorder.add_phase(
            "websocket_smoke",
            "succeeded",
            websocket_connected=getattr(adapter, "websocket_connected", False),
            quote_received=quote_received,
            daily_order_count=len(_extract_daily_orders(daily_orders_response)),
        )

        recorder.add_phase("buy_submit", "started")
        buy_result = engine.buy(config.symbol, config.quantity, current_price, origin="probe")
        if not buy_result.success:
            raise LiveRoundTripProbeError(f"buy submit failed: {buy_result.message}")
        recorder.add_phase(
            "buy_submit",
            "succeeded",
            order_id=buy_result.order_id,
            broker_order_id=buy_result.broker_order_id,
        )

        buy_opened = _wait_until(
            lambda: engine.get_position(config.symbol) is not None
            and not engine._has_pending_order(config.symbol, side="buy"),
            timeout_sec=config.buy_fill_timeout_sec,
            poll_interval_sec=config.poll_interval_sec,
            on_poll=engine._reconciler.reconcile_now,
        )
        if not buy_opened:
            raise LiveRoundTripProbeError("buy fill confirmation timed out.")

        position = engine.get_position(config.symbol)
        if position is None:
            raise LiveRoundTripProbeError("buy fill timed out without an open position.")
        if not _quote_monitoring_active(engine, config.symbol):
            raise LiveRoundTripProbeError("quote monitoring did not arm for the filled position.")

        recorder.add_phase(
            "buy_fill",
            "succeeded",
            entry_price=position.entry_price,
            quantity=position.quantity,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
        )

        recorder.add_phase("sell_submit", "started")
        sell_result = engine.sell(
            config.symbol,
            position.quantity,
            price=None,
            origin="probe",
            exit_reason="MANUAL",
        )
        if not sell_result.success:
            raise LiveRoundTripProbeError(f"sell submit failed: {sell_result.message}")
        recorder.add_phase(
            "sell_submit",
            "succeeded",
            order_id=sell_result.order_id,
            broker_order_id=sell_result.broker_order_id,
        )

        sell_closed = _wait_until(
            lambda: engine.get_position(config.symbol) is None
            and not engine._has_pending_order(config.symbol, side="sell"),
            timeout_sec=config.sell_fill_timeout_sec,
            poll_interval_sec=config.poll_interval_sec,
            on_poll=engine._reconciler.reconcile_now,
        )
        if not sell_closed:
            if engine.get_position(config.symbol) is not None and not engine._has_pending_order(
                config.symbol, side="sell"
            ):
                engine.sell(
                    config.symbol,
                    engine.get_position(config.symbol).quantity,  # type: ignore[union-attr]
                    price=None,
                    origin="probe",
                    exit_reason="LIQUIDATE_ALL",
                )
            raise LiveRoundTripProbeError("sell fill confirmation timed out.")

        final_reconcile = engine._reconciler.reconcile_now()
        unresolved_count, primary_unresolved_reason, unresolved_reasons = (
            engine._unresolved_orders_summary()
        )
        if not final_reconcile.is_clean:
            raise LiveRoundTripProbeError(
                f"final reconciliation not clean: {final_reconcile.discrepancies[:3]}"
            )
        if unresolved_count > 0:
            raise LiveRoundTripProbeError(
                "probe finished with unresolved pending orders: "
                f"{primary_unresolved_reason or unresolved_reasons[:1]}"
            )
        recorder.add_phase("final_reconcile", "succeeded", discrepancies=final_reconcile.discrepancies)

        engine.stop()
        engine = None

        reloaded_state = load_state(artifact_dir / "probe-state.json") or TradingState()
        startup_report = startup_reconciliation(
            local_state=reloaded_state,
            client=runtime.client,
            inquire_balance_func=lambda _client: balance_request and runtime.client.make_request(
                method="GET",
                path=balance_request["url_path"],
                params=balance_request["params"],
                headers={"tr_id": balance_request["tr_id"]},
            ),
            inquire_daily_orders_func=lambda _client: TradingEngine(
                client=runtime.client,
                config=TradingConfig(),
                account_number=runtime.account_number,
                account_product_code=runtime.account_product_code,
                state_path=artifact_dir / "startup-recovery-state.json",
                is_paper_trading=False,
            )._inquire_daily_orders(runtime.client),
            save_state_func=save_state_atomic,
            state_path=artifact_dir / "probe-state.json",
        )
        if startup_report.result != RecoveryResult.CLEAN:
            raise LiveRoundTripProbeError(
                f"startup recovery not clean: {startup_report.result.value} {startup_report.errors}"
            )
        recorder.add_phase("startup_recovery", "succeeded", result=startup_report.result.value)

        result = LiveRoundTripProbeResult(
            artifact_dir=artifact_dir,
            current_price=current_price,
            notional=notional,
            buy_order_id=buy_result.order_id,
            sell_order_id=sell_result.order_id,
            final_reconciliation=final_reconcile.is_clean and "clean" or "not_clean",
            startup_recovery=startup_report.result.value,
            captured_quote_count=len(recorder.payload["captures"]["quotes"]),
            captured_execution_count=len(recorder.payload["captures"]["executions"]),
        )
        recorder.set_metadata(result=_json_safe(result.__dict__))
        recorder.write()
        _notify_probe_event(
            "probe.live_roundtrip.succeeded",
            "Live Roundtrip Succeeded",
            symbol=config.symbol,
            artifact_dir=artifact_dir,
        )
        return result
    except Exception as exc:
        recorder.add_phase("probe", "failed", error=str(exc))
        recorder.write()
        _notify_probe_event(
            "probe.live_roundtrip.failed",
            "Live Roundtrip Failed",
            symbol=config.symbol,
            artifact_dir=artifact_dir,
            error=str(exc),
        )
        if isinstance(exc, LiveRoundTripProbeError):
            raise
        raise LiveRoundTripProbeError(str(exc)) from exc
    finally:
        if engine is not None:
            try:
                if engine._running:
                    engine.stop()
            except Exception:
                pass


def run_live_roundtrip_command(
    *,
    symbol: str,
    quantity: int,
    max_notional: int,
    confirm_live: bool,
) -> None:
    setup_logging()
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        typer.echo("--symbol is required.")
        raise typer.Exit(code=1)
    if quantity <= 0:
        typer.echo("--quantity must be a positive integer.")
        raise typer.Exit(code=1)
    if max_notional <= 0:
        typer.echo("--max-notional must be a positive integer.")
        raise typer.Exit(code=1)
    if not confirm_live:
        typer.echo("Live verification is blocked without --confirm-live.")
        raise typer.Exit(code=1)

    try:
        result = _run_live_roundtrip_probe(
            LiveRoundTripProbeConfig(
                symbol=normalized_symbol,
                quantity=quantity,
                max_notional=max_notional,
            )
        )
    except Exception as exc:
        typer.echo(f"Live roundtrip failed: {exc}")
        raise typer.Exit(code=1)

    typer.echo(
        "Live roundtrip OK: "
        f"symbol={normalized_symbol} qty={quantity} notional={result.notional} "
        f"artifact_dir={result.artifact_dir}"
    )


def create_verify_app() -> typer.Typer:
    app = typer.Typer(help="Run guarded verification flows against live KIS paths.")

    @app.command("live-roundtrip")
    def live_roundtrip(
        symbol: str = typer.Option(..., "--symbol", help="6-digit domestic stock symbol"),
        quantity: int = typer.Option(..., "--quantity", help="Small verification order quantity"),
        max_notional: int = typer.Option(
            ...,
            "--max-notional",
            help="Hard cap for buy notional in KRW; probe aborts if exceeded.",
        ),
        confirm_live: bool = typer.Option(
            False,
            "--confirm-live",
            help="Required safety flag to submit any live verification orders.",
        ),
    ) -> None:
        run_live_roundtrip_command(
            symbol=symbol,
            quantity=quantity,
            max_notional=max_notional,
            confirm_live=confirm_live,
        )

    return app
