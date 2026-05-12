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
# Domain catalog (tier-0 for progressive disclosure)
# ---------------------------------------------------------------------------

_BUILTIN_DOMAIN_DESCRIPTIONS: dict[str, str] = {
    "diffraction": (
        "Measurement of coherent scattering intensity as a function of scattering "
        "angle or momentum transfer. Includes powder and single-crystal diffraction, "
        "Rietveld refinement, Bragg peak analysis, and crystal structure determination."
    ),
    "general-scattering": (
        "Cross-cutting fundamentals shared by all scattering techniques: "
        "momentum transfer (Q), wavelength/angle relations, d-spacing, instrument-"
        "independent geometry and unit conventions."
    ),
    "inelastic": (
        "Techniques that resolve the energy transfer of scattered neutrons to probe "
        "dynamics and excitations. Includes triple-axis, time-of-flight, and "
        "spin-echo spectroscopy."
    ),
    "reflectometry": (
        "Specular and off-specular neutron reflection for probing thin films, "
        "multilayers, interfaces, and magnetic structures. Includes model building, "
        "fitting with refl1d/bumps, and scattering length density profiles."
    ),
    "sans": (
        "Small-angle neutron scattering for nanoscale structure in solutions, "
        "polymers, colloids, proteins, and soft matter. Includes scan scripting, "
        "reduction, and form/structure factor analysis."
    ),
    "spectroscopy": (
        "Neutron spectroscopy techniques focused on characterizing excitations, "
        "vibrations, and dynamical modes in materials."
    ),
}


def build_domain_catalog(
    registry: SkillRegistry,
    descriptions: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """
    Return a tier-0 catalog of unique domains seen in ``registry``.

    Each entry is ``{"name": <domain>, "description": <desc>}``. The
    description is looked up in ``descriptions`` first (user override),
    then falls back to the built-in map, and finally to the domain name.

    Args:
        registry: A populated :class:`SkillRegistry`.
        descriptions: Optional mapping from domain name to description,
            overriding the built-in defaults.

    Returns:
        One dict per unique non-empty domain, ordered by first appearance.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for skill in registry.all():
        d = skill.domain
        if not d or d in seen:
            continue
        seen.add(d)
        ordered.append(d)

    overrides = descriptions or {}
    catalog: list[dict[str, str]] = []
    for d in ordered:
        desc = overrides.get(d) or _BUILTIN_DOMAIN_DESCRIPTIONS.get(d) or d
        catalog.append({"name": d, "description": desc})
    return catalog


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
    top_k_domains: int = 2,
    domain_descriptions: dict[str, str] | None = None,
) -> list[Skill]:
    """
    Retrieve relevant skills for a natural-language task description.

    The LLM path uses **progressive disclosure**: the selector is called
    twice. Stage 1 picks up to ``top_k_domains`` relevant domains (tier-0
    catalog) from the set of domains present in the registry. Stage 2
    picks up to ``top_k`` skills (tier-1 catalog) restricted to those
    domains. This prevents cross-domain leakage — e.g. a reflectometry
    skill cannot be returned for a diffraction query.

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
        top_k_domains: Maximum number of domains kept after stage 1 of
            the LLM path. Ignored by the deterministic path.
        domain_descriptions: Optional mapping ``{domain_name: description}``
            overriding the built-in domain descriptions for stage 1.

    Returns:
        The ranked list of matching :class:`Skill` objects. Each skill's
        ``allowed_tools`` attribute exposes its ``allowed-tools``
        frontmatter (permission tokens per the Agent Skills spec) if you
        need it. Skills may ship CLI scripts under ``<skill>/scripts/``
        that can be run via ``uv run`` in a subprocess.

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
        selected = _progressive_llm_select(
            query,
            registry,
            selector,
            top_k=top_k,
            top_k_domains=top_k_domains,
            domain_descriptions=domain_descriptions,
        )
    else:
        selected = deterministic_select(query, registry, top_k)

    return selected


def _progressive_llm_select(
    query: str,
    registry: SkillRegistry,
    selector: LLMSelector,
    *,
    top_k: int,
    top_k_domains: int,
    domain_descriptions: dict[str, str] | None,
) -> list[Skill]:
    """
    Two-stage LLM selection: pick domains first, then skills within those
    domains. Falls back to deterministic scoring on any failure.
    """
    # ---- Stage 1: domain selection ----
    domain_catalog = build_domain_catalog(registry, domain_descriptions)
    all_domains = [d["name"] for d in domain_catalog]

    chosen_domains: list[str]
    if not domain_catalog:
        chosen_domains = []
    else:
        try:
            picked = selector.select(query, domain_catalog, top_k_domains)
        except Exception as exc:  # noqa: BLE001 - graceful fallback
            logger.warning(
                "LLM domain selection failed (%s); falling back to deterministic", exc
            )
            return deterministic_select(query, registry, top_k)

        chosen_domains = [name for name in picked[:top_k_domains] if name in all_domains]
        if not chosen_domains:
            logger.warning(
                "LLM returned no recognized domains (got %r); falling back to deterministic",
                picked,
            )
            return deterministic_select(query, registry, top_k)

    # ---- Stage 2: skill selection within chosen domains ----
    in_domain_skills = [s for s in registry.all() if s.domain in chosen_domains]
    if not in_domain_skills:
        # Domain catalog picked something, but no skills sit under those
        # domains (e.g. an empty domain folder). Fall back broadly.
        return deterministic_select(query, registry, top_k)

    skill_catalog = [
        {"name": s.name, "description": s.description} for s in in_domain_skills
    ]
    by_name = {s.name: s for s in in_domain_skills}

    try:
        names = selector.select(query, skill_catalog, top_k)
    except Exception as exc:  # noqa: BLE001 - graceful fallback
        logger.warning(
            "LLM skill selection failed (%s); scoring within %d chosen domain(s)",
            exc,
            len(chosen_domains),
        )
        return _deterministic_among(query, in_domain_skills, top_k)

    selected: list[Skill] = []
    for name in names[:top_k]:
        skill = by_name.get(name)
        if skill is None:
            logger.warning("LLM selector returned unknown skill %r; skipping", name)
            continue
        selected.append(skill)

    if not selected:
        return _deterministic_among(query, in_domain_skills, top_k)
    return selected


def _deterministic_among(
    query: str,
    skills: list[Skill],
    top_k: int,
) -> list[Skill]:
    """Score a pre-filtered subset of skills deterministically."""
    query_tokens = set(_tokenize(query))
    scored: list[tuple[int, str, Skill]] = []
    for skill in skills:
        s = _score(skill, query_tokens)
        if s > 0:
            scored.append((s, skill.name, skill))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in scored[:top_k]]
