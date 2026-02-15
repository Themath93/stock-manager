from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import typer

from stock_manager.adapters.broker.kis.config import KISConfig
from stock_manager.config.env_writer import (
    backup_file,
    ensure_env_file,
    scan_env_file,
    set_env_vars,
)
from stock_manager.config.paths import require_project_root

_ACCOUNT_NUMBER_PATTERN = re.compile(r"^\d{8}$")
_ACCOUNT_PRODUCT_CODE_PATTERN = re.compile(r"^\d{2}$")


@dataclass(frozen=True)
class SetupResult:
    env_path: Path
    verified_kis: bool
    verified_slack: bool


def _mask(value: str) -> str:
    v = value.strip()
    if len(v) <= 8:
        return "****"
    return f"{v[:4]}...{v[-4:]}"


def _verify_kis(config: KISConfig) -> bool:
    """Best-effort KIS token issuance verification. Never raises."""
    try:
        app_key = config.app_key
        app_secret = config.app_secret
        if app_key is None or app_secret is None:
            typer.echo("KIS verify: FAILED (missing app credentials)")
            return False

        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key.get_secret_value(),
            "appsecret": app_secret.get_secret_value(),
        }
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "appkey": app_key.get_secret_value(),
            "appsecret": app_secret.get_secret_value(),
            "custtype": "P",
        }
        with httpx.Client(base_url=config.api_base_url, timeout=15.0) as client:
            resp = client.post(config.oauth_path, json=payload, headers=headers)
        data = resp.json()
        token = data.get("access_token", "")
        if token:
            typer.echo(f"KIS verify: OK (token {_mask(token)})")
            return True
        msg = data.get("msg1") or data.get("error_description") or json.dumps(data)[:200]
        typer.echo(f"KIS verify: FAILED ({resp.status_code}) {msg}")
        return False
    except Exception as e:
        typer.echo(f"KIS verify: FAILED ({e})")
        return False


def _verify_slack(bot_token: str) -> bool:
    """Best-effort Slack auth.test verification. Never raises."""
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {bot_token}"},
            )
        data = resp.json()
        if data.get("ok") is True:
            user = data.get("user") or ""
            team = data.get("team") or ""
            typer.echo(f"Slack verify: OK (@{user} / {team})")
            return True
        err = data.get("error") or json.dumps(data)[:200]
        typer.echo(f"Slack verify: FAILED ({resp.status_code}) {err}")
        return False
    except Exception as e:
        typer.echo(f"Slack verify: FAILED ({e})")
        return False


def _prompt_account_number(label: str, *, required: bool) -> str:
    value = typer.prompt(label, default="").strip()
    while True:
        if not value:
            if not required:
                return ""
            value = typer.prompt(f"{label} (cannot be empty in selected mode)").strip()
            continue
        if _ACCOUNT_NUMBER_PATTERN.fullmatch(value):
            return value
        value = typer.prompt(f"{label} must be exactly 8 digits (example: 12345678)").strip()


def _prompt_product_code() -> str:
    value = typer.prompt("KIS_ACCOUNT_PRODUCT_CODE (2 digits)", default="01").strip() or "01"
    while not _ACCOUNT_PRODUCT_CODE_PATTERN.fullmatch(value):
        value = typer.prompt(
            "KIS_ACCOUNT_PRODUCT_CODE must be exactly 2 digits (example: 01)"
        ).strip()
    return value


