# Skill-quality eval harness — reflectometry

A harness that measures whether the bundled neutron-scattering skills make
LLMs better at answering reflectometry textbook questions. The unit of
measurement is **accuracy on a fixed question bank**, compared across:

- model size / family (Ollama small → Anthropic / OpenAI large);
- skill-injection condition (no skills, deterministic retrieval, LLM
  retrieval, full-domain dump);
- repeat count (to measure variance from sampling).

This document is the design spec. Code in `runner/` is the implementation;
data in `questions.yaml` is the bank.

---

## 1. Goals & non-goals

**Goals**

1. Quantify the lift from injecting skills into the prompt of a given
   LLM, per question and aggregated.
2. Surface skills that *don't* help (or hurt) — i.e. when a skill is
   retrieved but the answer remains wrong, or the answer regresses.
3. Compare model families head-to-head on the same bank, with the same
   skill conditions.
4. Be reproducible: prompts, model versions, seeds, and raw responses
   are all logged and re-runnable.

**Non-goals**

1. Replacing physics textbook authority. Ground-truth answers are
   curated, not LLM-generated.
2. Open-ended evaluation of refl1d *fits* (no live `bumps` runs in the
   harness — that is `examples/` territory).
3. Benchmarking inference latency or cost. We log them but they are not
   scoring criteria.

---

## 2. Question bank format

One YAML file: `evals/reflectometry/questions.yaml`. Each entry:

```yaml
- id: refl-q-001                   # stable, citable
  topic: q-geometry                # for slicing the report
  type: numerical                  # numerical | mc | short_answer | code_diagnose
  difficulty: easy                 # easy | medium | hard
  question: |
    Compute Q for a neutron of wavelength 4.75 Å scattering at
    incident angle θ = 0.5°. Give the answer in Å⁻¹.
  expected:
    value: 0.02309                 # numerical
    units: "Å⁻¹"
    rel_tol: 0.03                  # ±3%
  must_mention: []                 # short_answer / code_diagnose only
  must_not_mention: []
  rubric: |
    Reward Q ≈ 0.0231 Å⁻¹. Common wrong answers: forgetting the factor
    of 4π (gives ~0.0058), or using 2θ instead of θ in sin().
  expected_helpful_skills:         # which skills SHOULD be retrieved
    - q-range-basics
  source: "Internal — Bragg geometry of elastic scattering"
```

Rules:

- `id` is permanent. Never reused across question rewrites — bump the
  number.
- `expected_helpful_skills` lets us score *retrieval* separately from
  *answer*: a question can be wrong because retrieval failed, or
  because the LLM ignored a correctly-retrieved skill.
- `rubric` is human-readable; the LLM-judge fallback uses it verbatim
  when no structured grader applies.

---

## 3. Question taxonomy & target coverage

Questions probe distinct skill features. Approximate target spread:

| Topic                              | # questions | Skill exercised                           |
|------------------------------------|-------------|--------------------------------------------|
| Q geometry (compute Q, λ, θ)        | 3           | `q-range-basics`                           |
| Multilayer / Bragg / d-spacing      | 1           | `q-range-basics`                           |
| Critical edge / SLD physics         | 2           | `reflectometry-common` (SLD table)        |
| Resolution: FWHM ↔ σ                | 1           | `refl1d-model-script` (dQ → σ)            |
| χ² interpretation                   | 1           | `reflectometry-common` (χ² table)         |
| BIC / model complexity              | 1           | `reflectometry-common` (BIC rules)        |
| Roughness constraints               | 1           | `reflectometry-common` (roughness rules)  |
| Refl1d API correctness              | 2           | `refl1d-model-script` + common            |
| Fitting strategy / refinement       | 2           | `reflectometry-common` (refinement)       |
| Multi-segment co-refinement         | 1           | `reflectometry-common` (sample_broadening)|
| SiO₂-on-Si default policy           | 1           | `reflectometry-common`                    |

Total: **16 questions** in the seed bank. The bank should grow over
time; the harness must run with any subset (`--ids`, `--topic` flags).

---

## 4. Conditions matrix

Each (question, model) pair is run under these prompt conditions:

| Condition         | What's in the system prompt                                   | Purpose                              |
|-------------------|---------------------------------------------------------------|--------------------------------------|
| `baseline`        | "You are a neutron-scattering tutor. Answer concisely."        | Lower bound; what the model knows.   |
| `retrieve_det`    | Baseline + top-k skills from deterministic retriever.          | Realistic agent setup, no extra LLM. |
| `retrieve_llm`    | Baseline + top-k skills from LLM-routed retriever.             | Best-case retrieval.                 |
| `oracle`          | Baseline + the `expected_helpful_skills` (perfect retrieval).  | Upper bound on skill-content help.   |
| `full_domain`     | Baseline + every skill in the `reflectometry/` domain.         | Stress test: does dumping more help? |

Run each condition `n_repeats` times (default 3) at low temperature
(0.0–0.3) to measure response variance.

---

## 5. Models

Configuration lives in `evals/reflectometry/models.yaml`:

```yaml
- id: ollama:llama3.2:1b      # parameter-tiny baseline
  backend: ollama
  params: {temperature: 0.0}
- id: ollama:llama3.2:3b
  backend: ollama
- id: ollama:qwen2.5:7b
  backend: ollama
- id: ollama:llama3.1:8b
  backend: ollama
- id: anthropic:claude-haiku-4-5
  backend: anthropic
- id: anthropic:claude-sonnet-4-6
  backend: anthropic
- id: openai:gpt-4o-mini
  backend: openai
- id: openai:gpt-4o
  backend: openai
```

