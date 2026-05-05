---
name: sns-snap-high-pressure-data-interpretation
description: >
  Interpret SNAP high-pressure powder-diffraction data at the analysis stage.
  Use when performing or reviewing Rietveld analysis of data collected with a
  paris-edinburgh cell, diamond anvil cell (DAC), or cylinder cell, and you
  need to identify and handle dataset-specific challenges: pressure-driven
  structural variation, multiple phases, microstructural effects, strain, low
  signal statistics, background, and cell-component Bragg scattering.
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
    reviewed_on: 2026-05-01
    basis: [instrument-science-review]
    notes: >
      Initial draft authored from instrument-scientist domain notes
      (Malcolm Guthrie, 2026-04-30). Source notes preserved in
      assets/high-pressure-data-notes.md. Covers analysis-stage challenges for
      high-pressure powder diffraction on SNAP: pressure-driven structural
      variation and indexing implications, multiple phases, microstructural
      effects, strain, sample signal and statistics, background handling, and
      cell-component artifacts. Reviewed and approved by Malcolm Guthrie
      2026-05-01; variable-structure section added post-initial-draft.
    approved_commit: review/sns-snap-high-pressure-data-interpretation-v1
metadata:
  facility: SNS
  beamline: BL3
  instruments: [SNAP, SNS]
  software: [GSAS-II, FullProf, Mantid]
  data_phase: analysis
  techniques: [diffraction, powder-diffraction, time-of-flight, high-pressure]
  tags:
    - rietveld
    - multiple-phases
    - preferred-orientation
    - microstructure
    - strain
    - background
    - attenuation
    - high-pressure
    - assembly.dac
    - assembly.pe
    - cylinder-cell
    - pixel-masking
    - wavelength-notching
    - analysis
---

# SNAP High-Pressure Data Interpretation

even disrupted under pressure and any rigid body constraints based on ambient models may need to be relaxed.
different scattering angles relative to the load axis. SNAP's multi-angle
detector coverage makes it possible to **resolve this angular dependence** by
development. Use available broadening models as approximations, and note their
diamond Bragg reflections produces a complex, highly structured background that
## Overview

Use this skill at the **analysis stage** after reduction is complete and you
have focused, merged powder patterns from a high-pressure device. These data
have a recurring set of interpretation problems that require explicit choices in
the Rietveld model or a deliberate decision to stop short of full structural
refinement.

For the **reduction-stage** counterpart, including masking, wavelength notching,
attenuation correction, and `SEEMeta` handling, see
[sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md).

### Evidence

| Item | Detail |
|---|---|
| Domain notes | Malcolm Guthrie instrument-scientist notes, 2026-04-30, preserved in `assets/high-pressure-data-notes.md` |
| Reduction cross-reference | `sns-snap-sample-environment-reduction-special-cases` |
| Rietveld framework reference | [rietveld-checklist](../rietveld-checklist/SKILL.md) |

---

## When to Use

Use this skill when:

- You are interpreting reduced SNAP high-pressure powder-diffraction data from
  a PE cell, DAC, or cylinder cell.
- The refinement must distinguish sample signal from pressure-medium,
  calibrant, gasket, anvil, or container contributions.
- Pressure, strain, texture, low statistics, or structured background are
  likely limiting factors.

Do **not** use this skill when:

- You still need to decide masking, notching, attenuation correction, or
  sample-environment metadata during reduction.
- You only need generic release order and fit-quality guidance without a
  high-pressure context; use
  [rietveld-checklist](../rietveld-checklist/SKILL.md).

### Required context before starting

- Device type and component details: PE, DAC, or cylinder cell.
- Starting structural model quality: ambient-only starting model or a
  pressure-appropriate indexed lattice.
- Pressure medium: hydrostatic or non-hydrostatic.
- Pixel grouping scheme used during reduction; this controls available angular
  resolution for strain analysis and artifact localization.
- Whether wavelength notching was applied during reduction.
- Known cell-component phases and pressure calibrant phases.
- Sample history such as annealing or use of crystallization seeds.

---

## Process

