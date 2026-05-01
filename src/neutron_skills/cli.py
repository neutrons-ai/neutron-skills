"""
Command-line interface for neutron-skills.

Subcommands:
    list        List discovered skills.
    show        Print a skill's full SKILL.md body.
    retrieve    Retrieve relevant skills for a natural-language query.
    validate    Structurally validate a SKILL.md file or a tree of skills.
    paths       Print the directories being scanned.
    corpus-summary  Summarize a script corpus catalog JSONL.
    corpus-list     List records from a script corpus catalog JSONL.
    snap-corpus-join  Join SNAP catalog+payload and extract flow/SEEMeta features.
    snap-corpus-archetypes  Build script archetypes for generation guidance.
    snap-corpus-exemplars  Emit representative exemplars per archetype.
"""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

import click

from . import __version__
from .instruments.sns.snap.ingestion import (
    build_archetypes,
    build_exemplars,
    filter_catalog,
    join_catalog_payload,
    load_jsonl,
    summarize_catalog,
    summarize_joined,
)
from .loader import parse_skill_md
from .registry import SkillRegistry, _bundled_skills_root, _iter_skill_md_files
from .retrieve import retrieve as retrieve_fn


def _build_registry(extra_paths: tuple[str, ...], *, bundled: bool = True) -> SkillRegistry:
    return SkillRegistry.discover(bundled=bundled, extra_paths=list(extra_paths) or None)


