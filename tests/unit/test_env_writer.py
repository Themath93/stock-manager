from __future__ import annotations

from pathlib import Path

import pytest

from stock_manager.config.env_writer import (
    EnvWriteError,
    ensure_env_file,
    scan_env_file,
    set_env_vars,
)


def test_ensure_env_file_copies_example(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    example.write_text("FOO=\n", encoding="utf-8")

    env_path = tmp_path / ".env"
    ensure_env_file(env_path, example_path=example, reset=False)

    assert env_path.exists()
    assert "FOO" in env_path.read_text(encoding="utf-8")


def test_set_env_vars_writes_quoted_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("", encoding="utf-8")

    set_env_vars(env_path, {"FOO": "bar"})

    text = env_path.read_text(encoding="utf-8")
    assert "FOO=" in text
    assert ("FOO='bar'" in text) or ('FOO="bar"' in text)


def test_set_env_vars_rejects_newlines(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("", encoding="utf-8")

    with pytest.raises(EnvWriteError):
        set_env_vars(env_path, {"BAD": "a\nb"})


def test_scan_env_file_detects_broken_lines(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("NOEQUALS\nK=Enter KIS App Key:\n", encoding="utf-8")

    warnings = scan_env_file(env_path)
    assert any("no '='" in w.message for w in warnings)
    assert any("Suspicious value" in w.message for w in warnings)
