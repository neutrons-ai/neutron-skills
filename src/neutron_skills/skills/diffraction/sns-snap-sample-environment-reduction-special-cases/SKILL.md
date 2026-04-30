---
name: sns-snap-sample-environment-reduction-special-cases
description: >
  Adapt SNAP powder-diffraction reduction workflows for sample-environment-driven
  special cases. Use when a paris-edinburgh cell, diamond anvil cell (DAC), or
  cylinder cell is in the beam and the standard reduction sequence requires
  environment-specific masking, notching, or background handling.
version: 1
review:
  status: human-reviewed
  reviewer: Malcolm Guthrie
  reviewed_on: 2026-04-30
  basis: [docs, code, instrument-science-review]
  notes: >
    Initial draft authored from instrument-scientist domain notes covering PE,
    DAC, and cylinder cell impacts on SNAP reduction. Encoded current operational
    practice including semi-manual workflow status, snapwrap masking interfaces,
    and outstanding R&D items. Review completed with DAC/PE/cylinder
    analysis-stage artifact guidance and SEEMeta lookup priority aligned to
    current snapwrap behavior. Cross-linked to existing workflow, calibration,
    and diagnostics skills.
  approved_commit: review/sns-snap-sample-environment-reduction-special-cases-v1
metadata:
  facility: SNS
  beamline: BL3
  instruments: [SNAP, SNS]
  software: [snapwrap, snapred, Mantid]
  data_phase: reduction
  techniques: [diffraction, powder-diffraction, time-of-flight, high-pressure]
  tags:
    - sample-environment
    - paris-edinburgh
    - diamond-anvil-cell
    - cylinder-cell
    - masking
    - wavelength-notching
    - binmask
    - pixelmask
    - attenuation
    - high-pressure
    - assembly.pe
    - assembly.dac
    - SEEMeta
    - swissCheese
---

# SNAP Sample-Environment Reduction Special Cases

Use this skill when a specific high-pressure sample environment is present and
the reduction workflow requires environment-specific modifications.  The
standard reduction workflow (described in
[sns-snap-reduction-workflow-overview](../sns-snap-reduction-workflow-overview/SKILL.md))
applies; this skill provides the branches that deviate from it.

SNAP is primarily a high-pressure powder diffractometer. Almost all
measurements use a high-pressure device that introduces occlusion, beam
attenuation, and background features not present in open-geometry experiments.
Each device class has a distinct set of reduction impacts and current solution
status.

## Provenance map

- snapwrap (user interface — first):
  - Hosts all sample-environment masking utilities under `snapwrap.maskUtils`.
  - Exposes `swissCheese` objects for combined pixel and bin mask management.
  - Passes environment-specific mask inputs to the reduction engine via the
    `binMaskList` argument and pixel mask inputs to `reduce`.
  - Communicates environment context to snapred via custom reduction hooks.
  - Provides `SEEMeta` extraction tools to retrieve assembly metadata from run
    logs.
- snapred (backend logic):
  - Receives environment-specific mask inputs and hook parameters from snapwrap.
  - Applies masking and binning decisions during reduction orchestration.
  - Routes output to `reduced` or `diagnostic` label based on calibration
    completeness (unaffected by environment type).
- Mantid (framework):
  - Executes masking, binning, focusing, and unit-conversion algorithms
    underlying the snapred reduction pipeline.

## Evidence tracking

**Domain notes baseline** (2026-04-30):
- Source: instrument-scientist domain notes (Malcolm Guthrie).
- Coverage: PE cell, DAC cell, cylinder cell — device characteristics,
  reduction impacts, and current solution status.

## Context to collect before use

- Assembly type from SEEMeta: `assembly.pe`, `assembly.dac`, or cylinder
  variant, plus nickname/model/comment when available.
  - SEEMeta lookup order in `snapwrap`: (1) IPTS override file
    `/IPTS-{ipts}/shared/SEE/SEE{runNumber}.json`, then (2) embedded JSON
    dictionary in the neutron data file run logs. This supports user override
    of embedded values when corrections are needed. If neither source is
    available, fall back to manual identification by run number or
    documentation.
