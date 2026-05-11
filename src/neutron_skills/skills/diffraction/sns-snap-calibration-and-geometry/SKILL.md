---
name: sns-snap-calibration-and-geometry
description: Guide calibration and geometry corrections for SNAP reduction workflows. Use when selecting or validating instrument calibrations, detector masks, and geometry-sensitive parameters before reduction.
version: 2
review:
  status: human-reviewed
  reviewer: Malcolm Guthrie
  reviewed_on: 2026-05-05
  basis: [docs, code, instrument-science-review]
  notes: >
    v2: expanded scope to cover 4 explicit workflows (difcal generation,
    normcal generation, reduction-time calibration validation/use,
    instrument-parameter file production/validation). Process section
    refactored into labelled branches A–D with branch-specific checkpoints
    and conditional exit criteria and verification checklist. Normalized
    US English spelling (artifact).
  approved_commit: review/sns-snap-calibration-and-geometry-v2
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
  instruments: [SNAP]
  software: [snapwrap, snapred, Mantid]
  data_phase: reduction
  techniques: [diffraction, powder-diffraction, time-of-flight, calibration]
  tags: [calibration, geometry, detector, masking, alignment]
---

# SNAP Calibration and Geometry

## Overview

This skill covers calibration and geometry decisions for SNAP powder-diffraction
workflows. Single-crystal SNAP diffraction uses different calibration and
reduction pathways and is **out of scope** here.

This skill is intentionally broader than reduction-only checks. It covers both
calibration generation and calibration use/validation.

### Supported workflows

1. `difcal` generation (SNAPRed calibration workflow).
2. `normcal` generation (SNAPRed calibration workflow).
3. Reduction-time calibration validation/use (SNAPWrap + SNAPRed).
4. Instrument-parameter file production/validation for downstream Rietveld work.

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
Corrects the wavelength-dependent instrument response. In practice this is
measured with vanadium (a null-scatterer), so users often call it the "vanadium
correction." It affects relative intensity and spectral shape, not the
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
calibration index per state; each entry includes an `appliesTo` field defining scope of the calibration in terms of run number. In addition, a cycle-matching policy is applied (n.b. this is currently implemented in SNAPWrap, but will be migrated to SNAPRed). The **default is cycle-strict**
(`requireSameCycle=True`): a calibration can exist for a state but still be
invalid for the run if it is from a different cycle or out of the `appliesTo` scope.

During reduction, SNAPRed checks the index for the current state and run number.
If required valid calibrations are missing it either proceeds via user-specified alternate paths using suitable approximations
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
  wavelength, Q, or d-spacing). Useful for excluding a known artifact at a
  specific d-spacing while keeping the rest of the pixel's data.

**SNAP-specific caveat**: either mask type can change effective detector coverage and
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

- Generating or validating a `difcal` calibration in SNAPRed.
- Generating or validating a `normcal` calibration in SNAPRed.
- Generating or validating an instrument parameter file for Rietveld analysis.
- Selecting or validating instrument calibrations before running SNAP reduction.
- Making grouping or masking decisions that may affect resolution or profile
  behavior.
- Preparing reduced SNAP data for Rietveld analysis (instrument parameter file
  coupling).
- Cross-cycle calibration use is being considered.

Do **not** use this skill for:

- Single-crystal SNAP diffraction (different calibration and reduction pathway).
- Post-reduction analysis steps beyond confirming the instrument parameter file
  exists (see the rietveld-refinement-workflow skill).

---

## Process

### Required context before starting

- Target workflow:
  - `difcal` generation/validation,
  - `normcal` generation/validation,
  - reduction-time calibration validation/use, or
  - instrument-parameter file production/validation.
- Run numbers for the full calibration dataset (one `difcal` dataset, two
  `normcal` datasets per current workflow).
- Instrument state ID tied to those run numbers.
- Calibration file set and version history.
- Detector mask policy and known bad regions.
- Intended grouping scheme and science rationale.

---

1. **Select the workflow and define success criteria** — Choose exactly one
   primary workflow for this execution and record what success means:
   - A: `difcal` generation/validation
   - B: `normcal` generation/validation
   - C: reduction-time calibration validation/use
   - D: instrument-parameter file production/validation

