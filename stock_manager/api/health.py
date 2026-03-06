"""Health check endpoint for monitoring."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class HealthStatus:
    """Health check response."""

    status: str = "ok"
    version: str = "1.0.0"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_seconds: float = 0.0


_start_time = time.monotonic()


def get_health() -> HealthStatus:
    """Return current health status."""
    return HealthStatus(
        uptime_seconds=round(time.monotonic() - _start_time, 2),
    )