_extra_path_option = click.option(
    "--extra-path",
    "extra_paths",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=str),
    help="Additional directory to scan for skills. May be given multiple times.",
)


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Curated Agent Skills for neutron scattering."""


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@main.command("list")
@click.option("--domain", default=None, help="Filter by domain (path segment, e.g. 'sans').")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@_extra_path_option
def list_cmd(domain: str | None, as_json: bool, extra_paths: tuple[str, ...]) -> None:
    """List all discovered skills."""
    registry = _build_registry(extra_paths)
    skills = registry.by_domain(domain) if domain else registry.all()

    if as_json:
        click.echo(
            _json.dumps(
                [
                    {"name": s.name, "description": s.description, "path": str(s.path)}
                    for s in skills
                ],
                indent=2,
            )
        )
        return

    if not skills:
        click.echo("No skills found.")
        return

    for s in skills:
        click.echo(f"{s.name}\n  {s.description}\n  {s.path}")


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@main.command("show")
@click.argument("name")
@_extra_path_option
def show_cmd(name: str, extra_paths: tuple[str, ...]) -> None:
    """Print the full SKILL.md body for NAME."""
    registry = _build_registry(extra_paths)
    skill = registry.get(name)
    if skill is None:
        click.echo(f"Skill not found: {name}", err=True)
        sys.exit(1)
    click.echo(skill.body)


# ---------------------------------------------------------------------------
# retrieve
# ---------------------------------------------------------------------------


@main.command("retrieve")
@click.argument("query")
@click.option("--top-k", default=5, show_default=True, type=int)
@click.option(
    "--method",
    type=click.Choice(["auto", "deterministic", "llm"]),
    default="auto",
    show_default=True,
    help="Retrieval backend. 'llm' requires a selector (not available from the CLI yet).",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@_extra_path_option
def retrieve_cmd(
    query: str,
    top_k: int,
    method: str,
    as_json: bool,
    extra_paths: tuple[str, ...],
) -> None:
    """Retrieve skills relevant to QUERY."""
    if method == "llm":
        click.echo(
            "The 'llm' method requires a selector injected via the Python API; "
            "use --method deterministic or auto from the CLI.",
            err=True,
        )
        sys.exit(2)

    registry = _build_registry(extra_paths)
    skills = retrieve_fn(query, registry=registry, method=method, top_k=top_k)

    if as_json:
        click.echo(
            _json.dumps(
                {
                    "skills": [
                        {
                            "name": s.name,
                            "description": s.description,
                            "path": str(s.path),
                            "allowed_tools": s.allowed_tools,
                        }
                        for s in skills
                    ],
                },
                indent=2,
            )
        )
        return

    if not skills:
        click.echo("No matching skills.")
        return

    for s in skills:
        click.echo(f"- {s.name}: {s.description}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@main.command("validate")
@click.argument(
    "path",
    type=click.Path(exists=True, path_type=Path),
    required=False,
)
def validate_cmd(path: Path | None) -> None:
    """
    Validate one skill (SKILL.md or skill directory) or a tree of skills.

    With no PATH, validates the bundled skills.
    """
    target = path or _bundled_skills_root()

    targets: list[Path] = []
    if target.is_file() and target.name == "SKILL.md":
        targets = [target]
    elif target.is_dir():
        if (target / "SKILL.md").is_file():
            targets = [target / "SKILL.md"]
        else:
            targets = list(_iter_skill_md_files(target))
    else:
        click.echo(f"Not a SKILL.md or skill directory: {target}", err=True)
        sys.exit(2)

    if not targets:
        click.echo(f"No SKILL.md files found under {target}")
        return

    failures = 0
    for skill_md in targets:
        skill = parse_skill_md(skill_md)
        if skill is None:
            click.echo(f"FAIL  {skill_md}")
            failures += 1
        else:
            click.echo(f"OK    {skill.name}  ({skill_md})")

    if failures:
        click.echo(f"\n{failures} skill(s) failed validation.", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------


@main.command("paths")
@_extra_path_option
def paths_cmd(extra_paths: tuple[str, ...]) -> None:
    """Print the directories that would be scanned for skills."""
    click.echo(f"bundled:  {_bundled_skills_root()}")
    for p in extra_paths:
        click.echo(f"external: {Path(p).expanduser().resolve()}")


# ---------------------------------------------------------------------------
# corpus-summary
# ---------------------------------------------------------------------------


@main.command("corpus-summary")
@click.argument(
    "catalog_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def corpus_summary_cmd(catalog_path: Path, as_json: bool) -> None:
    """Summarize a script corpus catalog JSONL file."""
    records = load_jsonl(catalog_path)
    summary = summarize_catalog(records)

    if as_json:
        click.echo(_json.dumps(summary, indent=2))
        return

    click.echo(f"Catalog: {catalog_path}")
    click.echo(f"Total records: {summary['total_records']}")
    click.echo(f"Active records: {summary['active_records']}")
    click.echo(f"IPTS count: {summary['ipts_count']}")
    click.echo(f"Scripts with runs: {summary['scripts_with_identified_runs']}")
    click.echo(f"Scripts with resolved titles: {summary['scripts_with_resolved_titles']}")
    click.echo(f"Parse failures: {summary['parse_failures']}")


# ---------------------------------------------------------------------------
# corpus-list
# ---------------------------------------------------------------------------


@main.command("corpus-list")
@click.argument(
    "catalog_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--active-only", is_flag=True, help="Show only records with active=true.")
@click.option("--ipts", type=int, default=None, help="Filter to a single IPTS number.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def corpus_list_cmd(
    catalog_path: Path, active_only: bool, ipts: int | None, as_json: bool
) -> None:
    """List records from a script corpus catalog JSONL file."""
    records = filter_catalog(load_jsonl(catalog_path), active_only=active_only, ipts=ipts)

    if as_json:
        click.echo(_json.dumps(records, indent=2))
        return

    if not records:
        click.echo("No corpus records found.")
        return

    for record in records:
        source_path = record.get("source_path", "<unknown>")
        record_ipts = record.get("ipts", "?")
        active = bool(record.get("active"))
        runs = len(record.get("run_numbers_detected") or [])
        click.echo(f"{source_path}\n  IPTS: {record_ipts}  active: {active}  runs: {runs}")


# ---------------------------------------------------------------------------
# snap-corpus-join
# ---------------------------------------------------------------------------


@main.command("snap-corpus-join")
@click.argument("catalog_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("payload_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--active-only", is_flag=True, help="Use only active catalog records before join.")
@click.option("--ipts", type=int, default=None, help="Filter to a single IPTS number before join.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def snap_corpus_join_cmd(
    catalog_path: Path,
    payload_path: Path,
    active_only: bool,
    ipts: int | None,
    as_json: bool,
) -> None:
    """Join SNAP script catalog and payload files and extract stage/SEEMeta features."""
    catalog_records = filter_catalog(
        load_jsonl(catalog_path), active_only=active_only, ipts=ipts
    )
    payload_records = load_jsonl(payload_path)
    joined = join_catalog_payload(catalog_records, payload_records)
    summary = summarize_joined(joined)

    if as_json:
        click.echo(_json.dumps({"summary": summary, "records": joined}, indent=2))
        return

    click.echo(f"Joined records: {summary['total_joined_records']}")
    click.echo(f"With SEEMeta: {summary['records_with_seemeta']}")
    click.echo(f"With assembly.pe: {summary['records_with_assembly_pe']}")
    click.echo(f"With assembly.dac: {summary['records_with_assembly_dac']}")


# ---------------------------------------------------------------------------
# snap-corpus-archetypes
# ---------------------------------------------------------------------------


@main.command("snap-corpus-archetypes")
@click.argument("catalog_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("payload_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--active-only", is_flag=True, help="Use only active catalog records before analysis.")
@click.option("--ipts", type=int, default=None, help="Filter to a single IPTS number before analysis.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def snap_corpus_archetypes_cmd(
    catalog_path: Path,
    payload_path: Path,
    active_only: bool,
    ipts: int | None,
    as_json: bool,
) -> None:
    """Build SNAP script archetypes from joined catalog+payload records."""
    catalog_records = filter_catalog(
        load_jsonl(catalog_path), active_only=active_only, ipts=ipts
    )
    payload_records = load_jsonl(payload_path)
    joined = join_catalog_payload(catalog_records, payload_records)
    archetypes = build_archetypes(joined)

    if as_json:
        click.echo(_json.dumps(archetypes, indent=2))
        return

    click.echo(f"Archetypes: {len(archetypes)}")
    for archetype in archetypes[:10]:
        click.echo(
            f"- {archetype['archetype_id']}: count={archetype['count']} assembly={archetype['assembly_type']}"
        )


# ---------------------------------------------------------------------------
# snap-corpus-exemplars
# ---------------------------------------------------------------------------


@main.command("snap-corpus-exemplars")
@click.argument("catalog_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("payload_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--active-only", is_flag=True, help="Use only active catalog records before analysis.")
@click.option("--ipts", type=int, default=None, help="Filter to a single IPTS number before analysis.")
@click.option("--max-per-archetype", default=3, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def snap_corpus_exemplars_cmd(
    catalog_path: Path,
    payload_path: Path,
    active_only: bool,
    ipts: int | None,
    max_per_archetype: int,
    as_json: bool,
) -> None:
    """Emit representative script exemplars per SNAP archetype."""
    catalog_records = filter_catalog(
        load_jsonl(catalog_path), active_only=active_only, ipts=ipts
    )
    payload_records = load_jsonl(payload_path)
    joined = join_catalog_payload(catalog_records, payload_records)
    archetypes = build_archetypes(joined)
    exemplars = build_exemplars(joined, archetypes, max_per_archetype=max_per_archetype)

    if as_json:
        click.echo(_json.dumps(exemplars, indent=2))
        return

    click.echo(f"Exemplars: {len(exemplars)}")
    for exemplar in exemplars[:20]:
        click.echo(
            f"- {exemplar['archetype_id']} :: {exemplar['script_id']} :: {exemplar['source_path']}"
        )


if __name__ == "__main__":  # pragma: no cover
    main()
