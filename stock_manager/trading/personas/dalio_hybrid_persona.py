"""Dalio hybrid persona: rule-based Dalio + optional LLM verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from stock_manager.trading.llm.circuit_breaker import CircuitBreaker
from stock_manager.trading.llm.config import InvocationCounter, LLMConfig
from stock_manager.trading.personas.dalio_persona import DalioPersona
from stock_manager.trading.personas.hybrid import HybridPersona
from stock_manager.trading.personas.models import MarketSnapshot, PersonaVote

if TYPE_CHECKING:
    from stock_manager.trading.logging.pipeline_logger import PipelineJsonLogger


class DalioHybridPersona(HybridPersona):
    """Hybrid wrapper that keeps Dalio's rule logic and trigger policy unchanged."""

    def __init__(
        self,
        *,
        base_persona: DalioPersona | None = None,
        circuit_breaker: CircuitBreaker,
        llm_config: LLMConfig | None = None,
        invocation_counter: InvocationCounter | None = None,
        pipeline_logger: PipelineJsonLogger | None = None,
    ) -> None:
        super().__init__(
            circuit_breaker=circuit_breaker,
            llm_config=llm_config,
            invocation_counter=invocation_counter,
            pipeline_logger=pipeline_logger,
        )
        self._base = base_persona or DalioPersona()
        self.name = self._base.name
        self.category = self._base.category

    @property
    def llm_trigger_rate(self) -> float:
        return self._base.llm_trigger_rate

    def should_trigger_llm(self, vote: PersonaVote) -> bool:
        return self._base.should_trigger_llm(vote)

    def screen_rule(self, snapshot: MarketSnapshot) -> PersonaVote:
        return self._base.screen_rule(snapshot)
