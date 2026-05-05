---
name: sns-snap-sample-environment-reduction-special-cases
description: >
  Adapt SNAP powder-diffraction reduction workflows for sample-environment-driven
  special cases. Use when a paris-edinburgh cell, diamond anvil cell (DAC), or
  cylinder cell is in the beam and the standard reduction sequence requires
  environment-specific masking, notching, or background handling.
version: 2
review:
  status: human-reviewed
  reviewer: Malcolm Guthrie
  reviewed_on: 2026-05-05
  basis: [docs, code, instrument-science-review]
  notes: >
    v2: preserved core PE/DAC/cylinder technical content and updated process
    sequencing so branch-support artifacts are gathered within the branch step
    before execution. Explicitly called out artifact acquisition/generation for
    PE pixel masks and DAC wavelength-notch bin masks.
  approved_commit: review/sns-snap-sample-environment-reduction-special-cases-v2
  prior_review:
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
  instruments: [SNAP]
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

## Overview

This skill guides SNAP powder-diffraction reduction when a high-pressure sample
environment changes the standard reduction path. Use it together with
[sns-snap-reduction-workflow-overview](../sns-snap-reduction-workflow-overview/SKILL.md):
that skill gives the baseline sequence, and this skill defines the branches for
Paris-Edinburgh cells, diamond anvil cells, and cylinder cells.

SNAP is primarily a high-pressure powder diffractometer, so many measurements
include beam attenuation, detector occlusion, and background features that are
not present in open-geometry reduction. Each environment class requires its own
masking, background, and downstream-analysis decisions.

### Provenance

- **snapwrap**: hosts masking utilities under `snapwrap.maskUtils`, provides
  `swissCheese` objects for combined pixel and bin masks, passes mask inputs via
  `reduce(..., binMaskList=...)` and `reduce(..., pixelMask=...)`, communicates
  environment context through reduction hooks, and provides `SEEMeta`
  extraction tools.
- **snapred**: applies the prepared environment-specific masking and binning
  decisions during reduction orchestration; output-label logic remains driven by
  calibration completeness, not environment class.
- **Mantid**: executes the masking, focusing, binning, and unit-conversion
  algorithms underneath the reduction workflow.

### Evidence

- Domain notes baseline (2026-04-30): instrument-scientist notes from Malcolm
  Guthrie covering PE, DAC, and cylinder-cell device characteristics,
  reduction impacts, and current solution status.

---

## When to Use

Use this skill when:

- `SEEMeta` or run documentation indicates `assembly.pe`, `assembly.dac`, or a
  cylinder-cell variant.
- The standard SNAP reduction workflow needs environment-specific pixel masks,
  wavelength notching, attenuation correction, or nonstandard background
  handling.
- You need to decide whether artifacts should be handled during reduction or
  deferred to analysis.

Do **not** use this skill when:

- The experiment is an open-geometry reduction case with no sample-environment
  driven masking or attenuation problems.
- You are deciding calibration validity; use
  [sns-snap-calibration-and-geometry](../sns-snap-calibration-and-geometry/SKILL.md)
  for calibration state controls.
- You need full failure-mode escalation after reduction; use
  [sns-snap-reduction-diagnostics](../sns-snap-reduction-diagnostics/SKILL.md).

### Required context before starting

- Assembly type from `SEEMeta`: `assembly.pe`, `assembly.dac`, or cylinder
  variant, plus nickname/model/comment when available.
- `SEEMeta` lookup order in `snapwrap`: (1) IPTS override file
  `/IPTS-{ipts}/shared/SEE/SEE{runNumber}.json`, then (2) embedded run-log JSON.
  If neither source is available, fall back to manual identification.
- Whether an environment-specific pixel mask already exists and is current.
- Whether wavelength-specific bin masks are required or can be reused.
- Grouping scheme in use. For DAC data, column grouping can create serious
  angular-coverage and d-range gaps after notching.
- Current calibration status. Environment handling changes masking and
  background work, but not calibration requirements.

---

## Process

1. **Identify the environment class before reduction** — Determine whether the
   run uses a PE cell, DAC, or cylinder cell. Prefer `SEEMeta`; if that is
   missing, use run documentation or manual instrument records. Record the
   environment class and evidence source in reduction notes.

   **[CHECKPOINT]**: The assembly type is known and documented.

2. **Load the baseline reduction path first** — Start from
   [sns-snap-reduction-workflow-overview](../sns-snap-reduction-workflow-overview/SKILL.md)
   and keep its calibration and output-label logic intact. This skill only adds
   the environment-specific branches.

