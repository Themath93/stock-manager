from __future__ import annotations

import re
import signal
import time
from dataclasses import dataclass
from types import FrameType
from typing import Literal

import typer

from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import inquire_current_price
from stock_manager.adapters.broker.kis.apis.domestic_stock.orders import (
    get_default_inquire_balance_params,
    inquire_balance,
)
from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.adapters.broker.kis.config import KISConfig
from stock_manager.engine import TradingEngine
from stock_manager.trading import OrderExecutor, TradingConfig

DEFAULT_SMOKE_SYMBOL = "005930"

_ACCOUNT_NUMBER_PATTERN = re.compile(r"^\d{8}$")
_ACCOUNT_PRODUCT_CODE_PATTERN = re.compile(r"^\d{2}$")


@dataclass(frozen=True)
class RuntimeContext:
    config: KISConfig
    client: KISRestClient
    account_number: str
    account_product_code: str


def _normalize_account_settings(account_number: str, account_product_code: str) -> tuple[str, str]:
    account_number = (account_number or "").strip()
    account_product_code = (account_product_code or "").strip()

    if not account_product_code:
        if "-" in account_number:
            base, _, product = account_number.partition("-")
            account_number = base.strip()
            account_product_code = product.strip()
        elif account_number.isdigit() and len(account_number) == 10:
            account_product_code = account_number[-2:]
            account_number = account_number[:8]

    return account_number, account_product_code


def _validate_account_settings(account_number: str, account_product_code: str) -> None:
    if not _ACCOUNT_NUMBER_PATTERN.fullmatch(account_number):
        raise ValueError("KIS_ACCOUNT_NUMBER must be exactly 8 digits (example: 12345678).")
    if not _ACCOUNT_PRODUCT_CODE_PATTERN.fullmatch(account_product_code):
        raise ValueError("KIS_ACCOUNT_PRODUCT_CODE must be exactly 2 digits (example: 01).")


def _looks_like_opsq2000_error(message: str) -> bool:
    upper = message.upper()
    return "OPSQ2000" in upper or "INVALID_CHECK_ACNO" in upper


def _build_runtime_context() -> RuntimeContext:
    config = KISConfig()
    account_number, account_product_code = _normalize_account_settings(
        config.account_number or "",
        config.account_product_code or "",
    )
    _validate_account_settings(account_number, account_product_code)

    return RuntimeContext(
        config=config,
        client=KISRestClient(config=config),
        account_number=account_number,
        account_product_code=account_product_code,
    )


def run_command(*, duration_sec: int, skip_auth: bool) -> None:
    if duration_sec < 0:
        typer.echo("--duration-sec must be 0 or a positive integer.")
        raise typer.Exit(code=1)

    runtime: RuntimeContext | None = None
    try:
        runtime = _build_runtime_context()
        if not skip_auth:
            runtime.client.authenticate()

        engine = TradingEngine(
            client=runtime.client,
            config=TradingConfig(),
            account_number=runtime.account_number,
            account_product_code=runtime.account_product_code,
            is_paper_trading=runtime.config.use_mock,
        )

        stop_requested = False

        def _on_signal(_signum: int, _frame: FrameType | None) -> None:
            nonlocal stop_requested
            stop_requested = True

        old_sigint = signal.getsignal(signal.SIGINT)
        old_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)

        started = False
        started_at = time.monotonic()
        try:
            engine.start()
            started = True
            typer.echo("Engine started.")

            while not stop_requested:
                if duration_sec > 0 and (time.monotonic() - started_at) >= duration_sec:
                    break
                time.sleep(0.2)
        finally:
            signal.signal(signal.SIGINT, old_sigint)
            signal.signal(signal.SIGTERM, old_sigterm)
            if started:
                engine.stop()
                typer.echo("Engine stopped.")
    except Exception as e:
        typer.echo(f"Run failed: {e}")
        if runtime is not None and runtime.config.use_mock and _looks_like_opsq2000_error(str(e)):
            typer.echo(
                "Hint: mock-mode account validation failed. Verify KIS_MOCK_ACCOUNT_NUMBER is set "
                "to your 8-digit virtual account and KIS_ACCOUNT_PRODUCT_CODE matches your mock account."
            )
        raise typer.Exit(code=1)


