"""Disk-backed access token cache for KIS OAuth.

Why:
- KIS OAuth token issuance is rate-limited (e.g. 1/min).
- Access tokens are valid for ~24h.

This cache prevents unnecessary re-issuance across processes and restarts.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from stock_manager.adapters.broker.kis.config import KISAccessToken


TOKEN_CACHE_VERSION = 1
TOKEN_MIN_TTL_SECONDS = 60  # don't reuse tokens that are about to expire


@dataclass(frozen=True)
class CachedAccessToken:
    token: KISAccessToken
    expires_at: datetime


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _dt_from_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_cached_token(
    path: Path,
    *,
    app_key: str,
    api_base_url: str,
    oauth_path: str,
    min_ttl_seconds: int = TOKEN_MIN_TTL_SECONDS,
) -> CachedAccessToken | None:
    """Load a cached token if it matches config and is not expired."""
    path = Path(path)
    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if raw.get("version") != TOKEN_CACHE_VERSION:
        return None
    if raw.get("api_base_url") != api_base_url:
        return None
    if raw.get("oauth_path") != oauth_path:
        return None
    if raw.get("appkey_sha256") != _sha256_hex(app_key):
        return None

    access_token = (raw.get("access_token") or "").strip()
    if not access_token:
        return None

    try:
        expires_at = _dt_from_iso(raw.get("expires_at") or "")
    except Exception:
        return None

    now = datetime.now(timezone.utc)
    if expires_at <= now + timedelta(seconds=min_ttl_seconds):
        return None

    token_type = raw.get("token_type") or "Bearer"
    expires_in = int(raw.get("expires_in") or 86400)
    token = KISAccessToken(access_token=access_token, token_type=token_type, expires_in=expires_in)
    return CachedAccessToken(token=token, expires_at=expires_at)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp"

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())

    # Restrict permissions (best-effort). Apply before rename on platforms that support it.
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass

    tmp.replace(path)

    try:
        os.chmod(path, 0o600)
    except Exception:
        pass

    # Ensure directory entry is durable.
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        pass


def save_cached_token(
    path: Path,
    *,
    token: KISAccessToken,
    expires_at: datetime,
    app_key: str,
    api_base_url: str,
    oauth_path: str,
    issued_at: datetime | None = None,
    access_token_token_expired: str | None = None,
) -> None:
    """Persist token to disk (atomic, best-effort 0600 permissions)."""
    issued_at = issued_at or datetime.now(timezone.utc)

    payload: dict[str, Any] = {
        "version": TOKEN_CACHE_VERSION,
        "api_base_url": api_base_url,
        "oauth_path": oauth_path,
        "appkey_sha256": _sha256_hex(app_key),
        "issued_at": _dt_to_iso(issued_at),
        "expires_at": _dt_to_iso(expires_at),
        "expires_in": token.expires_in,
        "token_type": token.token_type,
        "access_token": token.access_token,
    }
    if access_token_token_expired:
        payload["access_token_token_expired"] = access_token_token_expired

    _atomic_write_json(Path(path), payload)

