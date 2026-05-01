# Phase 0: SNAP Docs-vs-Code Validation

This document records the results of reconciling the public SNAP reduction page 
(https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html) against the 
current SNAPWrap source code at /Users/66j/Documents/ORNL/code/SNAPWrap.

Executed: 2026-04-29

---

## Stable claims (Phase 0 Verified ✓)

These claims from the public docs are validated against current SNAPWrap code:

| Claim | Evidence | Status |
|-------|----------|--------|
| `wrap.reduce(runNumber)` is the primary entry point | utils.py reduce() signature | ✓ |
| Lite mode is default | useLiteMode=True in config defaults | ✓ |
| Three built-in pixel grouping schemes: all (1 spectrum), bank (2 spectra), column (6 spectra); fully user-defined groupings also supported | configuration.py focusGroup definitions | ✓ corrected |
| Workspace naming: `reduced_dsp_pixelgroup_runnumber_[timestamp]` | io.py redObject parser | ✓ |
| Four modules: utils, maskUtils, io, snapStateMgr | __init__.py module exports | ✓ |
| d-Spacing is default output unit (qsp alternative) | reduce() default parameters | ✓ |
| SNAPRed manages calibration; snapwrap wraps it | imports and service layer | ✓ |
| `wrap.resample(factor)` controls binning | utils.py resample() signature | ✓ |
| `wrap.exportData()` produces multiple formats | io.py exportData formats list | ✓ |
| Calibration has difcal AND normcal tracks | snapStateMgr state model | ✓ |
| SNAPRed labels outputs `diagnostic` when calibration approximations were used; `reduced` when full calibration was applied | SNAPRed ContinueWarning/RecoverableException raise sites | ✓ |
| Two mask types: `pixelmask` (excludes entire pixels) and `binmask` (excludes data ranges specified in any unit: TOF, wavelength, Q, or d-spacing) | SNAPWrap maskUtils.py | ✓ |

---

## Drift findings (Phase 1 status)

### HIGH PRIORITY

**Export format semantics clarified (Phase 1)**
- Docs claim: "GSAS-II, TOPAS, Fullprof, plain ascii"
- Code state: `exportFormats=['gsa','xye','csv']`
- Resolution: user confirmed mapping
	- `gsa` -> GSAS-II workflows
	- `xye` -> TOPAS/FullProf workflows
	- `csv` -> plain ascii/general analysis workflows
- Status: resolved in Phase 1; retain as compatibility note in skills

**Calibration failure modes clarified from source**
- Docs claim: "Works knowing only run number"
- Code state: `reduce()` aborts (returns `[]`) when calibration is missing unless explicit continue flags are set.
- Source anchors:
	- `utils.py reduce(..., continueNoDifcal=False, continueNoVan=False, noNorm=False, requireSameCycle=True)`
	- early abort gates for missing difcal/normcal
	- continue-flag bitmask assignment (`ContinueWarning.Type.*`)
- Phase 1 matrix (source-derived):

| difcal status | normcal status | Flags | Outcome |
|---|---|---|---|
| present | present | none | normal reduction path (`reduced`) |
| missing | present | `continueNoDifcal=False` | abort (`[]`) |
| missing | present | `continueNoDifcal=True` | continue with `MISSING_DIFFRACTION_CALIBRATION` (`diagnostic`) |
| present | missing | `continueNoVan=False` and `noNorm=False` | abort (`[]`) |
| present | missing | `continueNoVan=True` or `noNorm=True` | continue with `MISSING_NORMALIZATION` (`diagnostic`) |
| missing | missing | both continue flags not set | abort (`[]`) |
| missing | missing | both continue pathways enabled | continue with both warning bits (`diagnostic`) |

- Status: documented from source; runtime matrix test still pending.

**Workspace naming cleanTree/timestamp variants clarified**
- Docs: Often show timestamped naming only.
- Code: parser supports both schemas:
	- cleanTree: `<prefix>_<units>_<pixelGroup>_<runNumber>`
	- timestamped: `<prefix>_<units>_<pixelGroup>_<runNumber>_<timestamp>`
- Parser behavior: validates timestamp tokens and falls back to timestamp-less parsing when token is not a timestamp.
- Status: resolved in Phase 1 docs/skills.

### MEDIUM PRIORITY

**Calibration cycle validation clarified**
- Code: `requireSameCycle=True` by default in `reduce()` and calibration status checks.
- Behavior:
	- with `requireSameCycle=True`, out-of-cycle calibrations are treated as invalid for the run.
	- with `requireSameCycle=False`, legacy out-of-cycle matching is allowed.
- Status: resolved in Phase 1 docs/skills.

**Resample behavior clarified**
- Code: `resample(sampleFactor=1, ...)` default is no change to bin spacing.
- Implementation uses `dsDelta = Delta / sampleFactor`:
	- `sampleFactor < 1` -> coarser bins (downsample)
	- `sampleFactor > 1` -> finer bins (upsample), warning printed as lossy
- Status: resolved in Phase 1 docs/skills.

---

## Phase 0 validation checklist (next steps)

Before Phase 1 calibration ingestion proceeds, these items must be cleared:

- [x] Export format semantics verified with user
- [ ] Calibration failure-mode matrix tested (no difcal + continue flags, etc.)
- [x] Workspace naming parser validated for both timestamped and cleaned modes (source validation)
- [x] Calibration cycle validation behavior documented
- [x] Resample sampleFactor defaults clarified

---

## Evidence anchors for skill authoring

Each validated claim above becomes an evidence anchor. When writing skills, cite:

```
Evidence: Phase 0 SNAP docs validation
Source: https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html
Verification: SNAPWrap utils.py, config, io.py, snapStateMgr.py
Date: 2026-04-29
```

---

## Known cooking metaphor translations

For use when reading SNAPRed code (Phase 1):

| Metaphor | Technical Meaning |
|----------|-------------------|
| Recipe | Workflow orchestration class |
| Ingredients | Input parameters (Pydantic models) |
| Groceries | `Dict[str, WorkspaceName]` — workspace reference registry (keys map to Mantid workspace identifiers, not data values) |
| chopIngredients() | Extracts and validates config parameters from an Ingredients object into instance variables (does not transform data) |
| unbagGroceries() | Extracts workspace name references from the Groceries dict into instance variables (data stays in Mantid's database) |
| stirInputs() | Validates consistency between chopped ingredients and unbagged groceries; often a no-op |
| cater() | Batch-processes multiple (Ingredients, Groceries) pairs — nothing to do with serving |
| queueAlgos() | Queue Mantid algorithms for execution |
| SousChef | Helper service for ingredient prep |
| Utensils | Empty PythonAlgorithm placeholder; Mantid progress infrastructure workaround |
| MakeDirtyDish | Clones a workspace to a new name for diagnostic preservation |
| WashDishes | Deletes temporary workspaces (or preserves them if diagnostic/CIS mode is enabled) |
| FetchGroceriesRecipe | Loads data files into Mantid workspaces |
| Pallet | `Tuple[Ingredients, Dict[str,str]]` — a single batch-processing unit for cater() |

---

## Next phase

Phase 1 begins with SNAPRed calibration architecture ingestion at:
/Users/66j/Documents/ORNL/code/SNAPRed/

Focus areas:
1. Generic TOF calibration primitives
2. SNAP-specific calibration implementation
3. How SNAPWrap interfaces with SNAPRed state/calibration APIs
4. Calibration failure signatures and recovery paths
