"""
Main eval loop.

Iterates over (model × question × condition × repeat), calls the backend,
grades the output (with optional judge fallback), and appends one JSONL
row per trial to ``results.jsonl``. Responses are cached on disk so that
re-running the loop only hits the network for new (model, messages, options)
keys.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from neutron_skills.registry import SkillRegistry

from . import conditions as conditions_mod
from . import grade as grade_mod
from . import judge as judge_mod
from .backends import ollama as ollama_backend

logger = logging.getLogger(__name__)


@dataclass
class RunConfig:
    """All inputs the runner needs. Built by the CLI from flags/defaults."""

    domain: str
    questions_path: Path
    models_path: Path
    out_dir: Path
    conditions: list[str]
    n_repeats: int
    top_k: int
    judge_model: str
    only_ids: list[str] | None
    only_topics: list[str] | None
    cache_dir: Path
    ollama_base_url: str
    git_sha: str | None


def _git_sha(repo_dir: Path | None = None) -> str | None:
    """Return ``git rev-parse HEAD`` for reproducibility, or None if unknown."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir) if repo_dir else None,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _load_yaml(path: Path) -> Any:
    with open(path) as f:
        return yaml.safe_load(f)


def _cache_key(model: str, messages: list[dict], options: dict) -> str:
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(b"\x00")
    h.update(json.dumps(messages, sort_keys=True).encode())
    h.update(b"\x00")
    h.update(json.dumps(options, sort_keys=True).encode())
    return h.hexdigest()


