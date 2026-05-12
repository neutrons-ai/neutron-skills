"""
LLM-judge fallback grader.

Used when the deterministic grader signals ``needs_judge=True`` (open-ended
short_answer questions and all code_diagnose questions, per ``PLAN.md`` §6).

The judge is intentionally model-agnostic: it accepts any ``generate_fn``
matching the backend interface, so the harness can plug an Ollama, Anthropic,
or OpenAI judge by configuration.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)


_JUDGE_SYSTEM_PROMPT = """\
You are a strict, fair grader of short answers to neutron-reflectometry
questions. You will receive:
- A question.
- A grading rubric (treat it as authoritative).
- A candidate answer.

Return STRICT JSON of the form:
    {"score": 0 | 1, "reason": "<one or two sentence justification>"}

Scoring rules:
- Score 1 only when the candidate satisfies the rubric.
- When in doubt, score 0 — false positives are worse than false negatives.
- Do NOT include prose, markdown, or code fences outside the JSON object.
"""


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_judge_output(text: str) -> dict[str, Any]:
    """Extract ``{score, reason}`` from a possibly-messy judge response."""
    match = _JSON_RE.search(text or "")
    if not match:
        raise ValueError(f"no JSON object in judge output: {text!r}")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError(f"judge output is not an object: {data!r}")

    score = data.get("score")
    try:
        score_int = int(score)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"score must be 0 or 1, got {score!r}") from exc
    if score_int not in (0, 1):
        raise ValueError(f"score must be 0 or 1, got {score_int}")

    return {"score": score_int, "reason": str(data.get("reason", "")).strip()}


def judge(
    question: dict,
    response: str,
    *,
    generate_fn: Callable[..., dict[str, Any]],
    model: str,
) -> dict[str, Any]:
    """
    Score a single (question, response) pair with the LLM judge.

    Args:
        question: A question entry from ``questions.yaml`` (the ``rubric``
            field is fed to the judge verbatim).
        response: The candidate model's raw answer.
        generate_fn: A backend ``generate(messages, *, model, ...)`` callable.
            Must accept ``temperature`` and ``json_mode`` kwargs.
        model: Judge model id (e.g. ``"llama3.1:8b"``).

    Returns:
        ``{"score": 0|1, "reason": str}``. On parse failure, returns a
        defensive ``score=0`` row with the parse error as the reason.
    """
    user_payload = {
        "question": question.get("question", "").strip(),
        "rubric": question.get("rubric", "").strip(),
        "type": question.get("type", ""),
        "candidate_answer": response,
    }
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, indent=2)},
    ]
    out = generate_fn(messages, model=model, temperature=0.0, json_mode=True)
    try:
        return _parse_judge_output(out["text"])
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("judge parse failed: %s", exc)
        return {"score": 0, "reason": f"judge parse error: {exc}"}
