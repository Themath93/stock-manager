from __future__ import annotations

from pathlib import Path

from stock_manager.cli.doctor import run_doctor
from stock_manager.config import paths


def test_doctor_not_ok_when_required_missing(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / ".env").write_text(
        "KIS_USE_MOCK=false\n"
        "KIS_APP_KEY=\n"
        "KIS_APP_SECRET=\n"
        "KIS_ACCOUNT_NUMBER=\n"
        "KIS_ACCOUNT_PRODUCT_CODE=01\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)
    paths.project_root_cached.cache_clear()

    result = run_doctor(verbose=False)
    assert result.ok is False


def test_doctor_ok_when_required_present(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / ".env").write_text(
        (
            "KIS_USE_MOCK=true\n"
            "KIS_MOCK_APP_KEY=mock_key\n"
            "KIS_MOCK_SECRET=mock_secret\n"
            "KIS_MOCK_ACCOUNT_NUMBER=87654321\n"
            "KIS_ACCOUNT_PRODUCT_CODE=01\n"
            "SLACK_ENABLED=false\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)
    paths.project_root_cached.cache_clear()

    result = run_doctor(verbose=False)
    assert result.ok is True


def test_doctor_not_ok_when_account_number_invalid(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / ".env").write_text(
        (
            "KIS_USE_MOCK=false\n"
            "KIS_APP_KEY=real_key\n"
            "KIS_APP_SECRET=real_secret\n"
            "KIS_ACCOUNT_NUMBER=1234567890\n"
            "KIS_ACCOUNT_PRODUCT_CODE=01\n"
            "SLACK_ENABLED=false\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)
    paths.project_root_cached.cache_clear()

    result = run_doctor(verbose=False)
    assert result.ok is False


def test_doctor_not_ok_when_account_product_code_invalid(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / ".env").write_text(
        (
            "KIS_USE_MOCK=false\n"
            "KIS_APP_KEY=real_key\n"
            "KIS_APP_SECRET=real_secret\n"
            "KIS_ACCOUNT_NUMBER=12345678\n"
            "KIS_ACCOUNT_PRODUCT_CODE=1\n"
            "SLACK_ENABLED=false\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)
    paths.project_root_cached.cache_clear()

    result = run_doctor(verbose=False)
    assert result.ok is False


def test_doctor_mock_without_mock_credentials_is_not_ok(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / ".env").write_text(
        (
            "KIS_USE_MOCK=true\n"
            "KIS_APP_KEY=real_key\n"
            "KIS_APP_SECRET=real_secret\n"
            "KIS_ACCOUNT_NUMBER=12345678\n"
            "KIS_ACCOUNT_PRODUCT_CODE=01\n"
            "SLACK_ENABLED=false\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)
    paths.project_root_cached.cache_clear()

    result = run_doctor(verbose=False)
    captured = capsys.readouterr()

    assert result.ok is False
    assert "KIS_MOCK_APP_KEY" in captured.out
    assert "KIS_MOCK_SECRET" in captured.out
    assert "KIS_MOCK_ACCOUNT_NUMBER" in captured.out
    assert "fallback" not in captured.out.lower()


def test_doctor_mock_missing_both_mock_and_real_is_not_ok(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / ".env").write_text(
        "KIS_USE_MOCK=true\nKIS_ACCOUNT_PRODUCT_CODE=01\nSLACK_ENABLED=false\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)
    paths.project_root_cached.cache_clear()

    result = run_doctor(verbose=False)
    assert result.ok is False
