"""Helpers for consuming SNAP-specific script corpus outputs."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import re
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load newline-delimited JSON records from ``path``."""
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected JSON object at {path}:{line_number}, got {type(record).__name__}"
                )
            records.append(record)
    return records


def summarize_catalog(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a compact summary of SNAP script-corpus catalog records."""
    ipts_counter: Counter[str] = Counter()
    active_records = 0
    scripts_with_runs = 0
    scripts_with_resolved_titles = 0
    parse_failures = 0
    title_status_counter: Counter[str] = Counter()

    for record in records:
        ipts = record.get("ipts")
        if ipts is not None:
            ipts_counter[str(ipts)] += 1

        if bool(record.get("active")):
            active_records += 1

        run_numbers = record.get("run_numbers_detected") or []
        if run_numbers:
            scripts_with_runs += 1

        run_titles = record.get("run_titles_resolved") or {}
        if any(details.get("status") == "resolved" for details in run_titles.values()):
            scripts_with_resolved_titles += 1
        for details in run_titles.values():
            status = details.get("status")
            if status:
                title_status_counter[str(status)] += 1

        if record.get("parse_status") not in (None, "ok"):
            parse_failures += 1

    return {
        "total_records": len(records),
        "active_records": active_records,
        "ipts_count": len(ipts_counter),
        "ipts_breakdown": dict(sorted(ipts_counter.items())),
        "scripts_with_identified_runs": scripts_with_runs,
        "scripts_with_resolved_titles": scripts_with_resolved_titles,
        "parse_failures": parse_failures,
        "title_status_counts": dict(sorted(title_status_counter.items())),
    }


def filter_catalog(
    records: list[dict[str, Any]], *, active_only: bool = False, ipts: int | None = None
) -> list[dict[str, Any]]:
    """Filter SNAP script-corpus records for listing and downstream inspection."""
    filtered: list[dict[str, Any]] = []
    for record in records:
        if active_only and not bool(record.get("active")):
            continue
        if ipts is not None and record.get("ipts") != ipts:
            continue
        filtered.append(record)
    return filtered


def _find_first_match_position(text: str, patterns: list[str]) -> tuple[int | None, str | None]:
    best_pos: int | None = None
    best_pat: str | None = None
    for pattern in patterns:
        idx = text.find(pattern)
        if idx == -1:
            continue
        if best_pos is None or idx < best_pos:
            best_pos = idx
            best_pat = pattern
    return best_pos, best_pat


def detect_flow_stages(script_text: str) -> dict[str, Any]:
    """Detect script flow stages and stage ordering from script text."""
    lower = script_text.lower()

    stage_patterns = {
        "prerequisites": [
            "swisscheese",
            "makemaskbinstables",
            "specieslisttojson",
            "specieslistfromjson",
            "load(",
            "setup",
            "create",
        ],
        "reduce": [
            ".reduce(",
            "wrap.reduce(",
            "blue.reduce(",
            ".reload(",
        ],
        "preprocessing": [
            ".resample(",
            "compositebackground(",
            ".exportdata(",
            "convertunits(",
            "rebin(",
            "plot(",
        ],
    }

    stage_positions: dict[str, int] = {}
    stage_evidence: dict[str, str] = {}
    for stage, patterns in stage_patterns.items():
        pos, pat = _find_first_match_position(lower, patterns)
        if pos is not None and pat is not None:
            stage_positions[stage] = pos
            stage_evidence[stage] = pat

    stage_order = [
        stage for stage, _ in sorted(stage_positions.items(), key=lambda item: item[1])
    ]
    return {
        "stage_detected": {
            "prerequisites": "prerequisites" in stage_positions,
            "reduce": "reduce" in stage_positions,
            "preprocessing": "preprocessing" in stage_positions,
        },
        "stage_order": stage_order,
        "stage_evidence": stage_evidence,
    }


def _extract_assembly_features(meta: dict[str, Any]) -> dict[str, Any] | None:
    """Extract assembly-level SEEMeta features from one run metadata object."""
    if not isinstance(meta, dict):
        return None

    assembly_type = meta.get("type")
    if assembly_type is None and "stringDescriptor" not in meta and "components" not in meta:
        return None

    components = meta.get("components") if isinstance(meta.get("components"), list) else []
    component_types = sorted(
        {
            str(component.get("type"))
            for component in components
            if isinstance(component, dict) and component.get("type")
        }
    )
    component_materials = sorted(
        {
            str(component.get("material"))
            for component in components
            if isinstance(component, dict) and component.get("material")
        }
    )

    return {
        "assembly_type": assembly_type,
        "assembly_nickname": meta.get("nickname"),
        "assembly_model": meta.get("model"),
        "assembly_comment": meta.get("comment"),
        "assembly_serial_number": meta.get("serialNumber"),
        "assembly_primary_category": meta.get("primaryCategory"),
        "assembly_secondary_category": meta.get("secondaryCategory"),
        "assembly_string_descriptor": meta.get("stringDescriptor"),
        "component_types": component_types,
        "component_materials": component_materials,
    }


def join_catalog_payload(
    catalog_records: list[dict[str, Any]], payload_records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Join catalog and payload records by script_id and enrich with extracted features."""
    payload_by_id = {record.get("script_id"): record for record in payload_records}
    joined: list[dict[str, Any]] = []

    for catalog_record in catalog_records:
        script_id = catalog_record.get("script_id")
        payload_record = payload_by_id.get(script_id)
        record = dict(catalog_record)
        warnings = list(record.get("warnings") or [])

        script_text = ""
        if payload_record is not None:
            script_text = str(payload_record.get("script_text") or "")
            payload_hash = payload_record.get("content_hash")
            catalog_hash = catalog_record.get("content_hash")
            if payload_hash and catalog_hash and payload_hash != catalog_hash:
                warnings.append("content_hash_mismatch_between_catalog_and_payload")
        else:
            warnings.append("missing_payload_record")

        flow = detect_flow_stages(script_text)
        record.update(flow)

        run_meta = catalog_record.get("run_meta_resolved") or {}
        seemeta_by_run: dict[str, dict[str, Any]] = {}
        assembly_types: set[str] = set()
        for run, meta in run_meta.items():
            if not isinstance(meta, dict):
                continue
            extracted = _extract_assembly_features(meta)
            if extracted is None:
                continue
            seemeta_by_run[str(run)] = extracted
            assembly_type = extracted.get("assembly_type")
            if isinstance(assembly_type, str) and assembly_type:
                assembly_types.add(assembly_type)

        record["seemeta_by_run"] = seemeta_by_run
        record["assembly_types_detected"] = sorted(assembly_types)
        record["has_seemeta"] = bool(seemeta_by_run)
        record["has_assembly_pe"] = "assembly.pe" in assembly_types
        record["has_assembly_dac"] = "assembly.dac" in assembly_types
        record["warnings"] = warnings
        joined.append(record)

    return joined


def build_archetypes(joined_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group joined records into script archetypes for generation guidance."""
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in joined_records:
        flags = record.get("reduce_flags") or {}
        stage_order = tuple(record.get("stage_order") or [])
        assembly_type = (record.get("assembly_types_detected") or ["unknown"])[0]
        key = (
            assembly_type,
            stage_order,
            bool(flags.get("mask_args")),
            bool(flags.get("continueNoDifcal")),
            bool(flags.get("continueNoVan")),
            bool(flags.get("requireSameCycle")),
            bool(flags.get("noNorm")),
        )
        buckets.setdefault(key, []).append(record)

    archetypes: list[dict[str, Any]] = []
    for i, (key, records) in enumerate(
        sorted(buckets.items(), key=lambda kv: len(kv[1]), reverse=True), start=1
    ):
        (
            assembly_type,
            stage_order,
            mask_args,
            continue_no_difcal,
            continue_no_van,
            require_same_cycle,
            no_norm,
        ) = key
        archetypes.append(
            {
                "archetype_id": f"snap-archetype-{i:03d}",
                "count": len(records),
                "assembly_type": assembly_type,
                "stage_order": list(stage_order),
                "reduce_flags": {
                    "mask_args": mask_args,
                    "continueNoDifcal": continue_no_difcal,
                    "continueNoVan": continue_no_van,
                    "requireSameCycle": require_same_cycle,
                    "noNorm": no_norm,
                },
                "script_ids": [str(r.get("script_id")) for r in records],
            }
        )
    return archetypes


def build_exemplars(
    joined_records: list[dict[str, Any]], archetypes: list[dict[str, Any]], max_per_archetype: int = 3
) -> list[dict[str, Any]]:
    """Build representative exemplars per archetype with stage evidence."""
    by_script_id = {record.get("script_id"): record for record in joined_records}
    exemplars: list[dict[str, Any]] = []
    for archetype in archetypes:
        archetype_id = archetype["archetype_id"]
        for script_id in archetype.get("script_ids", [])[:max_per_archetype]:
            record = by_script_id.get(script_id)
            if record is None:
                continue
            exemplars.append(
                {
                    "archetype_id": archetype_id,
                    "script_id": script_id,
                    "source_path": record.get("source_path"),
                    "assembly_types_detected": record.get("assembly_types_detected", []),
                    "stage_order": record.get("stage_order", []),
                    "stage_evidence": record.get("stage_evidence", {}),
                    "run_number_evidence": record.get("run_number_evidence", []),
                }
            )
    return exemplars


def summarize_joined(joined_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize joined records with stage and SEEMeta coverage."""
    stage_counter: Counter[str] = Counter()
    assembly_counter: Counter[str] = Counter()
    has_seemeta = 0
    has_assembly_pe = 0
    has_assembly_dac = 0

    for record in joined_records:
        for stage, present in (record.get("stage_detected") or {}).items():
            if present:
                stage_counter[str(stage)] += 1
        if record.get("has_seemeta"):
            has_seemeta += 1
        if record.get("has_assembly_pe"):
            has_assembly_pe += 1
        if record.get("has_assembly_dac"):
            has_assembly_dac += 1
        for assembly_type in record.get("assembly_types_detected") or []:
            assembly_counter[str(assembly_type)] += 1

    return {
        "total_joined_records": len(joined_records),
        "records_with_seemeta": has_seemeta,
        "records_with_assembly_pe": has_assembly_pe,
        "records_with_assembly_dac": has_assembly_dac,
        "stage_presence_counts": dict(sorted(stage_counter.items())),
        "assembly_type_counts": dict(sorted(assembly_counter.items())),
    }