from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer
from dotenv import dotenv_values

from stock_manager.config.env_writer import scan_env_file
from stock_manager.config.paths import find_project_root


@dataclass(frozen=True)
class DoctorResult:
    ok: bool
    env_path: Path


def run_doctor(*, verbose: bool = False) -> DoctorResult:
    """Diagnose common configuration issues around `.env`."""
    root = find_project_root(Path.cwd())
    env_path = (root or Path.cwd()).resolve() / ".env"

    typer.echo(f"Project root: {root if root is not None else '(not found; using CWD)'}")
    typer.echo(f".env path: {env_path}")

    warnings = scan_env_file(env_path)
    if warnings:
        typer.echo("")
        typer.echo("Env file warnings:")
        for w in warnings:
            if w.line_no == 0:
                typer.echo(f"  - {w.message}")
            else:
                typer.echo(f"  - L{w.line_no}: {w.message}")
                if verbose:
                    typer.echo(f"    {w.line}")

    values = {k: (v or "") for k, v in (dotenv_values(str(env_path)) or {}).items()}

    missing_required: list[str] = []
    for key in ["KIS_APP_KEY", "KIS_APP_SECRET"]:
        if not values.get(key, "").strip():
            missing_required.append(key)

    slack_enabled = values.get("SLACK_ENABLED", "").strip().lower() in {"1", "true", "yes", "y"}
    missing_slack: list[str] = []
    if slack_enabled:
        for key in ["SLACK_BOT_TOKEN", "SLACK_DEFAULT_CHANNEL"]:
            if not values.get(key, "").strip():
                missing_slack.append(key)

    ok = not warnings and not missing_required and not missing_slack

    typer.echo("")
    if missing_required:
        typer.echo("Missing required keys:")
        for k in missing_required:
            typer.echo(f"  - {k}")

    if missing_slack:
        typer.echo("Slack enabled but missing keys:")
        for k in missing_slack:
            typer.echo(f"  - {k}")

    typer.echo("")
    if ok:
        typer.echo("Doctor result: OK")
    else:
        typer.echo("Doctor result: NOT OK")
        typer.echo("Next step: run `stock-manager setup` to (re)configure.")

    return DoctorResult(ok=ok, env_path=env_path)
