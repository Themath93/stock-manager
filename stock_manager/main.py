from __future__ import annotations

"""stock-manager CLI entrypoint.

Focus: make environment configuration discoverable and hard to get wrong.
"""


def _require_typer():
    try:
        import typer  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "typer is required for the CLI. Install with: pip install -e '.[cli]'"
        ) from e
    return typer


def build_app():
    typer = _require_typer()

    from stock_manager.cli.doctor import run_doctor
    from stock_manager.cli.setup_wizard import run_setup
    from stock_manager.cli.trading_commands import (
        create_trade_app,
        run_command,
        smoke_command,
    )

    app = typer.Typer(help="Stock Manager CLI")

    @app.command()
    def setup(
        reset: bool = typer.Option(
            False, "--reset", help="Reset .env from .env.example (backup created)."
        ),
        skip_verify: bool = typer.Option(
            False, "--skip-verify", help="Skip network verification (KIS/Slack)."
        ),
    ) -> None:
        """Interactive .env setup wizard."""
        run_setup(reset=reset, skip_verify=skip_verify)

    @app.command()
    def doctor(
        verbose: bool = typer.Option(False, "--verbose", help="Print suspicious lines."),
    ) -> None:
        """Diagnose common `.env` configuration issues."""
        result = run_doctor(verbose=verbose)
        raise typer.Exit(code=0 if result.ok else 1)

    @app.command("run")
    def run(
        duration_sec: int = typer.Option(
            0,
            "--duration-sec",
            help="Runtime in seconds. 0 means run until interrupted.",
        ),
        skip_auth: bool = typer.Option(
            False,
            "--skip-auth",
            help="Skip preflight authentication before engine start.",
        ),
        strategy: str | None = typer.Option(
            None,
            "--strategy",
            help="Strategy name to run (for example: graham)",
        ),
        strategy_symbols: str | None = typer.Option(
            None,
            "--strategy-symbols",
            help="Comma-separated stock symbols for strategy screening.",
        ),
        strategy_order_quantity: int = typer.Option(
            1,
            "--strategy-order-quantity",
            help="Order quantity per strategy buy when condition is met.",
        ),
        strategy_max_symbols_per_cycle: int = typer.Option(
            50,
            "--strategy-max-symbols-per-cycle",
            help="Max symbols screened each strategy cycle.",
        ),
        strategy_max_buys_per_cycle: int = typer.Option(
            1,
            "--strategy-max-buys-per-cycle",
            help="Max number of buys submitted per strategy cycle.",
        ),
        strategy_run_interval_sec: float = typer.Option(
            60.0,
            "--strategy-run-interval-sec",
            help="Seconds between strategy cycles after startup.",
        ),
        strategy_auto_discover: bool = typer.Option(
            False,
            "--strategy-auto-discover",
            help="Auto-discover strategy symbols when --strategy-symbols is empty.",
        ),
        strategy_discovery_limit: int = typer.Option(
            20,
            "--strategy-discovery-limit",
            help="Maximum number of auto-discovered symbols per cycle.",
        ),
        strategy_discovery_fallback_symbols: str | None = typer.Option(
            None,
            "--strategy-discovery-fallback-symbols",
            help="Comma-separated fallback symbols for auto-discovery failures.",
        ),
        websocket_monitoring_enabled: bool = typer.Option(
            False,
            "--websocket-monitoring-enabled",
            help="Use websocket quote stream for position monitoring.",
        ),
        websocket_execution_notice_enabled: bool = typer.Option(
            False,
            "--websocket-execution-notice-enabled",
            help="Use websocket execution notice stream for reconciliation.",
        ),
    ) -> None:
        """Start trading engine and keep it running until stop signal."""
        run_command(
            duration_sec=duration_sec,
            skip_auth=skip_auth,
            strategy=strategy,
            strategy_symbols=strategy_symbols,
            strategy_order_quantity=strategy_order_quantity,
            strategy_max_symbols_per_cycle=strategy_max_symbols_per_cycle,
            strategy_max_buys_per_cycle=strategy_max_buys_per_cycle,
            strategy_run_interval_sec=strategy_run_interval_sec,
            strategy_auto_discover=strategy_auto_discover,
            strategy_discovery_limit=strategy_discovery_limit,
            strategy_discovery_fallback_symbols=strategy_discovery_fallback_symbols,
            websocket_monitoring_enabled=websocket_monitoring_enabled,
            websocket_execution_notice_enabled=websocket_execution_notice_enabled,
        )

    app.add_typer(create_trade_app(), name="trade")

    @app.command("smoke")
    def smoke() -> None:
        """Run no-order smoke checks: auth + quote + balance."""
        smoke_command()

    @app.command("slack")
    def slack_bot() -> None:
        """Start Slack Bot listener (Socket Mode) for /sm commands."""
        import threading
        import signal
        import logging
        from stock_manager.config.logging_config import setup_logging
        setup_logging()
        slack_log = logging.getLogger("slack_bolt")
        slack_log.setLevel(logging.WARNING)

        from stock_manager.notifications.config import SlackConfig
        from stock_manager.slack_bot.session_manager import SessionManager
        from stock_manager.slack_bot.app import create_slack_app

        slack_config = SlackConfig()

        if not slack_config.app_token:
            typer.echo("Error: SLACK_APP_TOKEN is not set. Set it in .env (xapp-1-...)")
            raise typer.Exit(code=1)

        app_token = slack_config.app_token.get_secret_value()

        def _on_engine_crash(exc: Exception) -> None:
            typer.echo(f"[slack-bot] Engine crashed: {exc}")

        session_manager = SessionManager(on_crash=_on_engine_crash)
        bolt_app = create_slack_app(session_manager)

        stop_event = threading.Event()

        def _on_signal(signum, frame):
            typer.echo("\n[slack-bot] Shutdown requested...")
            if session_manager.is_running:
                typer.echo("[slack-bot] Stopping active session...")
                try:
                    session_manager.stop_session()
                except Exception as e:
                    typer.echo(f"[slack-bot] Error stopping session: {e}")
            stop_event.set()

        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)

        from slack_bolt.adapter.socket_mode import SocketModeHandler
        handler = SocketModeHandler(bolt_app, app_token)

        typer.echo("[slack-bot] Starting Slack Socket Mode listener...")
        typer.echo("[slack-bot] Use /sm start|stop|status|config in Slack")
        typer.echo("[slack-bot] Press Ctrl+C to stop")

        # Start handler in background thread so we can catch signals
        handler_thread = threading.Thread(target=handler.start, daemon=True)
        handler_thread.start()

        # Wait for shutdown signal
        stop_event.wait()

        typer.echo("[slack-bot] Shutting down...")
        try:
            handler.close()
        except Exception:
            pass
        typer.echo("[slack-bot] Done.")

    return app


def main() -> None:
    app = build_app()
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
