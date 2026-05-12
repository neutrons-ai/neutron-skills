from __future__ import annotations

from neutron_skills.instruments.sns.snap.ingestion import (
    build_archetypes,
    build_exemplars,
    detect_flow_stages,
    join_catalog_payload,
    summarize_joined,
)


def test_detect_flow_stages_ordered_pipeline():
    script = """
import snapwrap.utils as wrap
cheese = mut.swissCheese()
wrap.reduce(12345)
wrap.resample(0.5)
wrap.exportData(prefix='resampled_dsp')
"""
    out = detect_flow_stages(script)
    assert out["stage_detected"]["prerequisites"] is True
    assert out["stage_detected"]["reduce"] is True
    assert out["stage_detected"]["preprocessing"] is True
    assert out["stage_order"] == ["prerequisites", "reduce", "preprocessing"]


def test_join_catalog_payload_extracts_seemeta_and_assembly_pe():
    catalog = [
        {
            "script_id": "s1",
            "source_path": "/tmp/s1.py",
            "ipts": 33219,
            "warnings": [],
            "run_meta_resolved": {
                "65891": {
                    "comment": "PE double toroid template",
                    "model": "VX3",
                    "serialNumber": "",
                    "primaryCategory": "None",
                    "secondaryCategory": "None",
                    "nickname": "PE",
                    "type": "assembly.pe",
                    "components": [
                        {"type": "gasket.toroidal", "material": "TiZr"},
                        {"type": "anvil.toroidal", "material": "sinteredDiamond"},
                    ],
                }
            },
            "reduce_flags": {"mask_args": True, "requireSameCycle": False},
        }
    ]
    payload = [
        {
            "script_id": "s1",
            "script_text": "cheese = mut.swissCheese()\nwrap.reduce(65891)\nwrap.resample(0.5)",
        }
    ]

    joined = join_catalog_payload(catalog, payload)
    assert len(joined) == 1
    rec = joined[0]
    assert rec["has_seemeta"] is True
    assert rec["has_assembly_pe"] is True
    assert rec["has_assembly_dac"] is False
    assert "assembly.pe" in rec["assembly_types_detected"]
    run_meta = rec["seemeta_by_run"]["65891"]
    assert run_meta["assembly_nickname"] == "PE"
    assert run_meta["assembly_model"] == "VX3"
    assert run_meta["assembly_comment"] == "PE double toroid template"


def test_archetypes_and_exemplars():
    joined = [
        {
            "script_id": "a",
            "source_path": "/tmp/a.py",
            "assembly_types_detected": ["assembly.pe"],
            "stage_order": ["prerequisites", "reduce", "preprocessing"],
            "stage_evidence": {"reduce": ".reduce("},
            "run_number_evidence": ["wrap.reduce(run)"],
            "reduce_flags": {
                "mask_args": True,
                "continueNoDifcal": False,
                "continueNoVan": False,
                "requireSameCycle": False,
                "noNorm": False,
            },
            "stage_detected": {"prerequisites": True, "reduce": True, "preprocessing": True},
            "has_seemeta": True,
            "has_assembly_pe": True,
            "has_assembly_dac": False,
        },
        {
            "script_id": "b",
            "source_path": "/tmp/b.py",
            "assembly_types_detected": ["assembly.pe"],
            "stage_order": ["prerequisites", "reduce", "preprocessing"],
            "stage_evidence": {"reduce": ".reduce("},
            "run_number_evidence": ["wrap.reduce(run)"],
            "reduce_flags": {
                "mask_args": True,
                "continueNoDifcal": False,
                "continueNoVan": False,
                "requireSameCycle": False,
                "noNorm": False,
            },
            "stage_detected": {"prerequisites": True, "reduce": True, "preprocessing": True},
            "has_seemeta": True,
            "has_assembly_pe": True,
            "has_assembly_dac": False,
        },
    ]

    archetypes = build_archetypes(joined)
    assert len(archetypes) == 1
    assert archetypes[0]["count"] == 2
    assert archetypes[0]["assembly_type"] == "assembly.pe"

    exemplars = build_exemplars(joined, archetypes, max_per_archetype=1)
    assert len(exemplars) == 1
    assert exemplars[0]["archetype_id"] == archetypes[0]["archetype_id"]

    summary = summarize_joined(joined)
    assert summary["records_with_assembly_pe"] == 2
    assert summary["records_with_assembly_dac"] == 0


def test_join_catalog_payload_extracts_assembly_dac():
    catalog = [
        {
            "script_id": "s2",
            "source_path": "/tmp/s2.py",
            "ipts": 33219,
            "warnings": [],
            "run_meta_resolved": {
                "70001": {
                    "comment": "DAC test",
                    "model": "DAC-X",
                    "nickname": "DAC",
                    "type": "assembly.dac",
                    "components": [{"type": "anvil.flat", "material": "diamond"}],
                }
            },
            "reduce_flags": {"mask_args": False},
        }
    ]
    payload = [{"script_id": "s2", "script_text": "wrap.reduce(70001)"}]

    joined = join_catalog_payload(catalog, payload)
    rec = joined[0]
    assert rec["has_assembly_pe"] is False
    assert rec["has_assembly_dac"] is True
    assert "assembly.dac" in rec["assembly_types_detected"]