def _execute_trade(
    *,
    side: Literal["buy", "sell"],
    symbol: str,
    qty: int,
    price: int,
    execute: bool,
    confirm_live: bool,
) -> None:
    symbol = symbol.strip().upper()
    if not symbol:
        typer.echo("SYMBOL cannot be empty.")
        raise typer.Exit(code=1)
    if qty <= 0:
        typer.echo("QTY must be a positive integer.")
        raise typer.Exit(code=1)
    if price <= 0:
        typer.echo("--price must be a positive integer.")
        raise typer.Exit(code=1)

    runtime: RuntimeContext | None = None
    try:
        runtime = _build_runtime_context()
    except Exception as e:
        typer.echo(f"Trade setup failed: {e}")
        raise typer.Exit(code=1)

    if not execute:
        typer.echo(
            f"DRY-RUN {side.upper()}: symbol={symbol} qty={qty} price={price} (no order sent)"
        )
        return

    if not runtime.config.use_mock and not confirm_live:
        typer.echo(
            "Live trading is blocked. When KIS_USE_MOCK=false, --execute requires --confirm-live."
        )
        raise typer.Exit(code=1)

    try:
        runtime.client.authenticate()
        executor = OrderExecutor(
            client=runtime.client,
            account_number=runtime.account_number,
            account_product_code=runtime.account_product_code,
            is_paper_trading=runtime.config.use_mock,
        )
        if side == "buy":
            result = executor.buy(symbol=symbol, quantity=qty, price=price)
        else:
            result = executor.sell(symbol=symbol, quantity=qty, price=price)
    except Exception as e:
        typer.echo(f"Trade execution failed: {e}")
        if runtime is not None and runtime.config.use_mock and _looks_like_opsq2000_error(str(e)):
            typer.echo(
                "Hint: mock-mode account validation failed. Verify KIS_MOCK_ACCOUNT_NUMBER is set "
                "to your 8-digit virtual account and KIS_ACCOUNT_PRODUCT_CODE matches your mock account."
            )
        raise typer.Exit(code=1)

    if result.success:
        typer.echo(
            f"ORDER OK {side.upper()}: symbol={symbol} qty={qty} price={price} broker_order_id={result.broker_order_id or '-'}"
        )
        return

    typer.echo(f"ORDER FAILED: {result.message}")
    raise typer.Exit(code=1)


def smoke_command() -> None:
    runtime: RuntimeContext | None = None
    try:
        runtime = _build_runtime_context()
        runtime.client.authenticate()

        price_response = inquire_current_price(
            client=runtime.client,
            stock_code=DEFAULT_SMOKE_SYMBOL,
            is_paper_trading=runtime.config.use_mock,
        )
        if str(price_response.get("rt_cd")) != "0":
            raise RuntimeError(f"price check failed: {price_response.get('msg1', 'unknown error')}")

        balance_request = inquire_balance(
            cano=runtime.account_number,
            acnt_prdt_cd=runtime.account_product_code,
            is_paper_trading=runtime.config.use_mock,
            **get_default_inquire_balance_params(),
        )
        balance_response = runtime.client.make_request(
            method="GET",
            path=balance_request["url_path"],
            params=balance_request["params"],
            headers={"tr_id": balance_request["tr_id"]},
        )
        if str(balance_response.get("rt_cd")) != "0":
            raise RuntimeError(
                f"balance check failed: {balance_response.get('msg1', 'unknown error')}"
            )

        current_price = (
            price_response.get("output", {}).get("stck_prpr")
            if isinstance(price_response.get("output"), dict)
            else None
        )
        holdings_count = (
            len(balance_response.get("output1", []))
            if isinstance(balance_response.get("output1"), list)
            else 0
        )
        typer.echo(
            f"Smoke OK: auth=ok, price({DEFAULT_SMOKE_SYMBOL})={current_price or 'n/a'}, holdings={holdings_count}"
        )
    except Exception as e:
        typer.echo(f"Smoke failed: {e}")
        if runtime is not None and runtime.config.use_mock and _looks_like_opsq2000_error(str(e)):
            typer.echo(
                "Hint: mock-mode account validation failed. Verify KIS_MOCK_ACCOUNT_NUMBER is set "
                "to your 8-digit virtual account and KIS_ACCOUNT_PRODUCT_CODE matches your mock account."
            )
        raise typer.Exit(code=1)


def create_trade_app() -> typer.Typer:
    app = typer.Typer(help="Submit buy/sell orders (dry-run by default).")

    @app.command("buy")
    def buy(
        symbol: str = typer.Argument(..., help="Stock symbol, e.g. 005930"),
        qty: int = typer.Argument(..., help="Quantity"),
        price: int = typer.Option(..., "--price", help="Limit price (required)"),
        execute: bool = typer.Option(False, "--execute", help="Actually submit the order."),
        confirm_live: bool = typer.Option(
            False,
            "--confirm-live",
            help="Required together with --execute when KIS_USE_MOCK=false.",
        ),
    ) -> None:
        _execute_trade(
            side="buy",
            symbol=symbol,
            qty=qty,
            price=price,
            execute=execute,
            confirm_live=confirm_live,
        )

    @app.command("sell")
    def sell(
        symbol: str = typer.Argument(..., help="Stock symbol, e.g. 005930"),
        qty: int = typer.Argument(..., help="Quantity"),
        price: int = typer.Option(..., "--price", help="Limit price (required)"),
        execute: bool = typer.Option(False, "--execute", help="Actually submit the order."),
        confirm_live: bool = typer.Option(
            False,
            "--confirm-live",
            help="Required together with --execute when KIS_USE_MOCK=false.",
        ),
    ) -> None:
        _execute_trade(
            side="sell",
            symbol=symbol,
            qty=qty,
            price=price,
            execute=execute,
            confirm_live=confirm_live,
        )

    return app