- Whether a pixel mask for this environment already exists and is current.
- Whether wavelength-specific bin masks are required (DAC) or previous masks
  can be reused.
- Grouping scheme in use: column grouping has angular-coverage implications
  for DAC measurements (see DAC section below).
- Calibration state: environment-specific masking does not change calibration
  requirements; see
  [sns-snap-calibration-and-geometry](../sns-snap-calibration-and-geometry/SKILL.md)
  for calibration state controls.

---

## Paris-Edinburgh (PE) cells

**Device characteristics**

PE cells are hydraulically driven presses that compress approximately
spherical samples (3–6 mm diameter) between two opposed anvils.  A metallic
gasket — typically TiZr alloy — provides lateral containment.  Anvil
materials include sintered diamond (SD), zirconium-toughened alumina (ZTA),
and tungsten carbide (WC); each has distinct mechanical and neutronics
properties.  Maximum pressure is approximately 20 GPa.  Temperature range
extends from room temperature down to approximately 10 K; high-temperature
capability is not currently available on SNAP.

Assembly type in SEEMeta: `assembly.pe`.

**Reduction impacts**

| Impact | Description |
|--------|-------------|
| Pixel occlusion | Anvil body blocks a large fraction of detector pixels; occluded pixels must be excluded by a PE-specific pixel mask. |
| Beam attenuation | Incident beam is attenuated primarily by the TiZr gasket. |
| Background | Gasket scattering contributes a large but smooth background due to TiZr null-scattering properties; no sharp parasitic peaks expected from the gasket itself. |
| Anvil scattering | Anvil material (SD, ZTA, WC) introduces material-specific background; WC has the largest cross-section. |

**Required reduction modifications**

1. Apply a PE-specific pixel mask to remove pixels occluded or contaminated by
   anvil scattering.  This mask is geometry-dependent and is not the same
   across all PE cell configurations.
2. Background handling: TiZr null-scattering means the gasket background is
   smoothly varying and can be treated as a continuous background component.
   Sharp features in background most likely originate from anvil material.

**Not yet implemented**

- Attenuation corrections for gasket and anvils are not currently implemented
  in snapred.  This is a known limitation; corrections must be applied
  post-reduction if required for quantitative analysis.

**Analysis-stage artifacts (post-reduction)**

- PE anvil materials can contribute powder Bragg peaks to the reduced pattern.
  These are not single-crystal spot artifacts and cannot be removed by the
  masking/notching workflow; handle them during analysis (for example, by
  explicit phase/background treatment in Rietveld refinement).

**Key diagnostic signatures for PE experiments**

- Large region of zero or near-zero counts in detector image →
  pixel mask coverage may be insufficient or shifted.
- Sharp structured background features not present in open-geometry measurement →
  check anvil material identification.
- See [sns-snap-reduction-diagnostics](../sns-snap-reduction-diagnostics/SKILL.md)
  for full failure-mode escalation guidance.

---

## Diamond Anvil Cells (DACs)

**Device characteristics**

DACs use opposed single-crystal diamond anvils with flat polished culets of
0.8–1.6 mm diameter.  The sample is contained in a metallic gasket (tungsten,
rhenium, or steel) 0.1–0.2 mm thick.  DACs can exceed 100 GPa and are the
highest-pressure devices available on SNAP.  Temperature range extends from
room temperature down to approximately 10 K.

Assembly type in SEEMeta: `assembly.dac`.

**Reduction impacts**

The small sample volume and complex beam path through the diamonds make DAC
reduction significantly more complex than PE.

