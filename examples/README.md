# Examples

Runnable examples that show how to consume `neutron_skills` from other
agent stacks.

## Contents

| File | What it shows |
|---|---|
| [langchain_ollama_selector.py](langchain_ollama_selector.py) | A [LangChain](https://python.langchain.com/) + [Ollama](https://ollama.com/) implementation of the `LLMSelector` protocol, plus an end-to-end chain that splices the retrieved skill bodies into a chat prompt. |
| [uv_toolcalling.py](uv_toolcalling.py) | Calls a skill's bundled CLI tools via `uv run` subprocess — no dynamic code import, no agent framework needed. Retrieves the `q-range-basics` skill, locates `scripts/q_range_tools.py`, and chains its subcommands (`half-angle`, `compute-q`, `compute-d-spacing`) to compute Q and d-spacing from a scattering angle. Requires only `uv` on PATH. |

## Prerequisites

1. **Install Ollama** and pull a small instruction-tuned model:

   ```bash
   # https://ollama.com/download
   ollama pull llama3.2:3b
   ```

   Make sure the Ollama daemon is running (`ollama serve` or the desktop app).

2. **Install the example extras** (from the repo root):

   ```bash
   pip install -e ".[examples]"
   ```

   This pulls in `langchain`, `langchain-core`, and `langchain-ollama`
   alongside the core `neutron_skills` package.

## Running the LangChain + Ollama example

```bash
python examples/langchain_ollama_selector.py \
    "We are writing a scan script to acquire data on the EQSANS instrument at SNS."
```

You should see:

1. The catalog of bundled skills sent to Ollama for selection.
2. The names of the skills the LLM picked (with deterministic fallback
   if the call fails or returns nothing useful).
3. A final answer from the LLM, generated with the matched skill bodies
   spliced into the system prompt (progressive disclosure, tier 2).

### Changing the model

Pass `--model` to use a different Ollama model, e.g.:

```bash
python examples/langchain_ollama_selector.py \
    --model qwen2.5:7b-instruct \
    "How do I choose a Q-range for a SANS experiment?"
```

## Running the uv tool-calling example

This example requires only `uv` on your PATH (no Ollama, no extras):

```bash
# Install uv: https://docs.astral.sh/uv/
pip install -e .
python examples/uv_toolcalling.py
```

You should see the tool chain its subcommands (`half-angle` → `compute-q`
→ `compute-d-spacing`) and print Q and d-spacing for the default
scattering angle.

Customise the parameters:

```bash
python examples/uv_toolcalling.py \
    --two-theta-deg 1.0 \
    --wavelength 5.0
```

You can also call the script directly (bypassing the Python wrapper):

```bash
uv run src/neutron_skills/skills/general-scattering/q-range-basics/scripts/q_range_tools.py \
    compute-q --theta-deg 0.25 --wavelength 6.0
```

### Authoring uv scripts for a skill

Bundle a `scripts/*.py` file that declares its own dependencies using
[PEP 723](https://peps.python.org/pep-0723/) inline metadata:

```python
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "numpy>=1.24",
# ]
# ///
```

Design guidelines (from the Agent Skills spec):

- Accept all input through **CLI flags** — no interactive prompts.
- Send structured data (JSON) to **stdout**; diagnostics to **stderr**.
- Provide a useful **`--help`** output so the agent can discover the interface.
- Use **meaningful exit codes** (0 = success, 2 = bad arguments, 1 = unexpected error).
- Support **`--output FILE`** for large results so the agent isn't flooded.

See [src/neutron_skills/skills/general-scattering/q-range-basics/scripts/q_range_tools.py](../src/neutron_skills/skills/general-scattering/q-range-basics/scripts/q_range_tools.py) for a complete reference implementation.
