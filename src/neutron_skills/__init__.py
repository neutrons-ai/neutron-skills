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

Skills may ship executable CLI scripts under ``<skill>/scripts/``.
These scripts are designed to be run via ``uv run`` in a subprocess —
no dynamic code import is needed. See the ``uv_toolcalling.py`` example.
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
