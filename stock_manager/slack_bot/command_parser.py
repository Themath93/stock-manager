"""Parse /sm slash command text into structured parameters."""
from __future__ import annotations
import shlex
from dataclasses import dataclass, field

_VALID_SUBCOMMANDS = {"start", "stop", "status", "config", "help"}


@dataclass
class ParsedCommand:
    subcommand: str  # "start", "stop", "status", "config"
    strategy: str | None = None
    symbols: tuple[str, ...] = ()
    duration_sec: int = 0
    is_mock: bool | None = None
    order_quantity: int = 1
    run_interval_sec: float = 60.0
    error: str | None = None  # set if parsing failed


def parse_command(text: str) -> ParsedCommand:
    """Parse /sm command text.

    Examples:
        "start" -> ParsedCommand(subcommand="start")
        "start --strategy consensus --symbols 005930,000660"
            -> ParsedCommand(subcommand="start", strategy="consensus", symbols=("005930", "000660"))
        "start --mock" -> ParsedCommand(subcommand="start", is_mock=True)
        "start --duration 3600" -> ParsedCommand(subcommand="start", duration_sec=3600)
        "stop" -> ParsedCommand(subcommand="stop")
        "status" -> ParsedCommand(subcommand="status")
        "config" -> ParsedCommand(subcommand="config")
        "" -> ParsedCommand(subcommand="help")
        "unknown" -> ParsedCommand(subcommand="unknown", error="Unknown subcommand: unknown")
    """
    text = text.strip()
    if not text:
        return ParsedCommand(subcommand="help")

    try:
        tokens = shlex.split(text)
    except ValueError as exc:
        return ParsedCommand(subcommand="help", error=f"Parse error: {exc}")

    subcommand = tokens[0].lower()
    if subcommand not in _VALID_SUBCOMMANDS:
        return ParsedCommand(subcommand=subcommand, error=f"Unknown subcommand: {subcommand}")

    result = ParsedCommand(subcommand=subcommand)
    args = tokens[1:]
    i = 0
    while i < len(args):
        flag = args[i]
        if flag == "--strategy":
            i += 1
            if i >= len(args):
                result.error = "--strategy requires a value"
                return result
            result.strategy = args[i]
        elif flag == "--symbols":
            i += 1
            if i >= len(args):
                result.error = "--symbols requires a value"
                return result
            result.symbols = tuple(
                s.strip().upper() for s in args[i].split(",") if s.strip()
            )
        elif flag == "--duration":
            i += 1
            if i >= len(args):
                result.error = "--duration requires a value"
                return result
            try:
                result.duration_sec = int(args[i])
            except ValueError:
                result.error = f"--duration must be an integer, got: {args[i]}"
                return result
        elif flag == "--mock":
            result.is_mock = True
        elif flag == "--no-mock":
            result.is_mock = False
        elif flag == "--order-quantity":
            i += 1
            if i >= len(args):
                result.error = "--order-quantity requires a value"
                return result
            try:
                result.order_quantity = int(args[i])
            except ValueError:
                result.error = f"--order-quantity must be an integer, got: {args[i]}"
                return result
        elif flag == "--run-interval":
            i += 1
            if i >= len(args):
                result.error = "--run-interval requires a value"
                return result
            try:
                result.run_interval_sec = float(args[i])
            except ValueError:
                result.error = f"--run-interval must be a number, got: {args[i]}"
                return result
        else:
            result.error = f"Unknown flag: {flag}"
            return result
        i += 1

    return result
