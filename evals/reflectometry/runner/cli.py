"""
CLI entry point for the reflectometry skill-quality eval harness.

Invocation::

    python -m evals.reflectometry.runner.cli validate
    python -m evals.reflectometry.runner.cli run --models ... --conditions ...
    python -m evals.reflectometry.runner.cli report results/results.jsonl
"""

from __future__ import annotations

import logging
from pathlib import Path

import click
import yaml

from . import report as report_mod
from .conditions import CONDITIONS
from .run import RunConfig, run as run_main

_REFL_DIR = Path(__file__).resolve().parent.parent  # evals/reflectometry/
DEFAULT_QUESTIONS = _REFL_DIR / "questions.yaml"
DEFAULT_MODELS = _REFL_DIR / "models.yaml"

# Fields every question must declare. `expected` is required only for the
# types that the structured graders consume (numerical, mc); short_answer
# and code_diagnose drive their contract through `must_mention` instead.
_BASE_REQUIRED_FIELDS = {"id", "topic", "type", "question", "rubric"}
_TYPES_REQUIRING_EXPECTED = {"numerical", "mc"}
_ALLOWED_TYPES = {"numerical", "mc", "short_answer", "code_diagnose"}
_ALLOWED_MC_LETTERS = {"A", "B", "C", "D"}


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
            # Either must_mention must be present (substring grader) or the
            # rubric is the sole contract for the LLM judge. Warn loudly if
            # both are absent — that question is ungradable in v1.
            must = q.get("must_mention")
            if must is not None and not isinstance(must, list):
                errors.append(f"{loc}: must_mention must be a list")
            if not must and not (q.get("rubric") or "").strip():
                errors.append(
                    f"{loc}: {qtype} needs either must_mention or a rubric "
                    "for the judge to grade against"
                )

    return errors


@click.group()
def cli() -> None:
    """Reflectometry skill-quality eval harness."""


@cli.command()
@click.option(
    "--questions", "questions_path",
    default=str(DEFAULT_QUESTIONS), show_default=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the question bank YAML.",
)
def validate(questions_path: Path) -> None:
    """Schema-validate the question bank without calling any LLM."""
    errors = _validate_questions(questions_path)
    if errors:
        for e in errors:
            click.echo(f"ERR  {e}", err=True)
        raise click.ClickException(f"{len(errors)} validation error(s)")
    click.echo(f"OK   {questions_path} — schema valid")


@cli.command()
@click.option(
    "--questions", "questions_path",
    default=str(DEFAULT_QUESTIONS), show_default=True,
    type=click.Path(exists=True, path_type=Path),
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
    questions_path: Path,
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
    """Run the eval matrix over Ollama models and write results + reports."""
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

    cfg = RunConfig(
        questions_path=questions_path,
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
