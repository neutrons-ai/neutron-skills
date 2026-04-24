"""
neutron_skills - A curated registry of Agent Skills for neutron scattering.

Skills follow the Agent Skills specification
(https://agentskills.io/specification) and can be discovered and retrieved
by other agents through a small Python and CLI surface.

Quickstart:
    >>> from neutron_skills import retrieve
    >>> skills = retrieve(
    ...     "We are writing a scan script to acquire data on the EQSANS instrument at SNS."
    ... )

Each returned :class:`Skill` exposes its frontmatter via attributes,
including ``allowed_tools`` (permission tokens per the Agent Skills
spec, e.g. ``"Read"``, ``"Write"``, ``"Bash(python:*)"``).

To discover and use the executable Python helpers a skill ships under
``<skill>/scripts/``, use :func:`load_skill_tools`::

    >>> from neutron_skills import retrieve, load_skill_tools
    >>> skills = retrieve("compute Q for SANS")
    >>> callables, _ = load_skill_tools(skills)
    >>> # wrap callables into your runtime's tool format (LangChain, OpenAI, MCP, ...)
"""

from .models import Skill
from .registry import SkillRegistry
from .retrieve import LLMSelector, retrieve
from .tools import load_skill_tools

__version__ = "0.1.0"
__all__ = [
    "LLMSelector",
    "Skill",
    "SkillRegistry",
    "__version__",
    "load_skill_tools",
    "retrieve",
]
