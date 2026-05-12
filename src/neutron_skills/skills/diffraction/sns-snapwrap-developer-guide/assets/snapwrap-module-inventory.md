# SNAPWrap Module Inventory

Derived from codebase exploration (2026-04-30).  
Source: `/Users/66j/Documents/ORNL/code/SNAPWrap`  
Repository: https://github.com/neutrons/SNAPWrap

This file is a stable reference artifact. For conceptual usage guidance see
`../SKILL.md`.

---

## Top-level package structure

```
src/snapwrap/
├── __init__.py            — loads WrapConfig, cycle index, version
├── _version.py            — package version string
├── utils.py               — primary reduction interface (reduce() and helpers)
├── io.py                  — workspace I/O and export (redObject)
├── maskUtils.py           — pixel and bin mask utilities
├── snapStateMgr.py        — calibration state management
├── cycleDates.py          — SNS operating cycle date utilities
├── wrapConfig.py          — YAML config loader
├── configuration.py       — INI config loader with defaults fallback
├── statusPrinter.py       — console output formatting
├── userScript.py          — Mantid Workbench script entry point
├── main.py                — Qt application bootstrap (minimal)
├── commands.py            — core module import wrappers
├── SEEBuilder.py          — sample environment assembly builder helper
├── application.yml        — runtime configuration
├── defaultRedConfig.yml   — default reduction parameters
├── configuration_template.ini — INI template for user config
├── override.yml           — local override template
├── SEEMeta/               — sample environment metadata sub-package
├── calibrationManager/    — Qt calibration UI sub-package
├── pixelResolution/       — resolution estimation sub-package
├── sampleMeta/            — sample metadata utilities sub-package
└── spectralTools/         — spectral analysis helpers sub-package
```

---

## `snapwrap.utils` — primary reduction interface

**File:** `src/snapwrap/utils.py`

### `reduce()`

```python
def reduce(
    runNumber,
    sampleEnv='none',
    pixelMaskIndex='none',
    binMaskList=[],
    YMLOverride='none',
    backgroundWSName=None,
    attenuationWSName=None,
    continueNoDifcal=False,
    continueNoVan=False,
    requireSameCycle=True,
    verbose=False,
    reduceData=True,
    keepUnfocussed=False,
    noNorm=False,
    emptyTrash=True,
    cisMode=False,
    focusGroupAllowList=None,
    qsp=False,
    linBin=0.01,
    removePGS=None,
    save=True,
) -> list[str]
```

Returns list of reduced workspace names (empty list on failure).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `runNumber` | int/str | — | SNAP run number |
| `binMaskList` | list[str] | `[]` | Bin-mask workspace names (Swiss cheese / wavelength notching) |
| `pixelMaskIndex` | int/list/'none' | `'none'` | User pixel mask index(es) to apply |
| `continueNoDifcal` | bool | `False` | Proceed without difcal → `diagnostic_` output |
| `continueNoVan` | bool | `False` | Proceed without normcal → artificial normalization → `diagnostic_` output |
| `noNorm` | bool | `False` | Skip normalization entirely |
| `requireSameCycle` | bool | `True` | Restrict calibration matches to same SNS cycle |
| `cisMode` | bool | `False` | Preserve intermediate workspaces for inspection |
| `keepUnfocussed` | bool | `False` | Retain pre-focusing workspace in Mantid |
| `focusGroupAllowList` | list[str]/None | `None` | Restrict to named pixel groups; `None` = all |
| `qsp` | bool | `False` | Output in Q-space instead of d-spacing |
| `linBin` | float | `0.01` | Linear bin width for Q-space output |
| `backgroundWSName` | str/None | `None` | Workspace for background subtraction hook |
| `attenuationWSName` | str/None | `None` | Workspace for attenuation correction hook |
| `YMLOverride` | str | `'none'` | Path to YAML override for reduction parameters |
| `save` | bool | `True` | Write outputs to disk |
| `emptyTrash` | bool | `True` | Delete temporary workspaces after reduction |

### `globalParams(YMLOverride='none') -> dict`

Parse default or override YAML to a parameter dictionary.

### `propagateDifcal(donorRunNumber, isLite=True, propagate=False)`

Find compatible instrument states and optionally propagate the donor run's
latest difcal to those states. Useful after a calibration run to share
calibration across states with identical geometry.

