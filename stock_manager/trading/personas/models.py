"""Shared data models for the consensus trading pipeline.

Defines vote types, persona categories, market snapshots, and consensus results
used across all investor personas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VoteAction(Enum):
    """Action a persona can recommend."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    ABSTAIN = "abstain"
    ADVISORY = "advisory"


class PersonaCategory(Enum):
    """Classification of investor persona style."""

    VALUE = "value"
    GROWTH = "growth"
    MOMENTUM = "momentum"
    MACRO = "macro"
    QUANTITATIVE = "quantitative"
    INNOVATION = "innovation"


# ---------------------------------------------------------------------------
# Vote dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PersonaVote:
    """A single persona's rule-based evaluation result."""

    persona_name: str
    action: VoteAction
    conviction: float  # 0.0 - 1.0
    reasoning: str
    criteria_met: dict[str, bool]
    category: PersonaCategory


@dataclass
class AdvisoryVote:
    """Non-binding advisory vote (e.g. Wood innovation assessment)."""

    persona_name: str  # Always "Wood"
    action: VoteAction  # Always ADVISORY
    innovation_score: float  # 0.0 - 1.0
    disruption_assessment: str
    category: PersonaCategory  # Always INNOVATION


# ---------------------------------------------------------------------------
# MarketSnapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarketSnapshot:
    """Immutable point-in-time market data for a single symbol.

    46 fields across 8 groups. Uses Decimal for monetary values, float for
    indicators, int for counts, and Optional types where data may be absent.
    """

    # --- Group 1: Price / Quote (12 fields) ---
    symbol: str = ""
    name: str = ""
    market: str = ""
    sector: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    current_price: Decimal = Decimal("0")
    open_price: Decimal = Decimal("0")
    high_price: Decimal = Decimal("0")
    low_price: Decimal = Decimal("0")
    prev_close: Decimal = Decimal("0")
    volume: int = 0
    avg_volume_20d: int = 0

    # --- Group 2: Valuation (7 fields) ---
    market_cap: Decimal = Decimal("0")
    per: float = 0.0
    pbr: float = 0.0
    eps: Decimal = Decimal("0")
    bps: Decimal = Decimal("0")
    dividend_yield: float = 0.0
    roe: float = 0.0

    # --- Group 3: Financial Health (5 fields) ---
    current_ratio: float = 0.0
    debt_to_equity: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    free_cash_flow: Decimal = Decimal("0")

    # --- Group 4: Growth (4 fields) ---
    revenue_growth_yoy: float = 0.0
    earnings_growth_yoy: float = 0.0
    revenue_growth_3yr: Optional[float] = None
    earnings_growth_3yr: Optional[float] = None

    # --- Group 5: Technical (8 fields) ---
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    rsi_14: float = 0.0
    macd_signal: float = 0.0
    bollinger_position: float = 0.0
    adx_14: float = 0.0
    atr_14: float = 0.0

    # --- Group 6: Balance Sheet (7 fields) ---
    total_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    current_assets: Decimal = Decimal("0")
    cash_and_equivalents: Decimal = Decimal("0")
    inventory: Decimal = Decimal("0")
    accounts_receivable: Decimal = Decimal("0")
    shares_outstanding: int = 0

    # --- Group 7: History (4 fields) ---
    price_52w_high: Decimal = Decimal("0")
    price_52w_low: Decimal = Decimal("0")
    years_positive_earnings: int = 0
    years_dividends_paid: int = 0

    # --- Group 8: Market Context (4 fields) ---
    kospi_index: Optional[Decimal] = None
    kospi_per: Optional[float] = None
    market_sentiment: str = ""
    vkospi: Optional[float] = None


# ---------------------------------------------------------------------------
# Request / Result
# ---------------------------------------------------------------------------


@dataclass
class EvaluationRequest:
    """Request to evaluate a symbol through the consensus pipeline."""

    symbol: str
    snapshot: MarketSnapshot
    context: dict = field(default_factory=dict)


@dataclass
class ConsensusResult:
    """Aggregated result from all persona votes."""

    symbol: str
    votes: list[PersonaVote]
    advisory_vote: AdvisoryVote | None
    buy_count: int
    sell_count: int
    hold_count: int
    abstain_count: int
    passes_threshold: bool
    avg_conviction: float
    category_diversity: int
