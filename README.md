# neutron-skills

A curated registry of **Agent Skills** for neutron scattering, consumable by
other AI agents through a small Python API and a Click-based CLI.

Skills follow the [Agent Skills specification](https://agentskills.io/specification):
each skill is a directory containing a `SKILL.md` file with YAML frontmatter
(`name`, `description`, optional `allowed-tools`, `metadata`, ...) and a
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

# Each Skill exposes its frontmatter, including `allowed_tools` —
# the spec's permission tokens (e.g. "Read", "Bash(python:*)") for
# runtimes that enforce a tool whitelist. To discover *executable*
# Python helpers a skill ships under `<skill>/scripts/`, see the
# "Tool calling" section below.
```

### Retrieval backends

Two backends are supported; both are selected via the `method=` argument:

| method | behavior |
|---|---|
| `"deterministic"` | Keyword/tag scoring over name, description, and `metadata.{tags,instruments,techniques}`. Offline, zero extra deps. |
| `"llm"` | Sends the tier-1 catalog (name + description only) to an LLM and uses its picks. Requires a user-supplied `LLMSelector`. |
| `"auto"` (default) | Use the LLM selector if provided, else fall back to deterministic. |

Example LLM selector:

```python
from neutron_skills import retrieve

class MySelector:
    def select(self, query, catalog, top_k):
        # call your LLM with the (name, description) catalog
        # and return a list of selected skill names
        ...

skills = retrieve("...", method="auto", selector=MySelector(), top_k=3)
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

## Tool calling: shipping executable helpers with a skill

A skill can ship **plain Python callables** alongside its instructions so
an agent can perform concrete work (compute, validate, transform, …)
through tool calls instead of free-form text.

### Convention

Drop a Python module under `<skill>/scripts/` that exposes a
module-level `TOOLS` list of plain callables:

```python
# src/neutron_skills/skills/<domain>/<skill>/scripts/tools.py
import math

def compute_q(theta_deg: float, wavelength_aa: float) -> dict[str, float]:
    """
    Compute the momentum transfer Q for elastic scattering.

    Args:
        theta_deg: HALF the scattering angle, in degrees.
        wavelength_aa: Neutron wavelength in angstroms.

    Returns:
        Dict with key ``Q`` in 1/Å.
    """
    q = 4 * math.pi / wavelength_aa * math.sin(math.radians(theta_deg))
    return {"Q": q}

TOOLS = [compute_q]
```

Rules:

- Use **type hints** on every parameter — they become the JSON schema.
- Write a clear **docstring** — it becomes the tool description.
- Keep imports to the **standard library** (or what the skill genuinely
  needs). The module must NOT depend on a specific agent framework, so
  any runtime can wrap it.
- Tool names must be unique across all bundled skills (prefix with the
  skill name if you risk a collision).
- Files starting with `_` are ignored.
- List the tool names in the `SKILL.md` body so the LLM knows what's
  available when the skill is in context.

The retrieved `Skill.directory` and `Skill.resources` fields point at
these files — runtimes are responsible for discovering and wrapping them.

### Discovering tools at runtime

Use :func:`neutron_skills.load_skill_tools` to import every matched
skill's ``scripts/*.py`` modules and collect their ``TOOLS`` lists as
plain Python callables:

```python
from neutron_skills import retrieve, load_skill_tools

skills = retrieve("scattering angle 0.5 deg, wavelength 6 A")
callables, sources = load_skill_tools(skills)
# callables: list[Callable]   — plain Python functions
# sources:   list[str]        — "<skill>:<file>:<callable>" for logging
```

This is **opt-in and side-effecting** — it imports skill modules,
executing their top-level code. The plain :func:`retrieve` call never
imports skill scripts.

Then wrap each callable in your runtime's tool format:

| Runtime | Wrap with |
|---|---|
| LangChain | `langchain_core.tools.StructuredTool.from_function(fn)` |
| OpenAI | `openai.pydantic_function_tool(fn)` (or build a JSON schema from `inspect.signature` + docstring) |
| Anthropic | Build the `input_schema` dict from `inspect.signature` |
| MCP | Register with `mcp.server.Server.list_tools` / `call_tool` |

A complete LangChain + Ollama agent loop using this pattern is in
[examples/langchain_ollama_toolcalling.py](examples/langchain_ollama_toolcalling.py).

## Adding a skill

1. Pick a domain directory under `src/neutron_skills/skills/`.
2. Create a subdirectory named exactly like your skill (`lowercase-with-hyphens`).
3. Add a `SKILL.md` with required frontmatter (`name`, `description`).
4. Populate `metadata.tags` / `instruments` / `techniques` - these feed the
   deterministic retriever.
5. Validate: `neutron-skills validate <path-to-skill>`.

See [src/neutron_skills/skills/README.md](src/neutron_skills/skills/README.md)
for authoring conventions and [docs/ground_truths.md](docs/ground_truths.md)
for recorded project decisions.

## Running tests

```bash
pytest
```

## License

BSD-3-Clause - see [LICENSE](LICENSE).
