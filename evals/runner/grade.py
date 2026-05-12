"""
Graders for each question type.

Each grader returns::

    {
        "score": 0 | 1,
        "reason": "<human readable note>",
        "extracted": <parsed value, type-dependent>,
        "needs_judge": bool,   # whether to defer to the LLM judge
    }

Per ``PLAN.md`` §6:
- ``numerical`` succeeds when a number within tolerance is found.
- ``mc`` extracts a single letter A|B|C|D.
- ``short_answer`` substring-matches ``must_mention`` / ``must_not_mention``,
  or defers to the judge if ``must_mention`` is empty.
- ``code_diagnose`` substring-matches *and* always defers to the judge —
  the substring check is a cheap pre-filter, not the final word.
"""

from __future__ import annotations

import re
from typing import Any, Callable

# Match scientific or decimal numbers. Anchored to digit/dot to avoid
# capturing isolated signs.
_NUM_RE = re.compile(
    r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
)

# Tokens that follow a *final answer* in physics responses. A number trailed
# by one of these is much more likely to be the model's stated answer than
# a bare digit inside algebra (e.g. `(sld_range / 2)`). We accept optional
# whitespace and an optional leading slash (handles "0.0785/Å"), and we
# also recognize "× 10⁻⁶" / "1e-6" prefixes so that "1.0 × 10⁻⁶ Å⁻²"
# anchors on the 1.0, not the 10 or the 6.
_UNIT_AFTER_RE = re.compile(
    r"[\s/]*"
    r"(?:"
    r"[×x*·]\s*10|10\^\s*[-−]?\s*\d+|1[eE][-−]?\s*\d+"
    r"|Å|angstrom|°|deg(?:rees?)?\b|rad(?:ians?)?\b"
    r"|eV|meV|nm|cm|μm|µm"
    r")",
    re.IGNORECASE,
)


def _extract_numbers(text: str) -> list[float]:
    """Pull every numeric token from ``text`` into a list of floats."""
    nums: list[float] = []
    for m in _NUM_RE.findall(text or ""):
        try:
            nums.append(float(m))
        except ValueError:
            continue
    return nums


def _extract_unit_anchored_numbers(text: str) -> list[float]:
    """
    Return numbers immediately followed by a physics-unit token.

    The point is to ignore bare integer constants that show up inside
    algebra (``/ 2``, ``n = 1``, etc.) and only keep numbers the model
    presented as a *value with units* — which is what a stated answer
    looks like. When the response uses no units at all, the caller
    should fall back to :func:`_extract_numbers`.
    """
    text = text or ""
    out: list[float] = []
    for m in _NUM_RE.finditer(text):
        tail = text[m.end():m.end() + 24]
        if _UNIT_AFTER_RE.match(tail):
            try:
                out.append(float(m.group()))
            except ValueError:
                continue
    return out


def _within_tolerance(
    value: float,
    target: float,
    *,
    rel_tol: float | None,
    abs_tol: float | None,
) -> bool:
    if abs_tol is not None and abs(value - target) <= abs_tol:
        return True
    if rel_tol is not None and target != 0 and abs(value - target) / abs(target) <= rel_tol:
        return True
    return False


def grade_numerical(question: dict, response: str) -> dict[str, Any]:
    """
    Score a numerical-answer question by extracting numbers from the response.

    Prefers numbers immediately followed by a physics-unit token (Å, °,
    eV, ×10⁻⁶, …) since those are the model's *stated* answer rather
    than intermediate scratch. Among matching candidates we pick the
    LAST one, since the final answer is conventionally written last.
    Falls back to every numeric token when the response carries no
    units at all.
    """
    expected = question["expected"]
    target = float(expected["value"])
    rel_tol = expected.get("rel_tol")
    abs_tol = expected.get("abs_tol")
    # Fall-back so the grader is never silently lenient: 5% relative.
    if rel_tol is None and abs_tol is None:
        rel_tol = 0.05

    unit_anchored = _extract_unit_anchored_numbers(response)
    if unit_anchored:
        candidates = unit_anchored
        source = "unit-anchored"
    else:
        candidates = _extract_numbers(response)
        source = "fallback (no units found)"

    if not candidates:
        return {
            "score": 0,
            "reason": "no number extracted from response",
            "extracted": None,
            "needs_judge": True,
        }

    # Walk from the END of the response — final answers come last.
    for n in reversed(candidates):
        if _within_tolerance(n, target, rel_tol=rel_tol, abs_tol=abs_tol):
            return {
                "score": 1,
                "reason": f"matched {n} ≈ {target} ({source})",
                "extracted": n,
                "needs_judge": False,
            }

    closest = min(candidates, key=lambda x: abs(x - target))
    return {
        "score": 0,
        "reason": (
            f"closest extracted {closest} outside tolerance of {target} ({source})"
        ),
        "extracted": closest,
        "needs_judge": False,
    }


