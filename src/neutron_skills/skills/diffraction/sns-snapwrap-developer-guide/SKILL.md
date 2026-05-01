---
name: sns-snapwrap-developer-guide
description: >
  Rapidly orient a developer or coding agent to the SNAPWrap architecture,
  module inventory, and scripting conventions. Use when writing reduction
  scripts, integrating SNAPWrap with SNAPRed, working with sample-environment
  masking utilities, or building tooling that consumes the SNAPWrap API.
version: 1
review:
  status: human-reviewed
  reviewer: Malcolm Guthrie
  reviewed_on: 2026-04-30
  basis: [docs, code, instrument-science-review]
  notes: Reviewed against current SNAPWrap behavior and naming conventions.
  approved_commit: review/sns-snapwrap-developer-guide-v1
metadata:
  facility: SNS
  beamline: BL3
  instruments: [SNAP, SNS]
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

SNAPWrap is a Python wrapper application that provides the primary user-facing
interface to the SNAPRed backend. Most SNAP users interact exclusively with
SNAPWrap scripts; SNAPRed is the engine they never see directly.

Repository: https://github.com/neutrons/SNAPWrap  
Manual: https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html  
SNAPRed backend guide: see `sns-snapred-developer-guide` skill.

---

## Evidence tracking

**Codebase exploration** (2026-04-30):
- Source: `/Users/66j/Documents/ORNL/code/SNAPWrap`
- Verified: module inventory, `reduce()` signature and data flow, `swissCheese`
  hook implementation, SEEMeta assembly extraction, SNAPRed integration points.

---

## Architecture overview

SNAPWrap is a **library-first** wrapper. Users write Python scripts (typically run inside
Mantid Workbench) that import and call SNAPWrap functions directly. There is no
dedicated shell CLI — the `snapwrap` command launches Mantid Workbench with
SNAPWrap installed.

```
User script (Mantid Workbench)
    └── snapwrap.utils.reduce(runNumber, ...)
            ├── snapwrap.snapStateMgr  — calibration status lookup
            ├── snapwrap.maskUtils     — pixel and bin mask utilities
            ├── snapwrap.SEEMeta       — sample environment assembly metadata
            ├── snapwrap.io            — workspace I/O and export
            └── SNAPRed InterfaceController.executeRequest(SNAPRequest)
```

SNAPWrap handles: configuration, calibration state lookup, mask preparation,
hook assembly, and result export. SNAPRed handles: all actual computation.

See `assets/snapwrap-module-inventory.md` in this skill directory for the
complete module and function reference.

---

## Primary entry point: `reduce()`

```python
from snapwrap.utils import reduce

workspace_names = reduce(
    runNumber,
    # --- Mask inputs ---
    binMaskList=[],           # list of bin-mask workspace names (Swiss cheese)
    pixelMaskIndex='none',    # int or list of ints: user pixel mask indices
    # --- Calibration policy ---
    continueNoDifcal=False,   # proceed without difcal → diagnostic output
    continueNoVan=False,      # proceed without normcal → artificial normalization
    noNorm=False,             # skip normalization entirely
    requireSameCycle=True,    # only use calibrations from the same SNS cycle
    # --- Grouping and output ---
    focusGroupAllowList=None, # list of group names to include (None = all), subset of default groups for the state
    keepUnfocussed=False,     # retain unfocused workspace in Mantid
    qsp=False,                # output in Q-space instead of d-spacing
    linBin=0.01,              # linear bin size for Q-space output
    save=True,                # write reduced data to disk
    # --- Advanced ---
    backgroundWSName=None,    # workspace name for background subtraction hook
    attenuationWSName=None,   # workspace name for attenuation correction hook
    cisMode=False,            # CIS mode: preserve diagnostic intermediate workspaces
    emptyTrash=True,          # clean up temporary workspaces after reduction
    YMLOverride='none',       # path to YAML override for reduction parameters
    verbose=False,
    reduceData=True,
)
# Returns: list[str] of reduced workspace names and the name of a pixel mask workspace if used, or [] on failure
```

### Internal data flow

```
reduce(runNumber)
  1. Load YAML defaults (globalParams / YMLOverride)
  2. Check difcal and normcal status → snapStateMgr.checkCalibrationStatus()
  3. Apply continue flags if calibrations missing
  4. Build Hook objects (if requested):
       PostPreprocessReductionRecipe → BackgroundAttenuationCorrection (if background/attenuation provided)
       PostPreprocessReductionRecipe → cheeseMask (if binMaskList non-empty)
  5. Assemble ReductionRequest (SNAPRed DAO)
  6. Call InterfaceController.executeRequest(SNAPRequest(path="/reduction", ...))
  7. Return list of workspace names
```

---

## Output workspace naming

SNAPRed-generated workspace names follow the pattern:
```
{prefix}_{unit}_{pixelGroup}_{runNumber}_{timestamp}
```

