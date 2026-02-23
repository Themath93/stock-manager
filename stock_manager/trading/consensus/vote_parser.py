"""Parse LLM text responses into structured PersonaVote instances.

Supports both English and Korean (한국어) action keywords and field labels.
Falls back to ABSTAIN with 0.0 conviction on any parse failure.
"""

from __future__ import annotations

import logging
import re

from stock_manager.trading.personas.models import PersonaCategory, PersonaVote, VoteAction

logger = logging.getLogger(__name__)


class VoteParser:
    """Parse LLM text responses into structured :class:`PersonaVote`.

    The parser is intentionally lenient: it searches the full response text
    for action, conviction, and reasoning fields using regex patterns that
    accept both English and Korean labels.
    """

    # Supports English and Korean action keywords
    ACTION_PATTERNS: dict[VoteAction, str] = {
        VoteAction.BUY: r"\b(BUY|매수)\b",
        VoteAction.SELL: r"\b(SELL|매도)\b",
        VoteAction.HOLD: r"\b(HOLD|보유)\b",
    }

    CONVICTION_PATTERN = r"(?:CONVICTION|확신도)[:\s]*([0-9]*\.?[0-9]+)"
    REASONING_PATTERN = r"(?:REASONING|분석|근거)[:\s]*(.*?)(?:\n|$)"

    @staticmethod
    def parse(
        response: str,
        persona_name: str,
        category: PersonaCategory,
    ) -> PersonaVote:
        """Parse an LLM response string into a :class:`PersonaVote`.

        Args:
            response: Raw text response from the LLM.
            persona_name: Name of the persona that generated the response.
            category: Category of the persona.

        Returns:
            A populated :class:`PersonaVote`. Defaults to ABSTAIN / 0.0
            conviction if parsing fails.
        """
        if not response or not response.strip():
            logger.warning(
                "Empty LLM response for persona %s, defaulting to ABSTAIN",
                persona_name,
            )
            return _abstain_vote(persona_name, category, "Empty LLM response")

        try:
            action = _extract_action(response)
            conviction = _extract_conviction(response)
            reasoning = _extract_reasoning(response)
        except Exception:
            logger.exception(
                "Failed to parse LLM response for persona %s", persona_name
            )
            return _abstain_vote(persona_name, category, "Parse error")

        return PersonaVote(
            persona_name=persona_name,
            action=action,
            conviction=conviction,
            reasoning=reasoning,
            criteria_met={},
            category=category,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_action(response: str) -> VoteAction:
    """Extract vote action from response text.

    Scans for ACTION: line first, then falls back to searching the
    entire response. Returns ABSTAIN if no action keyword is found.
    """
    # Try to find an ACTION: line first for precision
    action_line_match = re.search(
        r"(?:ACTION|행동)[:\s]*(.*?)(?:\n|$)", response, re.IGNORECASE
    )
    search_text = action_line_match.group(1) if action_line_match else response

    for vote_action, pattern in VoteParser.ACTION_PATTERNS.items():
        if re.search(pattern, search_text, re.IGNORECASE):
            return vote_action

    # If ACTION line was found but no match, search full response
    if action_line_match:
        for vote_action, pattern in VoteParser.ACTION_PATTERNS.items():
            if re.search(pattern, response, re.IGNORECASE):
                return vote_action

    return VoteAction.ABSTAIN


def _extract_conviction(response: str) -> float:
    """Extract conviction score from response text.

    Returns 0.0 if no conviction value is found. Clamps to [0.0, 1.0].
    """
    match = re.search(VoteParser.CONVICTION_PATTERN, response, re.IGNORECASE)
    if not match:
        return 0.0
    try:
        value = float(match.group(1))
        return max(0.0, min(1.0, value))
    except (ValueError, IndexError):
        return 0.0


def _extract_reasoning(response: str) -> str:
    """Extract reasoning text from response.

    Returns a fallback message if no reasoning field is found.
    """
    match = re.search(VoteParser.REASONING_PATTERN, response, re.IGNORECASE)
    if match:
        reasoning = match.group(1).strip()
        if reasoning:
            return reasoning
    return "LLM reasoning not extracted"


def _abstain_vote(
    persona_name: str, category: PersonaCategory, reason: str
) -> PersonaVote:
    """Create an ABSTAIN vote with zero conviction."""
    return PersonaVote(
        persona_name=persona_name,
        action=VoteAction.ABSTAIN,
        conviction=0.0,
        reasoning=reason,
        criteria_met={},
        category=category,
    )
