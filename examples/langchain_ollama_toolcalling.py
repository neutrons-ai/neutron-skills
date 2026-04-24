"""
LangChain + Ollama tool-calling example with **dynamic tool discovery**
from skill ``scripts/`` directories.

This example shows how a skill can ship its own tools alongside its
instructions. The flow:

1. Retrieve relevant skills for the user query.
2. Use :func:`neutron_skills.load_skill_tools` to import each matched
   skill's ``scripts/*.py`` modules and collect their ``TOOLS`` lists
   (plain Python callables — no LangChain dependency in the skill).
3. Wrap each callable into a LangChain ``StructuredTool`` and bind it
   to a tool-capable Ollama chat model.
4. Splice the matched skill bodies into the system prompt and tell the
   model to use the discovered tools for any concrete numeric work.
5. Run a short agent loop until the model answers without calling more
   tools.

Default query exercises the bundled ``q-range-basics`` skill::

    python examples/langchain_ollama_toolcalling.py

Requirements:
- Ollama running locally with a **tool-calling-capable** model pulled,
  e.g. ``ollama pull llama3.1:8b`` or ``ollama pull qwen2.5:7b``.
  Small models (llama3.2:3b) often refuse or fumble tool calls.
- ``pip install -e ".[examples]"``
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from neutron_skills import load_skill_tools, retrieve

try:
    from langchain_core.messages import (
        AIMessage,
        BaseMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )
    from langchain_core.tools import BaseTool, StructuredTool
    from langchain_ollama import ChatOllama
except ImportError as exc:  # pragma: no cover - import-time guidance
    raise SystemExit(
        "This example requires the 'examples' extras. Install with:\n"
        "    pip install -e '.[examples]'\n"
        "and make sure Ollama is installed and running (https://ollama.com)."
    ) from exc


logger = logging.getLogger("neutron_skills.examples.toolcalling")


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT = """\
You are an assistant for neutron-scattering scientists.

The following skill instructions are authoritative. Follow them exactly.

================ SKILL CONTEXT ================
{skill_bodies}
================ END SKILL CONTEXT ================

You have access to a set of tools (listed by the runtime). **Whenever the
user gives concrete numbers, you MUST use the tools to compute results —
never do arithmetic in your head.** Combine tools when needed (for
example, convert 2*theta to theta first if a tool requires theta).

Once you have the numerical result from the tools, write a short final
answer in plain prose that quotes the tool outputs and references the
skill (e.g. the formula or the typical Q range table) to interpret them.
Do not call any more tools after writing the final answer.
"""


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


def _dispatch_tool_calls(
    ai_msg: AIMessage,
    tools_by_name: dict[str, BaseTool],
) -> list[ToolMessage]:
    """Execute every tool call requested by the model."""
    results: list[ToolMessage] = []
    for call in ai_msg.tool_calls or []:
        name = call["name"]
        args = call.get("args", {}) or {}
        call_id = call.get("id", name)

        tool_obj = tools_by_name.get(name)
        if tool_obj is None:
            content = json.dumps({"error": f"Unknown tool {name!r}"})
            print(f"  ! model requested unknown tool: {name}")
        else:
            try:
                result = tool_obj.invoke(args)
                content = json.dumps(result)
                print(f"  > {name}({args}) -> {content}")
            except Exception as exc:  # noqa: BLE001
                content = json.dumps({"error": str(exc)})
                print(f"  ! {name}({args}) raised {exc}")

        results.append(ToolMessage(content=content, tool_call_id=call_id))
    return results


def run_agent(
    query: str,
    *,
    model: str,
    base_url: str | None,
    top_k: int,
    max_iterations: int = 5,
) -> str:
    """Retrieve skills, discover their tools, and run a tool-calling loop."""
    skills = retrieve(query, method="deterministic", top_k=top_k)

    print(f"\nMatched {len(skills)} skill(s):")
    for s in skills:
        print(f"  - {s.name}: {s.description}")

    callables, sources = load_skill_tools(skills)
    tools: list[BaseTool] = [
        fn if isinstance(fn, BaseTool) else StructuredTool.from_function(fn)
        for fn in callables
    ]
    print(f"\nDiscovered {len(tools)} tool(s):")
    for src in sources:
        print(f"  - {src}")

    if not skills:
        skill_bodies = "(no skills matched)"
    else:
        skill_bodies = "\n\n---\n\n".join(
            f"# Skill: {s.name}\n\n{s.body}" for s in skills
        )

    llm = ChatOllama(
        model=model,
        temperature=0.0,
        **({"base_url": base_url} if base_url else {}),
    )
    if tools:
        llm = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}

    messages: list[BaseMessage] = [
        SystemMessage(content=_SYSTEM_PROMPT.format(skill_bodies=skill_bodies)),
        HumanMessage(content=query),
    ]

    for iteration in range(1, max_iterations + 1):
        print(f"\n--- iteration {iteration} ---")
        ai_msg = llm.invoke(messages)
        if not isinstance(ai_msg, AIMessage):
            return str(getattr(ai_msg, "content", ai_msg))
        messages.append(ai_msg)

        if not ai_msg.tool_calls:
            content = ai_msg.content
            return content if isinstance(content, str) else str(content)

        print(f"  model requested {len(ai_msg.tool_calls)} tool call(s):")
        tool_msgs = _dispatch_tool_calls(ai_msg, tools_by_name)
        messages.extend(tool_msgs)

    return (
        f"[stopped after {max_iterations} iterations without a final answer; "
        "consider raising --max-iterations or switching to a stronger model]"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


_DEFAULT_QUERY = (
    "On a SANS instrument with wavelength 6 A and a scattering angle "
    "(2*theta) of 0.5 degrees, what is Q and what real-space length "
    "scale does it probe?"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "query",
        nargs="?",
        default=_DEFAULT_QUERY,
        help="Natural-language task description (default: a SANS Q computation)",
    )
    parser.add_argument(
        "--model",
        default="llama3.1:8b",
        help=(
            "Ollama model tag. MUST support tool calling (e.g. llama3.1:8b, "
            "qwen2.5:7b, mistral-nemo). Default: llama3.1:8b"
        ),
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=2,
        help="Max number of skills to retrieve (default: 2)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum agent loop iterations (default: 5)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    print(f"Query: {args.query}")
    answer = run_agent(
        args.query,
        model=args.model,
        base_url=args.base_url,
        top_k=args.top_k,
        max_iterations=args.max_iterations,
    )
    print("\n=== Answer ===\n")
    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
