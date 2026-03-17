"""Specification tests for VoteParser.

Each test documents an expected behavior of the LLM response parser.
"""

from unittest.mock import patch

from stock_manager.trading.consensus.vote_parser import VoteParser
from stock_manager.trading.personas.models import PersonaCategory, VoteAction


class TestVoteParser:
    """VoteParser behavior specifications."""

    def test_parses_standard_response(self):
        """Standard ACTION/CONVICTION/REASONING response parses correctly."""
        response = "ACTION: BUY\nCONVICTION: 0.8\nREASONING: Strong fundamentals"
        vote = VoteParser.parse(response, "TestPersona", PersonaCategory.VALUE)

        assert vote.action == VoteAction.BUY
        assert vote.conviction == 0.8
        assert vote.reasoning == "Strong fundamentals"
        assert vote.persona_name == "TestPersona"
        assert vote.category == PersonaCategory.VALUE

    def test_empty_response_returns_abstain(self):
        """Empty response yields ABSTAIN with 0.0 conviction."""
        vote = VoteParser.parse("", "TestPersona", PersonaCategory.VALUE)
        assert vote.action == VoteAction.ABSTAIN
        assert vote.conviction == 0.0

    def test_whitespace_only_response_returns_abstain(self):
        """Whitespace-only response also yields ABSTAIN."""
        vote = VoteParser.parse("   \n\t  ", "TestPersona", PersonaCategory.VALUE)
        assert vote.action == VoteAction.ABSTAIN

    def test_fallback_search_when_action_line_has_no_keyword(self):
        """When ACTION line contains no valid keyword, parser searches full text."""
        # ACTION line says "uncertain" (no keyword), but "BUY" appears later in text
        response = "ACTION: uncertain\nCONVICTION: 0.5\nI recommend BUY based on analysis"
        vote = VoteParser.parse(response, "TestPersona", PersonaCategory.VALUE)
        assert vote.action == VoteAction.BUY

    def test_conviction_clamped_above_one(self):
        """Conviction values above 1.0 are clamped to 1.0."""
        response = "ACTION: HOLD\nCONVICTION: 2.5\nREASONING: Very confident"
        vote = VoteParser.parse(response, "TestPersona", PersonaCategory.VALUE)
        assert vote.conviction == 1.0

    def test_missing_conviction_defaults_to_zero(self):
        """Response without CONVICTION field defaults to 0.0."""
        response = "ACTION: SELL\nREASONING: Overvalued"
        vote = VoteParser.parse(response, "TestPersona", PersonaCategory.VALUE)
        assert vote.conviction == 0.0

    def test_parse_exception_returns_abstain_with_parse_error(self):
        """Any exception during parsing yields ABSTAIN + 'Parse error'."""
        with patch(
            "stock_manager.trading.consensus.vote_parser._extract_action",
            side_effect=RuntimeError("boom"),
        ):
            vote = VoteParser.parse(
                "ACTION: BUY\nCONVICTION: 0.8",
                "TestPersona",
                PersonaCategory.VALUE,
            )
        assert vote.action == VoteAction.ABSTAIN
        assert vote.conviction == 0.0
        assert vote.reasoning == "Parse error"

    def test_korean_buy_keyword_recognized(self):
        """Korean 매수 keyword is recognized as BUY."""
        response = "ACTION: 매수\n확신도: 0.7\n근거: 저평가"
        vote = VoteParser.parse(response, "TestPersona", PersonaCategory.VALUE)
        assert vote.action == VoteAction.BUY

    def test_korean_sell_keyword_recognized(self):
        """Korean 매도 keyword is recognized as SELL."""
        response = "행동: 매도\n확신도: 0.6\n근거: 고평가"
        vote = VoteParser.parse(response, "TestPersona", PersonaCategory.VALUE)
        assert vote.action == VoteAction.SELL

    def test_korean_hold_keyword_recognized(self):
        """Korean 보유 keyword is recognized as HOLD."""
        response = "ACTION: 보유\nCONVICTION: 0.5\nREASONING: Wait and see"
        vote = VoteParser.parse(response, "TestPersona", PersonaCategory.VALUE)
        assert vote.action == VoteAction.HOLD

    def test_no_action_keyword_returns_abstain(self):
        """Response with no recognizable action keyword returns ABSTAIN."""
        response = "CONVICTION: 0.5\nREASONING: No clear direction"
        vote = VoteParser.parse(response, "TestPersona", PersonaCategory.VALUE)
        assert vote.action == VoteAction.ABSTAIN

    def test_conviction_value_error_returns_zero(self):
        """Malformed conviction match returns 0.0 gracefully."""
        from unittest.mock import MagicMock

        with patch("stock_manager.trading.consensus.vote_parser.re") as mock_re:
            # _extract_action needs re.search to work for ACTION matching
            # Set up re.search to return a match that causes ValueError on conviction
            action_match = MagicMock()
            action_match.group.return_value = "BUY"
            conviction_match = MagicMock()
            conviction_match.group.return_value = "not_a_number"
            reasoning_match = MagicMock()
            reasoning_match.group.return_value = "test reasoning"

            # re.search is called multiple times; route by pattern
            def search_side_effect(pattern, text, *args, **kwargs):
                if "CONVICTION" in pattern or "확신도" in pattern:
                    return conviction_match
                if "REASONING" in pattern or "분석" in pattern:
                    return reasoning_match
                if "ACTION" in pattern or "행동" in pattern:
                    return action_match
                # ACTION_PATTERNS check - return match for BUY
                if "BUY" in pattern:
                    return action_match
                return None

            mock_re.search.side_effect = search_side_effect
            mock_re.IGNORECASE = 0

            from stock_manager.trading.consensus.vote_parser import _extract_conviction

            result = _extract_conviction("CONVICTION: bad")
            assert result == 0.0
