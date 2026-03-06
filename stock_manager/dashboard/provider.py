"""Dashboard data provider for pipeline status."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DashboardData:
    """Snapshot of pipeline status for dashboard display."""

    total_symbols: int = 0
    active_positions: int = 0
    pipeline_states: dict[str, int] = field(default_factory=dict)
    recent_trades: list[dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DashboardProvider:
    """Provides read-only dashboard data from pipeline state."""

    def __init__(self, pipeline_runner: Any = None) -> None:
        self._runner = pipeline_runner

    def get_status(self) -> DashboardData:
        """Return current dashboard status snapshot."""
        if self._runner is None:
            return DashboardData()

        entries = self._runner.entries
        states: dict[str, int] = {}
        active = 0
        for entry in entries.values():
            state_name = entry.state.name
            states[state_name] = states.get(state_name, 0) + 1
            if state_name in ("BOUGHT", "MONITORING"):
                active += 1

        return DashboardData(
            total_symbols=len(entries),
            active_positions=active,
            pipeline_states=states,
        )
