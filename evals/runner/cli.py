"""
CLI entry point for the skill-quality eval harness.

The harness is domain-agnostic: each domain (``reflectometry``, ``sans``,
``diffraction``, …) lives in its own folder under ``evals/`` and ships a
``questions.yaml``. The runner figures out the right paths from the
positional ``domain`` argument.

Invocation::

    skill-eval list
    skill-eval validate reflectometry
    skill-eval run reflectometry --conditions baseline,oracle
    skill-eval report results/results.jsonl
"""

from __future__ import annotations

import logging
from pathlib import Path

import click
import yaml

from . import report as report_mod
from .conditions import CONDITIONS
from .run import RunConfig, run as run_main

# Repo path: <root>/evals/runner/cli.py -> .parent.parent == <root>/evals/
_EVALS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODELS = _EVALS_DIR / "models.yaml"

_BASE_REQUIRED_FIELDS = {"id", "topic", "type", "question", "rubric"}
_TYPES_REQUIRING_EXPECTED = {"numerical", "mc"}
_ALLOWED_TYPES = {"numerical", "mc", "short_answer", "code_diagnose"}
_ALLOWED_MC_LETTERS = {"A", "B", "C", "D"}


def _domain_questions_path(domain: str) -> Path:
    """Default path for a domain's question bank — ``evals/<domain>/questions.yaml``."""
    return _EVALS_DIR / domain / "questions.yaml"


def _discover_domains() -> list[str]:
    """Return sorted domain names that ship a ``questions.yaml``."""
    if not _EVALS_DIR.is_dir():
        return []
    return sorted(
        child.name
        for child in _EVALS_DIR.iterdir()
        if child.is_dir() and (child / "questions.yaml").exists()
    )


def _validate_questions(path: Path) -> list[str]:
    """Return a list of validation errors. Empty list means the bank is OK."""
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        return [f"YAML parse error in {path}: {exc}"]

    if not isinstance(data, list):
        return [f"{path} must contain a YAML list"]

    seen_ids: set[str] = set()
    for i, q in enumerate(data):
        if not isinstance(q, dict):
            errors.append(f"#{i}: entry is not a mapping")
            continue
        qid = q.get("id", f"#{i}")
        loc = str(qid)

        qtype = q.get("type")
        required = set(_BASE_REQUIRED_FIELDS)
        if qtype in _TYPES_REQUIRING_EXPECTED:
            required.add("expected")
        missing = required - set(q.keys())
        if missing:
            errors.append(f"{loc}: missing fields: {sorted(missing)}")

        if qtype not in _ALLOWED_TYPES:
            errors.append(f"{loc}: type {qtype!r} not in {sorted(_ALLOWED_TYPES)}")

        if qid in seen_ids:
            errors.append(f"{loc}: duplicate id")
        seen_ids.add(qid)

        expected = q.get("expected")
        if qtype in _TYPES_REQUIRING_EXPECTED:
            if not isinstance(expected, dict):
                errors.append(f"{loc}: 'expected' must be a mapping for {qtype}")
                continue
            if qtype == "numerical":
                if "value" not in expected:
                    errors.append(f"{loc}: numerical missing expected.value")
                else:
                    try:
                        float(expected["value"])
                    except (TypeError, ValueError):
                        errors.append(
                            f"{loc}: numerical expected.value must be a number"
                        )
                if "rel_tol" not in expected and "abs_tol" not in expected:
                    errors.append(f"{loc}: numerical needs rel_tol or abs_tol")
            elif qtype == "mc":
                v = expected.get("value")
                if not (isinstance(v, str) and v.strip().upper() in _ALLOWED_MC_LETTERS):
                    errors.append(
                        f"{loc}: mc expected.value must be one of "
                        f"{sorted(_ALLOWED_MC_LETTERS)}, got {v!r}"
                    )
        elif qtype in {"short_answer", "code_diagnose"}:
            must = q.get("must_mention")
            if must is not None and not isinstance(must, list):
                errors.append(f"{loc}: must_mention must be a list")
            if not must and not (q.get("rubric") or "").strip():
                errors.append(
                    f"{loc}: {qtype} needs either must_mention or a rubric "
                    "for the judge to grade against"
                )

    return errors


def _resolve_questions_path(domain: str, override: Path | None) -> Path:
    """Return the questions file for ``domain``, honoring an explicit override."""
    path = override or _domain_questions_path(domain)
    if not path.exists():
        available = _discover_domains()
        hint = ", ".join(available) if available else "(none discovered)"
        raise click.ClickException(
            f"Questions file not found: {path}\nAvailable domains: {hint}"
        )
    return path


@click.group()
def cli() -> None:
    """Skill-quality eval harness for neutron_skills."""


