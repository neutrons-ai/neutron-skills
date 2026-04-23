"""Tests for the SKILL.md parser (loader.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from neutron_skills.loader import parse_skill_md
from neutron_skills.models import parse_allowed_tools


def _write_skill(dir_path: Path, content: str) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    skill_file = dir_path / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


def test_parse_valid_skill(tmp_path: Path):
    skill_file = _write_skill(
        tmp_path / "my-skill",
        "---\nname: my-skill\ndescription: Does a thing.\n---\n\n# Body\n\nInstructions here.\n",
    )

    skill = parse_skill_md(skill_file)

    assert skill is not None
    assert skill.name == "my-skill"
    assert skill.description == "Does a thing."
    assert "Instructions here." in skill.body
    assert skill.allowed_tools == []
    assert skill.directory == skill_file.parent


def test_parse_allowed_tools_field(tmp_path: Path):
    skill_file = _write_skill(
        tmp_path / "tool-skill",
        "---\nname: tool-skill\ndescription: d\nallowed-tools: Bash(git:*) Read Write\n---\nbody\n",
    )

    skill = parse_skill_md(skill_file)

    assert skill is not None
    assert skill.allowed_tools == ["Bash(git:*)", "Read", "Write"]


def test_parse_missing_frontmatter_returns_none(tmp_path: Path):
    skill_file = _write_skill(tmp_path / "bad", "Just markdown, no frontmatter.\n")
    assert parse_skill_md(skill_file) is None


def test_parse_unparseable_yaml_returns_none(tmp_path: Path):
    skill_file = _write_skill(
        tmp_path / "bad-yaml",
        "---\nname: bad-yaml\ndescription: [unterminated\n---\nbody\n",
    )
    assert parse_skill_md(skill_file) is None


def test_parse_missing_description_returns_none(tmp_path: Path):
    skill_file = _write_skill(
        tmp_path / "no-desc",
        "---\nname: no-desc\n---\nbody\n",
    )
    assert parse_skill_md(skill_file) is None


def test_parse_name_mismatch_warns_but_loads(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    skill_file = _write_skill(
        tmp_path / "dirname",
        "---\nname: different-name\ndescription: d\n---\nbody\n",
    )
    with caplog.at_level("WARNING"):
        skill = parse_skill_md(skill_file)
    assert skill is not None
    assert skill.name == "different-name"
    assert any("does not match parent directory" in rec.message for rec in caplog.records)


def test_parse_missing_name_falls_back_to_directory(tmp_path: Path):
    skill_file = _write_skill(
        tmp_path / "fallback-name",
        "---\ndescription: d\n---\nbody\n",
    )
    skill = parse_skill_md(skill_file)
    assert skill is not None
    assert skill.name == "fallback-name"


def test_parse_oversize_name_warns_but_loads(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    long_name = "a" * 100
    skill_file = _write_skill(
        tmp_path / long_name,
        f"---\nname: {long_name}\ndescription: d\n---\nbody\n",
    )
    with caplog.at_level("WARNING"):
        skill = parse_skill_md(skill_file)
    assert skill is not None
    assert skill.name == long_name
    assert any("exceeds" in rec.message for rec in caplog.records)


def test_parse_enumerates_resources(tmp_path: Path):
    skill_dir = tmp_path / "res-skill"
    _write_skill(skill_dir, "---\nname: res-skill\ndescription: d\n---\nbody\n")
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "run.py").write_text("#!/usr/bin/env python\n")
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "REFERENCE.md").write_text("# ref\n")
    (skill_dir / "assets").mkdir()
    (skill_dir / "assets" / "template.txt").write_text("t\n")
    # Unrelated directory should be ignored.
    (skill_dir / "other").mkdir()
    (skill_dir / "other" / "ignore.me").write_text("x\n")

    skill = parse_skill_md(skill_dir / "SKILL.md")

    assert skill is not None
    assert sorted(skill.resources) == [
        "assets/template.txt",
        "references/REFERENCE.md",
        "scripts/run.py",
    ]


def test_parse_nonexistent_file_returns_none(tmp_path: Path):
    assert parse_skill_md(tmp_path / "missing" / "SKILL.md") is None


def test_parse_allowed_tools_helper():
    assert parse_allowed_tools(None) == []
    assert parse_allowed_tools("A  B C") == ["A", "B", "C"]
    assert parse_allowed_tools(["A", "B"]) == ["A", "B"]
    assert parse_allowed_tools(42) == []
