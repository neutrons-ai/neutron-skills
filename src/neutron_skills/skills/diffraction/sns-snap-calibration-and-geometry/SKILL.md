---
name: sns-snap-calibration-and-geometry
description: Guide calibration and geometry corrections for SNAP reduction workflows. Use when selecting or validating instrument calibrations, detector masks, and geometry-sensitive parameters before reduction.
version: 2
review:
  status: pending
  reviewer: null
  reviewed_on: null
  basis: []
  notes: >
    v2: restructured to required skill anatomy (Overview / When to Use /
    Process / Rationalizations / Red Flags / Verification). Prior reviewed
    technical content preserved and reorganized. Awaiting instrument-scientist
    sign-off.
  approved_commit: null
  prior_review:
    status: human-reviewed
    reviewer: Malcolm Guthrie
    reviewed_on: 2026-04-30
    basis: [docs, code, corpus, instrument-science-review]
    notes: >
      Scope clarified as powder diffraction only. Defined difcal (DIFC-fitted TOF-to-d
      constants) and normcal (vanadium-based wavelength-response correction) as distinct
      in-reduction calibrations. Added post-reduction instrument-parameter calibration as a
      third layer required for Rietveld analysis; reduced data and instrument parameter files
      are treated as a coupled deliverable. Added SNAP masking-resolution coupling caveat.
      Corrected diagnostic label, continue-flag default behavior, failure signatures, and
      required-context fields.
    approved_commit: review/sns-snap-calibration-and-geometry-v1
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

## Overview

This skill covers calibration and geometry decisions for SNAP powder-diffraction
reduction workflows. Single-crystal SNAP diffraction uses different calibration
and reduction pathways and is **out of scope** here.

### Three distinct calibration products

SNAP reduction and analysis depend on three separate calibration products with
different scientific roles. Do not treat one as a substitute for another.

**1. Diffraction calibration (`difcal`)**
Defines the constants needed to map measured time-of-flight (TOF) to the correct
d-spacing scale. SNAP follows the GSAS-style TOF parameterization:

`TOF = DIFC·d + DIFA·d² + ZERO + DIFB/d`

In current SNAPRed workflows the fitted and applied term is `DIFC`. If this
calibration is absent or wrong, peaks will broaden or map to incorrect d-values.

**2. Normalization calibration (`normcal`)**
Corrects the wavelength-dependent detector response. In practice this is
measured with vanadium (a null-scatterer), so users often call it the "vanadium
correction." It primarily affects relative intensity and spectral shape, not the
TOF-to-d mapping itself.

**3. Post-reduction instrument-parameter calibration**
Built from reduced diffraction-calibration datasets (typically a NIST silicon
calibrant used for the `difcal`). Produces analysis-code-specific instrument
parameter files (GSAS-II, TOPAS, etc.) capturing spectrum-level profile and
resolution for the chosen pixel grouping. For Rietveld analysis, reduced data
and the matching instrument parameter files are a **coupled deliverable**.

> Note: the profile-model topic (back-to-back exponential convolved with a
> pseudo-Voigt, GSAS "TOF Profile 3" family — `sigma*`, `gamma*`, `alpha*`,
> `beta*`) is broadly applicable beyond SNAP and should eventually become a
> general-diffraction skill.

### SNAPRed calibration state and index

Each calibration is associated with an instrument state. SNAPRed maintains a
calibration index per state; each entry includes an `appliesTo` field defining
the cycle-matching policy. The **default is cycle-strict**
(`requireSameCycle=True`): a calibration can exist for a state but still be
invalid for the run if it is from a different cycle.

During reduction, SNAPRed checks the index for the current state and run number.
If required calibrations are missing it either proceeds with an approximation
(labelling output **`diagnostic`**) or aborts, depending on continue-flag
settings.

### Output quality labels

- **`reduced`**: Both `difcal` and `normcal` were available and applied.
- **`diagnostic`**: SNAPRed used approximations to replace missing calibration.
  Valid uses: exploratory decision-making only. Final outputs require `reduced`.

### Masking mechanisms

SNAP uses two distinct mask types:

- **pixelmask**: Excludes entire detector pixels (known bad detectors, failed
  calibration pixels). Calibration failures automatically generate a calibration
  mask; all applied pixel masks are written to the reduction record.
- **binmask**: Excludes data ranges within pixels, specifiable in any unit (TOF,
  wavelength, Q, or d-spacing). Useful for excluding a known artefact at a
  specific d-spacing while keeping the rest of the pixel's data.

