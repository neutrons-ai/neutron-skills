"""
Discover executable Python tools shipped inside skill ``scripts/`` directories.

This module is **opt-in** and separate from :mod:`neutron_skills.registry`:
the registry only reads markdown metadata, while :func:`load_skill_tools`
imports Python files from disk and is therefore a side-effecting operation.

Convention
----------
A skill that wants to ship executable helpers places one or more Python
modules under ``<skill>/scripts/``. Each module exposes a module-level
``TOOLS`` list of plain Python callables::

    # src/neutron_skills/skills/<domain>/<skill>/scripts/tools.py
    def compute_q(theta_deg: float, wavelength_aa: float) -> dict[str, float]:
        '''Compute Q from theta and wavelength.'''
        ...

    TOOLS = [compute_q]

Files starting with ``_`` are ignored. Tool callables are returned as
plain Python objects with no agent-framework dependency; callers wrap
them into LangChain ``StructuredTool``, OpenAI function tools, MCP, etc.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .models import Skill

logger = logging.getLogger(__name__)


def _module_name_for(py_file: Path, skill: Skill) -> str:
    """Build a unique import name so two skills can both ship ``tools.py``."""
    return f"neutron_skills_dynamic.{skill.name}.{py_file.stem}"


def _import_module(py_file: Path, skill: Skill) -> Any | None:
    """Import a single ``.py`` file by absolute path. Returns None on failure."""
    module_name = _module_name_for(py_file, skill)
    spec = importlib.util.spec_from_file_location(module_name, py_file)
    if spec is None or spec.loader is None:
        logger.warning("Could not build import spec for %s", py_file)
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - skill code is untrusted
        logger.warning("Failed to import %s: %s", py_file, exc)
        sys.modules.pop(module_name, None)
        return None
    return module


def load_skill_tools(
    skills: Iterable[Skill],
) -> tuple[list[Callable[..., Any]], list[str]]:
    """
    Discover plain Python callables exposed by each skill's ``scripts/*.py``.

    For every skill, scans ``<skill>/scripts/`` for ``*.py`` files (skipping
    those starting with ``_``), imports each module, and collects entries
    from its module-level ``TOOLS`` list.

    Args:
        skills: Iterable of :class:`Skill` instances (e.g. the first element
            returned by :func:`neutron_skills.retrieve`).

    Returns:
        ``(callables, sources)`` where:

        - ``callables`` is the deduped list of plain Python callables, in
          the order they were discovered. Deduplication is by
          ``callable.__name__`` so the same function exported by two
          skills is reported once and a warning is logged.
        - ``sources`` is a list of human-readable origin strings of the
          form ``"<skill-name>:<file>:<callable-name>"`` for logging /
          debugging.

    Side effects:
        Imports skill modules, executing their top-level code. Only call
        this when you intend to bind the tools into an agent runtime.
    """
    callables: list[Callable[..., Any]] = []
    sources: list[str] = []
    seen: set[str] = set()

    for skill in skills:
        scripts_dir = skill.directory / "scripts"
        if not scripts_dir.is_dir():
            continue

        for py_file in sorted(scripts_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            module = _import_module(py_file, skill)
            if module is None:
                continue

            module_tools = getattr(module, "TOOLS", None)
            if not isinstance(module_tools, list):
                logger.debug("No TOOLS list in %s; skipping", py_file)
                continue

            for obj in module_tools:
                if not callable(obj):
                    logger.warning(
                        "Entry in %s.TOOLS is not callable: %r", py_file, obj
                    )
                    continue
                name = getattr(obj, "__name__", None) or repr(obj)
                if name in seen:
                    logger.warning(
                        "Duplicate tool name %r (from %s) ignored",
                        name,
                        py_file,
                    )
                    continue
                seen.add(name)
                callables.append(obj)
                sources.append(f"{skill.name}:{py_file.name}:{name}")

    return callables, sources
