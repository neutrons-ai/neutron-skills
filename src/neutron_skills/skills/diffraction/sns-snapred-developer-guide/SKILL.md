---
name: sns-snapred-developer-guide
description: >
  Rapidly orient a developer or coding agent to the SNAPRed architecture,
  coding conventions, and extension points. Use when writing new recipes,
  services, or hooks; debugging calibration or reduction workflows; or
  consuming SNAPRed as a backend from an external wrapper such as SNAPWrap.
version: 1
review:
  status: pending
  reviewer: null
  reviewed_on: null
  basis: []
  notes: null
  approved_commit: null
metadata:
  facility: SNS
  beamline: BL3
  instruments: [SNAP, SNS]
  software: [snapred, Mantid]
  data_phase: reduction
  techniques: [diffraction, powder-diffraction, time-of-flight]
  tags:
    - developer
    - architecture
    - snapred
    - recipe
    - service
    - cooking-metaphor
    - hooks
    - state-management
    - calibration
    - reduction
    - mantid
    - backend
---

# SNAPRed Developer Guide

SNAPRed is the data-reduction backend for the SNAP high-pressure diffractometer
at SNS/ORNL. It is a Python 3.11 application that orchestrates three workflows —
Diffraction Calibration (DifCal), Normalization Calibration (NormCal), and
Reduction — on top of the Mantid framework.

**Version coverage**: This skill documents the architecture and conventions
stable across v2.0.0 (SoftwareX paper, 2026) through the current development
branch (post-v2.3.1, April 2026). Core architecture (layer structure, cooking
metaphor, service registration, hooks) remains unchanged; check release notes
for algorithm and API refinements in specific versions.

Repository: https://github.com/neutrons/SNAPRed  
Docs: https://snapred.readthedocs.io/en/latest/  
Paper: Guthrie et al., SoftwareX 33 (2026) 102464

---

## Evidence tracking

**SoftwareX paper** (v2.0.0 baseline, 2026-04-30):
- Source: Guthrie et al., SoftwareX 33 (2026) 102464
- Verified: layer descriptions (Interface → Service → Data → Recipe),
  DifCal two-step workflow, NormCal vanadium approach, Lite mode factor-of-64
  compression, workspace naming conventions, calibration index and
  appliesTo policy, diagnostic output definition.

**Live codebase verification** (post-v2.3.1 development, 2026-04-30):
- Source: `/Users/66j/Documents/ORNL/code/SNAPRed` (branch: `next`)
- Verified: cooking metaphor class inventory (Recipe, SousChef, GroceryService),
  layer structure, hook system, state-ID formation, diagnostic/reduced labelling
  logic, service path registration.
- Finding: core architecture stable; v2.0.0 documentation remains accurate for
  current development version.

---

## Backend layer architecture

SNAPRed cleanly separates frontend from backend and divides the backend into
four layers of increasing specificity (outermost → innermost):

```
InterfaceController   ← sole external entry point; validates, routes, handles errors
    └── Service layer ← orchestration; registers methods to string paths
            └── Data layer  ← read/write, cache, revision-control, packaging
                    └── Recipe layer ← processing unit; executes Mantid algorithms
```

| Layer | Key class(es) | Role |
|-------|--------------|------|
| Interface | `InterfaceController` | Receives `SNAPRequest`, routes to Service via `ServiceFactory`, returns `SNAPResponse` |
| Service | `Service` (ABC), `CalibrationService`, `ReductionService`, `SousChef` | Orchestrates recipes and data; methods registered to paths via `@Register` decorator |
| Data | `LocalDataService`, `DataFactoryService`, `GroceryService` | Persistence (JSON + HDF5), caching, workspace loading |
| Recipe | `Recipe[T]` (ABC), concrete subclasses | Actual Mantid algorithm execution |

**Entry point for external callers (e.g., SNAPWrap):**
```python
from snapred.backend.api.InterfaceController import InterfaceController
controller = InterfaceController.instance()
response = controller.executeRequest(snap_request)
```

---

## The cooking metaphor

SNAPRed uses a pervasive culinary metaphor throughout the processing layer.
This is intentional and internal — **user-facing skill language should avoid
the metaphors** but developers must know them to navigate the code.