In current SNAPWrap behavior, `cleanTheTree` is enabled by default. It hides
the timestamped workspace names in the Mantid tree and exposes a copy of the
latest workspace with the timestamp removed.

Displayed default names therefore follow:
```
{prefix}_{unit}_{pixelGroup}_{runNumber}
```

| Prefix | Meaning |
|--------|---------|
| `reduced_` | Full calibration (difcal + normcal) present |
| `diagnostic_` | Missing calibration; approximation used |

Examples:
```
reduced_dsp_all_064413                 ← displayed (default clean tree)
reduced_dsp_bank_064413                ← displayed (default clean tree)
reduced_dsp_column_064413              ← displayed (default clean tree)
reduced_dsp_all_064413_2025-11-17T154047     ← hidden timestamped source
dsp_unfoc_lite_064413          ← unfocused; keepUnfocussed=True
```

Units: `dsp` = d-spacing (default), `qsp` = momentum transfer (qsp=True).  
pixelGroups: `all`, `bank`, `column`, or user-defined group names.

Use `snapwrap.io.redObject` to parse workspace names programmatically:
```python
from snapwrap.io import redObject
obj = redObject('reduced_dsp_column_064413_2025-11-17T154047')
print(obj.runNumber, obj.pixelGroup, obj.units, obj.timestamp)
```

---

## Bin masking: Swiss cheese / `binMaskList`

Bin masking removes specific wavelength (or d-spacing, Q, TOF) ranges from the
data before reduction. The primary use case is DAC experiments where diamond
Bragg scattering contaminates specific wavelength bands (see
`sns-snap-sample-environment-reduction-special-cases` skill for full context).

**Mechanism**: bin masks are Mantid table workspaces. SNAPWrap assembles them
into a `cheeseMask` hook (`HookCollection.cheeseMask`) that calls
`MaskBinsFromTable` during the `PostPreprocessReductionRecipe` lifecycle point.

**Naming contract (required)**: mask workspace names are parsed to infer units
because the mask workspace itself does not carry a reliable unit attribute.
Names must be of the form:
`{prefix}_{units}`
where `{prefix}` is arbitrary and `{units}` must exactly match Mantid
unit naming (case-sensitive), for example `Wavelength` or `dSpacing`.
If units in the name do not match Mantid conventions exactly, the mask may be
applied in the wrong unit context or rejected by downstream logic.

```python
# Typical usage
reduce(runNumber, binMaskList=['mask_dsp_DAC_forbidden_range', 'mask_wav_notch_diamond'])
```

Multiple masks in different units can be supplied simultaneously; the hook
applies them in order. The workspace name encodes the unit
(`*_dSpacing` → d-spacing, `*_Wavelength` → wavelength, etc.).

**Creating Swiss cheese masks via UB matrix** (DAC notching):
- Use `snapwrap.maskUtils` utilities and the `swissCheese` / Swiss cheese
  class methods to compute notch positions from diamond UB matrices.
- See `assets/snapwrap-module-inventory.md` for the full `maskUtils` API.

**Extracting a mask from workspace history** (manual bin masking):
```python
# After manually masking bins in MantidWorkbench:
mask_ws = swissCheese.ExtractFromWorkspaceHistory(ws_name)
# Then pass the resulting workspace name to reduce()
reduce(runNumber, binMaskList=[mask_ws])
```

---

## Calibration state lookup

```python
from snapwrap.snapStateMgr import checkCalibrationStatus

status = checkCalibrationStatus(
    runNumber,
    stateID=None,          # auto-derived if None
    isLite=True,
    calType="difcal",      # or "normcal"
    requireSameCycle=True,
)
# Key fields:
status['runIsCalibrated']          # bool
status['stateIsCalibrated']        # bool
status['latestValidCalibrationDict']  # dict with calibration record
status['statusDetail']             # human-readable reason if not calibrated
```

Calibration data lives at:
```
{calibration.powder.home}/{stateId}/lite|native/diffraction/v{version}/
```
The Calibration Index (`CalibrationIndex.json`) maps run numbers to
calibration records via the `appliesTo` constraint. `requireSameCycle=True`
(the default) additionally restricts matches to calibrations from the same
SNS operating cycle.

---

## SEEMeta: sample environment assembly metadata

SEEMeta embeds sample-environment assembly information in run logs as a JSON
dictionary. SNAPWrap provides tools to extract and use this data.

SEEMeta is still being built out, but it is a core SNAP strategy for
automating sample-environment (SEE) aware reduction operations.

**Extraction:**
```python
from snapwrap.SEEMeta.utils import acquireMeta

meta = acquireMeta(runNumber)
# Returns dict with assembly type, components, material, orientation, nickname
```

