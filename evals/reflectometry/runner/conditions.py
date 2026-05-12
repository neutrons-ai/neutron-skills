"""
Prompt-condition assembly.

Each condition builds the ``(system, user)`` message pair the candidate
model sees. See ``PLAN.md`` §4 for the matrix.
"""

from __future__ import annotations

from typing import Iterable

from neutron_skills import Skill
from neutron_skills.registry import SkillRegistry
from neutron_skills.retrieve import LLMSelector, retrieve

#: Conditions exposed to the CLI. Order matters only for reporting consistency.
CONDITIONS: tuple[str, ...] = (
    "baseline",
    "retrieve_det",
    "retrieve_llm",
    "oracle",
    "full_domain",
)

BASELINE_SYSTEM = (
    "You are a neutron-scattering tutor specializing in reflectometry. "
    "Answer the question concisely. For numerical questions, show the "
    "formula you use and report the final value with units."
)


def _skill_block(skills: Iterable[Skill]) -> str:
    """Render skills as a single Markdown block for splicing into the prompt."""
    parts = []
    for s in skills:
        parts.append(f"## Skill: {s.name}\n\n{s.body.strip()}")
    return "\n\n---\n\n".join(parts)


def build_messages(
    question: dict,
    condition: str,
    registry: SkillRegistry,
    *,
    domain: str = "reflectometry",
    top_k: int = 3,
    llm_selector: LLMSelector | None = None,
) -> tuple[list[dict[str, str]], list[str]]:
    """
    Build the chat messages for one (question, condition) pair.

    Args:
        question: A question entry from ``questions.yaml``.
        condition: One of :data:`CONDITIONS`.
        registry: A populated :class:`SkillRegistry`.
        domain: Domain name used by the ``full_domain`` condition
            (default ``"reflectometry"``).
        top_k: Max skills to inject for the two retrieval conditions.
        llm_selector: Optional :class:`LLMSelector` for ``retrieve_llm``;
            if absent the runner silently falls back to deterministic
            retrieval so the matrix still runs.

    Returns:
        ``(messages, retrieved_skill_names)`` — the chat messages ready
        for the backend, plus the list of skill names actually injected
        (used by retrieval grading in :mod:`report`).

    Raises:
        ValueError: If ``condition`` is unknown.
    """
    if condition == "baseline":
        skills: list[Skill] = []
    elif condition == "retrieve_det":
        skills = retrieve(
            question["question"],
            method="deterministic",
            registry=registry,
            top_k=top_k,
        )
    elif condition == "retrieve_llm":
        if llm_selector is None:
            # Fall back to deterministic — keeps the matrix complete
            # rather than skipping cells when no selector is configured.
            skills = retrieve(
                question["question"],
                method="deterministic",
                registry=registry,
                top_k=top_k,
            )
        else:
            skills = retrieve(
                question["question"],
                method="llm",
                selector=llm_selector,
                registry=registry,
                top_k=top_k,
            )
    elif condition == "oracle":
        names = question.get("expected_helpful_skills") or []
        skills = [s for s in (registry.get(n) for n in names) if s is not None]
    elif condition == "full_domain":
        skills = [s for s in registry.all() if s.domain == domain]
    else:
        raise ValueError(f"unknown condition: {condition!r}")

    if skills:
        system = (
            BASELINE_SYSTEM
            + "\n\nUse the skill instructions below as authoritative guidance "
            + "from a domain expert. They are more current than your training data.\n\n"
            + "---\n\n"
            + _skill_block(skills)
            + "\n\n---"
        )
    else:
        system = BASELINE_SYSTEM

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question["question"].strip()},
    ]
    return messages, [s.name for s in skills]
