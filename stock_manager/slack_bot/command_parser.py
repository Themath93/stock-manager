"""Parse /sm slash command text into structured parameters."""

from __future__ import annotations
import shlex
from dataclasses import dataclass

_VALID_SUBCOMMANDS = {"start", "stop", "status", "config", "help", "balance", "orders", "sell-all"}
_VALID_LLM_MODES = {"off", "selective"}


@dataclass
class ParsedCommand:
    subcommand: str  # "start", "stop", "status", "config"
    strategy: str | None = None
    symbols: tuple[str, ...] = ()
    duration_sec: int = 0
    is_mock: bool | None = None
    order_quantity: int = 1
    run_interval_sec: float = 60.0
    strategy_auto_discover: bool = False
    strategy_discovery_limit: int = 20
    strategy_discovery_fallback_symbols: tuple[str, ...] = ()
    llm_mode: str = "off"
    confirm: bool = False
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
    discovery_limit_specified = False
    fallback_symbols_specified = False
    llm_mode_specified = False
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
            result.symbols = tuple(s.strip().upper() for s in args[i].split(",") if s.strip())
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
        elif flag == "--confirm":
            result.confirm = True
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
        elif flag == "--auto-discover":
            result.strategy_auto_discover = True
        elif flag == "--discovery-limit":
            i += 1
            if i >= len(args):
                result.error = "--discovery-limit requires a value"
                return result
            try:
                result.strategy_discovery_limit = int(args[i])
            except ValueError:
                result.error = f"--discovery-limit must be an integer, got: {args[i]}"
                return result
            discovery_limit_specified = True
            if result.strategy_discovery_limit <= 0:
                result.error = (
                    f"--discovery-limit must be a positive integer, got: {args[i]}"
                )
                return result
        elif flag == "--fallback-symbols":
            i += 1
            if i >= len(args):
                result.error = "--fallback-symbols requires a value"
                return result
            result.strategy_discovery_fallback_symbols = tuple(
                s.strip().upper() for s in args[i].split(",") if s.strip()
            )
            fallback_symbols_specified = True
        elif flag == "--llm-mode":
            i += 1
            if i >= len(args):
                result.error = "--llm-mode requires a value"
                return result
            result.llm_mode = args[i].strip().lower()
            llm_mode_specified = True
            if result.llm_mode not in _VALID_LLM_MODES:
                result.error = (
                    f"--llm-mode must be one of: off, selective (got: {args[i]})"
                )
                return result
        else:
            result.error = f"Unknown flag: {flag}"
            return result
        i += 1

    if result.subcommand == "start":
        if result.strategy is None:
            if result.strategy_auto_discover:
                result.error = "--auto-discover requires --strategy."
                return result
            if discovery_limit_specified:
                result.error = "--discovery-limit requires --strategy."
                return result
            if fallback_symbols_specified:
                result.error = "--fallback-symbols requires --strategy."
                return result
            if llm_mode_specified:
                result.error = "--llm-mode requires --strategy."
                return result
        if fallback_symbols_specified and not result.strategy_auto_discover:
            result.error = "--fallback-symbols requires --auto-discover."
            return result
        if result.llm_mode == "selective":
            normalized_strategy = (
                "".join(char for char in result.strategy.lower().strip() if char.isalnum())
                if result.strategy
                else ""
            )
            if normalized_strategy not in {"consensus", "consensusstrategy"}:
                result.error = "--llm-mode selective requires --strategy consensus."
                return result

    return result
