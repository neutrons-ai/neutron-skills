---
name: sns-snap-reduction-workflow-overview
description: >
  Guide an agent through the end-to-end SNAP powder-diffraction reduction
  sequence and its key decision points. Use when deciding the sequence of
  preprocessing, calibration, normalization, and output products for SNAP
  diffraction data.
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

This skill frames the complete SNAP powder-diffraction reduction sequence,
identifies which software layer handles each step, and defines the quality
gates that must pass before outputs are used downstream. It is the entry
point for all SNAP reduction work; subordinate skills handle calibration
detail, diagnostics, and sample-environment special cases.

Related skills:
- [sns-snap-calibration-and-geometry](../sns-snap-calibration-and-geometry/SKILL.md) — calibration selection and validation
- [sns-snap-reduction-diagnostics](../sns-snap-reduction-diagnostics/SKILL.md) — diagnosing failed or suspect outputs
- [sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md) — PE cell, DAC, cylinder cell branches

---

## Evidence tracking

**Phase 0 baseline** (2026-04-29):
- Source: https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html
- Validation: [sns-snap-phase0-validation.md](../../instruments/sns-snap-phase0-validation.md)
- Verified claims: `wrap.reduce()` entry point, lite mode default, pixel grouping (3 built-in
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

---

## Overview

This skill produces a reproducible reduction sequence for a SNAP dataset: a
confirmed calibration context (difcal + normcal), an appropriate grouping and
masking strategy, any sample-environment-specific adaptations, and labelled
output workspaces (`reduced_` or `diagnostic_`) ready for export and
downstream analysis.

**Software provenance:**
- **snapwrap** (user interface — first): users call reduction and export workflows
  by run number; user-visible choices include grouping scheme, masking inputs,
  output formats, and continue flags.
- **snapred** (backend): resolves state-dependent calibration context; missing
  calibration triggers approximation pathways and labels outputs `diagnostic`.
- **Mantid** (framework): executes calibration, focusing, unit conversion,
  masking, and normalization algorithms orchestrated by snapred.

**SNAP-specific conventions:**
- Lite mode is default; native mode is expert/special-case.
- Grouping is fully general: 3 built-in defaults (all, bank, column) plus custom schemes.
- Both mask types are first-class: pixelmask (exclude pixels) and binmask
  (exclude bin ranges in any unit: TOF, wavelength, Q, d-spacing).
- Output labels communicate calibration completeness: `reduced_` = full
  calibration applied; `diagnostic_` = approximation used.

---

## When to Use

- Use when planning or executing a new SNAP powder-diffraction reduction run.
- Use when you need to decide which grouping scheme, masking strategy, or
  export format to apply before writing a snapwrap script.
- Use when a collaborator hands you a run number and asks for reduced data.
- Do NOT use for single-crystal SNAP data — different calibration and
  reduction pathways apply.
- Do NOT use as the sole skill when a high-pressure sample environment is
  present — also invoke
  [sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md).

---

## Process

Collect this context before starting:
- Run numbers and experiment mode.
- Sample environment assembly type (`assembly.pe`, `assembly.dac`, cylinder,
  or none) from SEEMeta or documentation.
- Target output format (`gsa`, `xye`, `csv`).
- Whether cycle-strict calibration matching must remain enabled (`requireSameCycle`).
- Any known run exclusions or masking requirements.

---

1. **Verify input runs and metadata consistency** — Confirm run numbers exist,
   IPTS path is accessible, and run metadata (sample, title, configuration)
   is present and internally consistent. Flag any mismatches before
   proceeding.

2. **Resolve calibration context** — For the instrument state derived from the
   run, confirm that both a diffraction calibration (`difcal`) and a
   normalization calibration (`normcal`) exist and that their `appliesTo`
   fields cover the run number. Use `snapwrap.snapStateMgr.checkCalibrationStatus()`.
   If either is absent, decide explicitly: obtain the missing calibration
   (preferred) or set the appropriate continue flag and accept `diagnostic`
   output.

   **[CHECKPOINT]**: Calibration status is confirmed. The decision to proceed
   with full or diagnostic output is recorded before running reduction.

3. **Choose grouping and masking strategy** — Select a pixel grouping scheme
   (all, bank, column, or custom) based on the resolution/statistics tradeoff
   for the experiment. Identify and document any pixelmasks or binmasks
   required. Record the scientific rationale for each choice.

4. **Handle sample-environment special cases** — If a high-pressure device is
   present, branch to
   [sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md)
   to build environment-specific masks and attenuation inputs before
   proceeding. Return here after that skill's exit criteria are met.

5. **Run reduction** — Call `snapwrap.utils.reduce(runNumber, ...)` with the
   confirmed calibration policy, grouping, and mask inputs. Check the output
   workspace name prefix (`reduced_` vs `diagnostic_`) immediately on
   completion. Do not continue to export if the label is unexpected.

   **[CHECKPOINT]**: Output workspaces exist in the Mantid tree with the
   expected prefix and pixel-group suffixes. Any `diagnostic` output has an
   explicit documented reason.

6. **Perform background handling and normalization checks** — Inspect reduced
   spectra for normalization stability across detector groups. Compare
   baseline behavior against a reference or prior cycle. Flag anomalies for
   the diagnostics skill.

7. **Export for downstream analysis** — Convert and export to the required
   format (`gsa`, `xye`, `csv`) using `snapwrap.io.exportData()`. Confirm
   exported files exist on disk and are non-empty.

8. **Capture diagnostics and provenance** — Record in analysis notes: run
   numbers, calibration identifiers and versions, grouping/masking rationale,
   software versions, continue flags used (if any), and output label with
   justification.

**Exit criteria**: Reduced outputs are labelled correctly, exported files
exist, and provenance is recorded. If output is `diagnostic`, its intended
usage (exploratory only, or pending recalibration and rerun) is explicitly
stated.

---

## Rationalizations

| Rationalization | Why it is wrong |
|-----------------|-----------------|
| "The calibration is probably fine — it worked last cycle." | Cycle-strict matching (`requireSameCycle=True`) exists because detector state changes between cycles. An out-of-cycle calibration produces no warning; it silently maps TOF to wrong d values. Always run `checkCalibrationStatus()`. |
| "The output says `diagnostic_` but the peaks look reasonable, so I'll use it for final results." | `diagnostic_` means an approximation pathway was used. Publishing these as final results misrepresents the data provenance. Use diagnostic outputs for exploratory decisions only, then recalibrate and rerun. |
| "I'll document the masking choices after the analysis." | Undocumented mask rationale cannot be reproduced and cannot be reviewed. Write it down at step 3 and step 8, before the script runs. |
| "Native mode gives more pixels so it must be better." | Native mode is 64× more expensive and intended for special cases only. Lite mode matches the instrument's diffraction resolution. Using native mode routinely wastes compute and can destabilize calibration fits. |
| "I'll skip the background/normalization check — the data looks clean." | Normalization instability across groups is not visible in a single spectrum. Step 6 is a cross-group comparison; skipping it means you may export data with a systematic group-dependent error. |

---

## Red Flags

- Output workspace prefix is `diagnostic_` but no continue flag was
  intentionally set → calibration lookup failed silently; re-examine state ID
  and calibration index. Revisit step 2.
- No output workspaces appear in the Mantid tree after `reduce()` completes →
  reduction aborted (likely missing calibration with continue flags at
  default `False`). Check logs for `ContinueWarning`. Revisit step 2.
- Reduced spectra show systematic offsets between pixel groups (e.g., bank
  peaks do not align with column peaks) → calibration mismatch across
  groups. Invoke [sns-snap-reduction-diagnostics](../sns-snap-reduction-diagnostics/SKILL.md)
  and revisit step 2–3.
- Exported files are empty or zero-length → export step failed; check
  IPTS write permissions and `save=True` flag. Revisit step 7.
- Provenance record missing calibration version or software version →
  results cannot be reproduced; complete step 8 before sharing outputs.

---

## Verification

Before marking this skill complete:

- [ ] Both `difcal` and `normcal` status confirmed via `checkCalibrationStatus()`;
      result recorded.
- [ ] Output workspace prefix matches expectation: `reduced_` for full
      calibration, `diagnostic_` only when intentionally accepted.
- [ ] Grouping scheme and mask choices recorded with scientific rationale in
      analysis notes.
- [ ] Exported files exist on disk in the target format and are non-empty.
- [ ] Analysis notes include: run numbers, calibration identifiers + versions,
      software versions, any continue flags used, and output label with
      justification.
- [ ] If output is `diagnostic_`: explicit statement of whether it is for
      exploratory use only or will be superseded by a `reduced_` rerun.
