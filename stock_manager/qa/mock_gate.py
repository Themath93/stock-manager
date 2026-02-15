from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence
import argparse
import json
import shlex
import subprocess
import time


@dataclass(frozen=True)
class GateCheck:
    name: str
    command: tuple[str, ...]
    critical: bool = True
    timeout_sec: float = 900.0


@dataclass
class GateRunResult:
    name: str
    command: str
    critical: bool
    passed: bool
    exit_code: int
    duration_sec: float
    timed_out: bool = False
    stdout_tail: str = ""
    stderr_tail: str = ""


def build_default_checks() -> tuple[GateCheck, ...]:
    return (
        GateCheck(
            name="unit_engine_risk_executor",
            command=(
                "uv",
                "run",
                "pytest",
                "tests/unit/test_engine.py",
                "tests/unit/test_risk.py",
                "tests/unit/test_order_executor.py",
                "--no-cov",
                "-q",
            ),
            critical=True,
        ),
        GateCheck(
            name="smoke_auth_price_balance",
            command=("uv", "run", "stock-manager", "smoke"),
            critical=True,
        ),
        GateCheck(
            name="unit_cli_live_gate",
            command=(
                "uv",
                "run",
                "pytest",
                "tests/unit/test_cli_main.py::test_trade_execute_blocks_live_without_promotion_gate_even_with_confirm_live",
                "tests/unit/test_cli_main.py::test_run_blocks_live_without_promotion_gate",
                "--no-cov",
                "-q",
            ),
            critical=True,
        ),
        GateCheck(
            name="unit_state_roundtrip",
            command=(
                "uv",
                "run",
                "pytest",
                "tests/unit/test_state.py::TestTradingState::test_risk_controls_round_trip",
                "--no-cov",
                "-q",
            ),
            critical=False,
        ),
    )


def _tail(text: str, *, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def run_gate(
    *,
    checks: Sequence[GateCheck],
    fail_fast: bool = True,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    results: list[GateRunResult] = []
    started_at = datetime.now(timezone.utc)

    for check in checks:
        began = time.perf_counter()
        command = tuple(check.command)
        command_text = " ".join(shlex.quote(part) for part in command)

        try:
            completed = runner(
                command,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=check.timeout_sec,
                check=False,
            )
            passed = completed.returncode == 0
            result = GateRunResult(
                name=check.name,
                command=command_text,
                critical=check.critical,
                passed=passed,
                exit_code=int(completed.returncode),
                duration_sec=round(time.perf_counter() - began, 3),
                stdout_tail=_tail(completed.stdout or ""),
                stderr_tail=_tail(completed.stderr or ""),
            )
        except subprocess.TimeoutExpired as exc:
            result = GateRunResult(
                name=check.name,
                command=command_text,
                critical=check.critical,
                passed=False,
                exit_code=124,
                duration_sec=round(time.perf_counter() - began, 3),
                timed_out=True,
                stdout_tail=_tail((exc.stdout or "") if isinstance(exc.stdout, str) else ""),
                stderr_tail=_tail((exc.stderr or "") if isinstance(exc.stderr, str) else ""),
            )

        results.append(result)

        if fail_fast and result.critical and not result.passed:
            break

    critical_failed = any(item.critical and not item.passed for item in results)
    report = {
        "mode": "mock",
        "pass": not critical_failed,
        "timestamp": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "fail_fast": fail_fast,
        "checks": [asdict(item) for item in results],
    }
    return report


def write_gate_report(report: dict[str, object], emit_path: Path) -> None:
    emit_path.parent.mkdir(parents=True, exist_ok=True)
    emit_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="mock_qa_gate")
    parser.add_argument(
        "--emit",
        default=".sisyphus/evidence/mock-promotion-gate.json",
        help="Output artifact path",
    )
    parser.add_argument(
        "--continue-on-fail",
        action="store_true",
        help="Run all checks even after first critical failure",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_gate(checks=build_default_checks(), fail_fast=not args.continue_on_fail)
    emit_path = Path(args.emit)
    write_gate_report(report, emit_path)

    for check in report["checks"]:
        line = (
            f"[{check['name']}] {'PASS' if check['passed'] else 'FAIL'} ({check['duration_sec']}s)"
        )
        print(line)

    if report["pass"]:
        print(f"Mock QA gate passed. Artifact: {emit_path}")
        return 0

    print(f"Mock QA gate failed. Artifact: {emit_path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
