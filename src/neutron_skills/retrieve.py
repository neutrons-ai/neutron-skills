"""
Skill retrieval: deterministic keyword scoring + pluggable LLM selector.

Public entry point: :func:`retrieve`.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from .models import Skill
from .registry import SkillRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM selector protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMSelector(Protocol):
    """
    Protocol for an LLM-backed skill selector.

    Implementations receive the skill *catalog* (tier 1 of progressive
    disclosure — name + description only) plus the user query, and return
    the names of skills that should be activated.

    Implementations should be best-effort: raising is allowed, but callers
    may fall back to deterministic retrieval if the selector fails.
    """

    def select(
        self,
        query: str,
        catalog: list[dict[str, str]],
        top_k: int,
    ) -> list[str]:  # pragma: no cover - protocol
        """
        Choose up to ``top_k`` skill names relevant to ``query``.

        Args:
            query: The user's task description.
            catalog: List of ``{"name": ..., "description": ...}`` dicts.
            top_k: Maximum number of skills to return.

        Returns:
            A list of skill names from the catalog, ordered by relevance.
        """
        ...


def build_catalog(registry: SkillRegistry) -> list[dict[str, str]]:
    """Return the tier-1 catalog (name + description per skill)."""
    return [{"name": s.name, "description": s.description} for s in registry.all()]


# ---------------------------------------------------------------------------
# Deterministic scoring
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _metadata_terms(frontmatter: dict[str, Any]) -> list[str]:
    """Collect searchable terms from ``metadata.{tags,instruments,techniques}``."""
    meta = frontmatter.get("metadata") or {}
    if not isinstance(meta, dict):
        return []
    terms: list[str] = []
    for key in ("tags", "instruments", "techniques"):
        value = meta.get(key)
        if isinstance(value, list):
            terms.extend(str(v) for v in value)
        elif isinstance(value, str):
            terms.extend(value.split(","))
    return terms


def _score(skill: Skill, query_tokens: set[str]) -> int:
    """
    Weighted keyword hit count:

    - metadata (tags / instruments / techniques): 5 per exact term hit
    - name tokens: 3 per hit
    - description tokens: 1 per hit
    """
    if not query_tokens:
        return 0

    score = 0

    for term in _metadata_terms(skill.frontmatter):
        term_tokens = set(_tokenize(term))
        if term_tokens & query_tokens:
            score += 5

    name_tokens = set(_tokenize(skill.name))
    score += 3 * len(name_tokens & query_tokens)

    desc_tokens = _tokenize(skill.description)
    score += sum(1 for t in desc_tokens if t in query_tokens)

    return score


def deterministic_select(
    query: str,
    registry: SkillRegistry,
    top_k: int,
) -> list[Skill]:
    """Score all skills against ``query`` and return the top ``top_k``."""
    query_tokens = set(_tokenize(query))
    scored: list[tuple[int, str, Skill]] = []
    for skill in registry.all():
        s = _score(skill, query_tokens)
        if s > 0:
            # Include name as tiebreaker for stable ordering.
            scored.append((s, skill.name, skill))

    scored.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in scored[:top_k]]


# ---------------------------------------------------------------------------
# Public retrieve()
# ---------------------------------------------------------------------------


def retrieve(
    query: str,
    *,
    method: str = "auto",
    selector: LLMSelector | None = None,
    extra_paths: Iterable[str] | None = None,
    registry: SkillRegistry | None = None,
    top_k: int = 5,
) -> list[Skill]:
    """
    Retrieve relevant skills for a natural-language task description.

    Args:
        query: The user's task description (e.g. "scan script on EQSANS").
        method: One of ``"auto"``, ``"deterministic"``, or ``"llm"``.
            ``"auto"`` uses the ``selector`` if provided, else deterministic.
        selector: An :class:`LLMSelector` implementation. Required when
            ``method="llm"``; optional when ``method="auto"``.
        extra_paths: Additional directories to scan for external skills.
            Ignored when an explicit ``registry`` is passed.
        registry: Pre-built :class:`SkillRegistry`. Useful for tests or to
            avoid re-scanning the filesystem on repeated calls.
        top_k: Maximum number of skills to return.

    Returns:
        The ranked list of matching :class:`Skill` objects. Each skill's
        ``allowed_tools`` attribute exposes its ``allowed-tools``
        frontmatter (permission tokens per the Agent Skills spec) if you
        need it. To discover Python helpers shipped under
        ``<skill>/scripts/``, use :func:`neutron_skills.load_skill_tools`.

    Raises:
        ValueError: If ``method="llm"`` without a ``selector``, or if
            ``method`` is not one of the recognized values.
    """
    if method not in {"auto", "deterministic", "llm"}:
        raise ValueError(
            f"Unknown method {method!r}; expected 'auto', 'deterministic', or 'llm'"
        )
    if method == "llm" and selector is None:
        raise ValueError("method='llm' requires a selector")

    if registry is None:
        registry = SkillRegistry.discover(extra_paths=extra_paths)

    use_llm = method == "llm" or (method == "auto" and selector is not None)

    selected: list[Skill]
    if use_llm:
        assert selector is not None  # for type checkers
        catalog = build_catalog(registry)
        try:
            names = selector.select(query, catalog, top_k)
        except Exception as exc:  # noqa: BLE001 - graceful fallback
            logger.warning("LLM selector failed (%s); falling back to deterministic", exc)
            selected = deterministic_select(query, registry, top_k)
        else:
            selected = []
            for name in names[:top_k]:
                skill = registry.get(name)
                if skill is None:
                    logger.warning("LLM selector returned unknown skill %r; skipping", name)
                    continue
                selected.append(skill)
            # If the LLM returned nothing useful, fall back.
            if not selected:
                selected = deterministic_select(query, registry, top_k)
    else:
        selected = deterministic_select(query, registry, top_k)

    return selected
