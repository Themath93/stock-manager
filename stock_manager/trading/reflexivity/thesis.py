"""Soros-style investment thesis management."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

class CycleStage(Enum):
    INCEPTION = "inception"       # New trend, unrecognized
    ACCELERATION = "acceleration" # Positive feedback strengthening
    TESTING = "testing"           # Minor corrections
    EUPHORIA = "euphoria"         # Unsustainable exuberance
    TWILIGHT = "twilight"         # Smart money exiting
    COLLAPSE = "collapse"         # Feedback loop reverses

@dataclass
class MarketThesis:
    """Soros-style investment thesis."""

    # Core Thesis
    symbol: str
    perception: str          # Current market narrative
    reality: str             # Actual fundamental conditions
    feedback_loop: str       # How perception affects reality
    prediction: str          # Expected outcome

    # Reflexivity Metrics
    perception_reality_gap: Decimal   # Mispricing magnitude
    feedback_strength: Decimal        # Loop intensity (0.0-1.0)
    cycle_stage: CycleStage          # Boom-bust phase

    # Invalidation
    invalidation_triggers: list[str] = field(default_factory=list)

    # Asymmetric Payoff
    potential_upside: Decimal = Decimal("0")
    potential_downside: Decimal = Decimal("0")
    asymmetry_ratio: Decimal = Decimal("0")  # Must be >= 3.0 for high conviction
    conviction: Decimal = Decimal("0.5")     # 0.0-1.0

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_validated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid_entry(self) -> bool:
        """Check if thesis supports entry."""
        return (
            self.cycle_stage in [CycleStage.INCEPTION, CycleStage.ACCELERATION, CycleStage.TESTING] and
            self.asymmetry_ratio >= Decimal("3.0") and
            self.conviction >= Decimal("0.5")
        )

    def update_validation(self) -> None:
        """Update last validation timestamp."""
        self.last_validated = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Serialize for persistence."""
        return {
            "symbol": self.symbol,
            "perception": self.perception,
            "reality": self.reality,
            "feedback_loop": self.feedback_loop,
            "prediction": self.prediction,
            "perception_reality_gap": str(self.perception_reality_gap),
            "feedback_strength": str(self.feedback_strength),
            "cycle_stage": self.cycle_stage.value,
            "invalidation_triggers": self.invalidation_triggers,
            "potential_upside": str(self.potential_upside),
            "potential_downside": str(self.potential_downside),
            "asymmetry_ratio": str(self.asymmetry_ratio),
            "conviction": str(self.conviction),
            "created_at": self.created_at.isoformat(),
            "last_validated": self.last_validated.isoformat(),
        }
