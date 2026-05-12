"""
Ollama backend for the reflectometry eval harness.

The runner only depends on the standard library here — calls are made
to a local Ollama server via HTTP ``/api/chat``. This avoids forcing
LangChain (or the official ``ollama`` Python client) onto users who
just want to run the eval.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://localhost:11434"


def generate(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float = 0.0,
    seed: int | None = None,
    base_url: str = DEFAULT_BASE_URL,
    json_mode: bool = False,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """
    Run a chat completion against a local Ollama server.

    Args:
        messages: OpenAI-style chat messages (``role`` ∈ {system, user, assistant}).
        model: Ollama model tag (e.g. ``"llama3.2:3b"``). Must be pulled locally.
        temperature: Sampling temperature.
        seed: Optional sampling seed for reproducibility across repeats.
        base_url: Ollama server URL.
        json_mode: If True, ask Ollama to constrain output to valid JSON
            (``format: "json"`` in the request).
        timeout: HTTP timeout in seconds.

    Returns:
        Dict with keys:
            ``text``                str  — response content
            ``latency_ms``          int  — wall-clock request latency
            ``prompt_tokens``       int|None — Ollama's ``prompt_eval_count``
            ``completion_tokens``   int|None — Ollama's ``eval_count``
            ``model_digest``        str|None — model tag echoed by Ollama

    Raises:
        urllib.error.URLError: If the Ollama server cannot be reached.
        RuntimeError: If Ollama returns an error response.

    Example:
        >>> out = generate(
        ...     [{"role": "user", "content": "hi"}],
        ...     model="llama3.2:3b",
        ... )
        >>> "text" in out
        True
    """
    options: dict[str, Any] = {"temperature": temperature}
    if seed is not None:
        options["seed"] = seed

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options,
    }
    if json_mode:
        payload["format"] = "json"

    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace") if hasattr(exc, "read") else ""
        raise RuntimeError(f"Ollama HTTP {exc.code} for model {model!r}: {detail}") from exc
    latency_ms = int((time.perf_counter() - start) * 1000)

    data = json.loads(raw)
    if "error" in data:
        raise RuntimeError(f"Ollama error for model {model!r}: {data['error']}")

    text = data.get("message", {}).get("content", "")
    return {
        "text": text,
        "latency_ms": latency_ms,
        "prompt_tokens": data.get("prompt_eval_count"),
        "completion_tokens": data.get("eval_count"),
        "model_digest": data.get("model"),
    }