@cli.command(name="list")
def list_cmd() -> None:
    """List eval domains discovered under evals/."""
    domains = _discover_domains()
    if not domains:
        click.echo("(no eval domains found)")
        return
    for name in domains:
        qpath = _domain_questions_path(name)
        try:
            data = yaml.safe_load(qpath.read_text()) or []
            n: int | str = sum(1 for q in data if isinstance(q, dict))
        except yaml.YAMLError:
            n = "?"
        click.echo(
            f"  {name:<20} {n} question(s)  ({qpath.relative_to(_EVALS_DIR)})"
        )


@cli.command()
@click.argument("domain")
@click.option(
    "--questions", "questions_path", default=None,
    type=click.Path(path_type=Path),
    help="Override path to questions YAML (default: evals/<domain>/questions.yaml).",
)
def validate(domain: str, questions_path: Path | None) -> None:
    """Schema-validate a domain's question bank without calling any LLM."""
    path = _resolve_questions_path(domain, questions_path)
    errors = _validate_questions(path)
    if errors:
        for e in errors:
            click.echo(f"ERR  {e}", err=True)
        raise click.ClickException(f"{len(errors)} validation error(s)")
    click.echo(f"OK   {path} — schema valid")


@cli.command()
@click.argument("domain")
@click.option(
    "--questions", "questions_path", default=None,
    type=click.Path(path_type=Path),
    help="Override path to questions YAML (default: evals/<domain>/questions.yaml).",
)
@click.option(
    "--models", "models_path",
    default=str(DEFAULT_MODELS), show_default=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--out", "out_dir",
    default="results", show_default=True,
    type=click.Path(path_type=Path),
    help="Directory for results.jsonl and reports.",
)
@click.option(
    "--conditions",
    default="baseline,retrieve_det,oracle",
    show_default=True,
    help=f"Comma-separated subset of: {', '.join(CONDITIONS)}.",
)
@click.option(
    "--repeats", "n_repeats",
    default=1, show_default=True, type=int,
    help="Number of repeats per (model, question, condition).",
)
@click.option(
    "--top-k", default=3, show_default=True, type=int,
    help="Max skills to inject for the two retrieval conditions.",
)
@click.option(
    "--judge-model",
    default="gemma4:26b", show_default=True,
    help="Ollama model tag used as the LLM judge.",
)
@click.option(
    "--ids", "only_ids", default=None,
    help="Comma-separated question ids to run (default: all).",
)
@click.option(
    "--topic", "only_topics", default=None,
    help="Comma-separated topics to run (default: all).",
)
@click.option(
    "--cache-dir",
    default=".eval-cache", show_default=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--ollama-base-url",
    default="http://localhost:11434", show_default=True,
)
@click.option("--verbose", is_flag=True)
def run(
    domain: str,
    questions_path: Path | None,
    models_path: Path,
    out_dir: Path,
    conditions: str,
    n_repeats: int,
    top_k: int,
    judge_model: str,
    only_ids: str | None,
    only_topics: str | None,
    cache_dir: Path,
    ollama_base_url: str,
    verbose: bool,
) -> None:
    """Run the eval matrix for DOMAIN over Ollama models and write reports."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    selected_conditions = [c.strip() for c in conditions.split(",") if c.strip()]
    unknown = set(selected_conditions) - set(CONDITIONS)
    if unknown:
        raise click.ClickException(
            f"Unknown conditions: {sorted(unknown)}; allowed: {list(CONDITIONS)}"
        )

    resolved_questions = _resolve_questions_path(domain, questions_path)

    cfg = RunConfig(
        domain=domain,
        questions_path=resolved_questions,
        models_path=models_path,
        out_dir=out_dir,
        conditions=selected_conditions,
        n_repeats=n_repeats,
        top_k=top_k,
        judge_model=judge_model,
        only_ids=[s.strip() for s in only_ids.split(",")] if only_ids else None,
        only_topics=[s.strip() for s in only_topics.split(",")] if only_topics else None,
        cache_dir=cache_dir,
        ollama_base_url=ollama_base_url,
        git_sha=None,
    )

    results_path = run_main(cfg)
    click.echo(f"\nWrote {results_path}")
    report_mod.write_report(results_path, out_dir)
    click.echo(f"Wrote report files to {out_dir}")


@cli.command()
@click.argument("results_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--out", "out_dir", default=None,
    type=click.Path(path_type=Path),
    help="Output directory (default: same dir as results).",
)
def report(results_path: Path, out_dir: Path | None) -> None:
    """Regenerate reports from an existing results.jsonl."""
    out = out_dir or results_path.parent
    report_mod.write_report(results_path, out)
    click.echo(f"Wrote report files to {out}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
