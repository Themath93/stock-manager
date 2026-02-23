"""Investor personas for the consensus trading pipeline.

Public API
----------
Data models:
    VoteAction, PersonaCategory, PersonaVote, AdvisoryVote,
    MarketSnapshot, EvaluationRequest, ConsensusResult

Base class:
    InvestorPersona

Persona implementations:
    GrahamPersona, BuffettPersona, LynchPersona, SorosPersona, DalioPersona,
    MungerPersona, TempletonPersona, LivermorePersona, FisherPersona, SimonsPersona
"""

from .models import (
    AdvisoryVote,
    ConsensusResult,
    EvaluationRequest,
    MarketSnapshot,
    PersonaCategory,
    PersonaVote,
    VoteAction,
)
from .base import InvestorPersona
from .graham_persona import GrahamPersona
from .buffett_persona import BuffettPersona
from .lynch_persona import LynchPersona
from .soros_persona import SorosPersona
from .dalio_persona import DalioPersona
from .munger_persona import MungerPersona
from .templeton_persona import TempletonPersona
from .livermore_persona import LivermorePersona
from .fisher_persona import FisherPersona
from .simons_persona import SimonsPersona

__all__ = [
    # Enums
    "VoteAction",
    "PersonaCategory",
    # Vote types
    "PersonaVote",
    "AdvisoryVote",
    # Snapshot & request/result
    "MarketSnapshot",
    "EvaluationRequest",
    "ConsensusResult",
    # Base
    "InvestorPersona",
    # Personas
    "GrahamPersona",
    "BuffettPersona",
    "LynchPersona",
    "SorosPersona",
    "DalioPersona",
    "MungerPersona",
    "TempletonPersona",
    "LivermorePersona",
    "FisherPersona",
    "SimonsPersona",
]
