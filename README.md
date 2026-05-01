# neutron-skills

A curated registry of **Agent Skills** for neutron scattering, consumable by
other AI agents through a small Python API and a Click-based CLI.

Skills follow the [Agent Skills specification](https://agentskills.io/specification):
each skill is a directory containing a `SKILL.md` file with YAML
frontmatter (`name`, `description`, optional `metadata`, ...) and a
Markdown body of instructions.

## Install

```bash
pip install -e ".[dev]"
```

## Python API

```python
from neutron_skills import retrieve

skills = retrieve(
    "We are writing a scan script to acquire data on the EQSANS instrument at SNS."
)

# Splice skill bodies into your prompt
for s in skills:
    print(s.name, s.description)
    prompt += s.body
```

To discover the executable Python helpers a skill ships under
`<skill>/scripts/`, see the ["Tool calling"](#tool-calling-shipping-executable-helpers-with-a-skill)
section below.

### Retrieval backends

Two backends are supported; both are selected via the `method=` argument:

| method | behavior |
|---|---|
| `"deterministic"` | Keyword/tag scoring over name, description, and `metadata.{tags,instruments,techniques}`. Offline, zero extra deps. Considers all skills globally. |
| `"llm"` | **Progressive two-stage selection.** Stage 1: the selector picks the most relevant *domains* (e.g. `diffraction`, `sans`) from a tier-0 catalog. Stage 2: the selector picks skills *only from those domains* using a filtered tier-1 catalog. This prevents cross-domain leakage — a reflectometry skill can never surface on a pure diffraction query. Requires a user-supplied `LLMSelector`. Any stage failure falls back to deterministic. |
| `"auto"` (default) | Use the LLM selector if provided, else fall back to deterministic. |

Domains are inferred from the folder layout
`<skills_root>/<domain>/<skill-name>/SKILL.md`. Domain descriptions for
stage 1 come from a built-in map for the usual neutron scattering
domains (`sans`, `diffraction`, `reflectometry`, `spectroscopy`,
`inelastic`, `general-scattering`); override or extend via the
`domain_descriptions=` argument to `retrieve()`.

Example LLM selector:

```python
from neutron_skills import retrieve

class MySelector:
    def select(self, query, catalog, top_k):
        # Called once with the domain catalog, then once with the
        # filtered skill catalog. Both are lists of {name, description}.
        # Return a list of names picked from `catalog`.
        ...

skills = retrieve(
    "...",
    method="auto",
    selector=MySelector(),
    top_k=3,            # skills returned (stage 2)
    top_k_domains=2,    # domains kept after stage 1
)
```

### External skills

Add extra skill directories at runtime - they override bundled skills on
name collision:

```python
skills = retrieve("...", extra_paths=["/path/to/my/skills"])
```

## CLI

```bash
neutron-skills list                                    # all bundled skills
neutron-skills list --domain sans                      # filter by domain
neutron-skills show eqsans-scan-scripting              # print a skill body
neutron-skills retrieve "scan on EQSANS" --top-k 3     # deterministic retrieval
neutron-skills validate src/neutron_skills/skills      # lint the skill tree
neutron-skills paths                                   # show scan locations
```

## Examples

See [examples/](examples/) for runnable integrations, including a
LangChain + Ollama implementation of the `LLMSelector` protocol:

```bash
pip install -e ".[examples]"
ollama pull llama3.2:3b
python examples/langchain_ollama_selector.py \
    "scan script on EQSANS"
```

## Tool calling: shipping executable scripts with a skill

A skill can ship **CLI scripts** alongside its instructions so an agent
can perform concrete work (compute, validate, transform, …) by running
them via `uv run` in a subprocess. This is secure — no dynamic code
import, no `importlib` tricks — the script runs in an isolated
environment and communicates via JSON on stdout.

### Convention

Drop a PEP 723 Python script under `<skill>/scripts/` with CLI
subcommands:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///

import argparse, json, math

def compute_q(theta_deg: float, wavelength_aa: float) -> dict:
    q = 4 * math.pi / wavelength_aa * math.sin(math.radians(theta_deg))
    return {"Q": q}

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("compute-q")
    p.add_argument("--theta-deg", type=float, required=True)
    p.add_argument("--wavelength", type=float, required=True)
    args = parser.parse_args()
    print(json.dumps(compute_q(args.theta_deg, args.wavelength)))

if __name__ == "__main__":
    main()
```

Rules:

- Accept all input through **CLI flags** — no interactive prompts.
- Send structured data (JSON) to **stdout**; diagnostics to **stderr**.
- Provide a useful **`--help`** output so the agent can discover the interface.
- Use **meaningful exit codes** (0 = success, 2 = bad arguments, 1 = unexpected error).
- Declare dependencies using [PEP 723](https://peps.python.org/pep-0723/)
  inline metadata so `uv run` can install them automatically.
- List the script and its subcommands in the `SKILL.md` body so the LLM
  knows what's available when the skill is in context.

The retrieved `Skill.directory` and `Skill.resources` fields point at
these files.

### Running a skill's tools

Use `uv run` to execute a skill's script in an isolated environment:

```bash
uv run src/neutron_skills/skills/general-scattering/q-range-basics/scripts/q_range_tools.py \
    compute-q --theta-deg 0.25 --wavelength 6.0
```

A complete Python example that chains multiple tool calls via subprocess
is in [examples/uv_toolcalling.py](examples/uv_toolcalling.py).

## Adding a skill

1. Pick a domain directory under `src/neutron_skills/skills/`.
2. Create a subdirectory named exactly like your skill (`lowercase-with-hyphens`).
3. Add a `SKILL.md` with required frontmatter (`name`, `description`).
4. Populate `metadata.tags` / `instruments` / `techniques` - these feed the
   deterministic retriever.
5. Validate: `neutron-skills validate <path-to-skill>`.

### Instrument-specific naming (SNS and HFIR)

For instrument-specific contributions, use the global skill name pattern:

- `facility-instrument-topic`
- Example: `sns-snap-reduction-diagnostics`

Keep skill placement flat by domain so retrieval can infer domains correctly:

- `src/neutron_skills/skills/<domain>/<skill-name>/SKILL.md`

SNAP-specific note:

- Initial SNAP contributions are focused on data reduction.
- SNAP reduction skills should include software provenance in `metadata.software`
    and in the body (for example Mantid, `snapred`, `snapwrap`).
- This does not block future non-reduction SNAP skills; they should follow the
    same naming and placement scheme.

See [src/neutron_skills/skills/README.md](src/neutron_skills/skills/README.md)
for authoring conventions and [docs/ground_truths.md](docs/ground_truths.md)
for recorded project decisions.

### Human skill review vs other review types

This repository uses multiple review processes. Human review of skill content
(frontmatter `review` block updates, review commit, and review tag) is
documented in
[src/neutron_skills/skills/README.md](src/neutron_skills/skills/README.md#human-skill-review-workflow-content-review).

This is distinct from code/test/security/design reviews, which assess software
changes rather than skill-content approval state.

## Running tests

```bash
pytest
```

## License

BSD-3-Clause - see [LICENSE](LICENSE).