| Impact | Description |
|--------|-------------|
| Diamond Bragg scattering | As the incident beam passes through each diamond, specific wavelengths satisfy the Bragg condition for the diamond lattice.  This produces: (1) localised single-crystal diffraction spots on the detector, (2) diffuse scattering extending beyond the spots, and (3) highly distributed multiple scattering. |
| Structured beam attenuation | Scattering at Bragg-condition wavelengths removes neutrons from the transmitted beam, creating sharp dips in the wavelength response.  This modifies the effective wavelength distribution seen by the sample. |
| d-coverage gaps | Removing wavelength bands from the reduction introduces gaps in d-spacing coverage.  Low-angular-coverage subgroups (e.g. column grouping) are most affected and may show significant d-gaps. |
| Complex resolution function | Wavelength notching creates a non-standard effective instrument resolution function.  This is currently supported only in GSAS-II analysis; other analysis codes require special handling or exclusion of notched regions. |

**Primary mitigation strategy: wavelength notching**

Wavelength notching identifies affected wavelength bands and excludes them
from the reduction using bin masks.  This is the recommended first-line
approach for DAC data.

Requirements for successful notching:
- Sufficient angular coverage in the chosen grouping scheme to maintain
  acceptable d-range despite missing wavelength bands.
- Check that analysis code supports non-uniform wavelength coverage
  (currently GSAS-II only for quantitative Rietveld work).
- Experimental alignment of each diamond anvil relative to the beam is
  critical. If a diamond unit-cell axis is even slightly misaligned from the
  beam, Bragg-wavelength degeneracy is lifted: symmetry-equivalent
  reflections produce multiple notch wavelengths rather than a single notch.
  Larger misalignment increases wavelength spread, requiring broader/more
  notch removal and reducing usable coverage.

**Notch generation: two pathways**

Both pathways are currently semi-manual.  Full automation is a high-priority
development target.

*Pathway 1 — transmission inspection:*
Inspect the transmitted beam spectrum; affected wavelengths appear as sharp
dips at specific wavelengths.  Notch positions are determined by eye or by
automated dip-finding.

*Pathway 2 — UB matrix calculation:*
Determine the crystallographic orientation (UB matrix) of each diamond by
fitting its single-crystal diffraction pattern.  Calculate affected wavelengths
from the diamond UB matrices using `snapwrap.maskUtils.swissCheese`, which
provides methods to construct notch masks from a specified UB matrix pair
(one matrix per diamond).

Resultant notch masks are applied during reduction by passing them in the
`binMaskList` argument to `reduce`.  Multiple masks in different units
(TOF, wavelength, Q, d-spacing) can be supplied simultaneously.

**Supplementary manual bin masking**

Wavelength notching alone may not remove all artifact regions.  Manual bin
masking is typically applied in addition to notching:

1. Convert the full three-dimensional dataset to the unit of choice
   (pre-reduction but optionally post-notching) using Mantid.
2. Inspect data using the MantidWorkbench `ShowInstrument` view.
3. View slices at specific x-unit ranges and manually mark artifact regions
   for exclusion.
4. Extract the mask into a `swissCheese` object using the
   `swissCheese.ExtractFromWorkspaceHistory` method.
5. Combine with notch masks and pass the combined object into reduction via
   `binMaskList`.

Manual mask generation will be automated in a future snapwrap release.

**Analysis-stage artifacts (post-reduction)**

- The beam can intersect the DAC gasket, producing gasket Bragg peaks in the
  reduced data. These peaks are identifiable by the characteristic d-spacings
  of the gasket material and should be handled during analysis (for example,
  with explicit phase/background treatment in Rietveld refinement).
- Scattering from the DAC collimator (located very close to the sample) has
  also been observed and is a warning flag for experimental setup issues.
  It manifests as additional Bragg peaks from the collimator, but can be
  difficult to identify unambiguously because the off-center upstream
  collimator position shifts the apparent d-spacing of those peaks.

**Key diagnostic signatures for DAC experiments**

- Sharp-edged gaps in d-coverage at specific d values →
  notch mask is applied; verify coverage is acceptable for analysis.
- Residual structured background at positions corresponding to diamond d-spacings →
  notching is incomplete; review UB matrix accuracy or extend manual mask.
- Unexpected broadening in analysis code other than GSAS-II →
  resolution function from notching is not modelled; switch to GSAS-II or
  exclude notched regions from analysis.

