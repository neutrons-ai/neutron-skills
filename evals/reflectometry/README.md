# Reflectometry skill-quality evals

This folder is the reflectometry-specific bank for the [`skill-eval`
harness](../README.md). The harness itself is generic and lives in
[`evals/runner/`](../runner); only the questions and the design notes
are domain-specific.

## Files

- [PLAN.md](PLAN.md) — itemized harness design (architecture, prompt
  conditions, grading, models, reporting). The directory tree there is
  pre-refactor; the code now lives under `evals/runner/`.
- [questions.yaml](questions.yaml) — 17 reflectometry questions across
  Q geometry, multilayers, critical edge / SLD, resolution, χ²/BIC
  interpretation, roughness, refl1d API, refinement strategy, multi-
  segment co-refinement, and modeling defaults.

## Question coverage at a glance

| Topic                           | IDs                              |
|---------------------------------|----------------------------------|
| Q geometry                      | refl-q-001, -002, -003           |
| Multilayer / Bragg              | refl-q-004                       |
| Critical edge / SLD             | refl-q-005, -006                 |
| Resolution (FWHM ↔ σ)           | refl-q-007, -008                 |
| χ² interpretation               | refl-q-009                       |
| BIC / model complexity          | refl-q-010                       |
| Roughness                       | refl-q-011                       |
| Refl1d API                      | refl-q-012, -013                 |
| Refinement strategy             | refl-q-014                       |
| Multi-segment co-refinement     | refl-q-015                       |
| Defaults / SiO₂ policy          | refl-q-016, -017                 |

## Running

```bash
# Validate the schema (no LLM calls):
skill-eval validate reflectometry

# Smoke test against local Ollama models:
skill-eval run reflectometry \
    --conditions baseline,retrieve_det,oracle \
    --repeats 3 \
    --out results/

# Aggregate results from an existing JSONL:
skill-eval report results/results.jsonl
```

See [`evals/README.md`](../README.md) for the full CLI reference and
notes on adding new domains.

## Adding a question

1. Pick the next free `refl-q-NNN` id (don't reuse retired ids).
2. Decide the `type` (`numerical` | `mc` | `short_answer` |
   `code_diagnose`) — pick the one whose grader needs the *least*
   help from the LLM judge.
3. Fill out `expected_helpful_skills` honestly. If a question can be
   answered from training-set knowledge alone, mark it as such — those
   are useful as controls.
4. Include a `rubric` that names the most common wrong answer and why
   it is wrong. The judge prompt uses the rubric verbatim.

## Rules for ground truth

- Numerical answers must be re-derivable from the question alone using
  the formula(e) given in the relevant skill body. Don't bake in any
  hidden constant the question doesn't reveal.
- Recall-style questions (`sld-recall`, `defaults`) should match the
  values written in the skill exactly. If you change the skill, also
  update the question — that link is intentional.
- For MC questions, all distractors should be plausible failure modes
  the harness has actually seen, not strawmen.