**Lookup priority:**
1. Override JSON file at `/IPTS-{ipts}/shared/SEE/SEE{runNumber}.json`
2. Embedded in NeXus HDF5 at `entry/DASlogs/BL3:SE:SEEMeta:JSON/value`
3. Not present → returns None (fall back to manual identification)

**Assembly classes** (`snapwrap.SEEMeta.assembly`):

| Class | Assembly type | SEEMeta `type` value |
|-------|--------------|----------------------|
| `DAC` | Diamond Anvil Cell | `assembly.dac` |
| `PE` | Paris-Edinburgh / opposed anvil | `assembly.pe` |
| `CylinderCell` | Gas or piston-cylinder cell | `assembly.cylinder` |
| `Empty` | No sample environment | `assembly.empty` |

Each Assembly contains a `components` list of typed `Component` objects
(anvils, gaskets, cylinders) with material information from the SQLite
materials database (`SEEMeta.material`).

**Using assembly type in a script:**
```python
meta = acquireMeta(runNumber)
if meta and meta.get('type') == 'assembly.dac':
    # Apply DAC-specific masking
    reduce(runNumber, binMaskList=dac_notch_masks)
elif meta and meta.get('type') == 'assembly.pe':
    # Apply PE pixel mask
    reduce(runNumber, pixelMaskIndex=pe_mask_index)
```

---

## Hook system

SNAPWrap injects custom processing into the SNAPRed reduction lifecycle via
`Hook` objects attached to a `SNAPRequest`.

```python
from snapred.backend.dao.Hook import Hook

hook = Hook(
    func=my_callback_function,
    kwarg1=value1,
    kwarg2=value2,
)
hooks = {"PostPreprocessReductionRecipe": [hook]}
```

SNAPRed's `HookManager` executes all registered hooks at the named lifecycle
point. All registered hooks must execute; failing to run any raises
`ValueError`.

Built-in SNAPWrap hooks (assembled automatically by `reduce()`):
- `BackgroundAttenuationCorrection` — applies background subtraction and
  attenuation correction when `backgroundWSName` / `attenuationWSName` provided.
- `cheeseMask` — applies bin masking from `binMaskList` via `MaskBinsFromTable`.

---

## Module quick reference

Full details in `assets/snapwrap-module-inventory.md`.
This table is intentionally non-exhaustive; use the asset for complete
module coverage.

| Import | Key exports | When to use |
|--------|------------|-------------|
| `snapwrap.utils` | `reduce()`, `globalParams()`, `propagateDifcal()` | All reduction scripts |
| `snapwrap.io` | `redObject`, `exportData()` | Parse workspace names, export to GSAS-II/TOPAS |
| `snapwrap.snapStateMgr` | `checkCalibrationStatus()`, `SNAPHome` | Calibration state queries |
| `snapwrap.maskUtils` | Swiss cheese mask creation, pixel mask tools | DAC/PE masking workflows |
| `snapwrap.SEEMeta.utils` | `acquireMeta()` | Extract assembly metadata from run logs |
| `snapwrap.SEEMeta.assembly` | `DAC`, `PE`, `CylinderCell`, `Empty` | Assembly type objects |
| `snapwrap.cycleDates` | `get_cycle_for_run()` | Cycle-aware calibration lookups |
| `snapwrap.wrapConfig` | `WrapConfig` | Runtime config loading |

---

## Configuration

SNAPWrap uses a YAML-based configuration (`application.yml` + optional
`override.yml`):

```python
from snapwrap.wrapConfig import WrapConfig
WrapConfig.load()
value = WrapConfig.get("instrument.calibration.home")
```

For local testing outside the SNS Analysis Cluster, set path overrides in
`override.yml` and launch with:
```bash
env=/full/path/to/override.yml pixi run snapwrap
```

Default reduction parameters live in `defaultRedConfig.yml`; these are the
values used when `YMLOverride='none'`.

---

## Developer conventions

- **Library-first**: SNAPWrap is imported in scripts; it is not a CLI tool.
- **Mantid Workbench environment**: all scripts run inside a Mantid Python
  environment; assume Mantid algorithms and workspace APIs are available.
- **SNAPRed is the computation engine**: SNAPWrap only prepares inputs,
  assembles hooks, and parses outputs. Never re-implement reduction logic in
  SNAPWrap.
- **Hook points are SNAPRed lifecycle names**: check the SNAPRed service layer
  for valid hook registration points before adding new hooks.
- **Calibration index is source of truth**: do not hardcode calibration file
  paths; always resolve via `checkCalibrationStatus()` or the SNAPRed Data
  layer.

---

## Cross-references

- SNAPRed backend architecture: see `sns-snapred-developer-guide` skill.
- Reduction workflow (user-facing): see `sns-snap-reduction-workflow-overview`.
- Sample-environment masking details: see
  `sns-snap-sample-environment-reduction-special-cases`.
- Calibration state controls: see `sns-snap-calibration-and-geometry`.
