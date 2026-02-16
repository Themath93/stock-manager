from __future__ import annotations

from pathlib import Path
import json
import subprocess
from typing import Any, cast

from stock_manager.qa import mock_gate

from stock_manager.qa.mock_gate import (
    _tail,
    GateCheck,
    parse_args,
    run_gate,
    write_gate_report,
)


def test_tail_keeps_short_text() -> None:
    assert _tail("short", limit=20) == "short"


def test_tail_truncates_long_text() -> None:
    long_text = "x" * 2500
    result = _tail(long_text, limit=2000)

    assert len(result) == 2000
    assert result == "x" * 2000


def test_run_gate_passes_when_all_critical_checks_pass() -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command, **kwargs):
        calls.append(tuple(command))
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    checks = (
        GateCheck(name="c1", command=("cmd1",), critical=True),
        GateCheck(name="c2", command=("cmd2",), critical=False),
    )

    report = run_gate(checks=checks, fail_fast=True, runner=fake_runner)
    checks_result = cast(list[dict[str, Any]], report["checks"])

    assert report["pass"] is True
    assert len(checks_result) == 2
    assert calls == [("cmd1",), ("cmd2",)]


def test_run_gate_fails_fast_on_first_critical_failure() -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command, **kwargs):
        calls.append(tuple(command))
        if command[0] == "bad":
            return subprocess.CompletedProcess(args=command, returncode=2, stdout="", stderr="boom")
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    checks = (
        GateCheck(name="bad", command=("bad",), critical=True),
        GateCheck(name="later", command=("later",), critical=True),
    )

    report = run_gate(checks=checks, fail_fast=True, runner=fake_runner)
    checks_result = cast(list[dict[str, Any]], report["checks"])

    assert report["pass"] is False
    assert len(checks_result) == 1
    assert calls == [("bad",)]


def test_run_gate_records_timeout_as_failure() -> None:
    def fake_runner(command, **kwargs):
        raise subprocess.TimeoutExpired(cmd=command, timeout=10, output="out", stderr="err")

    checks = (GateCheck(name="hang", command=("hang",), critical=True),)

    report = run_gate(checks=checks, fail_fast=True, runner=fake_runner)
    checks_result = cast(list[dict[str, Any]], report["checks"])

    assert report["pass"] is False
    result = checks_result[0]
    assert result["name"] == "hang"
    assert result["passed"] is False
    assert result["timed_out"] is True
    assert result["exit_code"] == 124
    assert result["stdout_tail"] == "out"
    assert result["stderr_tail"] == "err"


def test_write_gate_report_creates_json_artifact(tmp_path: Path) -> None:
    report = {
        "mode": "mock",
        "pass": True,
        "timestamp": "2026-02-15T00:00:00+00:00",
        "checks": [
            {
                "name": "unit",
                "critical": True,
                "passed": True,
                "command": "pytest",
                "exit_code": 0,
                "duration_sec": 0.1,
                "timed_out": False,
                "stdout_tail": "",
                "stderr_tail": "",
            }
        ],
    }

    artifact = tmp_path / ".sisyphus" / "evidence" / "mock-promotion-gate.json"
    write_gate_report(report, artifact)

    loaded = json.loads(artifact.read_text(encoding="utf-8"))
    assert loaded["pass"] is True
    assert loaded["mode"] == "mock"
    assert loaded["checks"][0]["name"] == "unit"


def test_parse_args_has_expected_defaults() -> None:
    args = parse_args([])

    assert args.emit == ".sisyphus/evidence/mock-promotion-gate.json"
    assert args.continue_on_fail is False


def test_parse_args_supports_continue_on_fail() -> None:
    args = parse_args(["--continue-on-fail"])

    assert args.continue_on_fail is True


def test_main_runs_all_checks_when_continue_on_fail_is_set(monkeypatch, tmp_path) -> None:
    report = {
        "mode": "mock",
        "pass": False,
        "timestamp": "2026-02-15T00:00:00+00:00",
        "finished_at": "2026-02-15T00:00:00+00:00",
        "fail_fast": False,
        "checks": [
            {
                "name": "unit",
                "passed": False,
                "critical": True,
                "command": "cmd",
                "exit_code": 1,
                "duration_sec": 0.1,
                "timed_out": False,
                "stdout_tail": "",
                "stderr_tail": "",
            }
        ],
    }

    run_calls = []

    def fake_run_gate(*, checks, fail_fast, cwd=None, runner=None):
        run_calls.append(fail_fast)
        return report

    monkeypatch.setattr("stock_manager.qa.mock_gate.run_gate", fake_run_gate)
    emitted = tmp_path / "gate.json"
    monkeypatch.setattr(
        "stock_manager.qa.mock_gate.write_gate_report",
        lambda _report, path: Path(path).write_text(json.dumps(_report), encoding="utf-8"),
    )

    return_code = mock_gate.main(["--emit", str(emitted), "--continue-on-fail"])

    assert return_code == 1
    assert run_calls == [False]
    assert emitted.read_text(encoding="utf-8") == json.dumps(report)


def test_main_prints_success_when_checks_pass(monkeypatch, tmp_path, capsys) -> None:
    report = {
        "mode": "mock",
        "pass": True,
        "timestamp": "2026-02-15T00:00:00+00:00",
        "finished_at": "2026-02-15T00:00:00+00:00",
        "fail_fast": True,
        "checks": [
            {
                "name": "unit",
                "passed": True,
                "critical": True,
                "command": "cmd",
                "exit_code": 0,
                "duration_sec": 0.1,
                "timed_out": False,
                "stdout_tail": "",
                "stderr_tail": "",
            }
        ],
    }

    def fake_run_gate(*, checks, fail_fast, cwd=None, runner=None):
        return report

    emitted = tmp_path / "gate.json"
    monkeypatch.setattr("stock_manager.qa.mock_gate.run_gate", fake_run_gate)
    monkeypatch.setattr(
        "stock_manager.qa.mock_gate.write_gate_report",
        lambda _report, path: Path(path).write_text(json.dumps(_report), encoding="utf-8"),
    )

    return_code = mock_gate.main(["--emit", str(emitted)])
    output = capsys.readouterr().out

    assert return_code == 0
    assert "[unit] PASS (0.1s)" in output
    assert "Mock QA gate passed. Artifact:" in output
    assert str(emitted) in output