3. **Apply the correct environment branch and gather branch-support artifacts**
  — Use the branch that matches the identified device class, and assemble all
  required reduction inputs before execution.

  Branch-support artifacts can include masks, correction workspaces, and
  background references. Use the snapwrap masking layer as the primary
  integration point for mask objects, and prepare any additional branch-specific
  inputs needed by the reduction call.

  | Artifact/component | Role |
  |--------------------|------|
  | `snapwrap.maskUtils.swissCheese` | Manages combined pixel and bin mask objects and can construct masks in several ways (including from diamond UB matrix pairs or workspace history). |
  | `reduce(..., binMaskList=...)` | Accepts one or more bin masks in TOF, wavelength, Q, or d-spacing. |
  | `reduce(..., pixelMask=...)` | Accepts a pixel mask for environment occlusion. |
  | Attenuation correction workspace | Encodes wavelength-dependent attenuation behavior when branch physics requires correction (for example cylinder-cell workflows). |
  | Empty-cell/background workspace | Supplies environment/container background subtraction inputs when valid for the pressure state. |
  | Reduction hooks | Passes environment-specific parameters into snapred orchestration. |

   ### Paris-Edinburgh (PE) branch

   Device facts:

   - Hydraulically driven opposed-anvil press with approximately spherical
     3-6 mm samples.
   - TiZr gasket provides lateral containment.
   - Common anvil materials: sintered diamond, zirconium-toughened alumina,
     tungsten carbide.
   - Pressure up to about 20 GPa; low-temperature operation down to about 10 K.

   Reduction impacts:

   | Impact | Description |
   |--------|-------------|
   | Pixel occlusion | Large detector regions are shadowed by the anvil body and require a geometry-specific pixel mask. |
   | Beam attenuation | Incident beam is attenuated primarily by the TiZr gasket. |
   | Background | TiZr contributes smooth background; sharp background structure usually points to anvil material instead. |
   | Anvil scattering | SD, ZTA, and WC produce different background behavior; WC is the most scattering-intensive. |

   Required actions:

   - Acquire or generate a PE-specific pixel-mask artifact that matches the
     current geometry and pressure-cell configuration.
   - Apply that PE-specific pixel mask for occluded or contaminated detector
     regions.
   - Treat the TiZr gasket as a smooth background contributor.
   - If sharp background structure appears, verify anvil material assignment.

   Known limitation:

   - Attenuation corrections for gasket and anvils are not yet implemented in
     snapred. Quantitative attenuation treatment must be handled later if
     required.

   Analysis carryover:

   - PE anvil materials can contribute powder Bragg peaks to reduced data; these
     are handled during analysis, not by masking/notching.

   ### Diamond anvil cell (DAC) branch

   Device facts:

   - Opposed single-crystal diamond anvils with 0.8-1.6 mm culets.
   - Metallic gasket typically tungsten, rhenium, or steel.
   - Pressure can exceed 100 GPa; low-temperature operation down to about 10 K.

   Reduction impacts:

   | Impact | Description |
   |--------|-------------|
   | Diamond Bragg scattering | Produces localized spots, diffuse scattering, and multiple scattering from the diamonds. |
   | Structured beam attenuation | Bragg-condition wavelengths are removed from the transmitted beam, creating sharp wavelength dips. |
   | d-coverage gaps | Wavelength removal creates d-spacing gaps, especially for narrow-angle groupings such as columns. |
   | Complex resolution function | Notching creates a nonstandard effective resolution function currently supported quantitatively only in GSAS-II. |

   Primary mitigation:

   - Acquire or generate a wavelength-notch bin-mask artifact for the current
     DAC geometry/orientation state.
   - Use wavelength notching with that bin-mask artifact as the first-line
     correction.
   - Confirm the chosen grouping preserves acceptable d-range after notch
     removal.
   - Confirm the downstream analysis code can tolerate nonuniform wavelength
     coverage; for quantitative Rietveld work this currently means GSAS-II.

   Notch-generation pathways:

   - **Transmission inspection**: identify notch wavelengths from dips in the
     transmitted beam spectrum and construct the corresponding notch bin-mask
     artifact.
   - **UB matrix calculation**: fit the orientation of both diamonds and use
     `snapwrap.maskUtils.swissCheese` to calculate notch bin-mask artifacts
     from the diamond UB matrices.

   Supplementary action:

   - Add manual bin masking when notching alone leaves artifact regions.
   - Typical workflow: convert to the desired unit, inspect in MantidWorkbench
     `ShowInstrument`, mark artifact regions, extract a `swissCheese` object via
     `ExtractFromWorkspaceHistory`, then combine it with notch masks.

   Known limitations:

   - Both notch-generation pathways remain semi-manual.
   - Analysis codes other than GSAS-II may require exclusion of notched regions
     or special handling.

   Analysis carryover:

   - DAC gasket peaks and DAC-collimator scattering can survive reduction and
     must be treated explicitly during analysis.

   ### Cylinder-cell branch

   Device facts:

   - Includes both gas cylinders and piston-cylinder devices.
   - Pressure up to about 2 GPa; often used at cryogenic temperatures.

   Reduction impacts:

   | Impact | Description |
   |--------|-------------|
   | Beam attenuation | Cylinder walls attenuate both incident and diffracted beams. |
   | Bragg-edge attenuation structure | Cylinder material introduces wavelength-dependent attenuation that must be modeled, not simply masked. |
   | Background | Cylinder-body background must be subtracted or otherwise modeled. |

   Required actions:

   - Apply attenuation correction with cylinder geometry and material included.
   - Use empty-cell background subtraction when valid.
   - At higher pressures, reassess empty-cell validity because the cell itself
     deforms under load.

   Known limitation:

   - Robust background treatment for pressure-deformed cylinder geometry is
     still active R&D and is not yet a standard workflow.

   Analysis carryover:

   - Cylinder-cell scattering may remain in reduced data and must be handled in
     analysis with explicit container/background terms.

