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

skills, tools = retrieve(
    "We are writing a scan script to acquire data on the EQSANS instrument at SNS."
)

# Splice skill bodies into your prompt
for s in skills:
    print(s.name, s.description)
    prompt += s.body

# `tools` is the deduped union of `allowed-tools` from matched skills.
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

skills, tools = retrieve("...", method="auto", selector=MySelector(), top_k=3)
```

### External skills

Add extra skill directories at runtime - they override bundled skills on
name collision:

```python
skills, _ = retrieve("...", extra_paths=["/path/to/my/skills"])
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
