---
name: sns-snap-reduction-diagnostics
description: Diagnose quality issues in SNAP reduction outputs and propose targeted fixes. Use when reduced diffraction products show artifacts, unstable baselines, inconsistent normalization, or unexpected peak behavior.
version: 1
metadata:
  facility: SNS
  beamline: BL3
  instruments: [SNAP, SNS]
  software: [snapwrap, snapred, Mantid]
  data_phase: reduction
  techniques: [diffraction, powder-diffraction, time-of-flight, diagnostics]
  tags: [diagnostics, quality-control, troubleshooting, baseline, normalization]
---

# SNAP Reduction Diagnostics

Use this skill after an initial reduction run to identify failure modes and
prioritize corrective actions.

## Evidence tracking

**Phase 0 baseline** (2026-04-29):
- Source: https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html
- Validation: [sns-snap-phase0-validation.md](../../instruments/sns-snap-phase0-validation.md)
- Verified claims: workspace naming conventions, export formats, calibration state management,
  diagnostic vs reduced output labelling (diagnostic = calibration approximation used),
  pixelmask and binmask types

**Phase 1 calibration foundation** (2026-04-29):
- Sources:
  - https://powder.ornl.gov/general_aspects/calibration/snap/diffCalib/diffCal_assessment_output.html
  - https://powder.ornl.gov/general_aspects/calibration/snap/diffCalib/overview.html
  - https://powder.ornl.gov/general_aspects/calibration/snap/normCalib/overview.html
- Clarified user policy: diagnostic outputs are valid for exploratory work, or can trigger
  post-hoc calibration and rereduction.

## Provenance map

- snapwrap (user interface — first):
  - Surface warnings, status labels, and outputs that indicate calibration completeness.
  - Expose user decision points for export, rerun, or deeper diagnostics.
- snapred (backend logic):
  - Determines whether full calibration context exists and routes reduction accordingly.
  - Emits diagnostic pathways and can preserve intermediate workspaces in CIS mode.
- Mantid (framework; diagnostics and edge cases):
  - Produces diagnostic workspaces and metrics used to inspect calibration quality,
    masking effects, and fit behavior.

## Diagnostic workflow

1. Check reduction logs for warnings or fallback behavior.
2. Inspect baseline/background behavior and normalization stability.
3. Compare detector groups for consistency and outlier behavior.
4. Validate peak shape/position against expected references.
5. Determine output intent:
  - exploratory workflow acceptable with `diagnostic` label, or
  - final workflow requires calibration completion and rerun to `reduced`.
6. Attribute likely root causes and rerun with focused changes.

## Root-cause categories

- Calibration mismatch or stale calibration products.
- Geometry/masking choices suppressing valid signal.
- Background or normalization configuration drift.
- Run metadata mismatch across grouped reductions.

## High-value checks

- Confirm output label and expected usage (`diagnostic` vs `reduced`).
- Confirm continue-policy inputs used in the run (`continueNoDifcal`, `continueNoVan`, `noNorm`).
- Check whether cycle matching was strict (`requireSameCycle=True`) and whether an out-of-cycle calibration was rejected.
- Inspect number and geometry of masked pixels; large clusters often indicate upstream issues.
- Compare calibration metrics across groups and against previous state-compatible calibrations.
- If CIS mode is enabled, inspect retained intermediate workspaces for offset saturation,
  failed groups, or unstable fits.

## Resampling interpretation

- `sampleFactor=1` means no effective change in bin spacing.
- `sampleFactor<1` coarsens bins (downsampling).
- `sampleFactor>1` refines bins (upsampling) and is warned as lossy in current tooling.

## Output expectations

- A ranked list of likely causes.
- Recommended next run configuration changes.
- Minimal reproducible parameter set for rerun.
- Explicit decision: keep diagnostic result for exploration, or calibrate and rereduce for final output.