Backends are pluggable — each implements `generate(messages, **kw) -> str`.
Ollama is the only required backend (offline-capable); cloud backends
are opt-in via env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) and the
runner skips them silently if absent.

Picking a parameter ladder (1B → 3B → 7B → 8B → cloud-small → cloud-large)
is deliberate: the hypothesis is that *skills help small models more*,
because larger models have more reflectometry knowledge in-weights.

---

## 6. Grading

Per question type:

- **numerical** — extract a number with a regex/JSON parser, compare to
  `expected.value` with `rel_tol` (or `abs_tol` for near-zero values).
  Tolerant of unit prefixes ("0.023 / Å", "2.3e-2 Å⁻¹"). If extraction
  fails, fall back to LLM-judge.
- **mc** — the question text lists labelled options; extract the chosen
  letter from the response. Single correct letter.
- **short_answer** — score 1 if all `must_mention` substrings appear
  (case-insensitive) AND no `must_not_mention` appears; else 0. LLM-judge
  fallback if `must_mention` is empty.
- **code_diagnose** — output must contain a specific string (e.g. the
  buggy line) and a corrected fragment. Substring match + LLM-judge.

The LLM-judge is a separate strong model (default
`anthropic:claude-sonnet-4-6`) given the question, the rubric, and the
candidate answer; it returns `{score: 0|1, reason: "..."}` as JSON. The
judge model is NEVER one of the candidates — to avoid self-grading bias.

**Retrieval grade** (separate metric): for `retrieve_det` and
`retrieve_llm`, count how many of `expected_helpful_skills` appear in
the retrieved set. Reported as precision/recall.

---

## 7. Runner architecture

```
evals/reflectometry/
├── PLAN.md                  # this file
├── README.md                # how to run
├── questions.yaml           # question bank
├── models.yaml              # model registry
└── runner/
    ├── __init__.py
    ├── cli.py               # `python -m runner` entry, argparse
    ├── backends/            # one file per backend
    │   ├── ollama.py
    │   ├── anthropic.py
    │   └── openai.py
    ├── conditions.py        # builds system prompts per condition
    ├── grade.py             # numerical / mc / short / code_diagnose
    ├── judge.py             # LLM-judge fallback
    ├── run.py               # main loop: question × model × condition × repeat
    └── report.py            # aggregate to Markdown / JSON / CSV
```

Data flow per cell of the matrix:

```
question + condition  →  system+user messages
                      →  backend.generate()        (logged: raw response, tokens, ms)
                      →  grade.score()             (logged: parsed value, judge note)
                      →  results.jsonl row
```

`results.jsonl` is the durable artifact. Reports are derived from it
and can be regenerated without re-querying any model.

---

## 8. Reporting

`runner.report` produces:

1. **`report.md`** — top-level: per-model accuracy table across
   conditions, with skills-lift column (`oracle - baseline`).
2. **`per_question.csv`** — long format for pivoting in a notebook.
3. **`failures.md`** — every wrong answer, grouped by question, with
   the response and judge reasoning. This is the debugging surface.
4. **`retrieval.md`** — precision/recall of the two retrievers vs.
   `expected_helpful_skills`.

Headline number: **mean accuracy under `retrieve_det` minus mean
accuracy under `baseline`**, per model. If positive and significant
across the bank, the skills are doing their job.

---

## 9. Reproducibility

- Pin model versions in `models.yaml` (use the dated alias when offered;
  for Ollama, log the digest).
- Log the `neutron_skills` git SHA into every `results.jsonl` row so
  results from different skill versions don't get aggregated.
- Set `temperature=0` by default. When `n_repeats > 1`, vary the seed
  (Anthropic / OpenAI) or rely on Ollama's nondeterminism.
- Cache responses by hash of (model, messages, params). A re-run only
  hits the network for new cells.

---

## 10. CI integration

- A `pytest` smoke test (`tests/test_eval_smoke.py`) loads the YAML and
  validates schema only — no LLM calls. Runs on every PR.
- A GitHub Actions workflow `.github/workflows/eval-ollama.yml`, manual
  trigger, runs the Ollama-only models on a small `--ids` subset and
  posts the report as a PR comment.
- Cloud backends run only on tagged releases (avoid burning quota on
  every push).

---

## 11. Open questions

- **Multi-turn questions.** Some realistic agent tasks (e.g. iterative
  refinement of a fit) need multi-turn context. v1 is single-turn only;
  v2 should add a `dialogue:` field with N turns and graded final state.
- **Tool use.** Skills can ship CLI scripts (`scripts/`). Should the
  harness allow the LLM to invoke them, and grade the *combined*
  answer? That changes the contract from "knowledge guidance" to
  "agent capability." Defer to v2.
- **Question generation.** Hand-curated seed bank is fine for v1; once
  the harness is stable we can add a meta-step that *generates*
  candidate questions from each skill and asks a strong model + a human
  to validate them.
- **Statistical confidence.** With 16 questions × 3 repeats = 48 trials
  per (model, condition), confidence intervals on per-condition deltas
  are wide. Plan to grow the bank to ~50 before drawing strong
  conclusions.
