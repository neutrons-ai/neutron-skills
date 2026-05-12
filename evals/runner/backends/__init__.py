"""Pluggable backends for the eval runner.

Each backend module exposes a ``generate(messages, *, model, ...)``
function that returns a dict with ``text``, ``latency_ms``,
``prompt_tokens``, ``completion_tokens``, and ``model_digest`` keys.

Only the :mod:`ollama` backend is implemented today.
"""
