---
name: sns-snapwrap-developer-guide
description: >
  Rapidly orient a developer or coding agent to the SNAPWrap architecture,
  module inventory, and scripting conventions. Use when writing reduction
  scripts, integrating SNAPWrap with SNAPRed, working with sample-environment
  masking utilities, or building tooling that consumes the SNAPWrap API.
version: 2
review:
  status: human-reviewed
  reviewer: Malcolm Guthrie
  reviewed_on: 2026-05-07
  basis: [docs, code, instrument-science-review]
  notes: >
    v2: Developer guidance with technical accuracy corrections for cleanTheTree
    behavior (actual copies, not aliases; timestamped originals retained in
    tree), bin-mask naming contract (strictly {prefix}-{units} format with full
    Mantid unit names), artifact responsibility boundaries (when/why in
    special-cases skill, how in snapwrap), and SNAPWrap vs SNAPRed config layer
    separation (SNAPWrap has own application.yml; queries SNAPRed through
    interface; no YAML override support in SNAPWrap). Hook lifecycle names
    clarified and referenced to sns-snapred-developer-guide.
  approved_commit: review/sns-snapwrap-developer-guide-v2
  prior_review:
    status: human-reviewed
    reviewer: Malcolm Guthrie
    reviewed_on: 2026-04-30
    basis: [docs, code, instrument-science-review]
    notes: Reviewed against current SNAPWrap behavior and naming conventions.
    approved_commit: review/sns-snapwrap-developer-guide-v1
metadata:
  facility: SNS
  beamline: BL3
  instruments: [SNAP]
  software: [snapwrap, snapred, Mantid]
  data_phase: reduction
  techniques: [diffraction, powder-diffraction, time-of-flight]
  tags:
    - developer
    - architecture
    - snapwrap
    - reduce
    - binMaskList
    - pixelMask
    - swissCheese
    - SEEMeta
    - hooks
    - calibration
    - reduction
    - scripting
    - api
---

# SNAPWrap Developer Guide

## Overview

SNAPWrap is the primary user-facing Python layer for SNAP reduction. Most users
write Mantid Workbench scripts that import SNAPWrap directly; SNAPRed is the
backend engine SNAPWrap prepares requests for and calls.

Repository: https://github.com/neutrons/SNAPWrap
Manual: https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html

### Evidence

- Codebase exploration (2026-04-30) against `/Users/66j/Documents/ORNL/code/SNAPWrap`
  verified module inventory, `reduce()` flow, `swissCheese` integration,
  `SEEMeta` extraction, and SNAPRed request wiring.

### Architecture sketch

```text
User script (Mantid Workbench)
    -> snapwrap.utils.reduce(runNumber, ...)
         -> snapwrap.snapStateMgr
         -> snapwrap.maskUtils
         -> snapwrap.SEEMeta
         -> snapwrap.io
         -> SNAPRed InterfaceController.executeRequest(SNAPRequest)
```

SNAPWrap owns configuration, calibration lookup, mask preparation, hook
assembly, and output handling. SNAPRed owns the actual reduction computation.

---

## When to Use

Use this skill when:

- Writing or reviewing SNAP reduction scripts that call `snapwrap`.
- Integrating sample-environment masking, `SEEMeta`, or calibration checks into
  a user-facing workflow.
- Debugging how SNAPWrap assembles a reduction request before it reaches
  SNAPRed.
- Building tooling that needs to parse SNAPWrap outputs or interact with its
  module surface.

Do **not** use this skill when:

- You need the backend architecture inside SNAPRed rather than the wrapper
  layer.
- You are looking for scientific reduction decisions rather than wrapper/API
  structure.

---

## Process

1. **Start from the library-first mental model** — SNAPWrap is imported from
   scripts, usually inside Mantid Workbench. It is not the place to duplicate
   reduction algorithms.

   Developer conventions:

   - Treat SNAPWrap as a library, not a standalone CLI.
   - Assume Mantid algorithms and workspace APIs are available.
   - Keep reduction computation in SNAPRed, not in SNAPWrap.
   - Treat the calibration index as the source of truth.

2. **Use `reduce()` as the primary integration surface** — Most user workflows
   should pass through `snapwrap.utils.reduce()`.

   ```python
   from snapwrap.utils import reduce

   workspace_names = reduce(
       runNumber,
       binMaskList=[],
       pixelMaskIndex='none',
       continueNoDifcal=False,
       continueNoVan=False,
       noNorm=False,
       requireSameCycle=True,
       focusGroupAllowList=None,
       keepUnfocussed=False,
       qsp=False,
       linBin=0.01,
       save=True,
       backgroundWSName=None,
       attenuationWSName=None,
       cisMode=False,
       emptyTrash=True,
       YMLOverride='none',
       verbose=False,
       reduceData=True,
   )
   ```

   Internal data flow:

   ```text
   reduce(runNumber)
     1. Load YAML defaults (globalParams / YMLOverride)
     2. Check difcal and normcal status via snapStateMgr
     3. Apply continue-flag policy
     4. Build requested hooks (background/attenuation, cheeseMask)
     5. Assemble ReductionRequest
     6. Call InterfaceController.executeRequest(SNAPRequest)
     7. Return workspace names
   ```

   **[CHECKPOINT]**: If you are extending a user-facing reduction path, you can
   point to the `reduce()` call and explain which arguments or hooks you are
   changing.

