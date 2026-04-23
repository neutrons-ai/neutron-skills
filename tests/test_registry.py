"""Tests for skill discovery and the SkillRegistry."""

from __future__ import annotations

from pathlib import Path

import pytest

from neutron_skills.registry import SkillRegistry


def _make_skill(root: Path, rel: str, name: str, description: str = "desc") -> Path:
    skill_dir = root / rel
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nbody\n",
        encoding="utf-8",
    )
    return skill_file


def test_discover_external_only(tmp_path: Path):
    _make_skill(tmp_path, "domain-a/alpha", "alpha")
    _make_skill(tmp_path, "domain-b/beta", "beta")

    registry = SkillRegistry.discover(bundled=False, extra_paths=[tmp_path])

    assert len(registry) == 2
    assert registry.names() == ["alpha", "beta"]
    assert registry.get("alpha") is not None
    assert "alpha" in registry


def test_discover_skips_non_skill_directories(tmp_path: Path):
    _make_skill(tmp_path, "good/one", "one")
    (tmp_path / "README.md").write_text("# not a skill\n")
    (tmp_path / "node_modules").mkdir()
    _make_skill(tmp_path / "node_modules", "ignored/should-not-load", "should-not-load")
    (tmp_path / ".hidden").mkdir()
    _make_skill(tmp_path / ".hidden", "hidden/also-ignored", "also-ignored")

    registry = SkillRegistry.discover(bundled=False, extra_paths=[tmp_path])

    assert registry.names() == ["one"]


def test_collision_external_overrides_earlier_external(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    first = tmp_path / "first"
    second = tmp_path / "second"
    _make_skill(first, "x/dup", "dup", description="first")
    _make_skill(second, "x/dup", "dup", description="second")

    with caplog.at_level("WARNING"):
        registry = SkillRegistry.discover(bundled=False, extra_paths=[first, second])

    skill = registry.get("dup")
    assert skill is not None
    # Second external path should shadow the first.
    assert skill.description == "second"
    assert any("shadows" in rec.message for rec in caplog.records)


def test_external_overrides_bundled(tmp_path: Path):
    # We don't have bundled skills with overlapping names, so simulate by
    # pointing two external roots and verifying last-write-wins for "external".
    a = tmp_path / "a"
    b = tmp_path / "b"
    _make_skill(a, "d/same", "same", description="from-a")
    _make_skill(b, "d/same", "same", description="from-b")

    registry = SkillRegistry.discover(bundled=False, extra_paths=[a, b])
    skill = registry.get("same")
    assert skill is not None
    assert skill.description == "from-b"


def test_by_domain(tmp_path: Path):
    _make_skill(tmp_path, "sans/eqsans-thing", "eqsans-thing")
    _make_skill(tmp_path, "diffraction/rietveld-thing", "rietveld-thing")

    registry = SkillRegistry.discover(bundled=False, extra_paths=[tmp_path])

    sans = registry.by_domain("sans")
    assert [s.name for s in sans] == ["eqsans-thing"]


def test_discover_bundled_only_does_not_raise(tmp_path: Path):
    # Bundled directory exists but is empty except for .gitkeep files.
    registry = SkillRegistry.discover(bundled=True)
    # Should at least be a registry; count may be zero or more.
    assert isinstance(registry.all(), list)


def test_depth_bounded(tmp_path: Path):
    # Nesting deeper than _MAX_DEPTH should not be scanned.
    deep = tmp_path
    for i in range(10):
        deep = deep / f"level{i}"
    _make_skill(deep, "too-deep", "too-deep")

    # Also place one at shallow depth.
    _make_skill(tmp_path, "shallow/ok", "ok")

    registry = SkillRegistry.discover(bundled=False, extra_paths=[tmp_path])

    assert "ok" in registry
    assert "too-deep" not in registry
