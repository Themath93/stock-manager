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
    ) -> None:
        """Start trading engine and keep it running until stop signal."""
        run_command(duration_sec=duration_sec, skip_auth=skip_auth)

    app.add_typer(create_trade_app(), name="trade")

    @app.command("smoke")
    def smoke() -> None:
        """Run no-order smoke checks: auth + quote + balance."""
        smoke_command()

    return app


def main() -> None:
    app = build_app()
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
