---
name: sns-snap-calibration-and-geometry
description: Guide calibration and geometry corrections for SNAP reduction workflows. Use when selecting or validating instrument calibrations, detector masks, and geometry-sensitive parameters before reduction.
version: 1
review:
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

Use this skill when calibration and geometry choices are likely to dominate
reduction quality.

This skill is for SNAP powder-diffraction reduction workflows. Single-crystal
diffraction uses different calibration and reduction pathways and is out of
scope here.

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

## Distinct calibration products across reduction and analysis

SNAP reduction depends on two different calibration products. In SNAPRed usage,
these are often shortened to `difcal` and `normcal`. Those abbreviations are
project-local slang and should be defined explicitly when used.

- **Diffraction calibration (`difcal`)**:
  - Defines the constants needed to convert measured time-of-flight into the
    correct d-spacing scale.
  - SNAP follows the GSAS-style TOF parameterization:
    `TOF = DIFC*d + DIFA*d^2 + ZERO + DIFB/d`.
  - In current SNAPRed reduction workflows, the fitted and applied term is
    `DIFC`.
  - This is the calibration that ensures correct conversion from time-of-flight to d-spacing (or other derived units).
  - If this calibration is wrong or missing, peaks will broaden or map to the
    wrong d values.
- **Normalization calibration (`normcal`)**:
  - Corrects the wavelength-dependent response of the instrument.
  - In practice this is commonly derived from a vanadium measurement (used because this is a null-scatterer), so users
    often refer to it as a vanadium correction.
  - This calibration primarily affects relative intensity and spectral response,
    not the TOF-to-d conversion itself.

These are separate calibrations with different scientific roles during
reduction. They are produced by different calibration workflows and generate
different outputs. Do not treat `normcal` as a substitute for `difcal`, and do
not treat `difcal` as a substitute for vanadium-based normalization.

The output of either calibration workflow is a versioned folder containing specific calibration products. Creation of a versioned folder is accompanied by an associated entry in a calibration index. Calibrations properties of specific instrument states and each state has its own calibration index. During reduction, SNAPRed checks the calibration index for the current state and run number to determine whether required calibrations are available, and if not, whether to proceed with an approximation (diagnostic output) or abort. Each calibration index entry also includes an `appliesTo` field that defines the state-matching policy for that calibration; by default this is cycle-strict, meaning the calibration must be from the same cycle as the run being reduced.

There is also a third, distinct calibration layer used after reduction during
powder-pattern analysis:

- **Instrument-parameter calibration (post-reduction analysis calibration)**:
  - Built from reduced diffraction calibration datasets (typically derived from a NIST silicon calibrant used for the `difcal`).
  - Produces analysis-code-specific instrument parameter files (for example,
    GSAS-II and TOPAS use different formats).
  - Captures spectrum-level profile and resolution behavior for the chosen pixel
    grouping and can include re-refinement of a subset of diffractometer
    constants under the analysis profile model.

For powder Rietveld analysis, reduced data and the matching instrument
parameter files should be treated as a coupled deliverable.

## Post-reduction instrument-parameter calibration details

- This calibration is organized by pixel-group output spectrum (for example,
  column or bank groupings).
- A profile model is determined for each output spectrum in the grouping.
- In practical SNAP workflows, this also refines profile-sensitive position
  terms under the analysis profile model, because apparent peak position and
  profile are coupled in TOF refinement.

The commonly used TOF profile model is a back-to-back exponential convolved
with a pseudo-Voigt (GSAS "TOF Profile 3" family), which includes Gaussian
(`sigma*`), Lorentzian (`gamma*`), and leading/trailing exponential
(`alpha*`/`beta*`) parameter families.

Note for skill architecture: this profile-model topic is broadly applicable to
powder diffraction beyond SNAP and should eventually be maintained as a reusable
general-diffraction skill, while this skill remains SNAP-implementation-focused.

## Calibration checklist

1. Confirm both required calibration artifacts for the run interval:
   - diffraction calibration (`difcal`) for TOF-to-d conversion,
   - normalization calibration (`normcal`) for wavelength-response correction.