def _cached_generate(
    model: str,
    messages: list[dict],
    options: dict,
    *,
    cache_dir: Path,
    base_url: str,
    json_mode: bool = False,
) -> dict[str, Any]:
    """Read-through cache around :func:`ollama_backend.generate`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(model, messages, {**options, "json_mode": bool(json_mode)})
    cache_path = cache_dir / f"{key}.json"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            cached["_cache_hit"] = True
            return cached
        except json.JSONDecodeError:
            logger.warning("corrupt cache entry, regenerating: %s", cache_path)

    result = ollama_backend.generate(
        messages,
        model=model,
        temperature=options.get("temperature", 0.0),
        seed=options.get("seed"),
        base_url=base_url,
        json_mode=json_mode,
    )
    cache_path.write_text(json.dumps(result))
    result["_cache_hit"] = False
    return result


def _filter_questions(questions: list[dict], cfg: RunConfig) -> list[dict]:
    out = questions
    if cfg.only_ids:
        wanted = set(cfg.only_ids)
        out = [q for q in out if q.get("id") in wanted]
    if cfg.only_topics:
        wanted = set(cfg.only_topics)
        out = [q for q in out if q.get("topic") in wanted]
    return out


def _select_models(models: list[dict]) -> list[dict]:
    """Keep only Ollama-backed entries. Others are silently skipped (PLAN §5)."""
    keep: list[dict] = []
    for m in models:
        backend = m.get("backend")
        if backend == "ollama":
            keep.append(m)
        else:
            logger.info(
                "Skipping model %r — backend %r is not implemented yet.",
                m.get("id"), backend,
            )
    return keep


def run(cfg: RunConfig) -> Path:
    """
    Execute the eval matrix and return the path to ``results.jsonl``.

    Side effects:
        - Creates ``cfg.out_dir`` and ``cfg.cache_dir`` if missing.
        - Appends one JSONL row per (model, question, condition, repeat).
        - Logs per-trial progress to stdout via ``print()``.
    """
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    results_path = cfg.out_dir / "results.jsonl"

    questions_all = _load_yaml(cfg.questions_path) or []
    models_all = _load_yaml(cfg.models_path) or []
    if not isinstance(questions_all, list) or not isinstance(models_all, list):
        raise SystemExit("questions.yaml and models.yaml must be YAML lists")

    models = _select_models(models_all)
    if not models:
        raise SystemExit("No Ollama models configured in models.yaml")

    questions = _filter_questions(questions_all, cfg)
    if not questions:
        raise SystemExit("No questions match the given filters.")

    registry = SkillRegistry.discover()
    git_sha = cfg.git_sha or _git_sha(cfg.questions_path.parent)

    # Judge calls reuse the Ollama backend through the same cache. The
    # judge model is configurable so users can avoid self-grading bias
    # by picking a non-candidate model (PLAN §6).
    def _judge_generate(
        messages: list[dict], *, model: str, temperature: float = 0.0,
        json_mode: bool = False,
    ) -> dict[str, Any]:
        return _cached_generate(
            model,
            messages,
            {"temperature": temperature},
            cache_dir=cfg.cache_dir / "judge",
            base_url=cfg.ollama_base_url,
            json_mode=json_mode,
        )

    n_total = len(models) * len(questions) * len(cfg.conditions) * cfg.n_repeats
    logger.info(
        "Running %d trials: %d model(s) × %d question(s) × %d condition(s) × %d repeat(s)",
        n_total, len(models), len(questions), len(cfg.conditions), cfg.n_repeats,
    )

    completed = 0
    with open(results_path, "a") as outfh:
        for model_entry in models:
            model_id = model_entry["id"]
            model_tag = model_id.split("ollama:", 1)[1]
            params = model_entry.get("params") or {}
            temperature = float(params.get("temperature", 0.0))

            for q in questions:
                for cond in cfg.conditions:
                    messages, retrieved = conditions_mod.build_messages(
                        q, cond, registry,
                        domain=cfg.domain, top_k=cfg.top_k,
                    )
                    for repeat in range(cfg.n_repeats):
                        completed += 1
                        # Vary seed per repeat so n>1 actually probes variance.
                        seed = repeat if cfg.n_repeats > 1 else None
                        try:
                            gen = _cached_generate(
                                model_tag,
                                messages,
                                {"temperature": temperature, "seed": seed},
                                cache_dir=cfg.cache_dir / "candidate",
                                base_url=cfg.ollama_base_url,
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.error(
                                "generation failed for %s / %s / %s rep %d: %s",
                                model_id, q["id"], cond, repeat, exc,
                            )
                            continue

                        response_text = gen.get("text", "")
                        det_result = grade_mod.grade(q, response_text)
                        judge_result: dict[str, Any] | None = None
                        final_score = int(det_result["score"])
                        if det_result.get("needs_judge"):
                            try:
                                judge_result = judge_mod.judge(
                                    q, response_text,
                                    generate_fn=_judge_generate,
                                    model=cfg.judge_model,
                                )
                                final_score = int(judge_result["score"])
                            except Exception as exc:  # noqa: BLE001
                                logger.warning(
                                    "judge failed for %s / %s / %s: %s",
                                    model_id, q["id"], cond, exc,
                                )

                        row = {
                            "git_sha": git_sha,
                            "model": model_id,
                            "question_id": q.get("id"),
                            "topic": q.get("topic"),
                            "type": q.get("type"),
                            "condition": cond,
                            "repeat": repeat,
                            "response": response_text,
                            "retrieved_skills": retrieved,
                            "expected_helpful_skills": q.get("expected_helpful_skills") or [],
                            "deterministic_grade": det_result,
                            "judge": judge_result,
                            "score": final_score,
                            "latency_ms": gen.get("latency_ms"),
                            "prompt_tokens": gen.get("prompt_tokens"),
                            "completion_tokens": gen.get("completion_tokens"),
                            "cache_hit": gen.get("_cache_hit", False),
                        }
                        outfh.write(json.dumps(row) + "\n")
                        outfh.flush()
                        print(
                            f"[{completed}/{n_total}] {model_id:<28} "
                            f"{q['id']:<12} {cond:<14} rep={repeat} "
                            f"score={final_score}"
                            f"{' (cache)' if gen.get('_cache_hit') else ''}"
                        )

    return results_path