# Patterns ordered by specificity — we trust "Answer: B" over a bare "B".
_MC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"answer\s*(?:is|:|=|-)?\s*\(?\s*([ABCD])\b", re.IGNORECASE),
    re.compile(r"\b(?:option|choice|correct)\s*[:\-]?\s*\(?\s*([ABCD])\b", re.IGNORECASE),
    re.compile(r"\(\s*([ABCD])\s*\)"),
    re.compile(r"\b([ABCD])\s*[\):]"),
    re.compile(r"\b([ABCD])\b"),
]


def grade_mc(question: dict, response: str) -> dict[str, Any]:
    """Score a multiple-choice question by finding the chosen letter."""
    target = str(question["expected"]["value"]).strip().upper()
    text = response or ""
    for pat in _MC_PATTERNS:
        m = pat.search(text)
        if m:
            chosen = m.group(1).upper()
            return {
                "score": int(chosen == target),
                "reason": f"chose {chosen}, expected {target}",
                "extracted": chosen,
                "needs_judge": False,
            }
    return {
        "score": 0,
        "reason": "no candidate letter (A|B|C|D) found",
        "extracted": None,
        "needs_judge": True,
    }


def _substring_check(question: dict, response: str) -> dict[str, Any]:
    """Shared substring grader used by short_answer and code_diagnose."""
    must = [s.lower() for s in question.get("must_mention") or []]
    must_not = [s.lower() for s in question.get("must_not_mention") or []]
    text = (response or "").lower()
    forbidden = [s for s in must_not if s in text]

    if not must:
        return {
            "score": 0,
            "reason": "no must_mention rules; defer to judge",
            "extracted": None,
            "needs_judge": True,
        }

    missing = [s for s in must if s not in text]
    if missing or forbidden:
        bits = []
        if missing:
            bits.append(f"missing: {missing}")
        if forbidden:
            bits.append(f"forbidden present: {forbidden}")
        return {
            "score": 0,
            "reason": "; ".join(bits),
            "extracted": {"missing": missing, "forbidden": forbidden},
            "needs_judge": False,
        }
    return {
        "score": 1,
        "reason": "all must_mention terms present, none forbidden",
        "extracted": None,
        "needs_judge": False,
    }


def grade_short_answer(question: dict, response: str) -> dict[str, Any]:
    """Score a short_answer question via substring match (judge if no rules)."""
    return _substring_check(question, response)


def grade_code_diagnose(question: dict, response: str) -> dict[str, Any]:
    """
    Score a code_diagnose question.

    Substring check is run as a cheap pre-filter — but the judge is *always*
    invoked downstream, because identifying-the-buggy-line is a soft contract
    that's hard to express purely with substrings.
    """
    result = _substring_check(question, response)
    result["needs_judge"] = True
    return result


GRADERS: dict[str, Callable[[dict, str], dict[str, Any]]] = {
    "numerical": grade_numerical,
    "mc": grade_mc,
    "short_answer": grade_short_answer,
    "code_diagnose": grade_code_diagnose,
}


def grade(question: dict, response: str) -> dict[str, Any]:
    """Dispatch to the correct grader based on ``question['type']``."""
    grader = GRADERS.get(question.get("type", ""))
    if grader is None:
        raise ValueError(f"unknown question type: {question.get('type')!r}")
    return grader(question, response)
