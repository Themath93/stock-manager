"""HybridPersona: 2-stage evaluation (rule-based + optional LLM verification).

Stage 1: Rule-based screen via screen_rule() (fast, deterministic)
Stage 2: Optional LLM verification via screen_llm() when should_trigger_llm() is True

Concrete persona subclasses inherit from HybridPersona instead of InvestorPersona
to gain LLM augmentation. The screen_rule() method remains abstract and must be
implemented by each persona.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from stock_manager.trading.personas.base import InvestorPersona
from stock_manager.trading.personas.models import (
    MarketSnapshot,
    PersonaVote,
)
from stock_manager.trading.llm.client import sync_persona_query
from stock_manager.trading.llm.circuit_breaker import CircuitBreaker
from stock_manager.trading.llm.config import InvocationCounter, LLMConfig
from stock_manager.trading.consensus.vote_parser import VoteParser
from stock_manager.trading.personas.prompts.prompt_loader import load_persona_prompt

if TYPE_CHECKING:
    from stock_manager.trading.logging.pipeline_logger import PipelineJsonLogger

logger = logging.getLogger(__name__)


class HybridPersona(InvestorPersona):
    """Persona with optional LLM 2nd-stage verification.

    Concrete persona subclasses inherit from this instead of
    :class:`InvestorPersona` to gain LLM augmentation capability.  The
    :meth:`screen_rule` method remains abstract and must be implemented by
    each persona.

    When :meth:`should_trigger_llm` returns ``True`` **and** the circuit
    breaker allows it, the LLM is consulted to verify or override the
    rule-based vote.  If the LLM is unavailable (circuit breaker OPEN,
    invocation limit reached, query failure), the rule-based vote is
    returned unchanged -- graceful degradation.

    Args:
        circuit_breaker: Shared circuit breaker protecting LLM calls.
        llm_config: LLM settings (model, timeout, limits).  Defaults to
            :class:`LLMConfig` with stock values.
        invocation_counter: Optional daily rate limiter.
        pipeline_logger: Optional structured logger for agent vote events.
    """

    def __init__(
        self,
        circuit_breaker: CircuitBreaker,
        llm_config: LLMConfig | None = None,
        invocation_counter: InvocationCounter | None = None,
        pipeline_logger: PipelineJsonLogger | None = None,
    ) -> None:
        self._circuit_breaker = circuit_breaker
        self._llm_config = llm_config or LLMConfig()
        self._invocation_counter = invocation_counter
        self._pipeline_logger = pipeline_logger
        self._system_prompt: str | None = None

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------

    @property
    def system_prompt(self) -> str:
        """Persona system prompt loaded from YAML (lazy, LRU-cached)."""
        if self._system_prompt is None:
            self._system_prompt = load_persona_prompt(self.name.lower())
        return self._system_prompt

    def _build_llm_prompt(
        self,
        snapshot: MarketSnapshot,
        rule_vote: PersonaVote,
    ) -> str:
        """Build the user prompt for LLM 2nd-stage verification.

        Includes symbol identification, key financials, technical indicators,
        the rule-based vote context, and the expected response format.

        Args:
            snapshot: Current market data for the symbol.
            rule_vote: The vote produced by :meth:`screen_rule`.

        Returns:
            Formatted prompt string ready for ``sync_persona_query``.
        """
        criteria_lines = "\n".join(
            f"  - {k}: {'PASS' if v else 'FAIL'}"
            for k, v in rule_vote.criteria_met.items()
        )

        return (
            f"## Symbol: {snapshot.symbol} ({snapshot.name})\n"
            f"Market: {snapshot.market} | Sector: {snapshot.sector}\n\n"
            f"## Price\n"
            f"Current: {snapshot.current_price} | "
            f"52w High: {snapshot.price_52w_high} | "
            f"52w Low: {snapshot.price_52w_low}\n\n"
            f"## Valuation\n"
            f"PER: {snapshot.per:.2f} | PBR: {snapshot.pbr:.2f} | "
            f"ROE: {snapshot.roe:.2f}% | EPS: {snapshot.eps} | "
            f"Dividend Yield: {snapshot.dividend_yield:.2f}%\n\n"
            f"## Financial Health\n"
            f"Debt/Equity: {snapshot.debt_to_equity:.2f} | "
            f"Current Ratio: {snapshot.current_ratio:.2f} | "
            f"Operating Margin: {snapshot.operating_margin:.2f}% | "
            f"Net Margin: {snapshot.net_margin:.2f}%\n\n"
            f"## Growth\n"
            f"Revenue YoY: {snapshot.revenue_growth_yoy:.2f}% | "
            f"Earnings YoY: {snapshot.earnings_growth_yoy:.2f}%\n\n"
            f"## Technical Indicators\n"
            f"SMA20: {snapshot.sma_20:.2f} | SMA200: {snapshot.sma_200:.2f} | "
            f"RSI14: {snapshot.rsi_14:.2f} | MACD Signal: {snapshot.macd_signal:.4f} | "
            f"ADX14: {snapshot.adx_14:.2f} | ATR14: {snapshot.atr_14:.2f}\n\n"
            f"## Rule-Based Vote (1st Stage)\n"
            f"Action: {rule_vote.action.value} | "
            f"Conviction: {rule_vote.conviction:.2f}\n"
            f"Reasoning: {rule_vote.reasoning}\n"
            f"Criteria:\n{criteria_lines}\n\n"
            f"## Instructions\n"
            f"Review the data above and the rule-based vote. "
            f"Provide your independent assessment.\n\n"
            f"Respond in EXACTLY this format:\n"
            f"ACTION: BUY | SELL | HOLD\n"
            f"CONVICTION: 0.0-1.0\n"
            f"REASONING: <your analysis>\n"
        )

    # ------------------------------------------------------------------
    # LLM 2nd-stage
    # ------------------------------------------------------------------

    def screen_llm(
        self,
        snapshot: MarketSnapshot,
        rule_vote: PersonaVote,
    ) -> PersonaVote:
        """LLM 2nd-stage verification.

        1. Check circuit breaker -- if OPEN, return *rule_vote* unchanged.
        2. Check invocation counter limit (if configured).
        3. Build prompt with persona context, market data, and rule vote.
        4. Call :func:`sync_persona_query` (blocking, safe in thread pool).
        5. Record success/failure on the circuit breaker.
        6. Parse response via :class:`VoteParser`.
        7. Log as ``agent_vote`` event with ``_llm`` suffix on persona_id.
        8. Return the LLM-verified vote.

        On any failure the rule-based vote is returned unchanged (graceful
        degradation).

        Args:
            snapshot: Current market data.
            rule_vote: Vote from :meth:`screen_rule`.

        Returns:
            LLM-verified :class:`PersonaVote`, or *rule_vote* on fallback.
        """
        # 1. Circuit breaker gate
        if not self._circuit_breaker.allow_request():
            logger.info(
                "%s: Circuit breaker OPEN, using rule-based vote", self.name
            )
            return rule_vote

        # 2. Daily invocation limit gate
        if self._invocation_counter is not None:
            if not self._invocation_counter.allow_invocation(
                self._llm_config.daily_invocation_limit
            ):
                logger.info(
                    "%s: Daily invocation limit reached (%d), using rule-based vote",
                    self.name,
                    self._invocation_counter.count,
                )
                return rule_vote
            self._invocation_counter.increment()

        # 3. Build prompt
        prompt = self._build_llm_prompt(snapshot, rule_vote)

        # 4-5. Query LLM with circuit breaker bookkeeping
        try:
            response = sync_persona_query(
                prompt=prompt,
                system_prompt=self.system_prompt,
                model=self._llm_config.model,
                max_turns=self._llm_config.max_turns,
                timeout_sec=self._llm_config.timeout_sec,
                max_retries=self._llm_config.max_retries,
            )

            if response is None:
                logger.warning(
                    "%s: LLM returned empty response, using rule-based vote",
                    self.name,
                )
                self._circuit_breaker.record_failure()
                return rule_vote

            self._circuit_breaker.record_success()

        except Exception:
            logger.warning(
                "%s: LLM query failed, using rule-based vote",
                self.name,
                exc_info=True,
            )
            self._circuit_breaker.record_failure()
            return rule_vote

        # 6. Parse LLM response
        llm_vote = VoteParser.parse(response, self.name, self.category)

        # 7. Log LLM evaluation
        if self._pipeline_logger is not None:
            self._pipeline_logger.log_agent_vote(
                symbol=snapshot.symbol,
                persona_id=f"{self.name}_llm",
                action=llm_vote.action.value,
                conviction=llm_vote.conviction,
                reasoning=llm_vote.reasoning,
            )

        return llm_vote

    # ------------------------------------------------------------------
    # 2-stage evaluate override
    # ------------------------------------------------------------------

    def evaluate(self, snapshot: MarketSnapshot) -> PersonaVote:
        """Run 2-stage evaluation: rule-based, then optional LLM.

        Stage 1 always runs (:meth:`screen_rule`).  Stage 2 runs only when
        :meth:`should_trigger_llm` returns ``True``.

        **Merge logic** when both stages run:

        * **Agreement** (same action): boost conviction by 0.1 (capped at
          1.0).  Reasoning is prefixed ``[Hybrid]``.
        * **Disagreement**: use the LLM action with conviction set to
          ``min(llm, rule) * 0.8``.  Reasoning notes the override.

        Args:
            snapshot: Current market data.

        Returns:
            Final merged :class:`PersonaVote`.
        """
        rule_vote = self.screen_rule(snapshot)

        if not self.should_trigger_llm(rule_vote):
            return rule_vote

        llm_vote = self.screen_llm(snapshot, rule_vote)

        # screen_llm returns rule_vote itself on fallback (identity check)
        if llm_vote is rule_vote:
            return rule_vote

        # Merge: agreement vs disagreement
        if llm_vote.action == rule_vote.action:
            # Agreement -- boost conviction
            merged_conviction = min(1.0, rule_vote.conviction + 0.1)
            return PersonaVote(
                persona_name=self.name,
                action=rule_vote.action,
                conviction=merged_conviction,
                reasoning=(
                    f"[Hybrid] Rule + LLM agree: {llm_vote.reasoning}"
                ),
                criteria_met=rule_vote.criteria_met,
                category=self.category,
            )

        # Disagreement -- LLM overrides with reduced conviction
        merged_conviction = min(llm_vote.conviction, rule_vote.conviction) * 0.8
        return PersonaVote(
            persona_name=self.name,
            action=llm_vote.action,
            conviction=merged_conviction,
            reasoning=(
                f"[Hybrid] LLM override: {llm_vote.reasoning} "
                f"(rule said {rule_vote.action.value})"
            ),
            criteria_met=rule_vote.criteria_met,
            category=self.category,
        )
