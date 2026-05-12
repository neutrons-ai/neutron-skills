---
name: sns-snapred-developer-guide
description: >
  Rapidly orient a developer or coding agent to the SNAPRed architecture,
  coding conventions, and extension points. Use when writing new recipes,
  services, or hooks; debugging calibration or reduction workflows; or
  consuming SNAPRed as a backend from an external wrapper such as SNAPWrap.
version: 2
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
  instruments: [SNAP]
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

## Overview

SNAPRed is the reduction backend for SNAP. It is a Python 3.11 application on
top of Mantid that orchestrates three workflows: diffraction calibration
(`DifCal`), normalization calibration (`NormCal`), and reduction.

This skill documents the architecture and conventions that stayed stable from
the v2.0.0 SoftwareX description through the current development branch checked
on 2026-05-11.

Repository: https://github.com/neutrons/SNAPRed  
Docs: https://snapred.readthedocs.io/en/latest/  
Paper: Guthrie et al., SoftwareX 33 (2026) 102464

### Evidence

- SoftwareX paper verified the four-layer architecture, calibration workflows,
  lite mode, workspace naming, calibration index behavior, and
  diagnostic/reduced labelling.
- Live codebase verification against `/Users/66j/Documents/ORNL/code/SNAPRed`
  confirmed the cooking-metaphor class inventory, layer structure, hooks,
  state-ID formation, and service-path registration remain aligned with the
  paper.
- Additional code scan on 2026-05-11 confirmed `MantidSnapper` remains the
  primary SNAPRed Mantid-consumption adapter for queued algorithm execution,
  workspace/log access, and algorithm-level logging.

---

## When to Use

Use this skill when:

- Writing new SNAPRed recipes, services, or request handlers.
- Debugging calibration or reduction behavior inside the backend.
- Understanding how SNAPWrap requests flow through SNAPRed.
- Adding hooks, state-dependent persistence, or new workflow endpoints.

Do **not** use this skill when:

- You only need the SNAPWrap wrapper/API layer.
- You are making scientific workflow decisions rather than backend code changes.

---

## Process

1. **Start from the backend layer model** — SNAPRed is organized into four
  layers from outermost to innermost:

  ```text
  InterfaceController
     -> Service layer
        -> Data layer
          -> Recipe layer
  ```

  | Layer | Key class(es) | Role |
  |-------|--------------|------|
  | Interface | `InterfaceController` | Sole external entry point; validates, routes, and returns `SNAPResponse` |
  | Service | `Service`, `CalibrationService`, `ReductionService`, `SousChef` | Orchestration and path registration |
  | Data | `LocalDataService`, `DataFactoryService`, `GroceryService` | Persistence, caching, workspace loading |
  | Recipe | `Recipe[T]` and subclasses | Mantid-algorithm execution units |

  **[CHECKPOINT]**: Before changing code, identify which layer owns the change.

2. **Follow the request path through `InterfaceController`** — External callers
  such as SNAPWrap should enter through `InterfaceController.executeRequest()`.

  ```python
  from snapred.backend.api.InterfaceController import InterfaceController
  controller = InterfaceController.instance()
  response = controller.executeRequest(snap_request)
  ```

  If you find yourself bypassing the controller for normal request flow,
  you are likely breaking the intended architecture boundary.

3. **Understand the cooking metaphor before navigating the code** — SNAPRed's
  internal processing language is culinary by design.

  | Metaphor term | Code class / concept | Meaning |
  |---------------|---------------------|---------|
  | `Recipe` | `Recipe[Ingredients]` | Abstract processing workflow |
  | `Ingredients` | Pydantic models | Strongly typed workflow inputs |
  | `Groceries` | `Dict[str, WorkspaceName]` | Mantid workspace references |
  | `Pallet` | `Tuple[Ingredients, Dict[str, str]]` | One batch-processing unit |
  | `SousChef` | `backend/service/SousChef.py` | Prepares complex ingredients and caches reusable state |
  | `GroceryService` | `backend/data/GroceryService.py` | Loads workspace data and caches common resources |
  | `MakeDirtyDish` / `WashDishes` | Diagnostic-preservation / cleanup helpers | Workspace lifecycle control |

  Developer rule:

  - Use the metaphors to navigate backend code, but do not expose them in
    user-facing skill language.

