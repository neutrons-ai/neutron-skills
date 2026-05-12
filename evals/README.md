# `skill-eval` — skill-quality eval harness

This directory hosts the harness that measures whether the bundled skills
in [`src/neutron_skills/skills/`](../src/neutron_skills/skills) make LLMs
better at answering domain-specific questions. The runner is
**domain-agnostic** — each scientific domain ships its own question bank
under `evals/<domain>/` and the same harness grades all of them.

```
evals/
├── README.md                    # this file
├── models.yaml                  # shared model registry (Ollama + future cloud)
├── runner/                      # generic harness — domain-agnostic
│   ├── cli.py                   # `skill-eval` entry point
│   ├── conditions.py            # baseline / retrieve_det / retrieve_llm / oracle / full_domain
│   ├── grade.py                 # numerical / mc / short_answer / code_diagnose
│   ├── judge.py                 # LLM-judge fallback
│   ├── report.py                # report.md / per_question.csv / failures.md / retrieval.md
│   ├── run.py                   # main loop, caching, JSONL output
│   └── backends/ollama.py       # only backend in v1
└── reflectometry/               # one domain bank per folder
    ├── PLAN.md                  # design spec
    ├── README.md                # domain-specific notes
    └── questions.yaml
```

## Quick start

```bash
# Discover available domains
skill-eval list

# Validate a domain's question bank (no LLM calls)
skill-eval validate reflectometry

# Run the eval matrix (assumes Ollama is running locally)
skill-eval run reflectometry --conditions baseline,retrieve_det,oracle

# Restrict to a subset while iterating
skill-eval run reflectometry --ids refl-q-001,refl-q-006 --repeats 1

# Re-generate reports from an existing results.jsonl
skill-eval report results/results.jsonl
```

The CLI is installed by `pip install -e .` as a console script. See
[`run --help`](runner/cli.py) for the full option list.

## Conditions

Every `(model, question)` pair is graded under up to five conditions:

| Condition       | System prompt contents                                       |
|-----------------|--------------------------------------------------------------|
| `baseline`      | Tutor preamble only — lower bound, "what the model knows".   |
| `retrieve_det`  | Baseline + top-k skills from the deterministic retriever.    |
| `retrieve_llm`  | Baseline + top-k skills from the LLM-routed retriever.       |
| `oracle`        | Baseline + the question's `expected_helpful_skills`.         |
| `full_domain`   | Baseline + every skill in the current domain.                |

The headline number is **mean accuracy under `retrieve_det` minus mean
accuracy under `baseline`**, per model. Positive → the skills are
helping.

## Adding a new domain

A "domain" is just a folder under `evals/` that contains a
`questions.yaml`. The harness picks up new domains automatically.

1. **Pick a folder name** that matches the skill-registry domain you
   want the `full_domain` condition to filter on. The current options
   are `reflectometry`, `sans`, `diffraction`, `general-scattering`,
   `inelastic`, and `spectroscopy` — see
   [`src/neutron_skills/skills/`](../src/neutron_skills/skills).

2. **Create the folder and the question bank:**

   ```bash
   mkdir evals/sans
   touch evals/sans/questions.yaml
   ```

3. **Author questions** following the schema in
   [reflectometry/PLAN.md §2](reflectometry/PLAN.md). Every entry needs:

   ```yaml
   - id: sans-q-001                 # stable, never re-used
     topic: form-factor             # for slicing the report
     type: numerical                # numerical | mc | short_answer | code_diagnose
     difficulty: easy               # easy | medium | hard
     question: |
       ... the question text ...
     expected:
       value: 0.123                 # numerical / mc only
       rel_tol: 0.03                # or abs_tol
     must_mention: []               # short_answer / code_diagnose only
     rubric: |
       Plain-English grading note; the LLM judge sees this verbatim.
     expected_helpful_skills:
       - sans-i-of-q-fundamentals
   ```

4. **Validate the schema** before running anything expensive:

   ```bash
   skill-eval validate sans
   ```

5. **Smoke-test a single question** end-to-end:

   ```bash
   skill-eval run sans --ids sans-q-001 --conditions baseline,oracle
   ```

6. **Write a domain README** at `evals/sans/README.md` describing
   coverage, ground-truth sources, and any quirks (see the reflectometry
   bank for an example).

## Question types and grading

| Type            | Deterministic grader                                          | Judge fallback?                  |
|-----------------|---------------------------------------------------------------|----------------------------------|
| `numerical`     | Extracts numbers followed by a physics unit (Å, °, eV, …) and matches the *last* one against `expected.value ± tol`. | Only when no number can be parsed. |
| `mc`            | Extracts a single letter A/B/C/D from the response.           | Only when no letter is found.    |
| `short_answer`  | All `must_mention` substrings must appear (case-insensitive); no `must_not_mention` may appear. | When `must_mention` is empty.    |
| `code_diagnose` | Same substring contract as `short_answer`.                    | Always — substring is a pre-filter only. |

The deterministic graders are intentionally strict so the judge is only
invoked when needed. The judge model is configurable via
`--judge-model` (default: `gemma4:26b`) and should **not** be one of the
candidate models — self-grading bias is real.

## Models

`evals/models.yaml` is shared across domains. To add a model, append an
entry with `id` and `backend`:

```yaml
- id: ollama:qwen2.5:14b
  backend: ollama
  params:
    temperature: 0.0
```

Today only the `ollama` backend is implemented; entries with other
backends are silently skipped at run time. To use a domain-specific
model lineup, pass `--models path/to/local-models.yaml`.

## Reproducibility

Each row in `results.jsonl` records the model id, the git SHA of the
skills tree, the full message list, the raw response, the deterministic
grader output, and any judge result. Responses are cached on disk by
`sha256(model, messages, options)` under `.eval-cache/`, so re-running
the same matrix only hits the network for new cells. The cache is safe
to delete at any time.

## Adding a new backend

The runner only ships an Ollama backend in v1. To add Anthropic / OpenAI:

1. Create `runner/backends/<name>.py` exposing
   `generate(messages, *, model, temperature, seed, json_mode, **kw) -> dict`.
   The return dict must contain `text`, `latency_ms`, `prompt_tokens`,
   `completion_tokens`, and `model_digest`.
2. Add a `_select_models()` branch in
   [`run.py`](runner/run.py) that dispatches `backend: <name>` entries
   to your new module.
3. Wire credentials through env vars (`ANTHROPIC_API_KEY`,
   `OPENAI_API_KEY`); silently skip the backend if the key is missing,
   to keep the Ollama-only path working out of the box.

## Outputs

Every run writes four artifacts to `--out`:

- `results.jsonl` — durable, one row per trial. Reports are derived
  from this and can be regenerated with `skill-eval report` without
  re-querying any model.
- `report.md` — per-model accuracy table + skill-lift column.
- `per_question.csv` — long-format for pivoting in a notebook.
- `failures.md` — every wrong answer, grouped by question, with the
  retrieved vs. expected skills and the judge's reasoning.
- `retrieval.md` — precision/recall of the deterministic and LLM
  retrievers vs. `expected_helpful_skills`.

## See also

- [reflectometry/PLAN.md](reflectometry/PLAN.md) — the original design
  spec; conditions, grading, and reporting are documented in detail.
- [reflectometry/README.md](reflectometry/README.md) — example of a
  domain README to model your new banks on.
