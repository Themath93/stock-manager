from __future__ import annotations

from pathlib import Path
import json
import subprocess

from stock_manager.qa.mock_gate import GateCheck, run_gate, write_gate_report


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

    assert report["pass"] is True
    assert len(report["checks"]) == 2
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

    assert report["pass"] is False
    assert len(report["checks"]) == 1
    assert calls == [("bad",)]


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
