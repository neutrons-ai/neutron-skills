"""
Discovery and registry for Agent Skills.

Scans two kinds of locations:

- **Bundled**: skills packaged inside ``neutron_skills`` at
  ``src/neutron_skills/skills/<domain>/<skill-name>/SKILL.md``.
- **External**: additional directories provided by the caller.

Name collisions: external skills override bundled skills (with a warning).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from pathlib import Path

from .loader import parse_skill_md
from .models import Skill

logger = logging.getLogger(__name__)

_MAX_DEPTH = 6
_IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


def _iter_skill_md_files(root: Path) -> Iterator[Path]:
    """Yield SKILL.md files under ``root``, bounded in depth, skipping noise."""
    if not root.is_dir():
        return

    root = root.resolve()
    root_depth = len(root.parts)

    def _walk(directory: Path) -> Iterator[Path]:
        if len(directory.parts) - root_depth > _MAX_DEPTH:
            return
        try:
            entries = list(directory.iterdir())
        except OSError as exc:
            logger.warning("Cannot read %s: %s", directory, exc)
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in _IGNORE_DIRS or entry.name.startswith("."):
                    continue
                yield from _walk(entry)
            elif entry.is_file() and entry.name == "SKILL.md":
                yield entry

    yield from _walk(root)


def _bundled_skills_root() -> Path:
    """Return the directory containing bundled skills shipped with the package."""
    return Path(__file__).parent / "skills"


class SkillRegistry:
    """
    In-memory registry of discovered skills, keyed by skill name.

    Typical use::

        registry = SkillRegistry.discover()           # bundled only
        registry = SkillRegistry.discover(extra_paths=["~/my-skills"])
    """

    def __init__(self, skills: dict[str, Skill] | None = None) -> None:
        self._skills: dict[str, Skill] = dict(skills) if skills else {}

    # ---- Construction ----

    @classmethod
    def discover(
        cls,
        *,
        bundled: bool = True,
        extra_paths: Iterable[str | Path] | None = None,
    ) -> SkillRegistry:
        """
        Build a registry by scanning bundled and/or external paths.

        Args:
            bundled: If True, include skills shipped with ``neutron_skills``.
            extra_paths: Additional root directories to scan. These take
                precedence over bundled skills on name collision.

        Returns:
            A populated :class:`SkillRegistry`.
        """
        registry = cls()

        if bundled:
            registry._load_from(_bundled_skills_root(), origin="bundled")

        for path in extra_paths or ():
            registry._load_from(Path(path).expanduser(), origin="external")

        return registry

    # ---- Loading ----

    def _load_from(self, root: Path, *, origin: str) -> None:
        if not root.is_dir():
            logger.debug("Skills root %s does not exist (origin=%s)", root, origin)
            return

        for skill_md in _iter_skill_md_files(root):
            skill = parse_skill_md(skill_md)
            if skill is None:
                continue
            self._add(skill, origin=origin)

    def _add(self, skill: Skill, *, origin: str) -> None:
        existing = self._skills.get(skill.name)
        if existing is None:
            self._skills[skill.name] = skill
            return

        # Collision policy: external overrides bundled; same origin keeps first.
        if origin == "external":
            logger.warning(
                "Skill %r from %s shadows earlier skill at %s",
                skill.name,
                skill.path,
                existing.path,
            )
            self._skills[skill.name] = skill
        else:
            logger.warning(
                "Duplicate skill name %r: keeping %s, ignoring %s",
                skill.name,
                existing.path,
                skill.path,
            )

    # ---- Access ----

    def __len__(self) -> int:
        return len(self._skills)

    def __iter__(self) -> Iterator[Skill]:
        return iter(self._skills.values())

    def __contains__(self, name: object) -> bool:
        return name in self._skills

    def get(self, name: str) -> Skill | None:
        """Return the skill with this name, or None."""
        return self._skills.get(name)

    def names(self) -> list[str]:
        """Return all skill names, sorted."""
        return sorted(self._skills)

    def all(self) -> list[Skill]:
        """Return all skills, sorted by name."""
        return [self._skills[n] for n in self.names()]

    def by_domain(self, domain: str) -> list[Skill]:
        """
        Return skills whose containing directory path includes ``domain``
        as a path segment (e.g. ``"sans"``, ``"diffraction"``).
        """
        results: list[Skill] = []
        for skill in self.all():
            if domain in skill.path.parent.parts:
                results.append(skill)
        return results