4. **Implement work through the `Recipe` lifecycle instead of ad hoc Mantid
  calls** — Recipes should express the workflow in the standard sequence.

  Core abstract methods:

  - `chopIngredients()`
  - `unbagGroceries()`
  - `queueAlgos()`
  - `allGroceryKeys()`

  Concrete lifecycle:

  - `stirInputs()`
  - `prep()`
  - `cook()`
  - `cater()`

  Common concrete recipes include `PixelDiffCalRecipe`, `GroupDiffCalRecipe`,
  `ReductionRecipe`, `ApplyNormalizationRecipe`, and
  `PreprocessReductionRecipe`.

5. **Use `MantidSnapper` as the canonical Mantid integration surface** —
  SNAPRed consumes Mantid through `backend/recipe/algorithm/MantidSnapper.py`
  rather than through scattered direct calls in service logic.

  What `MantidSnapper` provides:

  - Dynamic Mantid algorithm access through `__getattr__()` and
    `AlgorithmManager.create(...)`.
  - Queued execution with `_algorithmQueue` and `executeQueue()`.
  - Workspace access via wrapped ADS access (`mantidSnapper.mtd[...]`).
  - SNAPRed-tagged run-log retrieval via `_CustomMtd.getSNAPRedLog(...)`.
  - Per-algorithm progress and logging integration through `snapredLogger`.

  Developer rule:

  - If you need new Mantid algorithm behavior in backend workflows, add it via
    recipe logic that queues work through `MantidSnapper` unless there is an
    explicit architectural reason not to.

6. **Route functionality through registered service paths** — Service methods
  are exposed through `@Register(...)` string paths.

  Common paths:

  | Path | Service | Purpose |
  |------|---------|---------|
  | `calibration/ingredients` | `CalibrationService` | Prepare DifCal ingredients |
  | `calibration/groceries` | `CalibrationService` | Fetch DifCal workspace names |
  | `calibration/` | `CalibrationService` | Run diffraction calibration |
  | `normalization/` | `CalibrationService` | Run normalization calibration |
  | `reduction/validate` | `ReductionService` | Validate reduction inputs |
  | `reduction/` | `ReductionService` | Run reduction |
  | `stateId/` | `StateIdLookupService` | Resolve state IDs |

  If you add a workflow, register it explicitly and make the path ownership
  obvious.

7. **Treat instrument state and state IDs as primary backend keys** — State IDs
  are 16-character SHAKE256 digests of rounded detector state.

  Formation steps:

  1. Read run-header PV values.
  2. Round them via the instrument `stateIdSchema`.
  3. Hash the rounded detector state into an `ObjectSHA`.

  Filesystem layout:

  ```text
  calibration.powder.home/{stateId}/lite|native/diffraction/v{version}/
  reduction.home/{stateId}/lite|native/{runNumber}/{timestamp}/
  ```

  Any code that ignores state-ID formation risks misrouting calibrations or
  reduction outputs.

8. **Understand calibration workflows before changing reduction behavior** —
  SNAPRed distinguishes `DifCal` from `NormCal` and persists each through an
  index structure.

  DifCal:

  - Pixel-level cross-correlation to derive logarithmic DIFC offsets.
  - Group-level focusing and peak fitting to set absolute d-spacing behavior.
  - Results tracked in the Calibration Index via `appliesTo`.

  NormCal:

  - Background subtraction from vanadium.
  - Absorption correction.
  - Smoothing outside expected Bragg regions.
  - Persistence as an unfocused event workspace.

  Current constraint:

  - SNAPRed currently fits `DIFC` only, not the full GSAS TOF parameter set.

9. **Preserve output-labelling semantics** — `reduced` versus `diagnostic` is
  determined from calibration state, not from subjective output quality.

  ```python
  isDiagnostic = (diffcalState != DiffcalStateMetadata.EXISTS
             or normalizationState != NormalizationStateMetadata.EXISTS)
  ```

  Approximation pathways include missing DifCal, missing NormCal, or alternate
  calibration files, and all continue-flag decisions are logged in the
  `ReductionRecord`.

10. **Use hooks as extension points, not code forks** — Hooks let external
  callers inject callbacks without editing SNAPRed internals.

  Key rule:

  - All registered hooks must execute successfully; `HookManager` raises if any
    registered hook fails to run.

11. **Respect the operational defaults** — Lite mode is the default because it
   reduces SNAP's native pixel count by about 64x, making all three workflows
   tractable for routine use. Native mode is expert-only and resource-heavy.