**SNAP-specific caveat**: pixel masks change effective detector coverage and
therefore profile/resolution behavior in focused spectra. Aggressive or
run-specific masking may require instrument parameter file re-treatment.
Current SNAP workflows handle this via calculated resolution-function pathways
in snapwrap; GSAS-II output is the primary production pathway.

### Provenance

- **snapwrap** (user interface): triggers workflows, provides output labels and
  logs; state-aware defaults; lite mode is standard. Cycle-strict policy is
  currently enforced at the snapwrap level (logic migration to SNAPRed is
  underway).
- **snapred** (backend): maintains calibration records, applies calibration
  workflows, manages approximation pathways, labels outputs.
- **Mantid** (framework): cross-correlation offset estimation, DIFC application,
  focusing, masking, unit conversion, normalization.

### Evidence

- Phase 0 (2026-04-29): https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html
- Phase 1 (2026-04-29): SNS calibration principles and SNAP-specific calibration
  pages at powder.ornl.gov/general_aspects/calibration/

---

## When to Use

Use this skill when:

- Selecting or validating instrument calibrations before running SNAP reduction.
- A reduction returns `diagnostic` output when `reduced` was expected.
- Making grouping or masking decisions that may affect resolution or profile
  behavior.
- Preparing reduced SNAP data for Rietveld analysis (instrument parameter file
  coupling).
- Cross-cycle calibration use is being considered.

Do **not** use this skill for:

- Single-crystal SNAP diffraction (different calibration and reduction pathway).
- Post-reduction analysis steps beyond confirming the instrument parameter file
  exists (see the rietveld-checklist skill).

---

## Process

### Required context before starting

- Run numbers for the full calibration dataset (one `difcal` dataset, two
  `normcal` datasets per current workflow).
- Instrument state ID tied to those run numbers.
- Calibration file set and version history.
- Detector mask policy and known bad regions.
- Intended grouping scheme and science rationale.

---

1. **Identify instrument state and run numbers** — Confirm the instrument state
   ID for the run(s) to be reduced. Verify that the state ID is consistent
   across calibration and sample runs. Record the state ID and run number range
   in your reduction notes.

2. **Confirm diffraction calibration (`difcal`) availability** — Check the
   calibration index for an entry covering the current state and run number.
   Verify that `appliesTo` matches the cycle of the run (default: cycle-strict).
   If a calibration exists but is out-of-cycle and cross-cycle use is required,
   set `requireSameCycle=False` and document the decision explicitly.

   > **Continue-flag behavior**: if `continueNoDifcal=False` (default) and
   > `difcal` is absent, reduction **aborts** with no output workspaces.

   **[CHECKPOINT]**: A valid `difcal` entry exists in the calibration index for
   the target state and cycle, or a cross-cycle exception is explicitly
   documented.

3. **Confirm normalization calibration (`normcal`) availability** — Check that
   the vanadium-based normalization calibration exists for the target state.
   Apply the same cycle-matching check as for `difcal`.

   > **Continue-flag behavior**: if `continueNoVan=False` (default) and
   > `noNorm=False` and `normcal` is absent, reduction **aborts**.

   **[CHECKPOINT]**: A valid `normcal` entry exists for the target state and
   cycle, or a cross-cycle exception is explicitly documented.

4. **Choose and document the grouping scheme** — Select a built-in or custom
   pixel grouping. Record why the chosen grouping matches the science question
   (for example, column vs. bank vs. custom grouping for high-pressure vs.
   ambient measurements). Note that changing grouping after reduction may
   require reprocessing: the grouping choice is coupled to the instrument
   parameter file.

5. **Apply and document detector masks** — Apply pixelmasks and binmasks. For
   each mask, record the scientific rationale (bad detector, artefact exclusion,
   etc.). Note any calibration-failure-triggered masks from the calibration
   workflow. Assess whether the cumulative masked coverage changes the effective
   resolution enough to require run-specific instrument parameter treatment.

   **[CHECKPOINT]**: All masks are applied and every mask has a documented
   rationale. Masking-resolution coupling impact has been assessed.

6. **Run reduction and verify output quality label** — Execute the reduction
   workflow. Inspect the output workspace label:
   - `reduced` → both calibrations applied; output is suitable for analysis.
   - `diagnostic` → approximations were used; treat as exploratory only and
     return to steps 2–3 to resolve missing calibrations before final output.

   If `diagnostic` was unexpected, check: calibration index entries, `appliesTo`
   cycle policy, continue-flag settings, and instrument state ID consistency.

   **[CHECKPOINT]**: Output label is `reduced`. If `diagnostic`, the cause is
   identified and a remediation path (obtain missing calibration and rerun) is
   documented.

