"""Tests for retrieval (deterministic + LLM paths)."""

from __future__ import annotations

from pathlib import Path

import pytest

from neutron_skills.registry import SkillRegistry
from neutron_skills.retrieve import build_catalog, retrieve


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def seeded_registry(tmp_path: Path) -> SkillRegistry:
    _write(
        tmp_path / "sans" / "eqsans-scan-scripting" / "SKILL.md",
        "---\n"
        "name: eqsans-scan-scripting\n"
        "description: Write scan scripts for small-angle neutron scattering on EQSANS.\n"
        "allowed-tools: Read Write Bash(python:*)\n"
        "metadata:\n"
        "  tags: [scan, script]\n"
        "  instruments: [EQSANS]\n"
        "  techniques: [SANS]\n"
        "---\n"
        "Body A\n",
    )
    _write(
        tmp_path / "diffraction" / "rietveld-checklist" / "SKILL.md",
        "---\n"
        "name: rietveld-checklist\n"
        "description: Checklist for Rietveld refinement of powder diffraction data.\n"
        "allowed-tools: Read\n"
        "metadata:\n"
        "  tags: [refinement]\n"
        "  techniques: [diffraction, rietveld]\n"
        "---\n"
        "Body B\n",
    )
    _write(
        tmp_path / "general-scattering" / "q-range-basics" / "SKILL.md",
        "---\n"
        "name: q-range-basics\n"
        "description: Basics of momentum-transfer (Q) range planning.\n"
        "metadata:\n"
        "  tags: [Q, planning]\n"
        "---\n"
        "Body C\n",
    )
    return SkillRegistry.discover(bundled=False, extra_paths=[tmp_path])


def test_deterministic_ranks_eqsans_first(seeded_registry: SkillRegistry):
    skills = retrieve(
        "We are writing a scan script on the EQSANS instrument at SNS.",
        registry=seeded_registry,
        method="deterministic",
    )
    assert skills, "expected at least one match"
    assert skills[0].name == "eqsans-scan-scripting"
    # The matched skill's allowed-tools are still available per-skill.
    assert set(skills[0].allowed_tools) == {"Read", "Write", "Bash(python:*)"}


def test_deterministic_ranks_rietveld_for_diffraction_query(seeded_registry: SkillRegistry):
    skills = retrieve(
        "How do I run a Rietveld refinement on powder diffraction?",
        registry=seeded_registry,
        method="deterministic",
    )
    assert skills[0].name == "rietveld-checklist"


def test_empty_query_returns_empty(seeded_registry: SkillRegistry):
    skills = retrieve("", registry=seeded_registry, method="deterministic")
    assert skills == []


def test_no_matches_returns_empty(seeded_registry: SkillRegistry):
    skills = retrieve(
        "Totally unrelated query about cooking pasta.",
        registry=seeded_registry,
        method="deterministic",
    )
    assert skills == []


def test_top_k_limits_results(seeded_registry: SkillRegistry):
    skills = retrieve(
        "scan script Q Rietveld diffraction",
        registry=seeded_registry,
        method="deterministic",
        top_k=1,
    )
    assert len(skills) == 1


# --- LLM path (progressive / two-stage) ---


class _StubSelector:
    """
    Two-stage stub: returns ``domain_picks`` on its first call and
    ``skill_picks`` on subsequent calls. Optionally raises on a chosen
    stage to exercise fallback paths.
    """

    def __init__(
        self,
        *,
        domain_picks: list[str] | None = None,
        skill_picks: list[str] | None = None,
        raise_on: str | None = None,
    ) -> None:
        self.domain_picks = domain_picks or []
        self.skill_picks = skill_picks or []
        self.raise_on = raise_on  # None | "domain" | "skill"
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def select(
        self, query: str, catalog: list[dict[str, str]], top_k: int
    ) -> list[str]:
        stage = "domain" if not self.calls else "skill"
        self.calls.append((stage, catalog))
        if self.raise_on == stage:
            raise RuntimeError(f"boom in {stage}")
        picks = self.domain_picks if stage == "domain" else self.skill_picks
        return picks[:top_k]


def test_llm_selector_progressive_happy_path(seeded_registry: SkillRegistry):
    selector = _StubSelector(
        domain_picks=["diffraction"], skill_picks=["rietveld-checklist"]
    )
    skills = retrieve(
        "Rietveld refinement on powder diffraction",
        registry=seeded_registry,
        method="llm",
        selector=selector,
    )
    assert [s.name for s in skills] == ["rietveld-checklist"]
    # Stage 1 received the tier-0 catalog (domains only).
    assert selector.calls[0][0] == "domain"
    stage1_names = {row["name"] for row in selector.calls[0][1]}
    assert {"diffraction", "sans", "general-scattering"} <= stage1_names
    # Stage 2 received only skills in the selected domain.
    assert selector.calls[1][0] == "skill"
    stage2_names = {row["name"] for row in selector.calls[1][1]}
    assert stage2_names == {"rietveld-checklist"}


