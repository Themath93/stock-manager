from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx

from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.adapters.broker.kis.config import KISConfig


def _mock_oauth_response(*, access_token: str = "token123", expires_in: int = 86400) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "access_token_token_expired": "2099-01-01 00:00:00",
    }
    return resp


def test_authenticate_writes_and_uses_disk_cache(tmp_path: Path, monkeypatch) -> None:
    cache_file = tmp_path / "kis_token.json"
    monkeypatch.setenv("KIS_APP_KEY", "test_app_key_12345")
    monkeypatch.setenv("KIS_APP_SECRET", "test_app_secret_67890")
    monkeypatch.setenv("KIS_USE_MOCK", "false")
    monkeypatch.setenv("KIS_TOKEN_CACHE_ENABLED", "true")
    monkeypatch.setenv("KIS_TOKEN_CACHE_PATH", str(cache_file))

    config = KISConfig(_env_file=None)

    http_client_1 = MagicMock(spec=httpx.Client)
    http_client_1.post.return_value = _mock_oauth_response(access_token="cached_token_abc")

    client_1 = KISRestClient(config=config, client=http_client_1)
    token_1 = client_1.authenticate()
    assert token_1.access_token == "cached_token_abc"
    assert cache_file.exists()

    http_client_2 = MagicMock(spec=httpx.Client)
    client_2 = KISRestClient(config=config, client=http_client_2)
    token_2 = client_2.authenticate()

    assert token_2.access_token == "cached_token_abc"
    http_client_2.post.assert_not_called()


def test_authenticate_ignores_expired_cache(tmp_path: Path, monkeypatch) -> None:
    cache_file = tmp_path / "kis_token.json"
    monkeypatch.setenv("KIS_APP_KEY", "test_app_key_12345")
    monkeypatch.setenv("KIS_APP_SECRET", "test_app_secret_67890")
    monkeypatch.setenv("KIS_USE_MOCK", "false")
    monkeypatch.setenv("KIS_TOKEN_CACHE_ENABLED", "true")
    monkeypatch.setenv("KIS_TOKEN_CACHE_PATH", str(cache_file))

    # Create an expired cache entry manually.
    expired = datetime.now(timezone.utc) - timedelta(hours=1)
    cache_file.write_text(
        json.dumps(
            {
                "version": 1,
                "api_base_url": "https://openapi.koreainvestment.com:9443",
                "oauth_path": "/oauth2/tokenP",
                "appkey_sha256": hashlib.sha256("test_app_key_12345".encode()).hexdigest(),
                "issued_at": expired.isoformat(),
                "expires_at": expired.isoformat(),
                "expires_in": 86400,
                "token_type": "Bearer",
                "access_token": "stale",
            }
        ),
        encoding="utf-8",
    )

    config = KISConfig(_env_file=None)
    http_client = MagicMock(spec=httpx.Client)
    http_client.post.return_value = _mock_oauth_response(access_token="fresh_token")

    client = KISRestClient(config=config, client=http_client)
    token = client.authenticate()
    assert token.access_token == "fresh_token"
    http_client.post.assert_called()