| Metaphor term | Code class / concept | What it is |
|---------------|---------------------|-----------|
| **Recipe** | `Recipe[Ingredients]` (ABC, `backend/recipe/Recipe.py`) | Abstract base for all processing workflows; generic over Ingredients type |
| **Ingredients** | Pydantic `BaseModel` subclasses (`backend/dao/ingredients/`) | Strongly-typed input parameters for a Recipe (e.g., `DiffractionCalibrationIngredients`, `ReductionIngredients`) |
| **Groceries** | `Dict[str, WorkspaceName]` | Mantid workspace references passed into a Recipe alongside Ingredients |
| **Pallet** | `Tuple[Ingredients, Dict[str, str]]` | One batch unit: one Ingredients + one Groceries dict pair |
| **FarmFreshIngredients** | `backend/dao/request/FarmFreshIngredients.py` | Run-time request object used by SousChef to prepare Ingredients before processing |
| **GroceryListItem** | `backend/dao/ingredients/GroceryListItem.py` | Builder for workspace name construction |
| **GroceryService** | `backend/data/GroceryService.py` | Loads workspace data; caches groupings, instruments, normalizations |
| **SousChef** | `backend/service/SousChef.py` | Prepares complex Ingredients; caches pixel groups and peaks; wraps `DataFactoryService` |
| **Utensils** | `backend/recipe/algorithm/Utensils.py` | Empty `PythonAlgorithm` wrapper that holds `MantidSnapper` for progress reporting |
| **MakeDirtyDish** | `backend/recipe/algorithm/MakeDirtyDish.py` | Clones a workspace to a new name for diagnostic (CIS mode) inspection |
| **WashDishes** | `backend/recipe/algorithm/WashDishes.py` | Deletes temporary workspaces; respects CIS mode preservation flag |
| **FetchGroceriesRecipe** | `backend/recipe/FetchGroceriesRecipe.py` | Loads neutron data, grouping definitions, calibrations into Mantid |

### Recipe abstract interface

Every Recipe must implement four abstract methods plus optional overrides:

```python
class Recipe(ABC, Generic[Ingredients]):
    def chopIngredients(self, ingredients: Ingredients) -> None:
        """Extract and validate needed elements from Ingredients into locals."""

    def unbagGroceries(self, groceries: Dict[str, str]) -> None:
        """Map workspace names from Groceries dict into local variables."""

    def queueAlgos(self) -> None:
        """Register Mantid algorithms for deferred execution."""

    def allGroceryKeys(self) -> List[str]:
        """Declare all workspace keys this recipe expects in Groceries."""

    # Concrete lifecycle — do not override unless necessary:
    def stirInputs(self)  -> None: ...  # cross-validate chopped + unbagged data
    def prep(self) -> None: ...         # validate → unbag → chop → stir → queue
    def cook(self, ingredients, groceries) -> Any: ...  # call prep(), run queued algos
    def cater(self, pallets: List[Pallet]) -> Any: ...  # batch-process multiple pallets
```

### Concrete Recipe subclasses

| Recipe | File | Purpose |
|--------|------|---------|
| `PixelDiffCalRecipe` | `recipe/PixelDiffCalRecipe.py` | Pixel-level DIFC calibration via cross-correlation |
| `GroupDiffCalRecipe` | `recipe/GroupDiffCalRecipe.py` | Group-level focused calibration and peak fitting |
| `ReductionRecipe` | `recipe/ReductionRecipe.py` | Main reduction workflow |
| `ApplyNormalizationRecipe` | `recipe/ApplyNormalizationRecipe.py` | Apply vanadium normalization correction |
| `PreprocessReductionRecipe` | `recipe/PreprocessReductionRecipe.py` | Preprocessing before reduction |
| `GenerateCalibrationMetricsWorkspaceRecipe` | `recipe/` | Quality metric generation |
| `GenericRecipe[AlgoType]` | `recipe/GenericRecipe.py` | Template for wrapping a single Mantid algorithm without custom logic |

---

## Service layer and path routing

Services register methods to string paths using the `@Register` decorator:

```python
class CalibrationService(Service):
    @Register("calibration/ingredients")
    def prepDiffractionCalibrationIngredients(self, request): ...

    @Register("calibration/")
    def diffractionCalibration(self, request): ...
```

`InterfaceController` routes an incoming `SNAPRequest.path` to the matching
registered method. Key registered paths:

| Path | Service | Purpose |
|------|---------|---------|
| `"calibration/ingredients"` | `CalibrationService` | Prepare DifCal Ingredients |
| `"calibration/groceries"` | `CalibrationService` | Fetch DifCal workspace names |
| `"calibration/"` | `CalibrationService` | Run full DifCal workflow |
| `"normalization/"` | `CalibrationService` | Run NormCal workflow |
| `"reduction/validate"` | `ReductionService` | Validate reduction inputs (raises `ContinueWarning` if missing data) |
| `"reduction/"` | `ReductionService` | Run reduction workflow |
| `"stateId/"` | `StateIdLookupService` | Resolve state IDs for a list of run configs |

---

## Instrument state and state IDs

State IDs are 16-character hex digests (SHAKE256) of a rounded `DetectorState`.

**Formation:**
1. Read run file header → extract detector PV values
   (`det_arc1`, `det_arc2`, `BL3:Mot:OpticsPos:Pos`, etc.)
2. Round PV values per the instrument's `stateIdSchema`
   (removes encoder jitter; makes state ID deterministic)
3. Hash the rounded `DetectorState` → `ObjectSHA` (16-char hex)

**Filesystem layout keyed by state:**
```
calibration.powder.home/{stateId}/lite|native/diffraction/v{version}/
reduction.home/{stateId}/lite|native/{runNumber}/{timestamp}/
```

**Key class:** `ObjectSHA` (`backend/dao/ObjectSHA.py`)  
**State data model:** `InstrumentState` (`backend/dao/state/InstrumentState.py`)  
— contains: `id`, `instrumentConfig`, `detectorState`, `gsasParameters`,
`particleBounds`, `fwhmMultipliers`

---

## Calibration workflows

### DifCal (Diffraction Calibration)

Two-step workflow run by an instrument scientist before user beamtime:

1. **Pixel Calibration** (`PixelDiffCalRecipe`): cross-correlate each pixel's
   spectrum against a reference pixel within its group; output is a table of
   logarithmic DIFC offsets.
2. **Group Calibration** (`GroupDiffCalRecipe`): diffraction-focus the spectra,
   fit all non-overlapping peaks per group, correct absolute d-spacing offset.

Output: diffractometer constants (DIFC table) written to a versioned folder.
A **Calibration Index** is maintained automatically, tracking which calibration
applies to which run numbers via the `appliesTo` field.

Currently SNAPRed fits DIFC only; the GSAS TOF parameterization also supports
DIFA, ZERO, DIFB but these are not yet fitted.

### NormCal (Normalization Calibration)

Vanadium (or V-Nb alloy) based wavelength-response correction:

1. Subtract background measurement from vanadium data.
2. Apply absorption correction (resource intensive; allow 10–20 min).
3. Smooth the result excluding expected Bragg-peak regions.
4. Persist smoothed correction as an unfocused event workspace.

A **Normalization Index** mirrors the Calibration Index structure.

---

## Diagnostic vs reduced output labelling

Determined in `ReductionService` from `WorkspaceMetadata`:

```python
isDiagnostic = (diffcalState != DiffcalStateMetadata.EXISTS
                or normalizationState != NormalizationStateMetadata.EXISTS)
```

| Output label | Condition |
|-------------|-----------|
| `reduced` | Both DifCal **and** NormCal are present for this state |
| `diagnostic` | Either calibration is missing; approximations were used |

Approximation pathways (controlled by continue flags):
- Missing DifCal → default calibration (VERSION_START) applied; flag `MISSING_DIFFRACTION_CALIBRATION`
- Missing NormCal → artificial normalization extracted from non-Bragg background; flag `MISSING_NORMALIZATION`
- Alternative calibration file used → flag `ALTERNATE_DIFFRACTION_CALIBRATION`

All continue flags are logged in the `ReductionRecord` for traceability.

**Continue flags require explicit user action** — defaults do not continue;
the user must set flags to proceed without full calibration.

---

## Hook system

Hooks allow external callers (e.g., SNAPWrap) to inject custom callbacks into
the SNAPRed request lifecycle without modifying SNAPRed code.

```python
# Hook data model
class Hook:
    func: Callable
    kwargs: Dict[str, Any]

# Attach hooks to a request
request = SNAPRequest(path="reduction/", payload=..., hooks={
    "before_recipe": [Hook(func=my_callback, kwargs={"run": run_number})],
})
```