def run_setup(*, reset: bool = False, skip_verify: bool = False) -> SetupResult:
    root = require_project_root()
    env_path = root / ".env"
    example_path = root / ".env.example"

    if env_path.exists():
        backup = backup_file(env_path)
        if backup is not None:
            typer.echo(f"Backed up .env -> {backup.name}")

    ensure_env_file(env_path, example_path=example_path, reset=reset)

    warnings = scan_env_file(env_path)
    if warnings:
        typer.echo("")
        typer.echo("Note: existing .env looks suspicious. Consider `stock-manager setup --reset`.")

    typer.echo("")
    typer.echo("KIS (Required)")
    kis_use_mock = typer.confirm("Use paper trading (KIS_USE_MOCK=true)?", default=True)
    if kis_use_mock:
        typer.echo("Selected mode: MOCK (paper trading)")
    else:
        typer.echo("Selected mode: REAL (live trading)")
    typer.echo("Tip: you can fill both REAL and MOCK credentials for quick mode switching.")

    typer.echo("")
    typer.echo("[REAL] Credentials")
    kis_app_key = typer.prompt("KIS_APP_KEY (real)", hide_input=True, default="").strip()
    kis_app_secret = typer.prompt("KIS_APP_SECRET (real)", hide_input=True, default="").strip()
    real_account_number = _prompt_account_number(
        "KIS_ACCOUNT_NUMBER (real, 8 digits)", required=not kis_use_mock
    )

    if not kis_use_mock:
        while not kis_app_key:
            kis_app_key = typer.prompt(
                "KIS_APP_KEY (real, cannot be empty in real mode)",
                hide_input=True,
            ).strip()
        while not kis_app_secret:
            kis_app_secret = typer.prompt(
                "KIS_APP_SECRET (real, cannot be empty in real mode)",
                hide_input=True,
            ).strip()

    typer.echo("")
    typer.echo("[MOCK] Credentials")
    kis_mock_app_key = typer.prompt("KIS_MOCK_APP_KEY (mock)", hide_input=True, default="").strip()
    kis_mock_secret = typer.prompt("KIS_MOCK_SECRET (mock)", hide_input=True, default="").strip()
    mock_account_number = _prompt_account_number(
        "KIS_MOCK_ACCOUNT_NUMBER (mock, 8 digits)", required=kis_use_mock
    )

    if kis_use_mock:
        while not kis_mock_app_key:
            kis_mock_app_key = typer.prompt(
                "KIS_MOCK_APP_KEY (cannot be empty in mock mode)",
                hide_input=True,
            ).strip()
        while not kis_mock_secret:
            kis_mock_secret = typer.prompt(
                "KIS_MOCK_SECRET (cannot be empty in mock mode)",
                hide_input=True,
            ).strip()
    else:
        if not kis_mock_app_key or not kis_mock_secret or not mock_account_number:
            typer.echo(
                "Note: mock credentials/account are optional now, but needed when switching to KIS_USE_MOCK=true."
            )

    if kis_use_mock and (not kis_app_key or not kis_app_secret or not real_account_number):
        typer.echo(
            "Note: real credentials/account are optional in mock mode. "
            "If omitted, set them later before switching to real trading."
        )

    product_code = _prompt_product_code()

    typer.echo("")
    slack_enabled = typer.confirm("Configure Slack notifications?", default=False)
    slack_bot_token = ""
    slack_default_channel = ""
    slack_order_channel = ""
    slack_alert_channel = ""
    slack_min_level = "INFO"
    if slack_enabled:
        slack_bot_token = typer.prompt("SLACK_BOT_TOKEN (xoxb-...)", hide_input=True).strip()
        while not slack_bot_token.startswith("xoxb-"):
            slack_bot_token = typer.prompt(
                "SLACK_BOT_TOKEN must start with xoxb-", hide_input=True
            ).strip()
        slack_default_channel = typer.prompt(
            "SLACK_DEFAULT_CHANNEL (e.g. C123... or #general)"
        ).strip()
        slack_order_channel = typer.prompt(
            "SLACK_ORDER_CHANNEL (optional; default=SLACK_DEFAULT_CHANNEL)",
            default=slack_default_channel,
        ).strip()
        slack_alert_channel = typer.prompt(
            "SLACK_ALERT_CHANNEL (optional; default=SLACK_DEFAULT_CHANNEL)",
            default=slack_default_channel,
        ).strip()
        slack_min_level = (
            typer.prompt(
                "SLACK_MIN_LEVEL (DEBUG/INFO/WARNING/ERROR)",
                default="INFO",
            )
            .strip()
            .upper()
            or "INFO"
        )

    updates: dict[str, str] = {
        "KIS_APP_KEY": kis_app_key,
        "KIS_APP_SECRET": kis_app_secret,
        "KIS_MOCK_APP_KEY": kis_mock_app_key,
        "KIS_MOCK_SECRET": kis_mock_secret,
        "KIS_USE_MOCK": "true" if kis_use_mock else "false",
        "KIS_ACCOUNT_NUMBER": real_account_number,
        "KIS_MOCK_ACCOUNT_NUMBER": mock_account_number,
        "KIS_ACCOUNT_PRODUCT_CODE": product_code,
        "SLACK_ENABLED": "true" if slack_enabled else "false",
        "SLACK_BOT_TOKEN": slack_bot_token,
        "SLACK_DEFAULT_CHANNEL": slack_default_channel,
        "SLACK_ORDER_CHANNEL": slack_order_channel,
        "SLACK_ALERT_CHANNEL": slack_alert_channel,
        "SLACK_MIN_LEVEL": slack_min_level,
    }

    set_env_vars(env_path, updates)
    typer.echo("")
    typer.echo("Saved configuration to .env")

    verified_kis = False
    verified_slack = False
    if not skip_verify:
        typer.echo("")
        typer.echo("Verification")
        try:
            config_kwargs: dict[str, Any] = {"_env_file": str(env_path)}
            config = KISConfig(**config_kwargs)  # type: ignore[call-arg]
            verified_kis = _verify_kis(config)
        except Exception as e:
            typer.echo(f"KIS verify: FAILED (config) {e}")
            verified_kis = False
        if slack_enabled and slack_bot_token:
            verified_slack = _verify_slack(slack_bot_token)

    return SetupResult(env_path=env_path, verified_kis=verified_kis, verified_slack=verified_slack)
