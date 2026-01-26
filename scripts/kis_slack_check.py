import os
import sys
from decimal import Decimal
from pathlib import Path

from stock_manager.adapters.broker.kis import KISConfig, KISRestClient
from stock_manager.utils import SlackClient

REQUIRED_ENV = [
    "ACCOUNT_ID",
    "SLACK_BOT_TOKEN",
    "SLACK_CHANNEL_ID",
]

KIS_KEY_ENV_CANDIDATES = [
    "KIS_KIS_APP_KEY",
    "KIS_APP_KEY",
]

KIS_SECRET_ENV_CANDIDATES = [
    "KIS_KIS_APP_SECRET",
    "KIS_APP_SECRET",
]


def load_dotenv() -> None:
    """Load .env from repo root if present (does not override existing env)."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"")
        if key and key not in os.environ:
            os.environ[key] = value


def pick_first(keys: list[str]) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def mask_account(account_id: str) -> str:
    if len(account_id) < 4:
        return "***"
    return f"{account_id[:2]}***{account_id[-2:]}"


def main() -> int:
    load_dotenv()

    missing = [key for key in REQUIRED_ENV if not os.getenv(key)]
    app_key = pick_first(KIS_KEY_ENV_CANDIDATES)
    app_secret = pick_first(KIS_SECRET_ENV_CANDIDATES)
    if not app_key:
        missing.append("KIS_KIS_APP_KEY or KIS_APP_KEY")
    if not app_secret:
        missing.append("KIS_KIS_APP_SECRET or KIS_APP_SECRET")

    if missing:
        print("Missing env vars:", ", ".join(missing))
        return 1

    account_id = os.environ["ACCOUNT_ID"].strip()

    config = KISConfig(kis_app_key=app_key, kis_app_secret=app_secret)
    client = KISRestClient(config)
    try:
        cash: Decimal = client.get_cash(account_id)
    finally:
        client.close()

    slack = SlackClient(
        token=os.environ["SLACK_BOT_TOKEN"].strip(),
        default_channel=os.environ["SLACK_CHANNEL_ID"].strip(),
    )

    message = (
        f"KIS cash ok | mode={config.mode} | account={mask_account(account_id)} | "
        f"cash={cash}"
    )
    result = slack.post_message(message, level="info")

    if not result.success:
        print("Slack error:", result.error)
        return 2

    print("Slack sent:", result.ref)
    return 0


if __name__ == "__main__":
    sys.exit(main())
