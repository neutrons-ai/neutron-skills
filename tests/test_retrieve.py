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
    skills, tools = retrieve(
        "We are writing a scan script on the EQSANS instrument at SNS.",
        registry=seeded_registry,
        method="deterministic",
    )
    assert skills, "expected at least one match"
    assert skills[0].name == "eqsans-scan-scripting"
    # Union of allowed-tools from matched skills, de-duplicated.
    for tool in ["Read", "Write", "Bash(python:*)"]:
        assert tool in tools


def test_deterministic_ranks_rietveld_for_diffraction_query(seeded_registry: SkillRegistry):
    skills, _ = retrieve(
        "How do I run a Rietveld refinement on powder diffraction?",
        registry=seeded_registry,
        method="deterministic",
    )
    assert skills[0].name == "rietveld-checklist"


def test_empty_query_returns_empty(seeded_registry: SkillRegistry):
    skills, tools = retrieve("", registry=seeded_registry, method="deterministic")
    assert skills == []
    assert tools == []


def test_no_matches_returns_empty(seeded_registry: SkillRegistry):
    skills, tools = retrieve(
        "Totally unrelated query about cooking pasta.",
        registry=seeded_registry,
        method="deterministic",
    )
    assert skills == []
    assert tools == []


def test_top_k_limits_results(seeded_registry: SkillRegistry):
    skills, _ = retrieve(
        "scan script Q Rietveld diffraction",
        registry=seeded_registry,
        method="deterministic",
        top_k=1,
    )
    assert len(skills) == 1


def test_tools_are_deduplicated(tmp_path: Path):
    _write(
        tmp_path / "a" / "skill-a" / "SKILL.md",
        "---\nname: skill-a\ndescription: alpha tool test\nallowed-tools: Read Write\n---\nb\n",
    )
    _write(
        tmp_path / "b" / "skill-b" / "SKILL.md",
        "---\nname: skill-b\ndescription: beta tool test\nallowed-tools: Read Bash\n---\nb\n",
    )
    reg = SkillRegistry.discover(bundled=False, extra_paths=[tmp_path])
    _, tools = retrieve("tool test", registry=reg, method="deterministic")
    # Order preserved first-seen; no duplicates.
    assert tools.count("Read") == 1
    assert set(tools) == {"Read", "Write", "Bash"}


# --- LLM path ---


class _StubSelector:
    def __init__(self, names: list[str], *, raise_exc: Exception | None = None) -> None:
        self.names = names
        self.raise_exc = raise_exc
        self.last_catalog: list[dict[str, str]] | None = None

    def select(self, query: str, catalog: list[dict[str, str]], top_k: int) -> list[str]:
        self.last_catalog = catalog
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.names[:top_k]


def test_llm_selector_chooses_skills(seeded_registry: SkillRegistry):
    selector = _StubSelector(["rietveld-checklist"])
    skills, _ = retrieve(
        "anything",
        registry=seeded_registry,
        method="llm",
        selector=selector,
    )
    assert [s.name for s in skills] == ["rietveld-checklist"]
    # Catalog passed to selector is tier-1 only.
    assert selector.last_catalog is not None
    assert set(selector.last_catalog[0].keys()) == {"name", "description"}


def test_auto_uses_llm_when_selector_provided(seeded_registry: SkillRegistry):
    selector = _StubSelector(["q-range-basics"])
    skills, _ = retrieve(
        "EQSANS scan",  # deterministic would pick eqsans first
        registry=seeded_registry,
        method="auto",
        selector=selector,
    )
    assert [s.name for s in skills] == ["q-range-basics"]


def test_auto_uses_deterministic_when_no_selector(seeded_registry: SkillRegistry):
    skills, _ = retrieve("EQSANS", registry=seeded_registry, method="auto")
    assert skills[0].name == "eqsans-scan-scripting"


def test_llm_failure_falls_back_to_deterministic(seeded_registry: SkillRegistry):
    selector = _StubSelector([], raise_exc=RuntimeError("boom"))
    skills, _ = retrieve(
        "EQSANS scan script",
        registry=seeded_registry,
        method="llm",
        selector=selector,
    )
    assert skills and skills[0].name == "eqsans-scan-scripting"


def test_llm_unknown_name_is_skipped_and_falls_back(seeded_registry: SkillRegistry):
    selector = _StubSelector(["does-not-exist"])
    skills, _ = retrieve(
        "EQSANS scan",
        registry=seeded_registry,
        method="llm",
        selector=selector,
    )
    # All names unknown -> fallback to deterministic.
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