4. **Run reduction with the prepared branch artifacts and note the limitations**
  — Pass the selected branch input artifacts into `reduce` (for example pixel masks,
  and branch-specific correction/background workspaces), record
  why each artifact exists, and explicitly write down anything the current
  workflow does not correct (for example unimplemented attenuation treatment or
  manual notch bounds).

5. **Check quality gates before accepting the output** — Confirm:

   - Pixel masks cover all occluded or contaminated detector regions.
   - For DAC data, notch positions are confirmed against UB matrices or observed
     transmission dips, and remaining coverage is acceptable.
   - For cylinder data, attenuation correction and background subtraction are
     justified for the pressure state.
   - Output label is `reduced` or `diagnostic` for calibration reasons only;
     sample environment does not alter output-label logic.
   - GSAS-II compatibility is confirmed before attempting quantitative analysis
     of notched DAC data.

6. **Hand off explicit analysis-stage warnings** — Record what artifacts may
   remain after reduction so the analysis stage does not treat them as sample
   signal by mistake.

**Exit criteria**: The reduction sequence is adapted to the identified sample
environment, required branch-support artifacts are prepared and supplied to
`reduce`, mask/correction/background choices are documented, unresolved
corrections are recorded, and post-reduction analysis warnings are explicitly
handed off.

---

## Rationalizations

| Excuse | Rebuttal |
|--------|----------|
| "The standard reduction path is probably fine even with a pressure cell." | Sample-environment effects are the point of failure here: occlusion, attenuation, and container/background artifacts are environment-specific. Running the baseline path without the environment branch produces misleading outputs, not just slightly imperfect ones. |
| "I can ignore `SEEMeta` and infer the environment later from the plot." | Environment identification controls mask choice and notching strategy up front. Deferring identification turns a deterministic branch decision into guesswork after artifacts are already baked into the reduction. |
| "DAC notching is too much work; I will just live with the artifacts." | For DAC data the structured wavelength loss changes both artifact content and usable d-range. Skipping notching means the reduction is knowingly wrong in a way that downstream fitting may misinterpret as sample physics. |
| "Any analysis code can handle notched DAC data." | The effective resolution function after wavelength notching is not generally supported. Quantitative DAC Rietveld analysis currently requires GSAS-II unless the notched regions are excluded deliberately. |
| "Empty-cell subtraction is always good enough for cylinder cells." | At higher pressure the container itself changes under load, so the empty-cell measurement may no longer represent the actual background. Blind subtraction can create structured residuals that look like sample features. |

---

## Red Flags

- Large regions of zero or near-zero counts in a PE detector image after masking
  changes: PE pixel-mask coverage may be shifted or incomplete.
- Sharp structured background in a PE reduction where only smooth TiZr-like
  behavior was expected: check anvil material identification.
- Sharp-edged d-coverage gaps in DAC reductions: notching is active; verify the
  remaining coverage is acceptable for the chosen grouping.
- Residual DAC background at diamond d-spacings after notching: UB matrices or
  manual mask extent may be wrong.
- Unexpected profile mismatch when analyzing notched DAC data outside GSAS-II:
  downstream resolution modeling is likely invalid.
- Structured residuals at cylinder material d-spacings: container background or
  Bragg-edge attenuation correction is inadequate.
- Systematic mismatch between high-pressure cylinder data and empty-cell
  subtraction: the pressure-loaded container no longer matches the empty-cell
  reference.

---

## Verification

- [ ] Environment class is identified and documented from `SEEMeta` or a clear
      manual source.
- [ ] The baseline reduction workflow was used and only environment-specific
      branches were altered.
- [ ] Required branch-support artifacts are prepared and passed to `reduce`
  (for example pixel masks, bin masks, attenuation corrections, and
  background references as applicable).
- [ ] Every prepared artifact has a recorded rationale and unit convention or
  usage basis.
- [ ] PE runs: pixel-occlusion handling is applied and any missing attenuation
      treatment is called out explicitly.
- [ ] DAC runs: the notch bin-mask artifact is acquired/generated from
  transmission dips or diamond UB matrices, and d-range coverage after
  notching is acceptable.
- [ ] Cylinder runs: attenuation correction and background strategy are justified
      for the current pressure state.
- [ ] Output label (`reduced` or `diagnostic`) is explained by calibration state,
      not by environment choice.
- [ ] Remaining analysis-stage artifacts are explicitly handed off in notes.
- [ ] Known workflow limitations and post-reduction obligations are documented.
