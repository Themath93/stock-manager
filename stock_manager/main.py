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


def main() -> None:
    typer = _require_typer()

    from stock_manager.cli.doctor import run_doctor
    from stock_manager.cli.setup_wizard import run_setup

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

    app()


if __name__ == "__main__":  # pragma: no cover
    main()