7. **Confirm instrument parameter file if Rietveld analysis is planned** —
   Verify that an instrument parameter file matching the chosen grouping scheme
   and pixel mask configuration exists. If it does not, generate it from the
   `difcal` silicon calibrant data before proceeding to Rietveld refinement.
   Reduced data and instrument parameter files are a coupled deliverable: do
   not analyse reduced data with an instrument parameter file built from a
   different grouping or masking configuration.

8. **Record all calibration metadata** — Document: instrument state ID, `difcal`
   and `normcal` version identifiers, grouping scheme used, masks applied (with
   rationale), cycle policy setting and any overrides, output quality label, and
   whether an instrument parameter file was generated or reused.

**Exit criteria**: Reduction output label is `reduced`. Both `difcal` and
`normcal` calibrations are confirmed valid for the target state and cycle.
Grouping and masking choices are documented. If Rietveld analysis is planned,
a matching instrument parameter file exists. All calibration metadata is
recorded.

---

## Rationalizations

| Excuse | Rebuttal |
|--------|----------|
| "The old calibration from a previous cycle is good enough." | The default cycle-strict policy exists because detector alignment and instrument response can shift between cycles. If cross-cycle use is justified, override explicitly with `requireSameCycle=False` and record why; do not silently accept stale calibrations. |
| "Diagnostic output is fine for my purposes." | Diagnostic output is appropriate for exploratory decisions only. Anything presented as a final reduced dataset must carry the `reduced` label, meaning both `difcal` and `normcal` were properly applied. |
| "I only care about peak positions, so I don't need normcal." | Even if d-spacing accuracy is the primary goal, a missing `normcal` produces wavelength-dependent intensity distortion that affects background shape, overlapping-peak separation, and scale factors — all of which matter for quantitative analysis. |
| "Masking more bad pixels makes the data cleaner." | Masking changes the effective detector coverage and therefore the profile/resolution function of focused spectra. Run-specific masking may invalidate the existing instrument parameter file and require new post-reduction calibration. |
| "One instrument parameter file covers all grouping schemes." | Instrument parameter files are grouping- and mask-specific. Using a file built for a different grouping or masking configuration introduces systematic profile errors in Rietveld refinement. |

---

## Red Flags

- **Output label is `diagnostic` when `reduced` was expected** — check
  calibration index entries, cycle-matching policy, and state ID consistency.
- **Peak positions do not match known calibrant d-spacings** — likely `difcal`
  mismatch or wrong state/run-number mapping.
- **Artificial peak broadening or blurring after focusing** — likely `difcal`
  mismatch across contributing pixels within a group.
- **Wavelength-dependent intensity distortion or poor spectral normalization** —
  likely missing or mismatched `normcal`.
- **Inconsistent d-spacings or intensities across banks or detector groups** —
  check geometry calibration and pixel grouping scheme.
- **Using `normcal` as a substitute for `difcal` or vice versa** — these are
  distinct calibrations with different scientific roles; neither replaces the
  other.
- **Rietveld refinement with an instrument parameter file built from a different
  grouping or masking configuration** — systematic profile errors will result.

---

## Verification

- [ ] Instrument state ID is confirmed and consistent across calibration and
      sample runs.
- [ ] A valid `difcal` entry exists in the calibration index for the target
      state and cycle; cycle policy recorded.
- [ ] A valid `normcal` entry exists for the target state and cycle; cycle
      policy recorded.
- [ ] If cross-cycle calibration is used, `requireSameCycle=False` is set and
      the decision is documented.
- [ ] Grouping scheme is chosen and the scientific rationale is recorded.
- [ ] All detector masks (pixelmask and binmask) are applied and every mask has
      a documented rationale.
- [ ] Masking-resolution coupling impact has been assessed; run-specific
      instrument parameter treatment flagged if needed.
- [ ] Reduction output label is `reduced` (not `diagnostic`).
- [ ] If `diagnostic` was returned, the cause is identified and a remediation
      path is recorded.
- [ ] Calibration version identifiers (`difcal` and `normcal`) are recorded in
      reduction logs.
- [ ] If Rietveld analysis is planned, a matching instrument parameter file
      (correct grouping and mask configuration) is confirmed or generated.