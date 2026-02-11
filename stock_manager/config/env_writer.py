"""Read/write helpers for `.env` files.

We use python-dotenv's `set_key` to safely update keys with quoting, while
keeping the implementation testable and OS-portable.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import set_key


class EnvWriteError(RuntimeError):
    pass


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup_file(path: Path) -> Path | None:
    """Create a timestamped backup of `path` if it exists."""
    if not path.exists():
        return None
    backup = path.with_name(f"{path.name}.backup.{_timestamp()}")
    shutil.copy2(path, backup)
    return backup


def ensure_env_file(env_path: Path, *, example_path: Path | None = None, reset: bool = False) -> None:
    """Ensure `.env` exists, optionally resetting from `.env.example`.

    Behavior:
    - If reset is True: backup existing `.env` (if any) and recreate from example or empty.
    - If `.env` missing: create from example or empty.
    """
    env_path = Path(env_path)
    example_path = Path(example_path) if example_path is not None else None

    if reset and env_path.exists():
        backup_file(env_path)
        env_path.unlink()

    if env_path.exists():
        return

    if example_path is not None and example_path.is_file():
        shutil.copy2(example_path, env_path)
    else:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text("", encoding="utf-8")


def set_env_vars(env_path: Path, updates: dict[str, str]) -> None:
    """Update keys in `.env` using safe quoting.

    Raises:
        EnvWriteError: if any value contains a newline (dotenv is line-based).
    """
    env_path = Path(env_path)
    for key, value in updates.items():
        if "\n" in value or "\r" in value:
            raise EnvWriteError(f"{key} value contains a newline; refusing to write to .env.")
        # Always quote to reduce parsing surprises and avoid accidental shell expansion.
        set_key(str(env_path), key, value, quote_mode="always", export=False, encoding="utf-8")


@dataclass(frozen=True)
class EnvParseWarning:
    line_no: int
    message: str
    line: str


def scan_env_file(env_path: Path) -> list[EnvParseWarning]:
    """Best-effort scan for common `.env` footguns and obvious corruption."""
    env_path = Path(env_path)
    if not env_path.exists():
        return [EnvParseWarning(0, "Missing .env file", "")]

    warnings: list[EnvParseWarning] = []
    for idx, raw in enumerate(env_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            warnings.append(EnvParseWarning(idx, "Line has no '=' (not a KEY=VALUE assignment)", raw))
            continue
        key, value = line.split("=", 1)
        if not key or any(c.isspace() for c in key):
            warnings.append(EnvParseWarning(idx, "Suspicious key (empty or contains whitespace)", raw))
        # Heuristic: prompts accidentally captured into .env values.
        suspicious_tokens = ["Enter ", "[Step", "[OK]", "[ERROR]", "[WARN]"]
        if any(tok in value for tok in suspicious_tokens):
            warnings.append(EnvParseWarning(idx, "Suspicious value (looks like setup output was captured)", raw))
    return warnings

