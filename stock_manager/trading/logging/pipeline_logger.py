"""NDJSON pipeline logger with daily rotation and 12 event types.

Writes one JSON object per line to daily-rotated files. Thread-safe via
RLock. Each log entry includes timestamp, session_id, event type, and
event-specific payload.

File naming: {prefix}-{YYYYMMDD}.ndjson
"""

import json
import threading
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


class PipelineJsonLogger:
    """NDJSON logger for trading pipeline events.

    Writes structured JSON events to daily-rotated files. Each line is a
    self-contained JSON object (NDJSON format) for easy streaming and parsing.

    Args:
        log_dir: Directory for log files (created if missing).
        prefix: Filename prefix (default: "pipeline").
    """

    def __init__(self, log_dir: Path, prefix: str = "pipeline") -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._prefix = prefix
        self._session_id = str(uuid.uuid4())[:8]
        self._lock = threading.RLock()

    def _write(self, event: dict[str, Any]) -> None:
        """Write single NDJSON line to daily file.

        Adds timestamp and session_id automatically. Uses default=str
        for serializing Decimal, datetime, and enum values.
        """
        event["timestamp"] = datetime.now().isoformat()
        event["session_id"] = self._session_id
        today = datetime.now().strftime("%Y%m%d")
        filepath = self._log_dir / f"{self._prefix}-{today}.ndjson"
        with self._lock:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    # --- 12 typed event methods ---

    def log_state_change(
        self,
        symbol: str,
        from_state: str,
        to_state: str,
        reason: str,
    ) -> None:
        """Log a pipeline state transition."""
        self._write({
            "event": "state_change",
            "symbol": symbol,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
        })

    def log_screening_complete(
        self,
        symbol: str,
        snapshot_summary: dict[str, Any],
    ) -> None:
        """Log completion of market data screening."""
        self._write({
            "event": "screening_complete",
            "symbol": symbol,
            "snapshot_summary": snapshot_summary,
        })

    def log_agent_vote(
        self,
        symbol: str,
        persona_id: str,
        action: str,
        conviction: float,
        reasoning: str,
        target_price: Decimal | None = None,
    ) -> None:
        """Log an individual persona agent's vote."""
        self._write({
            "event": "agent_vote",
            "symbol": symbol,
            "persona_id": persona_id,
            "action": action,
            "conviction": conviction,
            "reasoning": reasoning,
            "target_price": target_price,
        })

    def log_advisory_vote(
        self,
        symbol: str,
        innovation_score: float,
        disruption_assessment: str,
    ) -> None:
        """Log Cathie Wood advisory (non-binding) vote."""
        self._write({
            "event": "advisory_vote",
            "symbol": symbol,
            "innovation_score": innovation_score,
            "disruption_assessment": disruption_assessment,
        })

    def log_consensus_result(
        self,
        symbol: str,
        passed: bool,
        buy_count: int,
        total_count: int,
        avg_conviction: float,
        categories: dict[str, int],
    ) -> None:
        """Log the final consensus voting result."""
        self._write({
            "event": "consensus_result",
            "symbol": symbol,
            "passed": passed,
            "buy_count": buy_count,
            "total_count": total_count,
            "avg_conviction": avg_conviction,
            "categories": categories,
        })

    def log_buy_decision(
        self,
        symbol: str,
        price: Decimal,
        quantity: int,
        order_type: str,
        stop_loss: Decimal,
    ) -> None:
        """Log a buy decision before order execution."""
        self._write({
            "event": "buy_decision",
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "order_type": order_type,
            "stop_loss": stop_loss,
        })

    def log_order_executed(
        self,
        symbol: str,
        order_id: str,
        executed_price: Decimal,
        executed_quantity: int,
    ) -> None:
        """Log a confirmed order execution from the broker."""
        self._write({
            "event": "order_executed",
            "symbol": symbol,
            "order_id": order_id,
            "executed_price": executed_price,
            "executed_quantity": executed_quantity,
        })

    def log_condition_check(
        self,
        symbol: str,
        return_pct: float,
        holding_days: int,
    ) -> None:
        """Log a periodic position condition check."""
        self._write({
            "event": "condition_check",
            "symbol": symbol,
            "return_pct": return_pct,
            "holding_days": holding_days,
        })

    def log_condition_warning(
        self,
        symbol: str,
        condition: str,
        progress: float,
        threshold: float,
    ) -> None:
        """Log a warning when a condition approaches its threshold."""
        self._write({
            "event": "condition_warning",
            "symbol": symbol,
            "condition": condition,
            "progress": progress,
            "threshold": threshold,
        })

    def log_sell_trigger(
        self,
        symbol: str,
        trigger_reason: str,
        trigger_value: float,
        current_pnl: Decimal,
    ) -> None:
        """Log activation of a sell trigger."""
        self._write({
            "event": "sell_trigger",
            "symbol": symbol,
            "trigger_reason": trigger_reason,
            "trigger_value": trigger_value,
            "current_pnl": current_pnl,
        })

    def log_trade_complete(
        self,
        symbol: str,
        entry_price: Decimal,
        exit_price: Decimal,
        pnl: Decimal,
        holding_days: int,
        return_pct: float,
    ) -> None:
        """Log a fully completed trade (bought and sold)."""
        self._write({
            "event": "trade_complete",
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "holding_days": holding_days,
            "return_pct": return_pct,
        })

    def log_error(
        self,
        symbol: str,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log an error with optional context."""
        self._write({
            "event": "error",
            "symbol": symbol,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
        })
