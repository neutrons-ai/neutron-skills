---
name: sns-snap-reduction-workflow-overview
description: Outline the end-to-end SNAP data-reduction workflow and decision points. Use when deciding the sequence of preprocessing, calibration, normalization, and output products for SNAP diffraction data.
version: 1
review:
  status: human-reviewed
  reviewer: Malcolm Guthrie
  reviewed_on: 2026-04-30
  basis: [docs, code, instrument-science-review]
  notes: >
    Clarified reduction-level context requirements, including sample-environment
    assembly context and cycle-strict calibration matching policy, and added
    explicit sample-environment handling in the recommended workflow sequence.
  approved_commit: review/sns-snap-reduction-workflow-overview-v1
metadata:
  facility: SNS
  beamline: BL3
  instruments: [SNAP, SNS]
  software: [snapwrap, snapred, Mantid]
  data_phase: reduction
  techniques: [diffraction, powder-diffraction, time-of-flight, data-reduction]
  tags: [workflow, reduction, preprocessing, normalization, outputs]
---

# SNAP Reduction Workflow Overview

Use this skill to frame the overall reduction process before implementing or
running detailed steps.

## Evidence tracking

**Phase 0 baseline** (2026-04-29):
- Source: https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html
- Validation: [sns-snap-phase0-validation.md](../../instruments/sns-snap-phase0-validation.md)
- Verified claims: wrap.reduce() entry point, lite mode default, pixel grouping (3 built-in
  schemes + user-defined; grouping choice affects resolution and counting statistics),
  workspace naming, calibration difcal+normcal tracks, diagnostic vs reduced output labelling,
  pixelmask and binmask (bin ranges in any unit: TOF/wavelength/Q/d-spacing)

**Phase 1 calibration foundation** (2026-04-29):
- Sources:
  - https://powder.ornl.gov/general_aspects/calibration/SNAP_calibration.html
  - https://powder.ornl.gov/general_aspects/calibration/pd_calib_principles.html (SNS)
  - https://powder.ornl.gov/general_aspects/calibration/snap/coreConcepts.html
  - https://powder.ornl.gov/general_aspects/calibration/snap/diffCalib/overview.html
  - https://powder.ornl.gov/general_aspects/calibration/snap/normCalib/overview.html
- Notes: VULCAN cross-correlation text used as concept-only precedent, not implementation policy.

## Intended outcomes

- Define a reproducible reduction sequence for a SNAP dataset.
- Identify where snapwrap, snapred, and Mantid each contribute.
- Clarify expected outputs and quality gates at each stage.

## Provenance map

- snapwrap (user interface — first):
  - Users call reduction and export workflows from snapwrap scripts, primarily by run number.
  - User-visible choices include grouping scheme, masking inputs, output formats, and whether
    to proceed when calibration information is incomplete.
- snapred (backend logic):
  - SNAPRed resolves state-dependent calibration context and executes calibration-aware workflows.
  - Missing calibration context may trigger approximation pathways that label outputs diagnostic.
- Mantid (framework; diagnostics and edge cases):
  - Provides the underlying algorithms for calibration, focusing, unit conversion, masking,
    and normalization operations orchestrated by SNAPRed.

## Core TOF calibration concepts (cross-instrument)

- TOF diffractometers calibrate the mapping between measured TOF and crystallographic d-spacing.
- Pixel-level alignment and grouped/focused calibration are distinct steps with different goals:
  - Pixel-level: align relative peak positions across detectors.
  - Group-level: place focused peaks at correct absolute d values.
- Calibration quality depends on calibrant quality, counting statistics, background conditions,
  and sensible grouping/masking decisions.
- Divergent implementation choices are expected across instruments; skill guidance should separate:
  - Consensus physics constraints.
  - Instrument-team conventions.
  - Open interpretations under active discussion.

## SNAP-specific conventions

- Lite mode is default and expected for routine reductions; native mode is expert/special-case.
- Grouping is fully general (3 built-in defaults plus custom schemes).
- Both mask types are first-class: pixelmask and binmask (bin ranges in TOF, wavelength, Q, or d-spacing).
- Output labels communicate calibration completeness:
  - reduced: full calibration available.
  - diagnostic: approximation path used.

## Recommended reduction sequence

1. Verify input runs and metadata consistency.
2. Resolve calibration context (difcal + normcal) for the instrument state.
3. Choose grouping and masking strategy based on the resolution/statistics tradeoff.
4. Identify specific sample environments and create derivative reduction inputs (e.g. specific bin or pixels masks and attenuation correction)
5. Run reduction path adapting the workflow as needed for specific sample environments and check output label (`reduced` vs `diagnostic`).
6. Perform background handling and normalization checks.
7. Convert/bin/export for downstream analysis (`gsa`, `xye`, `csv` as needed).
8. Capture diagnostics and provenance for reproducibility.

## Quality gates

- Required run metadata present and consistent.
- Calibration validity period covers acquisition time.
- Grouping/masking rationale recorded in analysis notes.
- Reduction logs include software versions and key parameters.
- Diagnostic metrics checked before publishing results.
- If output is `diagnostic`, intended usage is explicit (exploratory vs rerun after calibration).

## Context to collect before use

- Experiment mode and target output format.
- Sample environment context (assembly type such as `assembly.pe` or `assembly.dac`,
  plus nickname/model/comment when available via SEEMeta).
- Calibration files and their validity window.
- Whether cycle-strict calibration matching should remain enabled (`requireSameCycle`).
- Any known run exclusions or detector masking requirements.
