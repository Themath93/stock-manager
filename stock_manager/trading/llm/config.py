"""LLM configuration and invocation counting.

Provides :class:`LLMConfig` for centralised settings (with env-var overrides)
and :class:`InvocationCounter` for thread-safe daily rate limiting that
resets at midnight KST.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class LLMConfig:
    """Immutable LLM configuration with environment variable overrides.

    All defaults can be overridden by calling :meth:`from_env` which reads
    the corresponding environment variables.
    """

    model: str = "claude-sonnet-4-6"
    cli_path: str = "~/.local/bin/claude"
    max_turns: int = 1
    timeout_sec: float = 30.0
    max_retries: int = 3
    cb_failure_threshold: int = 5
    cb_cooldown_sec: float = 60.0
    cb_sliding_window_sec: float = 300.0
    daily_invocation_limit: int | None = None
    log_all_invocations: bool = True

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Create an :class:`LLMConfig` populated from environment variables.

        Env vars read:
            ``CLAUDE_MODEL``, ``CLAUDE_CLI_PATH``, ``LLM_TIMEOUT_SEC``,
            ``LLM_MAX_RETRIES``, ``LLM_CB_FAILURE_THRESHOLD``,
            ``LLM_CB_COOLDOWN_SEC``, ``LLM_DAILY_LIMIT``.
        """
        return cls(
            model=os.environ.get("CLAUDE_MODEL", cls.model),
            cli_path=os.environ.get("CLAUDE_CLI_PATH", cls.cli_path),
            timeout_sec=float(os.environ.get("LLM_TIMEOUT_SEC", cls.timeout_sec)),
            max_retries=int(os.environ.get("LLM_MAX_RETRIES", cls.max_retries)),
            cb_failure_threshold=int(
                os.environ.get("LLM_CB_FAILURE_THRESHOLD", cls.cb_failure_threshold)
            ),
            cb_cooldown_sec=float(
                os.environ.get("LLM_CB_COOLDOWN_SEC", cls.cb_cooldown_sec)
            ),
            daily_invocation_limit=(
                int(v) if (v := os.environ.get("LLM_DAILY_LIMIT")) else None
            ),
        )


class InvocationCounter:
    """Thread-safe daily invocation counter. Resets at midnight KST.

    Used to enforce optional daily rate limits on LLM calls to control
    API spend.
    """

    def __init__(self) -> None:
        self._count: int = 0
        self._date: str = ""
        self._lock = threading.RLock()

    def increment(self) -> int:
        """Increment the counter and return the new value.

        Automatically resets if the KST date has changed since the last call.
        """
        with self._lock:
            today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
            if today != self._date:
                self._date = today
                self._count = 0
            self._count += 1
            return self._count

    @property
    def count(self) -> int:
        """Current invocation count for today (KST)."""
        with self._lock:
            return self._count

    def allow_invocation(self, limit: int | None) -> bool:
        """Check whether another invocation is permitted.

        Args:
            limit: Maximum daily invocations, or None for unlimited.

        Returns:
            True if the limit has not been reached (or is None).
        """
        if limit is None:
            return True
        with self._lock:
            return self._count < limit