def test_progressive_filters_out_other_domains(seeded_registry: SkillRegistry):
    """Stage 2 must never see skills outside the selected domains."""
    selector = _StubSelector(
        domain_picks=["diffraction"], skill_picks=["rietveld-checklist"]
    )
    retrieve(
        "diffraction question",
        registry=seeded_registry,
        method="llm",
        selector=selector,
    )
    stage2_names = {row["name"] for row in selector.calls[1][1]}
    # SANS and general-scattering skills must not appear in stage-2 catalog.
    assert "eqsans-scan-scripting" not in stage2_names
    assert "q-range-basics" not in stage2_names


def test_auto_uses_llm_when_selector_provided(seeded_registry: SkillRegistry):
    selector = _StubSelector(
        domain_picks=["general-scattering"], skill_picks=["q-range-basics"]
    )
    skills = retrieve(
        "EQSANS scan",  # deterministic would pick eqsans first
        registry=seeded_registry,
        method="auto",
        selector=selector,
    )
    assert [s.name for s in skills] == ["q-range-basics"]


def test_auto_uses_deterministic_when_no_selector(seeded_registry: SkillRegistry):
    skills = retrieve("EQSANS", registry=seeded_registry, method="auto")
    assert skills[0].name == "eqsans-scan-scripting"


def test_llm_stage1_failure_falls_back_to_deterministic(
    seeded_registry: SkillRegistry,
):
    selector = _StubSelector(raise_on="domain")
    skills = retrieve(
        "EQSANS scan script",
        registry=seeded_registry,
        method="llm",
        selector=selector,
    )
    assert skills and skills[0].name == "eqsans-scan-scripting"


def test_llm_stage2_failure_falls_back_within_selected_domains(
    seeded_registry: SkillRegistry,
):
    selector = _StubSelector(domain_picks=["sans"], raise_on="skill")
    skills = retrieve(
        "EQSANS scan script",
        registry=seeded_registry,
        method="llm",
        selector=selector,
    )
    # Fallback scores only skills inside the selected domain.
    assert [s.name for s in skills] == ["eqsans-scan-scripting"]


def test_llm_unknown_domain_falls_back_to_deterministic(
    seeded_registry: SkillRegistry,
):
    selector = _StubSelector(domain_picks=["does-not-exist"])
    skills = retrieve(
        "EQSANS scan",
        registry=seeded_registry,
        method="llm",
        selector=selector,
    )
    # Stage 1 returned no recognized domain -> broad fallback.
    assert skills and skills[0].name == "eqsans-scan-scripting"


def test_llm_unknown_skill_name_falls_back_within_domain(
    seeded_registry: SkillRegistry,
):
    selector = _StubSelector(
        domain_picks=["sans"], skill_picks=["does-not-exist"]
    )
    skills = retrieve(
        "EQSANS scan",
        registry=seeded_registry,
        method="llm",
        selector=selector,
    )
    # Stage 2 returned nothing usable -> deterministic within 'sans'.
    assert skills and skills[0].name == "eqsans-scan-scripting"


def test_llm_without_selector_raises(seeded_registry: SkillRegistry):
    with pytest.raises(ValueError, match="requires a selector"):
        retrieve("q", registry=seeded_registry, method="llm")


def test_unknown_method_raises(seeded_registry: SkillRegistry):
    with pytest.raises(ValueError, match="Unknown method"):
        retrieve("q", registry=seeded_registry, method="bogus")  # type: ignore[arg-type]


def test_build_catalog_shape(seeded_registry: SkillRegistry):
    catalog = build_catalog(seeded_registry)
    assert all(set(row.keys()) == {"name", "description"} for row in catalog)
    assert {row["name"] for row in catalog} == {
        "eqsans-scan-scripting",
        "rietveld-checklist",
        "q-range-basics",
    }


def test_build_domain_catalog_uses_builtin_descriptions(
    seeded_registry: SkillRegistry,
):
    from neutron_skills.retrieve import build_domain_catalog

    catalog = build_domain_catalog(seeded_registry)
    names = {row["name"] for row in catalog}
    assert names == {"sans", "diffraction", "general-scattering"}
    # Built-in descriptions are non-trivial (not just echoing the name).
    for row in catalog:
        assert len(row["description"]) > len(row["name"])


def test_build_domain_catalog_user_override(seeded_registry: SkillRegistry):
    from neutron_skills.retrieve import build_domain_catalog

    catalog = build_domain_catalog(
        seeded_registry, descriptions={"sans": "custom sans desc"}
    )
    by_name = {row["name"]: row["description"] for row in catalog}
    assert by_name["sans"] == "custom sans desc"
