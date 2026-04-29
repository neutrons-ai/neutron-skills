---
name: sns-snap-calibration-and-geometry
description: Guide calibration and geometry corrections for SNAP reduction workflows. Use when selecting or validating instrument calibrations, detector masks, and geometry-sensitive parameters before reduction.
version: 1
metadata:
  facility: SNS
  beamline: BL3
  instruments: [SNAP, SNS]
  software: [snapwrap, snapred, Mantid]
  data_phase: reduction
  techniques: [diffraction, powder-diffraction, time-of-flight, calibration]
  tags: [calibration, geometry, detector, masking, alignment]
---

# SNAP Calibration and Geometry

Use this skill when calibration and geometry choices are likely to dominate
reduction quality.

## Evidence tracking

**Phase 0 baseline** (2026-04-29):
- Source: https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html
- Validation: [sns-snap-phase0-validation.md](../../instruments/sns-snap-phase0-validation.md)
- Known drift: Export format semantics, calibration failure modes, cycle validation

**Phase 1 calibration foundation** (2026-04-29):
- Sources:
  - https://powder.ornl.gov/general_aspects/calibration/SNAP_calibration.html
  - https://powder.ornl.gov/general_aspects/calibration/pd_calib_principles.html (SNS)
  - https://powder.ornl.gov/general_aspects/calibration/snap/coreConcepts.html
  - https://powder.ornl.gov/general_aspects/calibration/snap/binning.html
  - https://powder.ornl.gov/general_aspects/calibration/snap/diffCalib/overview.html
  - https://powder.ornl.gov/general_aspects/calibration/snap/diffCalib/diffCal_assessment_output.html
  - https://powder.ornl.gov/general_aspects/calibration/snap/normCalib/overview.html
- Clarified in Phase 1: export mappings, diagnostic vs reduced behavior, dirty/CIS workspace meaning.

## Provenance map

- snapwrap (user interface — first):
  - Users trigger reduction workflows and receive user-facing status through output labels and logs.
  - Most users rely on state-aware defaults; lite mode remains standard.
- snapred (backend logic):
  - Maintains state-coupled calibration records and applies calibration workflows.
  - Uses approximation pathways when needed and labels outputs diagnostic accordingly.
  - CIS mode can retain intermediate workspaces for deeper inspection.
- Mantid (framework; diagnostics and edge cases):
  - Algorithms for cross-correlation offset estimation, applying diffractometer constants,
    focusing, masking, unit conversion, and normalization corrections.

## Core TOF calibration model (cross-instrument)

Use this model for all SNS TOF powder instruments unless instrument docs override:

- Consensus:
  - Calibration establishes reliable TOF-to-d mapping for reduction.
  - Relative detector alignment (pixel calibration) and absolute focused calibration (group calibration)
    are different operations and should be validated separately.
  - Calibration quality is constrained by calibrant quality, counting statistics, and background.
- Instrument-team conventions:
  - Specific calibrants, grouping defaults, convergence thresholds, and automation details differ by instrument.
  - Diagnostic metrics and acceptance thresholds vary across teams.
- Open interpretation:
  - Optimal masking and grouping strategy for a specific science case may differ between experts.
  - Treatment of imperfect calibrations may be intentionally conservative or permissive depending on goals.

## Calibration checklist

1. Confirm detector/instrument calibration artifacts (difcal and normcal) for the run interval.
2. Verify geometry assumptions against current instrument configuration.
3. Choose grouping scheme (built-in or custom) and record why it matches the science question.
4. Apply detector masks and document rationale.
5. Record all calibration identifiers and mode choices in reduction logs.

## Masking types

SNAP reduction uses two distinct masking mechanisms:

- **pixelmask**: Excludes entire detector pixels. Used for known bad detectors or detector regions.
- **binmask**: Excludes ranges of data within pixels. Ranges can be specified in any unit — TOF (µs), wavelength (Å), Q (Å⁻¹), or d-spacing (Å). This lets you exclude, for example, a specific d-spacing range affected by a known artefact while keeping the rest of the pixel's data.

Both mask types affect the effective detector coverage and therefore the resolution and counting statistics of the final output. Document the scientific rationale for each mask applied.

## Output quality labels

- **`reduced`**: Full calibration (difcal and normcal) was available and applied.
- **`diagnostic`**: SNAPRed used an approximation because required calibration data were missing. Two valid user responses exist:
  1. Use diagnostic output for exploratory decision-making.
  2. Complete calibration later, then rerun to generate final reduced output.

If diagnostic output is unexpected, check calibration availability and state matching first.

## Calibration validity and cycle policy

- Default behavior is cycle-strict: `requireSameCycle=True`.
- In this default mode, a calibration can exist for the state but still be invalid for the run if it is out-of-cycle.
- If cross-cycle use is intentionally required, relax this explicitly (`requireSameCycle=False`) and document why.

## Continue-flag decision points

- `continueNoDifcal=False` and missing difcal -> reduction aborts (no output workspaces).
- `continueNoVan=False` and `noNorm=False` with missing normcal -> reduction aborts.
- Enabling continue pathways permits diagnostic outputs with explicit warning flags.
- Treat diagnostic outputs as exploratory unless/until full calibration is completed and rerun.

## CIS mode and intermediate workspaces

- "Dirty" workspaces are intermediate products retained for inspection.
- In normal operation these are cleaned/discarded.
- In CIS mode they can be preserved to inspect offsets, masks, and pre/post calibration workspaces.

## Common failure signatures

- Peak position drift after reduction — likely difcal mismatch.
- Inconsistent results across banks or detector groups — check geometry calibration and pixel grouping scheme.
- Overly aggressive masking reducing useful signal.
- Unexpected `diagnostic` output — verify calibration availability, continue-policy settings, and instrument state ID.

## Required context before execution

- Run range and acquisition timestamps.
- SEEMeta assembly context when available (at minimum assembly type such as
  `assembly.pe` or `assembly.dac`, plus nickname/model/comment).
- Calibration file set and version history.
- Detector mask policy and known bad regions.
- Whether cycle-strict calibration matching should remain enabled.
- If resampling is planned: target intent for `sampleFactor` (coarser vs finer bins).
