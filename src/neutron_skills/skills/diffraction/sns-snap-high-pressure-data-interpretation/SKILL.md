---
name: sns-snap-high-pressure-data-interpretation
description: >
  Interpret SNAP high-pressure powder-diffraction data at the analysis stage.
  Use when performing or reviewing Rietveld analysis of data collected with a
  paris-edinburgh cell, diamond anvil cell (DAC), or cylinder cell, and you
  need to identify and handle dataset-specific challenges: multiple phases,
  microstructural effects, strain, low signal statistics, background, and
  cell-component Bragg scattering.
version: 1
review:
  status: pending
  reviewer: null
  reviewed_on: null
  basis: []
  notes: >
    Initial draft authored from instrument-scientist domain notes
    (Malcolm Guthrie, 2026-04-30). Source notes preserved in
    assets/high-pressure-data-notes.md. Covers analysis-stage challenges for
    high-pressure powder diffraction on SNAP: multiple phases, microstructural
    effects, strain, sample signal and statistics, background handling, and
    cell-component artifacts.
  approved_commit: null
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

Use this skill at the **analysis stage** — after reduction is complete and you
have focused, merged powder patterns — when the data come from a high-pressure
device. High-pressure datasets have a characteristic set of challenges that all
require specific treatment in the Rietveld model or experimental follow-up.

For the **reduction-stage** counterpart (masking, notching, attenuation
correction, SEEMeta handling) see
[sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md).

Source domain notes: `assets/high-pressure-data-notes.md`.

---

## Evidence tracking

| Item | Detail |
|---|---|
| Domain notes | Malcolm Guthrie, instrument-scientist notes, 2026-04-30 (`assets/high-pressure-data-notes.md`) |
| Reduction cross-reference | `sns-snap-sample-environment-reduction-special-cases` (human-reviewed 2026-04-30) |
| Rietveld framework reference | `rietveld-checklist` |

---

## Context to collect before use

Before applying guidance from this skill, establish:

- **Device type** — PE cell, DAC, or cylinder cell. Each has distinct artifact
  signatures (see
  [sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md)
  for device-specific reduction artifacts).
- **Pressure medium** — hydrostatic (noble gas, deuterated alcohol mixture,
  glycerin) or non-hydrostatic (solid).
- **Pixel grouping scheme** — which detector banks / groupings were used; this
  governs available angular resolution for strain analysis.
- **Notching applied?** — whether wavelength-notching was applied during
  reduction; this affects background tractability (see §Background).
- **Known cell-component phases** — chemical identity of anvils, gaskets, and
  any pressure calibrant phases present.
- **Sample history** — did the sample undergo annealing? Were crystallization
  seeds used? These affect expected microstructure.

---

## Multiple phases

High-pressure experiments routinely have several distinct crystallographic
phases contributing simultaneously to the measured pattern:

- The **sample** itself (which may exhibit one or more pressure-induced phases
  or decomposition products)
- **Pressure medium** (if crystalline at the measurement pressure)
- **Pressure calibrant** (e.g. gold, ruby — though ruby fluorescence is used
  off-line; NaCl or gold standard for in-situ TOF)
- **Cell-component phases** — anvil, gasket, and body materials (see
  §Cell-component Bragg scattering)

All illuminated phases are superimposed in the TOF pattern. The only reliable
analysis approach is a **multi-phase Rietveld model** that accounts for every
contributing crystalline phase. Unidentified peaks must be investigated — they
are likely from cell components or a new sample phase — before committing to a
structural interpretation.

**Experimental mitigations** (to reduce the number of phases): careful
collimation to restrict the illuminated volume; choice of non-diffracting or
weakly diffracting pressure media at the measurement conditions.

---

## Microstructural effects and preferred orientation

High-pressure phase transitions occur with little experimental control over
the resultant microstructure. Two effects can fundamentally limit the
reliability of intensities extracted from the Rietveld fit:

### Preferred orientation (texture)

Rietveld analysis assumes unbiased sampling of all crystallite orientations
(ideal powder averaging). Preferred orientation violates this assumption and
biases extracted intensities, which propagates into structural parameters.

**TOF-specific advantage**: SNAP's time-of-flight geometry enables the direct
resolution of orientational domains because the same $d$-spacing is measured
simultaneously at multiple detector positions covering a range of scattering
angles. This allows texture to be modelled explicitly using spherical harmonics
or other orientation distribution functions within the Rietveld model rather
than being treated as a single scalar correction.