1. **Establish the interpretation envelope first** — Record the device type,
   pressure medium, pixel grouping, notching status, and known cell-component
   phases before fitting. High-pressure interpretation is constrained by those
   experimental facts.

   **[CHECKPOINT]**: Device class, sample environment, grouping scheme, and
   reduction choices are known and documented.

2. **Treat ambient-pressure structures as starting guesses only** — High
   pressure can change a structure continuously or discontinuously. Do not trust
   ambient database entries as final truth under load.

   Required actions:

   - Pre-index the measured high-pressure lattice before full refinement when
     peak shifts are significant.
   - Re-index at each pressure regime where peak topology changes.
   - Do not assume ambient symmetry or metric constraints remain valid.
   - Delay aggressive atomic-parameter refinement until lattice assignment is
     stable.
   - Relax rigid-body assumptions if pressure may distort or disrupt the motif.

   Background consequence:

   - Any background-extraction method based on Bragg-peak locations must use the
     **current-pressure** peak positions, not ambient positions.

3. **Build a complete multi-phase model before interpreting structure** — High
   pressure commonly adds multiple simultaneous phases to the pattern.

   Typical contributors:

   - Sample phase or pressure-induced daughter phases.
   - Pressure medium if it crystallizes.
   - Pressure calibrant.
   - Cell-component phases from anvils, gaskets, or container bodies.

   Required actions:

   - Account for every visible peak before claiming a structural conclusion.
   - Treat unidentified peaks as unresolved physics or cell components, not as
     ignorable clutter.
   - Use multi-phase Rietveld models when more than one crystalline contributor
     is illuminated.

4. **Decide whether intensities are trustworthy enough for structural claims**
   — Texture, large crystallites, and strain can invalidate intensity-based
   refinement even when peak positions remain useful.

   Preferred orientation guidance:

   - Enable preferred-orientation corrections early if texture is suspected.
   - Use SNAP's multi-angle TOF geometry to constrain orientation effects when
     possible.
   - Multi-bank data generally constrain texture better than single merged views.

   Large-crystallite guidance:

   - If large crystallites created intense spikes that were not fully masked
     during reduction, treat refined intensities as suspect.

   Scope-limiting rule:

   - If intensity reliability is doubtful, limit conclusions to peak-position
     and profile information such as unit-cell parameters or equation-of-state
     results. Do not refine occupancies, thermal parameters, or subtle atomic
     coordinates on compromised intensities.

   **[CHECKPOINT]**: You have explicitly decided whether the analysis is
   intensity-trustworthy or position/profile-only.

5. **Assess strain with the grouping scheme in mind** — High-pressure strain
   gradients usually appear as peak broadening, and under uniaxial load they are
   angle-dependent.

   Required actions:

   - Use isotropic or anisotropic microstrain models available in GSAS-II or
     FullProf as the first approximation.
   - Check whether the chosen pixel grouping preserves enough angular resolution
     to separate strain effects across detector angles.
   - Document when the software model is only an approximation to SNAP's full
     TOF multi-angle strain information.

   Experimental interpretation notes:

   | Approach | Effect | Tradeoff |
   |---|---|---|
   | Hydrostatic medium | Reduces deviatoric stress | Adds additional phases or loading complexity |
   | Annealing near 50% melting temperature | Sharpens peaks and reduces stress | Can recrystallize and worsen intensity reliability |

6. **Check whether the sample signal is statistically adequate for the intended
   claim** — High pressure reduces sample volume and often makes the cell a
   dominant scatterer.

   Required actions:

   - Inspect uncertainties on key peaks and refined parameters.
   - Compare peak-to-background ratio against the needs of the intended analysis.
   - For DAC data, assume long counting times may be necessary before attempting
     intensity-dependent conclusions.

   Attenuation consequence:

   - Cell materials reduce flux and introduce wavelength-dependent attenuation.
   - These corrections are best handled during reduction, but missing or poor
     attenuation treatment can still be diagnosed at analysis stage through
     systematic trends versus Q or d-spacing and unphysical displacement
     parameters.

