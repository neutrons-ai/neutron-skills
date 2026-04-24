"""Tests for ``neutron_skills.tools.load_skill_tools``."""

from __future__ import annotations

from pathlib import Path

import pytest

from neutron_skills.loader import parse_skill_md
from neutron_skills.models import Skill
from neutron_skills.tools import load_skill_tools


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_skill(tmp_path: Path, name: str, tools_py: str | None) -> Skill:
    skill_dir = tmp_path / name
    _write(
        skill_dir / "SKILL.md",
        "---\n"
        f"name: {name}\n"
        "description: A test skill.\n"
        "---\n"
        "Body.\n",
    )
    if tools_py is not None:
        _write(skill_dir / "scripts" / "tools.py", tools_py)
    skill = parse_skill_md(skill_dir / "SKILL.md")
    assert skill is not None
    return skill


def test_load_skill_tools_discovers_callables(tmp_path: Path) -> None:
    skill = _make_skill(
        tmp_path,
        "math-tools",
        "def add(a: int, b: int) -> int:\n"
        "    '''Add two ints.'''\n"
        "    return a + b\n"
        "\n"
        "TOOLS = [add]\n",
    )

    callables, sources = load_skill_tools([skill])

    assert [c.__name__ for c in callables] == ["add"]
    assert sources == ["math-tools:tools.py:add"]
    assert callables[0](2, 3) == 5


def test_load_skill_tools_skips_skill_without_scripts(tmp_path: Path) -> None:
    skill = _make_skill(tmp_path, "no-scripts", None)
    callables, sources = load_skill_tools([skill])
    assert callables == []
    assert sources == []


def test_load_skill_tools_ignores_underscore_files(tmp_path: Path) -> None:
    skill = _make_skill(
        tmp_path,
        "private-modules",
        "TOOLS = []\n",  # tools.py present but empty
    )
    # Add a private file that should be ignored even if it has TOOLS.
    _write(
        skill.directory / "scripts" / "_private.py",
        "def secret() -> str:\n    return 'no'\n\nTOOLS = [secret]\n",
    )
    callables, _ = load_skill_tools([skill])
    assert callables == []


def test_load_skill_tools_ignores_modules_without_tools_list(
    tmp_path: Path,
) -> None:
    skill = _make_skill(
        tmp_path,
        "no-tools-attr",
        "def helper() -> int:\n    return 1\n",  # no TOOLS list
    )
    callables, sources = load_skill_tools([skill])
    assert callables == []
    assert sources == []


def test_load_skill_tools_warns_on_non_callable_entry(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    skill = _make_skill(
        tmp_path,
        "bad-entry",
        "TOOLS = ['not a callable']\n",
    )
    with caplog.at_level("WARNING"):
        callables, _ = load_skill_tools([skill])
    assert callables == []
    assert any("not callable" in r.message for r in caplog.records)


def test_load_skill_tools_dedupes_by_name(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    skill_a = _make_skill(
        tmp_path / "a",
        "skill-a",
        "def shared() -> int:\n    return 1\n\nTOOLS = [shared]\n",
    )
    skill_b = _make_skill(
        tmp_path / "b",
        "skill-b",
        "def shared() -> int:\n    return 2\n\nTOOLS = [shared]\n",
    )
    with caplog.at_level("WARNING"):
        callables, sources = load_skill_tools([skill_a, skill_b])

    assert [c.__name__ for c in callables] == ["shared"]
    assert sources == ["skill-a:tools.py:shared"]
    assert callables[0]() == 1  # first one wins
    assert any("Duplicate tool name" in r.message for r in caplog.records)


def test_load_skill_tools_continues_after_import_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = _make_skill(
        tmp_path / "bad",
        "bad-skill",
        "raise RuntimeError('boom')\n",
    )
    good = _make_skill(
        tmp_path / "good",
        "good-skill",
        "def ok() -> str:\n    return 'ok'\n\nTOOLS = [ok]\n",
    )
    with caplog.at_level("WARNING"):
        callables, sources = load_skill_tools([bad, good])

    assert [c.__name__ for c in callables] == ["ok"]
    assert sources == ["good-skill:tools.py:ok"]
    assert any("Failed to import" in r.message for r in caplog.records)
