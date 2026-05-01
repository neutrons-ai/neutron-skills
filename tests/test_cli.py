"""Tests for the neutron-skills CLI."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from neutron_skills.cli import main


def _seed(root: Path) -> None:
    (root / "sans" / "eqsans-scan-scripting").mkdir(parents=True)
    (root / "sans" / "eqsans-scan-scripting" / "SKILL.md").write_text(
        "---\n"
        "name: eqsans-scan-scripting\n"
        "description: Scan scripting on EQSANS for SANS.\n"
        "allowed-tools: Read Write\n"
        "metadata:\n"
        "  instruments: [EQSANS]\n"
        "  techniques: [SANS]\n"
        "---\n"
        "# Body\nDo the scan.\n",
        encoding="utf-8",
    )
    (root / "diffraction" / "rietveld-checklist").mkdir(parents=True)
    (root / "diffraction" / "rietveld-checklist" / "SKILL.md").write_text(
        "---\nname: rietveld-checklist\ndescription: Rietveld refinement checklist.\n---\nB\n",
        encoding="utf-8",
    )


def test_list_default(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["list", "--extra-path", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "eqsans-scan-scripting" in result.output
    assert "rietveld-checklist" in result.output


def test_list_domain_filter(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["list", "--domain", "sans", "--extra-path", str(tmp_path)])
    assert result.exit_code == 0
    assert "eqsans-scan-scripting" in result.output
    assert "rietveld-checklist" not in result.output


def test_list_json(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["list", "--json", "--extra-path", str(tmp_path)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    names = {row["name"] for row in data}
    assert {"eqsans-scan-scripting", "rietveld-checklist"} <= names


def test_show_existing(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        main, ["show", "eqsans-scan-scripting", "--extra-path", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "Do the scan." in result.output


def test_show_missing_returns_error(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["show", "nope", "--extra-path", str(tmp_path)])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_retrieve_deterministic(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "retrieve",
            "EQSANS scan script",
            "--method",
            "deterministic",
            "--extra-path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "eqsans-scan-scripting" in result.output


def test_retrieve_json(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["retrieve", "EQSANS", "--json", "--extra-path", str(tmp_path)],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["skills"][0]["name"] == "eqsans-scan-scripting"
    assert "Read" in data["skills"][0]["allowed_tools"]


def test_retrieve_llm_from_cli_is_rejected(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        main, ["retrieve", "x", "--method", "llm", "--extra-path", str(tmp_path)]
    )
    assert result.exit_code == 2
    assert "selector" in result.output.lower()


def test_validate_tree(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(tmp_path)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_validate_fails_on_bad_skill(tmp_path: Path):
    bad = tmp_path / "bad-skill"
    bad.mkdir()
    (bad / "SKILL.md").write_text("no frontmatter at all\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_paths(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["paths", "--extra-path", str(tmp_path)])
    assert result.exit_code == 0
    assert "bundled:" in result.output
    assert "external:" in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def _seed_corpus(catalog_path: Path) -> None:
    catalog_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "script_id": "a",
                        "source_path": "/tmp/a.py",
                        "ipts": 33219,
                        "active": True,
                        "run_numbers_detected": [1, 2],
                        "run_titles_resolved": {"1": {"status": "resolved", "title": "Run 1"}},
                        "parse_status": "ok",
                        "run_meta_resolved": {
                            "1": {
                                "type": "assembly.dac",
                                "nickname": "DAC",
                                "model": "DAC-X",
                            }
                        },
                    }
                ),
                json.dumps(
                    {
                        "script_id": "b",
                        "source_path": "/tmp/b.py",
                        "ipts": 33220,
                        "active": False,
                        "run_numbers_detected": [],
                        "run_titles_resolved": {},
                        "parse_status": "ok",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_payload(payload_path: Path) -> None:
    payload_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "script_id": "a",
                        "content_hash": "h1",
                        "script_text": "cheese = mut.swissCheese()\nwrap.reduce(1)\nwrap.resample(0.5)",
                    }
                ),
                json.dumps(
                    {
                        "script_id": "b",
                        "content_hash": "h2",
                        "script_text": "wrap.reduce(2)",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_corpus_summary_json(tmp_path: Path):
    catalog = tmp_path / "scripts_catalog.jsonl"
    _seed_corpus(catalog)
    runner = CliRunner()
    result = runner.invoke(main, ["corpus-summary", str(catalog), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["total_records"] == 2
    assert data["active_records"] == 1
    assert data["ipts_count"] == 2


def test_corpus_list_active_only(tmp_path: Path):
    catalog = tmp_path / "scripts_catalog.jsonl"
    _seed_corpus(catalog)
    runner = CliRunner()
    result = runner.invoke(main, ["corpus-list", str(catalog), "--active-only"])
    assert result.exit_code == 0, result.output
    assert "/tmp/a.py" in result.output
    assert "/tmp/b.py" not in result.output


def test_corpus_list_json_ipts_filter(tmp_path: Path):
    catalog = tmp_path / "scripts_catalog.jsonl"
    _seed_corpus(catalog)
    runner = CliRunner()
    result = runner.invoke(main, ["corpus-list", str(catalog), "--ipts", "33220", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["script_id"] == "b"


def test_snap_corpus_join_json(tmp_path: Path):
    catalog = tmp_path / "scripts_catalog.jsonl"
    payload = tmp_path / "scripts_payload.jsonl"
    _seed_corpus(catalog)
    _seed_payload(payload)
    runner = CliRunner()
    result = runner.invoke(main, ["snap-corpus-join", str(catalog), str(payload), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["summary"]["total_joined_records"] == 2
    assert data["summary"]["records_with_assembly_dac"] == 1
    assert len(data["records"]) == 2


def test_snap_corpus_archetypes_json(tmp_path: Path):
    catalog = tmp_path / "scripts_catalog.jsonl"
    payload = tmp_path / "scripts_payload.jsonl"
    _seed_corpus(catalog)
    _seed_payload(payload)
    runner = CliRunner()
    result = runner.invoke(main, ["snap-corpus-archetypes", str(catalog), str(payload), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "archetype_id" in data[0]


def test_snap_corpus_exemplars_json(tmp_path: Path):
    catalog = tmp_path / "scripts_catalog.jsonl"
    payload = tmp_path / "scripts_payload.jsonl"
    _seed_corpus(catalog)
    _seed_payload(payload)
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "snap-corpus-exemplars",
            str(catalog),
            str(payload),
            "--max-per-archetype",
            "1",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert isinstance(data, list)
