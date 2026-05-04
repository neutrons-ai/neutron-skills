---
name: sns-snap-reduction-diagnostics
description: >
  Diagnose quality issues in SNAP reduction outputs and propose targeted fixes.
  Use when reduced diffraction products show artifacts, unstable baselines,
  inconsistent normalization, or unexpected peak behavior.
version: 2
review:
  status: pending
  reviewer: null
  reviewed_on: null
  basis: []
  notes: >
    v2: restructured to required skill anatomy (Overview / When to Use /
    Process / Rationalizations / Red Flags / Verification). All prior content
    preserved; no domain changes. Awaiting instrument-scientist sign-off.
  approved_commit: null
  prior_review:
    status: human-reviewed
    reviewer: Malcolm Guthrie
    reviewed_on: 2026-04-30
    basis: [docs, code, instrument-science-review]
    notes: >
      Clarified root-cause coverage to include sample-environment-specific corrections
      and added a high-value masking-failure check for large background artifacts.
    approved_commit: review/sns-snap-reduction-diagnostics-v1
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

This skill guides an agent through a structured inspection of SNAP reduction
outputs to identify failure modes, attribute root causes, and produce a
targeted rerun plan. It is invoked after an initial reduction run completes.

Related skills:
- [sns-snap-reduction-workflow-overview](../sns-snap-reduction-workflow-overview/SKILL.md) — upstream reduction sequence
- [sns-snap-calibration-and-geometry](../sns-snap-calibration-and-geometry/SKILL.md) — calibration state controls
- [sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md) — environment-specific artifact sources

---

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

---

## Overview

This skill produces: (1) a ranked list of likely root causes for the observed
quality issue, (2) recommended parameter changes for the next run, and (3) an
explicit decision on whether to use the current output as exploratory results
or to recalibrate and rereduce for final output.

**Software provenance:**
- **snapwrap** (user interface — first): surfaces warnings, status labels, and
  outputs that indicate calibration completeness; exposes decision points for
  export, rerun, or deeper diagnostics.
- **snapred** (backend): determines whether full calibration context exists and
  routes reduction accordingly; emits diagnostic pathways and can preserve
  intermediate workspaces in CIS mode.
- **Mantid** (framework): produces diagnostic workspaces and metrics used to
  inspect calibration quality, masking effects, and fit behavior.

**Root-cause categories to consider:**
- Calibration mismatch or stale calibration products.
- Sample-environment-specific corrections not represented in calibration or
  reduction assumptions.
- Geometry or masking choices suppressing valid signal.
- Background or normalization configuration drift.
- Run metadata mismatch across grouped reductions.

---

## When to Use

- Use when reduced diffraction products show artifacts, unstable baselines,
  inconsistent normalization, or unexpected peak behavior.
- Use when output workspaces are labelled `diagnostic_` and the cause is
  unknown.
- Use when peak positions differ unexpectedly between detector groups.
- Use when large background artifacts appear in the reduced output.
- Do NOT use as a substitute for the upstream reduction workflow — invoke
  [sns-snap-reduction-workflow-overview](../sns-snap-reduction-workflow-overview/SKILL.md)
  first if a full reduction has not yet been attempted.

---

## Process

Collect this context before starting:
- The run number(s) that produced the suspect output.
- The output workspace name(s), including the full prefix
  (`reduced_` vs `diagnostic_`).
- The continue-policy flags used: `continueNoDifcal`, `continueNoVan`, `noNorm`.
- Whether cycle-strict matching was active (`requireSameCycle=True`).
- Whether CIS mode was enabled.
- The sample environment type (PE, DAC, cylinder, or none).

---

1. **Check the output label and continue-policy inputs** — Confirm whether the
   workspace prefix is `reduced_` or `diagnostic_`. Retrieve the continue flags
   used in the run. A `diagnostic_` label with no intentional continue flag set
   means the calibration lookup failed unexpectedly; treat this as a calibration
   issue until proven otherwise.

   **[CHECKPOINT]**: The output label is understood and its cause is attributed
   to either (a) an intentional continue flag or (b) a calibration lookup
   failure requiring investigation.

2. **Inspect reduction logs for warnings** — Look for `ContinueWarning`,
   `MISSING_DIFFRACTION_CALIBRATION`, `MISSING_NORMALIZATION`, or
   `ALTERNATE_DIFFRACTION_CALIBRATION` flags in the reduction record. Note
   every flag; each represents a deviation from full-calibration reduction.

3. **Check calibration cycle matching** — Confirm whether
   `requireSameCycle=True` was active and whether a valid same-cycle calibration
   existed for the run's instrument state. An out-of-cycle calibration that was
   silently accepted (or rejected) is a common root cause of subtle peak-position
   errors.

4. **Inspect masking coverage** — Examine the number and geometry of masked
   pixels. Large contiguous masked regions, unexpected zero-count areas in the
   detector image, or large background artifacts in the reduced output indicate
   a mask that is missing, shifted, or overly aggressive. For high-pressure
   devices, cross-check against the expected device-specific mask.