3. **Handle output names through SNAPWrap helpers instead of string guessing**
   — SNAPRed workspace names are timestamped internally. When `cleanTheTree` is
   enabled, SNAPWrap creates copies with clean names (no timestamps) and hides
   the originals, but the timestamped workspaces remain in the tree and can be
   re-exposed if needed.

   Timestamped internal naming pattern:

   ```text
   {prefix}_{unit}_{pixelGroup}_{runNumber}_{timestamp}
   ```

   Clean-tree displayed pattern when `cleanTheTree` is enabled:

   ```text
   {prefix}_{unit}_{pixelGroup}_{runNumber}
   ```

   Use `snapwrap.io.redObject` to parse names programmatically.

   | Prefix | Meaning |
   |--------|---------|
   | `reduced_` | Full calibration path succeeded |
   | `diagnostic_` | Approximation path used because calibration was missing |

4. **Use `binMaskList` and `swissCheese` through the naming contract** — Bin
   masks are table workspaces applied by the `cheeseMask` hook during
   `PostPreprocessReductionRecipe`. Masks are reduction artifacts governed by
   [sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md).

   Required naming format:

   - Workspace names must follow exactly: `{prefix}-{units}`
   - Two parts only, separated by a single hyphen.
   - The part after the hyphen must be the Mantid unit name (`Wavelength`, 
     `dSpacing`, `TOF`, `Energy`, etc.).
   - Nothing can follow the units; the units must be the final part.
   - Unit suffixes must match Mantid unit naming exactly (no abbreviations like 
     `wav` or `dsp`).
   - Multiple masks in different units can be supplied in one `binMaskList`.

   Typical usage:

   ```python
   reduce(runNumber, binMaskList=['DAC_notch-Wavelength', 'PE_occlusion-dSpacing'])
   ```

   SNAPWrap code for artifact construction (see
   [sns-snap-sample-environment-reduction-special-cases](../sns-snap-sample-environment-reduction-special-cases/SKILL.md)
   for when and why to create each artifact type):

   - DAC notch bin-mask artifacts: use `snapwrap.maskUtils` with diamond UB
     matrices.
   - Manual bin-mask artifacts extracted from workspace history: use
     `swissCheese.ExtractFromWorkspaceHistory(...)`.

5. **Resolve calibration state through `snapStateMgr`, not hardcoded paths**
   — Use `checkCalibrationStatus()` to determine whether the run and state have
   valid `difcal` or `normcal` coverage.

   ```python
   from snapwrap.snapStateMgr import checkCalibrationStatus

   status = checkCalibrationStatus(
       runNumber,
       stateID=None,
       isLite=True,
       calType="difcal",
       requireSameCycle=True,
   )
   ```

   Important outputs:

   - `runIsCalibrated`
   - `stateIsCalibrated`
   - `latestValidCalibrationDict`
   - `statusDetail`

   The calibration index maps runs to calibration records through `appliesTo`,
   and `requireSameCycle=True` further restricts matches to the same SNS cycle.

6. **Use `SEEMeta` to branch sample-environment behavior early** — SNAPWrap can
   extract assembly metadata from an override JSON file or embedded run logs.

   Lookup priority:

   1. `/IPTS-{ipts}/shared/SEE/SEE{runNumber}.json`
   2. Embedded NeXus log `entry/DASlogs/BL3:SE:SEEMeta:JSON/value`
   3. `None` if absent

   Assembly classes include `DAC`, `PE`, `CylinderCell`, and `Empty`. Use the
   extracted assembly type to decide whether to apply DAC notching, PE pixel
   masks, or other environment-specific branches before calling `reduce()`.

7. **Attach custom behavior through hooks only at valid SNAPRed lifecycle
   points** — SNAPWrap passes `Hook` objects into `SNAPRequest`, and SNAPRed's
   `HookManager` executes them. Lifecycle names are recipe steps in SNAPRed's
   reduction engine (e.g., `PostPreprocessReductionRecipe`).

   Built-in hooks assembled by `reduce()`:

   - `BackgroundAttenuationCorrection`
   - `cheeseMask`

   If you add new hooks, verify the lifecycle name against SNAPRed's recipe
   lifecycle documentation (see `sns-snapred-developer-guide`) and remember
   that all registered hooks must execute successfully.

