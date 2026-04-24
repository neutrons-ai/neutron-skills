# Examples

Runnable examples that show how to consume `neutron_skills` from other
agent stacks.

## Contents

| File | What it shows |
|---|---|
| [langchain_ollama_selector.py](langchain_ollama_selector.py) | A [LangChain](https://python.langchain.com/) + [Ollama](https://ollama.com/) implementation of the `LLMSelector` protocol, plus an end-to-end chain that splices the retrieved skill bodies into a chat prompt. |
| [langchain_ollama_toolcalling.py](langchain_ollama_toolcalling.py) | A skill-driven **tool-calling** agent with **dynamic tool discovery**. Retrieves the matching skill(s), scans each skill's `scripts/*.py` for module-level `TOOLS` lists of plain Python callables, wraps them into LangChain `StructuredTool`s at load time, and binds them to a tool-capable Ollama model. The skill scripts themselves have **no LangChain dependency** — see the bundled [q-range-basics tools](../src/neutron_skills/skills/general-scattering/q-range-basics/scripts/tools.py). Requires a tool-calling-capable model (e.g. `llama3.1:8b`, `qwen2.5:7b`). |

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

## Running the tool-calling example

This example needs a **tool-calling-capable** model. Pull one first:

```bash
ollama pull llama3.1:8b      # or: qwen2.5:7b, mistral-nemo
```

Then run with the default query (a SANS Q computation):

```bash
python examples/langchain_ollama_toolcalling.py
```

Or supply your own:

```bash
python examples/langchain_ollama_toolcalling.py \
    --model llama3.1:8b \
    "I want to look at features of size 200 A using lambda = 5 A. What 2theta do I need?"
```

You should see the agent loop print each tool call and result, then a
final natural-language answer that quotes the computed values and
references the retrieved skill.

### Authoring tools for a skill

To add tools to your own skill, drop a Python file in `<skill>/scripts/`
that exposes a module-level `TOOLS` list of plain Python callables.
**No LangChain (or any other agent framework) import required** — the
example wraps each callable into a `StructuredTool` at load time using
the function's type hints and docstring:

```python
# src/neutron_skills/skills/<domain>/<skill>/scripts/tools.py
def my_calculator(x: float, y: float) -> float:
    """Short description used as the tool schema."""
    return x + y

TOOLS = [my_calculator]
```

Guidelines:

- Add **type hints** on every parameter — they become the JSON schema.
- Write a clear **docstring** — it becomes the tool description.
- Keep the file's imports to the **standard library** (or libraries the
  skill genuinely needs). Other runtimes (OpenAI function calling,
  Anthropic tool use, MCP, …) can wrap the same callables in their own
  formats.
- Tool names must be unique across all bundled skills (prefix with the
  skill name if you risk a collision). Files starting with `_` are
  ignored.