2. Verify geometry assumptions against current instrument configuration.
3. Choose grouping scheme (built-in or custom) and record why it matches the science question.
4. Apply detector masks and document rationale.
5. Record all calibration identifiers and mode choices in reduction logs.

## Masking types

SNAP reduction uses two distinct masking mechanisms:

- **pixelmask**: Excludes entire detector pixels. Used for known bad detectors or detector regions.
- **binmask**: Excludes ranges of data within pixels. Ranges can be specified in any unit — TOF (µs), wavelength (Å), Q (Å⁻¹), or d-spacing (Å). This lets you exclude, for example, a specific d-spacing range affected by a known artefact while keeping the rest of the pixel's data.

Both mask types affect the effective detector coverage and therefore the resolution and counting statistics of the final output. Document the scientific rationale for each mask applied.

Note: pixels that fail diffraction calibration (for example, due to low counts or poor fit quality) trigger the creation of a calibration mask and will be automatically masked in the reduction. This is is in addition to user-applied pixelmasks and binmasks and also affects the effective detector coverage and resolution. All total of any applied pixel masks are tracked in the reduction record when applied during any run and that mask is written to disk. 

For SNAP specifically, masking also changes effective profile/resolution
behavior in focused spectra. Pixel masks can require run-specific instrument
parameter treatment. Bin masking can introduce additional structure in the
effective resolution function. Current SNAP workflows handle this with
calculated resolution-function pathways in snapwrap; GSAS-II output support is
currently the primary production pathway.

## Output quality labels

- **`reduced`**: A full set of valid calibrations were available and applied, meaning both the
  diffraction calibration (`difcal`) and the normalization calibration
  (`normcal`).
- **`diagnostic`**: SNAPRed used approximations to replace the missing calibration information. Two valid user responses exist:
  1. Use diagnostic output for exploratory decision-making.
  2. Complete calibration later, then rerun to generate final reduced output.

If either `difcal` or `normcal` is absent, reduction will not proceed unless a manual override is applied. In such cases, outputs are diagnostic by
definition.


## Calibration validity and cycle policy

- Default behavior is cycle-strict: `requireSameCycle=True`. This is currently enforced at the SNAPWrap level but work is underway to move this logic into SNAPRed for more robust enforcement and better provenance tracking.
- In this default mode, a calibration can exist for the state but still be invalid for the run if it is out-of-cycle.
- If cross-cycle use is intentionally required, relax this explicitly (`requireSameCycle=False`) and document why.

## Continue-flag decision points

- `continueNoDifcal=False` and missing diffraction calibration (`difcal`) -> reduction aborts (no output workspaces).
- `continueNoVan=False` and `noNorm=False` with missing normalization calibration (`normcal`, usually vanadium-based) -> reduction aborts.
- Continue flags are manual overrides; by default reduction does not proceed
  when required calibrations are missing.
- Enabling continue pathways permits diagnostic outputs with explicit warning flags.
- Treat diagnostic outputs as exploratory unless/until full calibration is completed and rerun.

## CIS mode and intermediate workspaces

- "Dirty" workspaces are intermediate products retained for inspection.
- In normal operation these are cleaned/discarded.
- In CIS mode they can be preserved to inspect offsets, masks, and pre/post calibration workspaces.

## Common failure signatures

- Peak position errors and artificial broadening/blurring after focusing —
  likely diffraction calibration (`difcal`) mismatch across contributing pixels.
- Wavelength-dependent intensity distortion or poor normalization behavior — likely normalization calibration (`normcal`) issue.
- Inconsistent results across banks or detector groups — check geometry calibration and pixel grouping scheme.
- Overly aggressive masking reducing useful signal.
- Diagnostic output when continue flags are enabled — expected behavior; verify
  calibration availability, continue-policy settings, and instrument state ID.

## Required context before execution

- Run numbers for the full calibration dataset set (one diffraction-calibration
  dataset, two normalization-calibration datasets, per current workflow).
- Instrument state identification tied to run numbers and calibration-index
  applicability (`appliesTo`).
- Calibration file set and version history.
- Detector mask policy and known bad regions.
- Rationale for grouping and masking choices, ideally captured in analysis notes.