7. **Model background as a physical problem, not a cosmetic one** — High-
   pressure background is often large, structured, and pressure-dependent.

   General guidance:

   | Property | Implication |
   |---|---|
   | Large relative to sample signal | Background quality directly controls interpretation reliability |
   | Structured | A low-order polynomial may be inadequate |
   | Pressure-dependent | Empty-cell subtraction may fail at pressure |

   Required actions:

   - Use polynomial background only when the residual structure justifies it.
   - Switch to fixed points or more flexible background treatment when the
     pattern is structured.
   - Make sure background-only anchor points are not actually overlapped sample
     peaks.

   DAC-specific rule:

   - If notching was not applied and DAC background is intractable, flag the
     data for re-reduction with notching before forcing a poor analysis-stage
     model.
   - Residual diamond scattering stronger than the sample is a sign the data are
     not ready for trustworthy refinement.

8. **Treat cell-component Bragg scattering as real phases** — Peaks from anvils,
   gaskets, and cell bodies are pressure-dependent and cannot be cleanly
   subtracted as a fixed background.

   Required actions:

   - Include them as additional phases when they are visible.
   - Use reduction-stage knowledge of the cell hardware to propose candidate
     phases.
   - Do not assume ambient-pressure empty-cell subtraction can remove them.

**Exit criteria**: The high-pressure lattice has been indexed or re-indexed as
needed, all visible peaks are assigned or explicitly flagged, intensity
reliability has been assessed, strain and background models are justified, and
the final interpretation scope matches the actual information content of the
data.

---

## Rationalizations

| Excuse | Rebuttal |
|--------|----------|
| "The ambient structure is close enough; refinement will sort it out." | Under pressure, anisotropic compression and phase changes can shift peak topology enough that ambient starting models destabilize the refinement. Pre-index first when peak shifts are significant. |
| "Those extra peaks are probably noise or background." | In high-pressure data, unidentified peaks are often real phases from the sample, calibrant, pressure medium, or cell components. Ignoring them forces the wrong structural interpretation. |
| "The fit looks okay, so I can trust the intensities." | A visually acceptable fit can still hide texture, large-crystallite contamination, or strain effects that invalidate intensity-based conclusions. Decide explicitly whether intensities are trustworthy. |
| "I can model DAC background with a higher-order polynomial." | Diamond multiple scattering often produces a structured background that is not meaningfully polynomial. If notching was not done and the background remains intractable, the correct action may be re-reduction, not polynomial escalation. |
| "Empty-cell subtraction should remove the pressure-cell contribution." | Cell-component peaks and pressure-dependent container changes do not behave like a fixed background. At pressure, these contributions often need explicit phase treatment. |

---

## Red Flags

- Refinement is seeded from ambient parameters despite clear pressure-driven peak
  shifts.
- Visible peaks remain unassigned after a nominally converged fit.
- Strong texture is suspected but no preferred-orientation correction is active.
- Large-crystallite spikes or masking artifacts from reduction are known, but
  intensity-dependent parameters are still being interpreted.
- Strain broadening dominates residuals, but the grouping scheme cannot support
  the angular-resolution claim being made.
- Unphysical atomic displacement parameters or systematic intensity trends versus
  Q or d-spacing suggest missing attenuation correction.
- DAC background remains highly structured after fitting attempts and no
  re-reduction with notching is being considered.
- Cell-component peaks are present but are being treated as generic background
  instead of explicit phases.

---

## Verification

- [ ] Device type, pressure medium, grouping scheme, and notching status are
      documented before interpretation begins.
- [ ] The measured high-pressure lattice is pre-indexed or re-indexed where peak
      topology changes.
- [ ] All visible peaks are accounted for by sample phases, medium, calibrant,
      or cell-component phases, or are explicitly flagged as unresolved.
- [ ] Background treatment is justified and no broad unmodelled features remain.
- [ ] Preferred-orientation correction is enabled when texture is suspected.
- [ ] Strain broadening treatment is applied and its software limitations are
      documented.
- [ ] If intensity reliability is doubtful, conclusions are limited to
      peak-position/profile outputs only.
- [ ] Required attenuation correction is confirmed from reduction or diagnosed as
      a remaining limitation.
- [ ] Uncertainties on key refined parameters are checked against counting
      statistics and scientific goals.

For general Rietveld parameter release order and goodness-of-fit metrics see
[rietveld-checklist](../rietveld-checklist/SKILL.md).