5. **Inspect baseline and normalization stability across groups** — Compare
   reduced spectra from each pixel group (all, bank, column). Systematic
   offsets between groups, wavelength-dependent intensity drift, or a group
   that is an outlier relative to others points to a calibration issue
   (`difcal` or `normcal`) or a grouping/masking mismatch. Although be aware that sample-specific corrections may also produce group-specific effects not due to calibration.

6. **Validate peak shape and position** — Compare peak positions and widths
   against expected references (a known standard or a prior run in the same
   state). Broadened or shifted peaks across all groups may indicate a
   diffraction calibration (`difcal`) mismatch, but for high-pressure samples
   can equally reflect pressure-driven structural changes (lattice strain,
   phase transitions) in the sample itself. Broadening confined to one group
   suggests a per-group calibration or masking issue rather than a sample
   effect. See [sns-snap-high-pressure-data-interpretation](../sns-snap-high-pressure-data-interpretation/SKILL.md)
   for guidance on distinguishing sample-driven from instrument-driven peak
   behaviour.

7. **If CIS mode was active, inspect intermediate workspaces** — Check retained
   intermediate workspaces for offset saturation, failed groups, or unstable
   fits. These provide the most direct evidence of where the reduction pipeline
   deviated.

   **[CHECKPOINT]**: A ranked list of root causes is established. Each cause is
   tied to at least one observable piece of evidence from steps 1–7.

8. **Propose and record a rerun plan** — For each attributed root cause, specify
   the minimum parameter change needed (e.g., obtain missing calibration,
   correct mask, relax cycle policy with documented justification). Record the
   minimal reproducible parameter set.

9. **Make an explicit output-intent decision** — State clearly: keep the current
   output for exploratory use only, OR recalibrate/remask and rereduce before
   treating results as final. This decision must be recorded in analysis notes.

**Exit criteria**: A ranked root-cause list, a rerun parameter set, and an
explicit output-intent decision are all documented.

---

## Rationalizations

| Rationalization | Why it is wrong |
|-----------------|-----------------|
| "The output is `diagnostic_` but the peaks look fine, so it's good enough." | `diagnostic_` means an approximation pathway was used. Visual inspection of peaks does not reveal subtle TOF-to-d mapping errors or normalization drift. The label is ground truth about data provenance, not a visual quality score. |
| "I checked one group — they all look the same." | Cross-group comparison at step 5 is the diagnostic, not single-group inspection. Normalization and calibration failures often manifest as inter-group offsets invisible within a single spectrum. |
| "The masking looks fine — there are no obvious gaps." | Mask failures can produce large background artifacts rather than obvious gaps. Step 4 requires checking both the detector image and the reduced output for artifact signatures, not just visual coverage. |
| "CIS mode is off so there's nothing to inspect." | Steps 1–6 do not require CIS mode. CIS mode provides additional evidence at step 7; its absence does not justify skipping the earlier checks. |
| "I'll record the root cause after the rerun." | The decision at step 9 and the evidence at steps 1–7 must be recorded before the rerun. After a successful rerun, the diagnostic context is routinely lost. |

---

## Red Flags

- Output label is `diagnostic_` with no intentional continue flag set →
  calibration lookup failed unexpectedly. Revisit steps 1–3.
- `MISSING_DIFFRACTION_CALIBRATION` or `ALTERNATE_DIFFRACTION_CALIBRATION`
  flag in the reduction record → peak positions and d-spacing values are
  unreliable. Do not use for final results without recalibration.
- Large contiguous zero-count region in the detector image not explained by
  the expected device mask → pixel mask is missing, shifted, or
  wrong for the current device. Revisit step 4 and invoke
  [sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md).
- Systematic peak-position offset between groups → `difcal` mismatch;
  revisit step 3 and invoke [sns-snap-calibration-and-geometry](../sns-snap-calibration-and-geometry/SKILL.md).
- Wavelength-dependent intensity drift in one or more groups → `normcal`
  issue; revisit step 5 and calibration state.
- `sampleFactor > 1` used → upsampling is lossy in current tooling and is
  warned. Note this in the root-cause list; do not use upsampled output for
  final intensity-dependent analysis.

---

## Resampling reference

- `sampleFactor=1`: no effective change in bin spacing.
- `sampleFactor<1`: coarsens bins (downsampling).
- `sampleFactor>1`: refines bins (upsampling) — warned as lossy in current
  tooling; rebinning parameters are spectrum-specific within a pixel grouping
  scheme.

---

## Verification

Before marking this skill complete:

- [ ] Output label (`reduced_` or `diagnostic_`) is confirmed and its cause
      is attributed.
- [ ] All reduction log flags (`ContinueWarning`, missing-calibration flags)
      are listed and explained.
- [ ] Calibration cycle-matching policy and outcome are confirmed.
- [ ] Masking coverage checked in both the detector image and the reduced
      output; any artifact-producing failures are identified.
- [ ] Cross-group normalization and peak-position comparison completed.
- [ ] Ranked root-cause list recorded in analysis notes.
- [ ] Rerun parameter set (minimum reproducible changes) recorded.
- [ ] Explicit output-intent decision recorded: exploratory use only, or
      recalibrate/rereduce before final results.