`HookManager` (`backend/api/HookManager.py`) executes all registered hooks at
the designated lifecycle point. All registered hooks must be executed;
failure to execute any registered hook raises `ValueError`.

---

## Lite mode and data compression

Lite mode compresses the native 1,179,648-pixel SNAP detector to 1,179,648 ÷ 64 =
~18,432 pixels by down-sampling spatial precision to match the instrument's
diffraction resolution. This:
- Accelerates calculations by up to 64×.
- Reduces histogram data volumes by ~64×.
- Is the **default** for all three workflows.

Native mode (`useLiteMode=False`) is available but is an expert/special-case
setting; RAM requirements are run-specific and depend on data volume, detector
masking, and available computing resources.

---

## Workspace naming conventions

Workspace names follow `WorkspaceNameGenerator`
(`backend/meta/mantid/WorkspaceNameGenerator.py`):

```
{base}_{unit}_{grouping}_{run}_{timestamp}
```

Examples from the paper:
```
reduced_dsp_all_064413_2025-11-17T154047
reduced_dsp_bank_064413_2025-11-17T154047
reduced_dsp_column_064413_2025-11-17T154047
dsp_unfoc_lite_064413
diagnostic_dsp_column_064431_<timestamp>
```

Key prefixes:
- `reduced_` — full calibration available
- `diagnostic_` — approximation pathway used
- `dsp_` — d-spacing units
- `unfoc_` — unfocused (pre-diffraction-focusing) workspace

---

## Response codes

`SNAPResponse` carries a `ResponseCode` enum:

| Code | Meaning |
|------|---------|
| `OK` | Success |
| `RECOVERABLE` | RecoverableException (e.g., missing IPTS, init failure) |
| `CONTINUE_WARNING` | ContinueWarning: user decision required (missing calibration but can proceed) |
| `LIVE_DATA_STATE` | Live data transition |
| `ERROR` | Unrecoverable error |

---

## Key developer conventions

### Error handling
- `RecoverableException`: missing data, initialization failures.
- `ContinueWarning`: user decision required; raised during `reduction/validate`.
- `StateValidationException`: invalid instrument state.
- Use specific exception types; avoid bare `Exception`.

### Caching
- `SousChef` maintains `_pixelGroupCache` and `_peaksCache`.
- `GroceryService` caches groupings, instruments, and normalizations.
- **Dump the SousChef cache when a pixel mask changes**
  (see `CalibrationService`).

### Singleton pattern
- Several services use `@Singleton`; reset with `ClassName.reset()` between
  tests to avoid state bleed.

### Configuration
- All runtime config accessed via `Config["key.path"]`
  (`snapred/meta/Config.py`).
- Override for local testing: edit `override.yml` and run with
  `env=/path/to/override.yml pixi run snapwrap`.

### Testing
- Tests follow pytest conventions under `tests/`.
- Mock Mantid APIs with provided test utilities where needed.
- Use `@Singleton.reset()` to clear singleton state between test cases.

---

## Adding a new workflow: minimal checklist

1. **Define Ingredients** (Pydantic `BaseModel`) in
   `backend/dao/ingredients/`.
2. **Define Groceries keys** — the workspace names the new recipe needs.
3. **Implement a Recipe subclass** in `backend/recipe/`:
   - Implement `chopIngredients`, `unbagGroceries`, `queueAlgos`,
     `allGroceryKeys`.
   - Add a docstring listing all expected Ingredients fields and Grocery keys.
4. **Register a Service method** in the appropriate Service subclass using
   `@Register("path/to/endpoint")`.
5. **Wire hooks** if the new workflow needs SNAPWrap callbacks.
6. **Update the Calibration or Normalization Index** if the workflow produces
   calibration artifacts that need to be tracked.
7. **Write tests** — mock Mantid APIs; reset Singletons between tests.

---

## Cross-references

- SNAPWrap wrapper API: see `sns-snapwrap-developer-guide` skill.
- Reduction workflow overview (user-facing): see
  `sns-snap-reduction-workflow-overview` skill.
- Calibration concepts and state controls: see
  `sns-snap-calibration-and-geometry` skill.
- Reduction failure modes: see `sns-snap-reduction-diagnostics` skill.