---

## Cylinder Cells

**Device characteristics**

Cylinder cells take two forms:
- Gas cylinders: a simple cylinder containing a pressurised gas sample.
- Piston-cylinder devices: the sample is contained in a cylinder compressed
  from both ends by pistons.

Maximum pressure is approximately 2 GPa.  Temperature operation is typically
cold (down to liquid-He temperatures with appropriate cryostat).

**Reduction impacts**

| Impact | Description |
|--------|-------------|
| Beam attenuation | The cylinder wall attenuates the incident and diffracted beams; an attenuation correction is required for quantitative work. |
| Bragg-edge attenuation structure | The cylinder material introduces wavelength-structured attenuation at wavelengths corresponding to its own crystallographic Bragg edges.  These must be correctly modelled in the attenuation correction, not simply masked out. |
| Background | The cylinder body contributes a background component that must be subtracted. |

**Required reduction modifications**

1. Apply an attenuation correction that accounts for the cylinder geometry and
   material, including Bragg-edge structure in the attenuation.
2. Background subtraction:
   - An empty-cell measurement is the preferred method.
   - At higher pressures the cylinder itself is modified by the applied pressure,
     degrading the empty-cell background estimate.  In these cases, background
     determination from the data is required.

**Not yet implemented / active R&D**

- Robust background determination that accounts for pressure-modified container
  geometry is under active development.  This is not currently available as a
  standard workflow.

**Analysis-stage artifacts (post-reduction)**

- Scattering from the cylinder cell body can contaminate the sample
  diffraction signal. Treat these contributions explicitly during analysis
  (for example, with container/background terms in Rietveld refinement),
  particularly at high pressure where container response changes with load.

**Key diagnostic signatures for cylinder experiments**

- Structured residuals in reduced data at positions corresponding to container
  material d-spacings → background subtraction is insufficient; check container
  identification and Bragg-edge correction quality.
- Systematic offset vs empty-cell background at high pressure → container has
  been deformed by pressure; standard empty-cell subtraction is unreliable.

---

## snapwrap integration summary

The bulk of sample-environment adaptation is implemented in snapwrap; snapred
receives the prepared inputs via reduction hooks.

| Component | Role |
|-----------|------|
| `snapwrap.maskUtils.swissCheese` | Manages combined pixel and bin mask objects; provides construction methods (e.g., from UB matrix pairs) and extraction from workspace history. |
| `reduce(..., binMaskList=...)` | Accepts a list of bin mask objects in any unit (TOF, wavelength, Q, d-spacing); multiple masks combined automatically. |
| `reduce(..., pixelMask=...)` | Accepts a pixel mask for environment occlusion (e.g., PE anvil shadow). |
| Reduction hooks | Environment-specific parameters are passed to snapred reduction orchestration via snapwrap-defined hooks; consult current snapwrap API docs for hook interface. |
| SEEMeta extraction | Use snapwrap tools with priority: IPTS override file first, embedded run-log JSON second (to allow user correction of embedded values). If neither is available, fall back to manual identification. |

## Quality gates

- Pixel mask accounts for all occluded or contaminated detector regions.
- For DAC: wavelength notch positions confirmed against diamond UB matrices
  or observed transmission dips; coverage after notching is acceptable for
  the chosen grouping and analysis code.
- For cylinder: attenuation correction applied; empty-cell background
  subtraction validity assessed relative to applied pressure.
- Output label is `reduced` (full calibration available) or `diagnostic`
  (approximation pathway used); environment masking does not change the
  label logic.
- Analysis code compatibility confirmed: GSAS-II required for notched DAC
  data in quantitative Rietveld work.

## Output expectations

- A reduction sequence adapted to the identified sample environment.
- Mask objects (pixel and/or bin) constructed and ready for the `reduce` call.
- A recorded rationale for mask choices and any known limitations
  (e.g., pending attenuation correction, manual notch bounds).
- Explicit statement of what is not corrected in the current reduction and
  what post-reduction handling is required.