**Modelling guidance**: enable preferred-orientation corrections in the
Rietveld model from an early stage. If strong texture is present, multi-bank
data (exploiting SNAP's angular coverage) substantially constrain the
orientation distribution.

**Experimental mitigations**: slow or oscillating pressure/temperature ramps
during phase transformation; crystallization seeds (e.g. silica wool,
mesoporous materials). Effectiveness is sample- and phase-dependent.

### Large crystallites

If individual crystallites are large relative to the beam footprint, their
single-crystal Bragg peaks appear as intense spikes that bias intensities in
the bins they fall in. **Pixel masking** applied during reduction (before
merging pixels into a powder average) is the primary mitigation. See
[sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md)
for the masking workflow.

### Limiting over-analysis

When intensities are known to be unreliable (strong texture unresolvable with
the available angular coverage, large-crystallite contamination not fully
masked), the information content of the pattern is reduced to what can be
derived from **peak positions and profiles** rather than intensities.
Analysis should be scoped accordingly:

- Unit-cell parameters and equation of state parameters remain accessible.
- Atomic coordinates, occupancies, and thermal parameters require reliable
  intensities — do not refine these if intensity reliability is in doubt.
- Document the basis for any intensity-dependent conclusions explicitly.

---

## Strain

Strain gradients are common in high-pressure samples because the neutron beam
samples an extended volume and averages over a range of local stress
conditions. The primary observable effect is **peak broadening** — both
Lorentzian (microstrain) and Gaussian (strain distribution) components can
contribute.

### Experimental mitigations

| Approach | Effect | Tradeoff |
|---|---|---|
| Hydrostatic pressure medium (noble gas, D₂O/ethanol, glycerin) | Minimizes deviatoric stress; near-hydrostatic sample environment | Medium adds phases; noble-gas loading requires cryostat or high-pressure gas loader |
| Annealing (≈50% of melting temperature) | Greatly reduces stress; sharpens peaks | Can induce recrystallisation, degrading intensity reliability |

### TOF angular-resolution advantage for uniaxial strain

Under uniaxial load (typical of DAC and PE geometries), strain is
angle-dependent: the sample experiences different $d$-spacing shifts at
different scattering angles relative to the load axis. SNAP's multi-angle
detector coverage makes it possible to **resolve this angular dependence** by
fitting data from different pixel groups separately or jointly with a
strain-model constraint.

This requires a pixel grouping scheme that provides adequate angular
resolution. Higher angular resolution groups fewer pixels, reducing counting
statistics per bin. The appropriate tradeoff depends on the strain magnitude
and peak overlap.

### Rietveld package support

Most Rietveld packages (GSAS-II, FullProf) support isotropic and anisotropic
microstrain broadening models. However, **TOF-specific strain modelling** —
particularly the simultaneous multi-angle strain analysis enabled by SNAP's
geometry — is not fully supported in current packages. Full exploitation of
SNAP's TOF information content for strain analysis is an active area of
development. Use available broadening models as approximations, and note their
limitations in any analysis documentation.

---

## Sample signal and statistics

High-pressure devices constrain the sample volume to maximise pressure (force
per unit area). The resulting sample mass is small, and the net Bragg
scattering signal is proportionally small.

### Counting time

Adequate counting statistics typically require long exposure. DAC samples
(the smallest sample volumes) may require many hours of counting time. When
assessing whether statistics are sufficient:

- Check the uncertainty on key peaks explicitly.
- Compare peak-to-background ratio against the threshold needed for the
  intended analysis (position-only analysis has a lower threshold than
  intensity-dependent structural refinement).

### Attenuation by cell materials

The beam passes through cell-body and anvil materials both inbound and
outbound. This:

1. **Reduces flux** reaching the sample and **reduces detected scattered
   intensity**, degrading statistics.
2. **Introduces a wavelength-dependent correction** — attenuation cross
   sections are wavelength-dependent, so the effective transmission function
   is not flat across the TOF pattern.

The wavelength-dependent correction must be applied during **reduction**, not
at the analysis stage. Confirm the correction was applied before interpreting
absolute or relative intensities. See
[sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md).

---

## Background

The pressure cell invariably contributes background to the measured signal.
This background has several characteristics that make standard empty-cell
subtraction insufficient:

| Property | Implication |
|---|---|
| Large relative to sample signal | Accurate modelling is critical |
| Structured (non-polynomial) | Standard background polynomial may be inadequate |
| **Pressure-dependent** | Empty-cell measurement at ambient pressure cannot be subtracted at high pressure — the cell deforms, beam path changes, and cell-component phases shift |

### Analysis-stage background modelling

Rietveld packages provide several background models (Chebyshev polynomial,
linear interpolation, fixed points). Where the background is smooth, a
polynomial of adequate degree is usually sufficient. Where it is structured
(e.g. broad amorphous humps from glass-forming media, oscillatory features),
use fixed background points with manual adjustment or a higher-complexity
model.

### DAC background: diamond fluorescence and multiple scattering

DAC data present the most challenging background case. Multiple scattering of
diamond Bragg reflections produces a complex, highly structured background that
is effectively intractable by standard polynomial fitting. Two approaches help:

1. **Wavelength notching** applied during reduction removes the diamond Bragg
   wavelengths entirely from the TOF pattern. This not only eliminates the
   peaks themselves but dramatically smooths the residual background and makes
   it nearly pressure-independent, enabling effective subtraction or polynomial
   modelling. (See
   [sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md)
   for the notching workflow.)
2. **Amorphisation / melting technique**: the sample (or a sacrificial
   material) is amorphised or melted so its signal is smeared into a broad
   hump. The resulting pattern provides a usable approximation of the true
   total background, which can then be subtracted before the main analysis.

If notching was not applied during reduction and the background is intractable,
consider flagging the data for re-reduction with notching before proceeding.

### Cell-component Bragg scattering

Bragg peaks from anvil, gasket, and cell-body materials are commonly visible in
high-pressure patterns. Because these components are physically close to the
sample and under significant load, their $d$-spacings are also
**pressure-dependent** — making them unsubtractable even in principle. They
must be **included as additional phases in the Rietveld model**.

Experimental minimization procedures (collimation, beam footprint tuning)
reduce but do not eliminate this contribution. See
[sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md)
for device-specific descriptions of which components contribute and at which
$d$-spacings.

---

## Quality gates

Before accepting a high-pressure Rietveld refinement as complete:

- [ ] All visible peaks accounted for in the model (sample phases + pressure
      medium + calibrant + cell-component phases)
- [ ] Background model provides a good residual; no broad unmodelled features
- [ ] Preferred-orientation correction enabled if texture is suspected
- [ ] Strain broadening model applied and $R_{wp}$ not dominated by profile
      mismatch
- [ ] If intensities are unreliable, analysis limited to peak-position /
      equation-of-state outputs only
- [ ] Attenuation correction confirmed applied during reduction
- [ ] Uncertainties on key parameters checked against counting statistics

For general Rietveld parameter release order and goodness-of-fit metrics see
[rietveld-checklist](../rietveld-checklist/SKILL.md).
