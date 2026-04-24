"""
LangChain + Ollama example for ``neutron_skills``.

This example demonstrates two things:

1. **Implementing the** :class:`neutron_skills.LLMSelector` **protocol** using
   a local Ollama model via ``langchain-ollama``. The selector receives the
   tier-1 catalog (name + description per skill) and asks the model to pick
   the most relevant skill names as strict JSON.

2. **End-to-end usage**: once skills are retrieved, their Markdown bodies are
   spliced into a chat prompt (tier-2 progressive disclosure) and the same
   local model answers the user's question with that extra context.

Usage::

    # Make sure Ollama is running and the model is pulled:
    #   ollama pull llama3.2:3b
    pip install -e ".[examples]"
    python examples/langchain_ollama_selector.py \\
        "We are writing a scan script to acquire data on EQSANS."

The selector is intentionally defensive: if the model returns malformed
JSON or unknown skill names, ``retrieve(..., method="auto")`` will fall
back to the deterministic keyword scorer.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from typing import Any

from neutron_skills import LLMSelector, retrieve

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_ollama import ChatOllama
except ImportError as exc:  # pragma: no cover - import-time guidance
    raise SystemExit(
        "This example requires the 'examples' extras. Install with:\n"
        "    pip install -e '.[examples]'\n"
        "and make sure Ollama is installed and running (https://ollama.com)."
    ) from exc


logger = logging.getLogger("neutron_skills.examples.langchain_ollama")


# ---------------------------------------------------------------------------
# LLMSelector implementation
# ---------------------------------------------------------------------------


_SELECTOR_SYSTEM_PROMPT = """\
You are a router that picks the most relevant neutron-scattering skills for a
user's task.

You will receive:
- A user query describing a task.
- A catalog of available skills, each with a `name` and short `description`.

Return STRICT JSON of the form:
    {"skills": ["skill-name-1", "skill-name-2"]}

Rules:
- Only use names that appear in the catalog.
- Return at most `top_k` names, ordered from most to least relevant.
- If nothing in the catalog is relevant, return {"skills": []}.
- Do NOT include any prose, markdown, or code fences. JSON only.
"""


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_selector_response(text: str) -> list[str]:
    """Extract ``skills`` list from a possibly-messy model response."""
    match = _JSON_BLOCK_RE.search(text or "")
    if not match:
        raise ValueError(f"No JSON object found in response: {text!r}")

    data: Any = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    skills = data.get("skills", [])
    if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
        raise ValueError(f"'skills' must be a list of strings, got {skills!r}")

    return skills


class LangChainOllamaSelector(LLMSelector):
    """
    :class:`LLMSelector` backed by a local Ollama chat model via LangChain.

    Args:
        model: Ollama model tag (e.g. ``"llama3.2:3b"``). Must already be
            pulled locally (``ollama pull <model>``).
        temperature: Sampling temperature. Keep low for routing tasks.
        base_url: Optional Ollama base URL; defaults to the library default
            (``http://localhost:11434``).
    """

    def __init__(
        self,
        model: str = "llama3.2:3b",
        *,
        temperature: float = 0.0,
        base_url: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"model": model, "temperature": temperature}
        if base_url is not None:
            kwargs["base_url"] = base_url
        # format="json" asks Ollama to constrain output to valid JSON.
        kwargs["format"] = "json"
        self._llm = ChatOllama(**kwargs)

    def select(
        self,
        query: str,
        catalog: list[dict[str, str]],
        top_k: int,
    ) -> list[str]:
        user_payload = {
            "query": query,
            "top_k": top_k,
            "catalog": catalog,
        }
        messages = [
            SystemMessage(content=_SELECTOR_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(user_payload, indent=2)),
        ]
        response = self._llm.invoke(messages)
        text = response.content if isinstance(response.content, str) else str(response.content)
        logger.debug("Selector raw response: %s", text)

        names = _parse_selector_response(text)

        # Filter to known names while preserving model ordering.
        known = {item["name"] for item in catalog}
        filtered = [n for n in names if n in known]
        return filtered[:top_k]


# ---------------------------------------------------------------------------
# End-to-end demo: retrieve skills, then answer with them as context
# ---------------------------------------------------------------------------


_ANSWER_SYSTEM_PROMPT = """\
You are an assistant for neutron-scattering scientists. Use the skill
instructions below as authoritative guidance. If the skills do not cover
the question, say so briefly.

---
{skill_bodies}
---
"""


def answer_with_skills(
    query: str,
    *,
    model: str,
    top_k: int,
    base_url: str | None,
) -> str:
    """Retrieve skills for ``query`` and answer using the same local model."""
    selector = LangChainOllamaSelector(model=model, base_url=base_url)

    skills = retrieve(query, method="auto", selector=selector, top_k=top_k)

    print(f"\nMatched {len(skills)} skill(s):")
    for s in skills:
        print(f"  - {s.name}: {s.description}")

    if not skills:
        print("\nNo relevant skills found; answering without extra context.\n")
        skill_bodies = "(no skills matched)"
    else:
        skill_bodies = "\n\n---\n\n".join(
            f"# Skill: {s.name}\n\n{s.body}" for s in skills
        )

    answer_llm = ChatOllama(
        model=model,
        temperature=0.2,
        **({"base_url": base_url} if base_url else {}),
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _ANSWER_SYSTEM_PROMPT),
            ("human", "{query}"),
        ]
    )
    chain = prompt | answer_llm
    result = chain.invoke({"skill_bodies": skill_bodies, "query": query})
    return result.content if isinstance(result.content, str) else str(result.content)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query", help="Natural-language task description")
    parser.add_argument(
        "--model",
        default="llama3.2:3b",
        help="Ollama model tag (default: llama3.2:3b)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Max number of skills to retrieve (default: 3)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging (shows raw selector responses)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    answer = answer_with_skills(
        args.query,
        model=args.model,
        top_k=args.top_k,
        base_url=args.base_url,
    )
    print("\n=== Answer ===\n")
    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