### `makeResolutionWorkspace(...)`

Generate a pixel-resolution workspace for a given run and grouping scheme.

### `HookCollection` class

Container for SNAPRed hook factory methods:

| Method | Hook point | Purpose |
|--------|-----------|---------|
| `BackgroundAttenuationCorrection(...)` | `PostPreprocessReductionRecipe` | Background subtraction + attenuation correction |
| `cheeseMask(context, binMaskList)` | `PostPreprocessReductionRecipe` | Apply bin masks via `MaskBinsFromTable` |

---

## `snapwrap.io` — workspace I/O and export

**File:** `src/snapwrap/io.py`

### `redObject`

```python
class redObject:
    def __init__(
        self,
        wsName,
        requiredPrefix='reduced',
        requiredUnits='dsp',
        requiredPGS=None,
        requiredRunNumber=None,
        iptsOverride=None,
        exportFormats=[],
        fileTag=None,
        cleanTreeOverride=None,
        allowSuffix=False,
        requiredSuffix=None,
    )
```

Parses a reduced workspace name and exposes structured attributes.

Workspace name formats accepted:
- Clean: `reduced_dsp_all_064413` (4 elements)
- Timestamped: `reduced_dsp_all_064413_2025-11-17T154047` (5 elements)

Key attributes:
| Attribute | Description |
|-----------|-------------|
| `prefix` | `reduced` or `diagnostic` |
| `units` | `dsp` (d-spacing) or `q` (Q-space) |
| `pixelGroup` | `all`, `bank`, `column`, or custom name |
| `runNumber` | Run number string |
| `timestamp` | ISO timestamp string or None |
| `xMin`, `xMax`, `delta` | Binning parameters from workspace |
| `redRecord` | Path to JSON reduction record file |

### `exportData(wsName, formats=['gsa', 'xye', 'csv'], ...)`

Export a reduced workspace to one or more formats:
- `gsa` → GSAS-II format
- `xye` → TOPAS / FullProf format
- `csv` → general ASCII

---

## `snapwrap.snapStateMgr` — calibration state management

**File:** `src/snapwrap/snapStateMgr.py`

### `checkCalibrationStatus()`

```python
def checkCalibrationStatus(
    runNumber,
    stateID=None,
    isLite=True,
    calType="difcal",     # or "normcal"
    requireSameCycle=True,
) -> dict
```

Returns dict with keys:

| Key | Type | Description |
|-----|------|-------------|
| `stateID` | str | 16-char hex instrument state ID |
| `runIsCalibrated` | bool | Valid calibration exists for this run |
| `stateIsCalibrated` | bool | Any calibration exists for this state |
| `numberCalibrations` | int | Total calibrations in index |
| `latestCalibrationDict` | dict | Most recent calibration record |
| `latestValidCalibrationDict` | dict | Most recent calibration valid for this run |
| `latestValidVBRunNumber` | int | Vanadium background run (normcal) |
| `statusDetail` | str | Human-readable reason if not calibrated |

### `SNAPHome`

```python
class SNAPHome:
    calib: str    # Config['instrument.calibration.home']
    powder: str   # calib + "/Powder/"
```

Access calibration root paths without hardcoding.

---

## `snapwrap.maskUtils` — pixel and bin mask utilities

**File:** `src/snapwrap/maskUtils.py`

Core utilities for creating and managing pixel masks and bin masks.

Key functionality (from codebase exploration):
- Pixel mask creation tools (threshold, grid, region selection)
- Swiss cheese bin mask creation from UB matrix pairs (DAC notching)
- `swissCheese` / Swiss cheese class with:
  - Constructor accepting UB matrix pair (one per diamond)
  - `ExtractFromWorkspaceHistory(wsName)` — extract bin mask from
    manual masking operations performed in MantidWorkbench
  - Methods to combine multiple masks
- `MaskBinsFromTable` wrapping for application during reduction

---

## `snapwrap.SEEMeta` — sample environment assembly metadata

**Sub-package:** `src/snapwrap/SEEMeta/`

### `SEEMeta.utils.acquireMeta(runNumber) -> dict | None`

Extract sample environment assembly metadata for a run.

