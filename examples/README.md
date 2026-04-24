# Examples

Runnable examples that show how to consume `neutron_skills` from other
agent stacks.

## Contents

| File | What it shows |
|---|---|
| [langchain_ollama_selector.py](langchain_ollama_selector.py) | A [LangChain](https://python.langchain.com/) + [Ollama](https://ollama.com/) implementation of the `LLMSelector` protocol, plus an end-to-end chain that splices the retrieved skill bodies into a chat prompt. |

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
