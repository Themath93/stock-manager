from __future__ import annotations

from pathlib import Path

import pytest

from stock_manager.config.paths import find_project_root, require_project_root


def test_find_project_root_finds_pyproject(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    child = root / "a" / "b" / "c"
    child.mkdir(parents=True)

    assert find_project_root(child) == root


def test_require_project_root_raises_when_missing(tmp_path: Path) -> None:
    start = tmp_path / "nope"
    start.mkdir()

    with pytest.raises(RuntimeError, match="pyproject.toml"):
        require_project_root(start)

