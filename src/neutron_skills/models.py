"""
Data model for a parsed Agent Skill.

See https://agentskills.io/specification for the full SKILL.md format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Skill:
    """
    A parsed Agent Skill.

    Attributes:
        name: Skill name (from frontmatter ``name``). Lowercase, hyphen-separated.
        description: Free-text description of what the skill does and when to use it.
        path: Absolute path to the ``SKILL.md`` file.
        body: Markdown body (everything after the closing ``---`` frontmatter delimiter).
        frontmatter: Full parsed YAML frontmatter as a mapping.
        allowed_tools: Tokens parsed from the ``allowed-tools`` frontmatter field
            (space-separated per spec). Empty list when the field is absent.
        resources: Relative paths of files found under ``scripts/``, ``references/``,
            and ``assets/`` subdirectories alongside the ``SKILL.md``.
    """

    name: str
    description: str
    path: Path
    body: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    allowed_tools: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)

    @property
    def directory(self) -> Path:
        """The skill's base directory (parent of ``SKILL.md``)."""
        return self.path.parent


def parse_allowed_tools(value: Any) -> list[str]:
    """
    Parse the ``allowed-tools`` frontmatter field.

    The spec defines it as a space-separated string. We also accept a list
    (lenient parsing) and ignore other types.

    Args:
        value: Raw value from YAML frontmatter.

    Returns:
        List of tool tokens. Empty if the field is missing or malformed.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return value.split()
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