8. **Use the module surface intentionally** — Reach for the right module rather
   than adding ad hoc helpers.

   | Import | Key exports | When to use |
   |--------|------------|-------------|
   | `snapwrap.utils` | `reduce()`, `globalParams()`, `propagateDifcal()` | Main reduction scripts |
   | `snapwrap.io` | `redObject`, `exportData()` | Workspace parsing and export |
   | `snapwrap.snapStateMgr` | `checkCalibrationStatus()`, `SNAPHome` | Calibration queries |
   | `snapwrap.maskUtils` | Swiss cheese utilities, pixel-mask tools | DAC/PE masking |
   | `snapwrap.SEEMeta.utils` | `acquireMeta()` | Assembly metadata extraction |
   | `snapwrap.SEEMeta.assembly` | `DAC`, `PE`, `CylinderCell`, `Empty` | Assembly objects |
   | `snapwrap.cycleDates` | `get_cycle_for_run()` | Cycle-aware logic |
   | `snapwrap.wrapConfig` | `WrapConfig` | Runtime config loading |

9. **Load configuration through the YAML config layer** — SNAPWrap uses its
   own `application.yml` for runtime configuration. For access to SNAPRed
   configuration (such as `instrument.calibration.home`), SNAPWrap queries
   SNAPRed's `application.yml` through the SNAPRed interface.

   ```python
   from snapwrap.wrapConfig import WrapConfig
   WrapConfig.load()
   # SNAPWrap-level config example
   seeJsonHome = WrapConfig.get("SEE.json.home")
   ```

   For local testing outside the SNS Analysis Cluster, SNAPWrap relies on
   environment setup or direct file paths; SNAPWrap config does not support
   YAML override files (SNAPRed config does). Check SNAPWrap documentation for
   local development setup options.

**Exit criteria**: You can explain how a SNAPWrap script flows through
`reduce()`, where calibration and sample-environment decisions are injected,
which helper modules own the relevant behavior, and which parts of the request
belong to SNAPWrap versus SNAPRed.

---

## Rationalizations

| Excuse | Rebuttal |
|--------|----------|
| "I can just implement the reduction logic directly in SNAPWrap for convenience." | SNAPWrap is a wrapper and orchestration layer. Re-implementing backend reduction logic there creates divergence from SNAPRed and breaks the architecture boundary the rest of the system relies on. |
| "I can parse workspace names with my own string split." | SNAPWrap already has `redObject`, and the visible name may differ from the timestamped underlying name. Guessing the format is brittle and unnecessary. |
| "Mask workspaces do not need strict unit naming." | `binMaskList` parsing depends on the workspace name because the workspace itself does not carry a reliable unit attribute. If the suffix is wrong, the mask can be misapplied or rejected. |
| "Hardcoding calibration paths is faster than using the state manager." | Calibration resolution is state- and cycle-dependent. Hardcoded paths bypass the real source of truth and are exactly how stale or invalid calibrations get used accidentally. |
| "SEEMeta is optional, so I can ignore it for automation." | `SEEMeta` is the intended pathway for environment-aware reduction branching. Ignoring it forces manual branching logic where the wrapper is already designed to carry the metadata. |

---

## Red Flags

- New code duplicates reduction algorithms that belong in SNAPRed.
- A script manipulates timestamped workspace names by hand instead of using
  `redObject` or SNAPWrap helpers.
- `binMaskList` masks have ambiguous or non-Mantid unit suffixes.
- Calibration file paths are hardcoded instead of resolved via
  `checkCalibrationStatus()` or the SNAPRed data layer.
- Hooks are attached to lifecycle names not documented in sns-snapred-developer-guide.
- Environment-specific behavior is added without consulting `SEEMeta`.
- Local testing relies on environment assumptions but does not define an
  `override.yml` or equivalent configuration path.

---

## Verification

- [ ] The workflow entry point is clearly a SNAPWrap library call, usually
      `snapwrap.utils.reduce()`.
- [ ] The developer can explain which work stays in SNAPWrap and which is owned
      by SNAPRed.
- [ ] Output-name handling uses `redObject` or existing I/O helpers rather than
      custom parsing.
- [ ] Any `binMaskList` workspace names follow the required unit-naming
      contract.
- [ ] Calibration status is resolved through `checkCalibrationStatus()` or the
      SNAPRed data layer.
- [ ] `SEEMeta` lookup and assembly typing are used when sample-environment
      branching is required.
- [ ] New hook lifecycle names are verified against sns-snapred-developer-guide.
- [ ] Configuration is loaded through `WrapConfig` and override behavior is
      documented for local testing.

Cross-references:

- SNAPRed backend architecture: `sns-snapred-developer-guide`
- Reduction workflow: `sns-snap-reduction-workflow-overview`
- Sample-environment masking: `sns-snap-sample-environment-reduction-special-cases`
- Calibration state controls: `sns-snap-calibration-and-geometry`
