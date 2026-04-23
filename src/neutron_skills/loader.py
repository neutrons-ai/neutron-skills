"""
Parser for Agent Skill SKILL.md files.

Implements lenient validation per the client-implementation guide:
- Warn but load when ``name`` mismatches the directory or exceeds constraints.
- Skip (return None) only when YAML is unparseable or ``description`` is missing.

See https://agentskills.io/specification and
https://agentskills.io/client-implementation/adding-skills-support
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from .models import Skill, parse_allowed_tools

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<yaml>.*?)\n---\s*(?:\n(?P<body>.*))?\Z",
    re.DOTALL,
)

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_NAME_MAX = 64
_DESCRIPTION_MAX = 1024

_RESOURCE_DIRS = ("scripts", "references", "assets")


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    """Split a SKILL.md file into (yaml_text, body_text). Returns None if no frontmatter."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return None
    return match.group("yaml"), (match.group("body") or "").strip()


def _enumerate_resources(skill_dir: Path) -> list[str]:
    """List files in scripts/, references/, assets/ as paths relative to skill_dir."""
    resources: list[str] = []
    for sub in _RESOURCE_DIRS:
        subdir = skill_dir / sub
        if not subdir.is_dir():
            continue
        for file_path in sorted(subdir.rglob("*")):
            if file_path.is_file():
                resources.append(str(file_path.relative_to(skill_dir)))
    return resources


def parse_skill_md(path: Path) -> Skill | None:
    """
    Parse a SKILL.md file into a :class:`Skill`.

    Args:
        path: Absolute or relative path to a ``SKILL.md`` file.

    Returns:
        A :class:`Skill` on success, or ``None`` if the file cannot be parsed
        as a valid skill (unparseable YAML, or missing required ``description``).

    Notes:
        Non-fatal issues (name mismatch with directory, over-length fields)
        produce a ``logger.warning`` but do not prevent loading.
    """
    path = Path(path).resolve()
    if not path.is_file():
        logger.error("SKILL.md not found: %s", path)
        return None

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to read %s: %s", path, exc)
        return None

    split = _split_frontmatter(text)
    if split is None:
        logger.error("No YAML frontmatter found in %s", path)
        return None
    yaml_text, body = split

    try:
        frontmatter = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        logger.error("Unparseable YAML frontmatter in %s: %s", path, exc)
        return None

    if not isinstance(frontmatter, dict):
        logger.error("Frontmatter in %s is not a mapping", path)
        return None

    name = frontmatter.get("name")
    description = frontmatter.get("description")

    if not isinstance(description, str) or not description.strip():
        logger.error("Skill at %s is missing a non-empty 'description'; skipping", path)
        return None

    dir_name = path.parent.name

    # Name: lenient — warn on issues but fall back to directory name.
    if not isinstance(name, str) or not name:
        logger.warning("Skill at %s has no 'name'; using directory name %r", path, dir_name)
        name = dir_name
    else:
        if name != dir_name:
            logger.warning(
                "Skill 'name' %r does not match parent directory %r (%s)",
                name,
                dir_name,
                path,
            )
        if len(name) > _NAME_MAX:
            logger.warning("Skill name %r exceeds %d chars (%s)", name, _NAME_MAX, path)
        if not _NAME_RE.match(name):
            logger.warning(
                "Skill name %r does not match spec pattern [a-z0-9-] (%s)",
                name,
                path,
            )

    if len(description) > _DESCRIPTION_MAX:
        logger.warning(
            "Skill description exceeds %d chars (%s)", _DESCRIPTION_MAX, path
        )

    allowed_tools = parse_allowed_tools(frontmatter.get("allowed-tools"))
    resources = _enumerate_resources(path.parent)

    return Skill(
        name=name,
        description=description.strip(),
        path=path,
        body=body,
        frontmatter=frontmatter,
        allowed_tools=allowed_tools,
        resources=resources,
    )
