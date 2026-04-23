"""
Command-line interface for neutron-skills.

Subcommands:
    list        List discovered skills.
    show        Print a skill's full SKILL.md body.
    retrieve    Retrieve relevant skills for a natural-language query.
    validate    Structurally validate a SKILL.md file or a tree of skills.
    paths       Print the directories being scanned.
"""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

import click

from . import __version__
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
    skills, tools = retrieve_fn(query, registry=registry, method=method, top_k=top_k)

    if as_json:
        click.echo(
            _json.dumps(
                {
                    "skills": [
                        {"name": s.name, "description": s.description, "path": str(s.path)}
                        for s in skills
                    ],
                    "tools": tools,
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
    if tools:
        click.echo("\nallowed-tools:")
        for t in tools:
            click.echo(f"  {t}")


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


if __name__ == "__main__":  # pragma: no cover
    main()