Lookup order:
1. Override JSON: `/IPTS-{ipts}/shared/SEE/SEE{runNumber}.json`
2. Embedded in NeXus HDF5: `entry/DASlogs/BL3:SE:SEEMeta:JSON/value`
3. Returns `None` if not present (fall back to manual identification)

### `SEEMeta.utils.SEEH5Loader(h5Path) -> dict`

Extract SEEMeta JSON from a NeXus HDF5 file directly.

### `SEEMeta.utils.SEEJsonLoader(filePath) -> dict`

Load SEEMeta from a standalone JSON file.

### Assembly classes (`SEEMeta.assembly`)

```python
from snapwrap.SEEMeta.assembly import DAC, PE, CylinderCell, Empty
```

| Class | `type` field | Description |
|-------|-------------|-------------|
| `DAC` | `assembly.dac` | Diamond Anvil Cell; requires DACAnvil + DACGasket components |
| `PE` | `assembly.pe` | Paris-Edinburgh / opposed anvil; requires toroidAnvil + toroidGasket |
| `CylinderCell` | `assembly.cylinder` | Gas or piston-cylinder cell; validates component adjacency |
| `Empty` | `assembly.empty` | No sample environment |

All assemblies extend `Assembly` base dataclass:
```python
@dataclass
class Assembly:
    components: List[Component]
    primaryCategory: str
    secondaryCategory: str
    nickname: str
    orientation: List[float]   # [x, y, z]
    origin: List[float]
    stringDescriptor: str
```

Serialization: `Assembly.from_dict(d)` / `assembly.to_dict()` with registry
pattern for polymorphic deserialization. Version migration via `upgrade()`.

### Component classes (`SEEMeta.component`)

Typed component dataclasses: `DACAnvil`, `DACGasket`, `toroidAnvil`,
`toroidGasket`, `CylinderWall`, `CylinderPiston`, and others.

### Material database (`SEEMeta.material`, `SEEMeta.db`)

SQLite-backed material properties database. Access via `SEEMeta.material`
interfaces; `SEEMeta.db` manages the SQLAlchemy engine.

---

## `snapwrap.cycleDates` — SNS operating cycle utilities

**File:** `src/snapwrap/cycleDates.py`

```python
from snapwrap.cycleDates import build_cycle_json, get_cycle_for_run

# Build/update the cycle date index
build_cycle_json(json_path, ods_path)

# Get cycle string for a run number
cycle = get_cycle_for_run(runNumber)
# e.g., '2025-A'
```

Used internally by `checkCalibrationStatus` when `requireSameCycle=True`.

---

## `snapwrap.wrapConfig` — YAML configuration

**File:** `src/snapwrap/wrapConfig.py`

```python
from snapwrap.wrapConfig import WrapConfig
WrapConfig.load()
value = WrapConfig.get("instrument.calibration.home")
```

Loads `application.yml` with string interpolation. Override for local
testing via `env=/path/to/override.yml pixi run snapwrap`.

---

## `snapwrap.pixelResolution` — resolution estimation

**Sub-package:** `src/snapwrap/pixelResolution/`

| Module | Key export | Purpose |
|--------|-----------|---------|
| `pixelResolution.core` | resolution workspace generation | Per-pixel resolution estimates |
| `pixelResolution.mantid_utils` | Mantid algorithm wrappers | Resolution calculation helpers |

---

## `snapwrap.sampleMeta` — sample metadata utilities

**Sub-package:** `src/snapwrap/sampleMeta/`

| Module | Key export | Purpose |
|--------|-----------|---------|
| `sampleMeta.latticeFittingFunctions` | Lattice parameter fitting | Used in DAC pressure determination |
| `sampleMeta.utils` | Sample metadata utilities | General sample property helpers |

---

## `snapwrap.spectralTools` — spectral analysis helpers

**Sub-package:** `src/snapwrap/spectralTools/`

| Module | Key export | Purpose |
|--------|-----------|---------|
| `spectralTools.tools` | Spectral processing functions | Post-reduction spectral analysis |

---

## Configuration files

| File | Purpose |
|------|---------|
| `application.yml` | Main runtime configuration; paths, defaults, instrument parameters |
| `defaultRedConfig.yml` | Default reduction parameters used when `YMLOverride='none'` |
| `configuration_template.ini` | INI template for user-specific config |
| `override.yml` | Local override template for off-cluster testing |
