"""
Aggregate ``results.jsonl`` into Markdown / CSV reports.

Outputs (see ``PLAN.md`` §8):

- ``report.md``        — accuracy table per model × condition with
                         oracle-minus-baseline skill lift.
- ``per_question.csv`` — long-format for pivoting in a notebook.
- ``failures.md``      — every wrong-answer row, grouped by question.
- ``retrieval.md``     — retrieval precision/recall against the
                         ``expected_helpful_skills`` field.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean


def _load_results(path: Path) -> list[dict]:
    """Read JSONL into a list of dicts, skipping blank lines."""
    rows: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _accuracy_by_model_condition(rows: list[dict]) -> dict[tuple[str, str], float]:
    """Mean ``score`` grouped by (model, condition)."""
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in rows:
        grouped[(r["model"], r["condition"])].append(int(r.get("score", 0)))
    return {k: (sum(v) / len(v) if v else 0.0) for k, v in grouped.items()}


def _retrieval_metrics(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Mean precision/recall over rows that have a non-empty oracle set."""
    by_key: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for r in rows:
        if r.get("condition") not in ("retrieve_det", "retrieve_llm"):
            continue
        expected = set(r.get("expected_helpful_skills") or [])
        if not expected:
            continue
        retrieved = set(r.get("retrieved_skills") or [])
        tp = len(retrieved & expected)
        precision = tp / len(retrieved) if retrieved else 0.0
        recall = tp / len(expected) if expected else 0.0
        by_key[(r["model"], r["condition"])].append((precision, recall))

    return {
        k: {
            "precision": mean(p for p, _ in v) if v else 0.0,
            "recall": mean(r for _, r in v) if v else 0.0,
            "n": len(v),
        }
        for k, v in by_key.items()
    }


def _format_pct(x: float) -> str:
    return f"{x:.1%}"


def _write_report_md(rows: list[dict], out_dir: Path) -> None:
    acc = _accuracy_by_model_condition(rows)
    retr = _retrieval_metrics(rows)
    models = sorted({r["model"] for r in rows})
    conditions = sorted({r["condition"] for r in rows})

    lines: list[str] = []
    lines.append("# Reflectometry eval report\n\n")
    lines.append(
        f"- Total trials: **{len(rows)}** "
        f"across {len(models)} model(s) × {len(conditions)} condition(s).\n"
    )

    lines.append("\n## Accuracy by model × condition\n\n")
    header = ["Model"] + conditions
    if "baseline" in conditions and "oracle" in conditions:
        header.append("lift (oracle − baseline)")
    lines.append("| " + " | ".join(header) + " |\n")
    lines.append("|" + "---|" * len(header) + "\n")
    for model in models:
        row = [model]
        for c in conditions:
            v = acc.get((model, c))
            row.append(_format_pct(v) if v is not None else "—")
        if "baseline" in conditions and "oracle" in conditions:
            b = acc.get((model, "baseline"))
            o = acc.get((model, "oracle"))
            row.append(f"{(o - b):+.1%}" if (b is not None and o is not None) else "—")
        lines.append("| " + " | ".join(row) + " |\n")

    if retr:
        lines.append("\n## Retrieval precision / recall\n\n")
        lines.append("| Model | Condition | Precision | Recall | n |\n")
        lines.append("|---|---|---|---|---|\n")
        for (m, c), metrics in sorted(retr.items()):
            lines.append(
                f"| {m} | {c} | {_format_pct(metrics['precision'])} | "
                f"{_format_pct(metrics['recall'])} | {metrics['n']} |\n"
            )

    (out_dir / "report.md").write_text("".join(lines))


