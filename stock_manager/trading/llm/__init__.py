"""LLM infrastructure for persona-augmented consensus trading.

Provides Claude Agent SDK integration, circuit breaker for fault tolerance,
configuration management, invocation counting, and vote parsing.
"""

from stock_manager.trading.llm.client import (
    async_persona_query,
    sync_persona_query,
)
from stock_manager.trading.llm.circuit_breaker import CircuitBreaker, CircuitState
from stock_manager.trading.llm.config import InvocationCounter, LLMConfig
from stock_manager.trading.consensus.vote_parser import VoteParser

__all__ = [
    "async_persona_query",
    "sync_persona_query",
    "CircuitBreaker",
    "CircuitState",
    "InvocationCounter",
    "LLMConfig",
    "VoteParser",
]