12. **Follow backend conventions for reliability** —

  Error handling:

  - Use `RecoverableException`, `ContinueWarning`, and
    `StateValidationException` rather than bare exceptions.

  Caching:

  - `SousChef` caches pixel groups and peaks.
  - `GroceryService` caches groupings, instruments, and normalizations.
  - Dump the `SousChef` cache when a pixel mask changes.

  Singletons:

  - Reset singleton services between tests to prevent state bleed.

  Configuration:

  - Read runtime config through `Config["key.path"]`.
  - Use `override.yml` for local testing overrides.

13. **Use the minimal workflow checklist when adding new functionality** —

  1. Define `Ingredients` in `backend/dao/ingredients/`.
  2. Define grocery keys.
  3. Implement the `Recipe` subclass and document expected inputs.
  4. Register a service method with `@Register`.
  5. Wire hooks if needed.
  6. Update calibration or normalization indexes if artifacts are produced.
  7. Write tests and reset singletons between cases.

**Exit criteria**: You can identify the correct SNAPRed layer for a change,
trace a request from interface to recipe execution, explain the state-ID and
calibration-index implications, and add or debug workflow logic without
breaking service-path, hook, or output-labelling conventions.

---

## Rationalizations

| Excuse | Rebuttal |
|--------|----------|
| "I can just add the logic directly in a service method and skip a recipe." | Recipes are the execution unit that keep Mantid workflow logic testable and structured. Bypassing them erodes the architecture and makes later reuse or batching harder. |
| "Calling Mantid directly in random places is faster than using `MantidSnapper`." | `MantidSnapper` centralizes queueing, workspace tracking, and SNAPRed log conventions. Bypassing it increases coupling and makes behavior harder to reason about and test. |
| "The cooking metaphor is silly, so I can ignore it." | The metaphor is deeply embedded in class and method names. Ignoring it makes the codebase harder to navigate and increases the odds of wiring the wrong abstraction. |
| "I can infer calibration behavior without checking the indexes or state IDs." | Calibration validity in SNAPRed is state- and index-driven. Skipping that model is how incorrect calibrations get associated with the wrong runs. |
| "Diagnostic versus reduced is basically a UI choice." | It is a backend semantic tied to calibration state and traceability. Changing or bypassing that logic breaks downstream trust in output labels. |
| "Singleton state probably will not matter in tests." | SNAPRed caches meaningful backend state. If you do not reset singletons, tests can pass or fail based on leftover state rather than the code under test. |

---

## Red Flags

- Code changes bypass `InterfaceController` for normal external request flow.
- Mantid algorithm logic is embedded directly in services instead of recipes.
- Direct Mantid calls bypass `MantidSnapper` in backend workflow code without a
  clear architectural exception.
- New functionality is added without a registered service path.
- State IDs or calibration indexes are bypassed in favor of hardcoded paths.
- Output-labelling logic is altered without reference to calibration-state
  semantics.
- Hooks are added without checking execution guarantees or lifecycle behavior.
- Lite-mode assumptions are broken without an explicit resource/performance
  reason.
- Tests do not reset singletons or account for cache invalidation.

---

## Verification

- [ ] The owning backend layer for the change is identified before editing.
- [ ] Request flow from `InterfaceController` to service to recipe is still
    coherent after the change.
- [ ] Mantid algorithm calls that belong to backend workflows are routed through
  `MantidSnapper` queueing/logging patterns.
- [ ] New workflow logic is implemented through a `Recipe` and registered
    service path when appropriate.
- [ ] State-ID and calibration-index behavior is preserved or deliberately
    updated with traceable rationale.
- [ ] Diagnostic versus reduced output semantics remain tied to calibration
    state.
- [ ] Hook usage is explicit and lifecycle-safe.
- [ ] Caches and singleton reset behavior are handled in tests.
- [ ] Local configuration/testing assumptions are documented when overrides are
    required.

Cross-references:

- SNAPWrap wrapper API: `sns-snapwrap-developer-guide`
- Reduction workflow overview: `sns-snap-reduction-workflow-overview`
- Calibration concepts and state controls: `sns-snap-calibration-and-geometry`
- Reduction failure modes: `sns-snap-reduction-diagnostics`
- SNAP instrument-specific decisions: `docs/instruments/sns-snap.md`
- Repository-level stable findings: `docs/ground_truths.md`