def _write_per_question_csv(rows: list[dict], out_dir: Path) -> None:
    fieldnames = [
        "model", "question_id", "topic", "type", "condition",
        "repeat", "score", "latency_ms",
        "prompt_tokens", "completion_tokens",
    ]
    with open(out_dir / "per_question.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in fieldnames})


def _format_skill_list(skills: list[str]) -> str:
    return ", ".join(skills) if skills else "(none)"


def _retrieval_gap(retrieved: list[str], expected: list[str]) -> str:
    """Summarize the mismatch between retrieved and expected skills."""
    r, e = set(retrieved or []), set(expected or [])
    missing = sorted(e - r)
    extra = sorted(r - e)
    parts: list[str] = []
    if missing:
        parts.append(f"missing {', '.join(missing)}")
    if extra:
        parts.append(f"extra {', '.join(extra)}")
    if not parts:
        return "exact match" if e else "no oracle to compare against"
    return "; ".join(parts)


def _write_failures_md(rows: list[dict], out_dir: Path) -> None:
    failures = [r for r in rows if int(r.get("score", 0)) == 0]
    parts: list[str] = []
    parts.append(f"# Failures\n\n{len(failures)} failing trial(s).\n\n")

    # Group by question id so reviewers see all failure modes per question.
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in failures:
        grouped[r.get("question_id", "<unknown>")].append(r)

    for qid in sorted(grouped):
        parts.append(f"## {qid}\n\n")
        for r in grouped[qid]:
            parts.append(
                f"### {r['model']} / {r['condition']} / rep {r['repeat']}\n\n"
            )
            parts.append(f"- type: {r.get('type')}, topic: {r.get('topic')}\n")
            expected_skills = r.get("expected_helpful_skills") or []
            retrieved_skills = r.get("retrieved_skills") or []
            parts.append(
                f"- expected skills: {_format_skill_list(expected_skills)}\n"
            )
            parts.append(
                f"- retrieved skills: {_format_skill_list(retrieved_skills)}"
            )
            # Only meaningful for conditions that actually retrieve — for
            # baseline/oracle/full_domain the comparison is uninformative.
            if r.get("condition") in ("retrieve_det", "retrieve_llm"):
                parts.append(
                    f" — retrieval: {_retrieval_gap(retrieved_skills, expected_skills)}"
                )
            parts.append("\n")
            det = r.get("deterministic_grade") or {}
            parts.append(f"- deterministic: {det.get('reason')}\n")
            j = r.get("judge")
            if j:
                parts.append(f"- judge: score={j.get('score')} — {j.get('reason')}\n")
            parts.append("\n```\n")
            parts.append((r.get("response") or "").strip() + "\n")
            parts.append("```\n\n")
    (out_dir / "failures.md").write_text("".join(parts))


def _write_retrieval_md(rows: list[dict], out_dir: Path) -> None:
    retr = _retrieval_metrics(rows)
    parts = ["# Retrieval audit\n\n"]
    if not retr:
        parts.append(
            "_No retrieval-eligible rows (need `retrieve_det` or `retrieve_llm` "
            "with non-empty `expected_helpful_skills`)._\n"
        )
    else:
        parts.append("| Model | Condition | Precision | Recall | n |\n")
        parts.append("|---|---|---|---|---|\n")
        for (m, c), metrics in sorted(retr.items()):
            parts.append(
                f"| {m} | {c} | {_format_pct(metrics['precision'])} | "
                f"{_format_pct(metrics['recall'])} | {metrics['n']} |\n"
            )
    (out_dir / "retrieval.md").write_text("".join(parts))


def write_report(results_path: Path, out_dir: Path) -> None:
    """
    Read ``results_path`` and emit all four report artifacts under ``out_dir``.

    Args:
        results_path: Path to the JSONL produced by :mod:`run`.
        out_dir: Directory to write the reports into. Created if missing.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = _load_results(results_path)
    if not rows:
        (out_dir / "report.md").write_text("# Report\n\nNo results.\n")
        return

    _write_report_md(rows, out_dir)
    _write_per_question_csv(rows, out_dir)
    _write_failures_md(rows, out_dir)
    _write_retrieval_md(rows, out_dir)
