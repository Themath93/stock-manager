"""Tests for scripts/validate_kis_endpoint_policy.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_kis_endpoint_policy.py"


def _write_wrapper_file(root: Path, relative_path: str, content: str) -> None:
    target = root / "stock_manager" / "adapters" / "broker" / "kis" / "apis" / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _run_policy_check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_endpoint_policy_passes_for_relative_paths(tmp_path: Path) -> None:
    _write_wrapper_file(
        tmp_path,
        "domestic_stock/info.py",
        'path = "/uapi/domestic-stock/v1/quotations/search-info"\n',
    )
    # oauth module is excluded from this policy scan.
    _write_wrapper_file(
        tmp_path,
        "oauth/oauth.py",
        'KIS_BASE_URL_REAL = "https://openapi.koreainvestment.com:9443"\n',
    )

    result = _run_policy_check(tmp_path)

    assert result.returncode == 0
    assert "[endpoint-policy] OK" in result.stdout


def test_endpoint_policy_fails_on_absolute_base_url_assignment(tmp_path: Path) -> None:
    _write_wrapper_file(
        tmp_path,
        "domestic_stock/info.py",
        '_BASE_URL = "https://api.koreainvestment.com"\npath = f"{_BASE_URL}/uapi/test"\n',
    )

    result = _run_policy_check(tmp_path)

    assert result.returncode == 1
    assert "absolute `_BASE_URL` assignment is forbidden" in result.stdout


def test_endpoint_policy_fails_on_absolute_path_assignment(tmp_path: Path) -> None:
    _write_wrapper_file(
        tmp_path,
        "domestic_stock/info.py",
        'path = "https://openapi.koreainvestment.com:9443/uapi/test"\n',
    )

    result = _run_policy_check(tmp_path)

    assert result.returncode == 1
    assert "absolute endpoint URL in `path` assignment is forbidden" in result.stdout
