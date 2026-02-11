from __future__ import annotations

from pathlib import Path

from stock_manager.cli.doctor import run_doctor
from stock_manager.config import paths


def test_doctor_not_ok_when_required_missing(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / ".env").write_text("KIS_APP_KEY=\n", encoding="utf-8")

    monkeypatch.chdir(repo)
    paths.project_root_cached.cache_clear()

    result = run_doctor(verbose=False)
    assert result.ok is False


def test_doctor_ok_when_required_present(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / ".env").write_text(
        "KIS_APP_KEY=test\nKIS_APP_SECRET=test\nSLACK_ENABLED=false\n", encoding="utf-8"
    )

    monkeypatch.chdir(repo)
    paths.project_root_cached.cache_clear()

    result = run_doctor(verbose=False)
    assert result.ok is True

