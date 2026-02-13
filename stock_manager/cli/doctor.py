from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import typer
from dotenv import dotenv_values

from stock_manager.config.env_writer import scan_env_file
from stock_manager.config.paths import find_project_root

_TRUE_VALUES = {"1", "true", "yes", "y"}
_FALSE_VALUES = {"0", "false", "no", "n"}
_ACCOUNT_NUMBER_PATTERN = re.compile(r"^\d{8}$")
_ACCOUNT_PRODUCT_CODE_PATTERN = re.compile(r"^\d{2}$")


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

    file_warnings = scan_env_file(env_path)
    if file_warnings:
        typer.echo("")
        typer.echo("Env file warnings:")
        for w in file_warnings:
            if w.line_no == 0:
                typer.echo(f"  - {w.message}")
            else:
                typer.echo(f"  - L{w.line_no}: {w.message}")
                if verbose:
                    typer.echo(f"    {w.line}")

    values = {k: (v or "") for k, v in (dotenv_values(str(env_path)) or {}).items()}

    mode_raw = values.get("KIS_USE_MOCK", "").strip().lower()
    mode_errors: list[str] = []
    if mode_raw in _TRUE_VALUES:
        use_mock = True
    elif mode_raw in _FALSE_VALUES:
        use_mock = False
    elif mode_raw == "":
        use_mock = True
    else:
        use_mock = True
        mode_errors.append("KIS_USE_MOCK must be one of: true/false/1/0/yes/no.")

    advisory_messages: list[str] = []
    missing_required: list[str] = []

    real_key = values.get("KIS_APP_KEY", "").strip()
    real_secret = values.get("KIS_APP_SECRET", "").strip()
    real_account = values.get("KIS_ACCOUNT_NUMBER", "").strip()

    mock_key = values.get("KIS_MOCK_APP_KEY", "").strip()
    mock_secret = values.get("KIS_MOCK_SECRET", "").strip()
    mock_account = values.get("KIS_MOCK_ACCOUNT_NUMBER", "").strip()

    effective_account = ""

    if use_mock:
        if not (mock_key and mock_secret):
            if real_key and real_secret:
                advisory_messages.append(
                    "KIS_USE_MOCK=true is using fallback credentials: "
                    "KIS_APP_KEY/KIS_APP_SECRET. Set KIS_MOCK_APP_KEY/KIS_MOCK_SECRET."
                )
            else:
                if not mock_key:
                    missing_required.append("KIS_MOCK_APP_KEY (or fallback KIS_APP_KEY)")
                if not mock_secret:
                    missing_required.append("KIS_MOCK_SECRET (or fallback KIS_APP_SECRET)")

        if mock_account:
            effective_account = mock_account
        elif real_account:
            effective_account = real_account
            advisory_messages.append(
                "KIS_USE_MOCK=true is using fallback account: "
                "KIS_ACCOUNT_NUMBER. Set KIS_MOCK_ACCOUNT_NUMBER."
            )
        else:
            missing_required.append("KIS_MOCK_ACCOUNT_NUMBER (or fallback KIS_ACCOUNT_NUMBER)")
    else:
        for key in ["KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NUMBER"]:
            if not values.get(key, "").strip():
                missing_required.append(key)
        effective_account = real_account

    slack_enabled = values.get("SLACK_ENABLED", "").strip().lower() in {"1", "true", "yes", "y"}
    missing_slack: list[str] = []
    if slack_enabled:
        for key in ["SLACK_BOT_TOKEN", "SLACK_DEFAULT_CHANNEL"]:
            if not values.get(key, "").strip():
                missing_slack.append(key)

    account_format_errors: list[str] = []
    if effective_account and not _ACCOUNT_NUMBER_PATTERN.fullmatch(effective_account):
        account_format_errors.append(
            "KIS account number must be exactly 8 digits (example: 12345678)."
        )

    account_product_code = values.get("KIS_ACCOUNT_PRODUCT_CODE", "").strip()
    if not _ACCOUNT_PRODUCT_CODE_PATTERN.fullmatch(account_product_code):
        account_format_errors.append(
            "KIS_ACCOUNT_PRODUCT_CODE must be exactly 2 digits (example: 01)."
        )

    ok = not mode_errors and not missing_required and not missing_slack and not account_format_errors

    typer.echo("")
    if mode_errors:
        typer.echo("KIS mode configuration errors:")
        for msg in mode_errors:
            typer.echo(f"  - {msg}")

    if missing_required:
        typer.echo("Missing required keys:")
        for key in missing_required:
            typer.echo(f"  - {key}")

    if advisory_messages:
        typer.echo("KIS fallback warnings:")
        for msg in advisory_messages:
            typer.echo(f"  - {msg}")

    if missing_slack:
        typer.echo("Slack enabled but missing keys:")
        for key in missing_slack:
            typer.echo(f"  - {key}")

    if account_format_errors:
        typer.echo("Account format errors:")
        for error in account_format_errors:
            typer.echo(f"  - {error}")
        typer.echo("Fix: run `stock-manager setup` and enter 8-digit account + 2-digit product code.")

    typer.echo("")
    if ok:
        typer.echo("Doctor result: OK")
    else:
        typer.echo("Doctor result: NOT OK")
        typer.echo("Next step: run `stock-manager setup` to (re)configure.")

    return DoctorResult(ok=ok, env_path=env_path)
