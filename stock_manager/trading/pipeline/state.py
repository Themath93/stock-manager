"""Pipeline states and entry tracking.

Defines the finite state machine for stock trading pipeline entries.
Each PipelineEntry tracks a symbol through: watchlist -> screening ->
evaluation -> consensus -> buy -> monitor -> sell lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Any


class PipelineState(Enum):
    """States a symbol can be in within the trading pipeline."""

    WATCHLIST = auto()
    SCREENING = auto()
    EVALUATING = auto()
    CONSENSUS_APPROVED = auto()
    CONSENSUS_REJECTED = auto()
    BUY_PENDING = auto()
    BOUGHT = auto()
    MONITORING = auto()
    SELL_PENDING = auto()
    SOLD = auto()
    ERROR = auto()


VALID_TRANSITIONS: dict[PipelineState, set[PipelineState]] = {
    PipelineState.WATCHLIST: {PipelineState.SCREENING, PipelineState.ERROR},
    PipelineState.SCREENING: {PipelineState.EVALUATING, PipelineState.ERROR},
    PipelineState.EVALUATING: {
        PipelineState.CONSENSUS_APPROVED,
        PipelineState.CONSENSUS_REJECTED,
        PipelineState.ERROR,
    },
    PipelineState.CONSENSUS_APPROVED: {PipelineState.BUY_PENDING, PipelineState.ERROR},
    PipelineState.CONSENSUS_REJECTED: {PipelineState.WATCHLIST, PipelineState.ERROR},
    PipelineState.BUY_PENDING: {PipelineState.BOUGHT, PipelineState.ERROR},
    PipelineState.BOUGHT: {PipelineState.MONITORING, PipelineState.ERROR},
    PipelineState.MONITORING: {PipelineState.SELL_PENDING, PipelineState.ERROR},
    PipelineState.SELL_PENDING: {PipelineState.SOLD, PipelineState.ERROR},
    PipelineState.SOLD: set(),  # Terminal
    PipelineState.ERROR: {PipelineState.WATCHLIST},  # Recovery
}


@dataclass
class PipelineEntry:
    """Tracks a single symbol through the trading pipeline.

    Attributes:
        symbol: Ticker symbol (e.g. "AAPL").
        state: Current pipeline state.
        entered_at: Timestamp when the current state was entered.
        consensus_result: ConsensusResult from persona voting (Any to avoid circular import).
        buy_price: Executed buy price.
        buy_quantity: Number of shares bought.
        current_price: Latest market price.
        unrealized_pnl: Current unrealized profit/loss.
        trailing_stop: Trailing stop-loss price.
        history: List of (previous_state, entered_at) tuples.
        error_message: Description of error if state is ERROR.
    """

    symbol: str
    state: PipelineState = PipelineState.WATCHLIST
    entered_at: datetime = field(default_factory=datetime.now)
    consensus_result: Any = None  # ConsensusResult (avoid circular import)
    buy_price: Decimal | None = None
    buy_quantity: int | None = None
    current_price: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    trailing_stop: Decimal | None = None
    history: list[tuple[PipelineState, datetime]] = field(default_factory=list)
    error_message: str | None = None

    def transition(self, new_state: PipelineState) -> None:
        """Validate and execute state transition.

        Args:
            new_state: Target state to transition to.

        Raises:
            ValueError: If the transition is not allowed by VALID_TRANSITIONS.
        """
        allowed = VALID_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {self.state.name} -> {new_state.name}"
            )
        self.history.append((self.state, self.entered_at))
        self.state = new_state
        self.entered_at = datetime.now()
