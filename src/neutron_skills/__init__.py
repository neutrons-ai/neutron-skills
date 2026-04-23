"""
neutron_skills - A curated registry of Agent Skills for neutron scattering.

Skills follow the Agent Skills specification
(https://agentskills.io/specification) and can be discovered and retrieved
by other agents through a small Python and CLI surface.

Quickstart:
    >>> from neutron_skills import retrieve
    >>> skills, tools = retrieve(
    ...     "We are writing a scan script to acquire data on the EQSANS instrument at SNS."
    ... )
"""

from .models import Skill
from .registry import SkillRegistry
from .retrieve import LLMSelector, retrieve

__version__ = "0.1.0"
__all__ = [
    "LLMSelector",
    "Skill",
    "SkillRegistry",
    "__version__",
    "retrieve",
]