2. **Identify instrument state and run scope** — Confirm instrument state ID,
   run-number scope, and calibration version scope (`appliesTo`). Record
   cycle-policy intent (`requireSameCycle` behavior) before execution.

3. **Execute the selected workflow branch**

   **A) `difcal` generation/validation (SNAPRed)**
   - Run SNAPRed diffraction-calibration workflow for the target state/run set.
   - Verify product creation and calibration-index insertion.
   - Validate product quality against known calibrant peak positions/fit
     behavior.
   - Quantify number of pixels that failed calibration and are therefore masked in reduction. Compare with known bad pixels and historical failure rates.
   - If product is invalid, record failure signature and rerun plan.

   **[CHECKPOINT A]**: `difcal` exists, is indexed for intended applicability,
   and passes basic product-quality checks.

   **B) `normcal` generation/validation (SNAPRed)**
   - Run SNAPRed normalization-calibration workflow for the target state/run
     set.
   - Verify product creation and calibration-index insertion.
   - Validate wavelength-response behavior and normalization stability.
   - If product is invalid, record failure signature and rerun plan.

   **[CHECKPOINT B]**: `normcal` exists, is indexed for intended applicability,
   and passes basic product-quality checks.

   **C) Reduction-time calibration validation/use (SNAPWrap + SNAPRed)**
   - Confirm `difcal` and `normcal` availability for state/run/cycle policy.
   - Choose grouping and masking strategy; document rationale for each choice.
   - Run reduction and verify output label:
     - `reduced` -> both calibrations applied.
     - `diagnostic` -> approximation pathway used; treat as exploratory only.
   - If `diagnostic` was unexpected, investigate index entries, policy
     settings, continue flags, and state ID consistency.

   > **Continue-flag behavior**: if `continueNoDifcal=False` (default) and
   > `difcal` is absent, reduction aborts; if `continueNoVan=False` and
   > `noNorm=False` and `normcal` is absent, reduction aborts.

   **[CHECKPOINT C]**: Output state is understood and documented (`reduced`,
   intentional `diagnostic`, or expected abort with missing calibration and
   continue flags unset).

   **D) Instrument-parameter file production/validation**
   - Confirm the file matches the chosen grouping and mask configuration.
   - If missing, generate from appropriate `difcal` silicon calibrant data.
   - Validate profile/resolution behavior for intended analysis code (GSAS-II,
     TOPAS, etc.).
   - Record linkage between reduced dataset and instrument-parameter file.

   **[CHECKPOINT D]**: Matching instrument-parameter file exists (or is
   generated) and is validated for intended grouping/masking/analysis code.

4. **Record workflow provenance and decisions** — Document: workflow selected,
   state ID, run scope, calibration version identifiers, cycle-policy settings
   and overrides, grouping/masking choices (if applicable), output label or
   abort state (if applicable), and instrument-parameter linkage (if
   applicable).

**Exit criteria**: The selected workflow's checkpoint is satisfied, and
workflow-specific provenance is fully recorded. For reduction-time use (workflow
C), output state is explicitly documented as `reduced`, intentional
`diagnostic`, or expected abort. For instrument-parameter workflow (D), matching
file linkage to data/grouping/masking is explicit.

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

- [ ] Workflow type is explicitly recorded (A `difcal`, B `normcal`,
  C reduction-time use, or D instrument-parameter file).
- [ ] Instrument state ID and run scope are confirmed and recorded.
- [ ] Cycle-policy decision is recorded (`requireSameCycle` behavior and any
  overrides).
- [ ] If workflow A (`difcal`): generated product exists, is indexed correctly,
  and passes basic calibrant-position/fit checks.
- [ ] If workflow B (`normcal`): generated product exists, is indexed correctly,
  and passes expected wavelength-response checks.
- [ ] If workflow C (reduction-time use): valid `difcal` and `normcal`
  availability is confirmed for state/run/cycle policy.
- [ ] If workflow C: grouping and masking choices are documented with rationale;
  masking-resolution coupling impact is assessed.
- [ ] If workflow C: output state is documented as `reduced`, intentional
  `diagnostic`, or expected abort with missing calibration and continue
  flags unset.
- [ ] If workflow D (instrument-parameter file): matching file for intended
  grouping/mask/analysis code is confirmed or generated.
- [ ] Calibration/version provenance is recorded for the selected workflow.