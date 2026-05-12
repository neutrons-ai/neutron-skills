"""
Smoke tests for the skill-eval harness.

These tests intentionally make **no** LLM calls — they validate the
schema of the bundled question banks under ``evals/`` and exercise the
condition-builder and the graders against the real :class:`SkillRegistry`.
Anything that needs a running Ollama server lives outside this module.

The reflectometry bank is used as the canonical example here; adding a
new domain (e.g. ``evals/sans/``) does not require updating these tests
because the schema validator is run via :func:`_validate_questions` which
is domain-agnostic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALS_DIR = REPO_ROOT / "evals"
REFL_DIR = EVALS_DIR / "reflectometry"

# Make the evals/ tree importable without installing it as a package.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_questions_yaml_is_loadable_and_nonempty() -> None:
    data = yaml.safe_load((REFL_DIR / "questions.yaml").read_text())
    assert isinstance(data, list) and data, "questions.yaml must be a non-empty list"


def test_models_yaml_lists_ollama_models() -> None:
    data = yaml.safe_load((EVALS_DIR / "models.yaml").read_text())
    assert isinstance(data, list) and data, "models.yaml must be a non-empty list"
    assert all(isinstance(m, dict) and "id" in m and "backend" in m for m in data)
    assert any(m.get("backend") == "ollama" for m in data), (
        "At least one ollama-backed model is required for the v1 runner."
    )


def test_question_bank_passes_schema_validation() -> None:
    from evals.runner.cli import _validate_questions

    errors = _validate_questions(REFL_DIR / "questions.yaml")
    assert errors == [], f"schema errors: {errors}"


def test_list_command_discovers_reflectometry() -> None:
    from evals.runner.cli import _discover_domains

    domains = _discover_domains()
    assert "reflectometry" in domains, domains


def test_build_messages_for_every_condition() -> None:
    from neutron_skills.registry import SkillRegistry

    from evals.runner.conditions import build_messages

    questions = yaml.safe_load((REFL_DIR / "questions.yaml").read_text())
    registry = SkillRegistry.discover()
    q = questions[0]

    # retrieve_llm is excluded — it requires a selector or falls back to
    # deterministic; either is exercised through retrieve_det/oracle.
    for cond in ("baseline", "retrieve_det", "oracle", "full_domain"):
        messages, names = build_messages(q, cond, registry,
                                         domain="reflectometry", top_k=3)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        # User content always contains the question text.
        assert q["question"].strip() in messages[1]["content"]
        # Baseline must inject no skills; full_domain must inject some.
        if cond == "baseline":
            assert names == []
        elif cond == "full_domain":
            assert names, "full_domain should inject every reflectometry skill"


def test_build_messages_humanizes_domain_in_system_prompt() -> None:
    from neutron_skills.registry import SkillRegistry

    from evals.runner.conditions import build_messages

    questions = yaml.safe_load((REFL_DIR / "questions.yaml").read_text())
    registry = SkillRegistry.discover()
    messages, _ = build_messages(
        questions[0], "baseline", registry, domain="reflectometry"
    )
    assert "specializing in reflectometry" in messages[0]["content"]


def test_oracle_condition_uses_expected_helpful_skills() -> None:
    from neutron_skills.registry import SkillRegistry

    from evals.runner.conditions import build_messages

    questions = yaml.safe_load((REFL_DIR / "questions.yaml").read_text())
    registry = SkillRegistry.discover()
    q = next(
        q for q in questions
        if q.get("expected_helpful_skills")
        and all(registry.get(n) is not None for n in q["expected_helpful_skills"])
    )
    _, names = build_messages(q, "oracle", registry, domain="reflectometry")
    assert set(names) == set(q["expected_helpful_skills"])


def test_grade_numerical_within_tolerance() -> None:
    from evals.runner.grade import grade

    question = {
        "type": "numerical",
        "expected": {"value": 0.02309, "rel_tol": 0.03},
    }
    result = grade(question, "The answer is Q = 0.0231 Å⁻¹.")
    assert result["score"] == 1
    assert result["extracted"] == 0.0231


def test_grade_numerical_outside_tolerance() -> None:
    from evals.runner.grade import grade

    question = {
        "type": "numerical",
        "expected": {"value": 0.02309, "rel_tol": 0.03},
    }
    result = grade(question, "I get Q = 0.0462 Å⁻¹ (used 2θ instead of θ).")
    assert result["score"] == 0


def test_grade_mc_extracts_letter() -> None:
    from evals.runner.grade import grade

    question = {"type": "mc", "expected": {"value": "B"}}
    assert grade(question, "Answer: B — best fit at χ² ≈ 1.5.")["score"] == 1
    assert grade(question, "I'd pick (C).")["score"] == 0


def test_grade_short_answer_substring() -> None:
    from evals.runner.grade import grade

    question = {
        "type": "short_answer",
        "must_mention": ["half"],
        "must_not_mention": [],
    }
    assert grade(question, "Roughness exceeds half the layer thickness.")["score"] == 1
    assert grade(question, "Roughness looks fine.")["score"] == 0


def test_grade_numerical_ignores_bare_digits_in_algebra() -> None:
    """Don't match a literal '2' inside '(sld_range / 2)' against target 2.0.

    Regression test for refl-q-017: a baseline response that never stated
    the answer scored 1 because the numeric extractor latched onto a stray
    digit in algebra notation.
    """
    from evals.runner.grade import grade

    question = {
        "type": "numerical",
        "expected": {"value": 2.0, "abs_tol": 0.1},
    }
    response = (
        "For a non-adhesive layer, the recommended minimum half-width is "
        "typically around 0.01-0.02 Å⁻².\n"
        "Formula:\n"
        "sld_min = sld_nominal - (sld_range / 2)\n"
        "sld_max = sld_nominal + (sld_range / 2)"
    )
    result = grade(question, response)
    assert result["score"] == 0, result


def test_grade_numerical_prefers_unit_anchored_final_answer() -> None:
    """A multi-number response should grade on the answer-with-units, not on
    an unrelated intermediate number that happens to match the target."""
    from evals.runner.grade import grade

    question = {
        "type": "numerical",
        "expected": {"value": 6.58, "rel_tol": 0.02},
    }
    # 6.58 also appears as an unrelated intermediate; the unit-anchored
    # number is 6.52 Å, which is within rel_tol of the target.
    response = (
        "Intermediate step uses the constant 6.58 as a placeholder.\n"
        "Plugging in θ = 1.5°, λ ≈ 6.52 Å."
    )
    result = grade(question, response)
    assert result["score"] == 1
    assert result["extracted"] == 6.52


def test_grade_numerical_accepts_scientific_notation_with_units() -> None:
    """`1.0 × 10⁻⁶ Å⁻²` should anchor on the 1.0 (the mantissa)."""
    from evals.runner.grade import grade

    question = {
        "type": "numerical",
        "expected": {"value": 2.0, "abs_tol": 0.1},
    }
    # Mantissa is 1.0 — must NOT match target 2.0.
    response = "The answer is approximately 1.0 × 10⁻⁶ Å⁻²."
    assert grade(question, response)["score"] == 0
    # Mantissa is 2.0 — must match.
    response = "The answer is approximately 2.0 × 10⁻⁶ Å⁻²."
    assert grade(question, response)["score"] == 1
