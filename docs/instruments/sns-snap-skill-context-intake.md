# SNAP Skill Context Intake

This guide defines the fastest way to provide context for writing accurate SNAP
skills, starting with data reduction and staying extensible to non-reduction
work later.

## Goal

Produce skill-ready context packets that are:

- Traceable to sources in snapwrap, snapred, and Mantid (in that priority order)
- Scoped to one skill topic at a time
- Easy to convert into SKILL.md instructions and diagnostics

## Data model

SNAP data follows the SNS event-mode model. See
[docs/facilities/sns.md](../facilities/sns.md) for the full reference
(event lists, TOF, NeXus/HDF5 format, PV logs, `EventWorkspace`).

## Evidence tracking for skills

Each skill must include evidence anchors linking back to the sources that inform
its claims. Use this pattern:

```
Evidence: Phase 0 SNAP docs validation
Source: https://powder.ornl.gov/bragg_diffraction/data_reduction/snap.html
Verification: SNAPWrap [module].py, SNAPRed [module].py
Date: 2026-04-29
Phase: 0 (baseline) | 1 (calibration) | 2 (wrap API) | 3 (patterns)
```

For drift findings or unresolved questions, reference the validation report:
[sns-snap-phase0-validation.md](sns-snap-phase0-validation.md)

## Software stack

See [sns-snap.md](sns-snap.md) for the full
stack-layering decision and rationale. Summary:

- `snapwrap` is the main human interface. Users run reduction by writing
  Python scripts that import and call `snapwrap`.
- `snapred` is the backend application that `snapwrap` wraps.
- Mantid is the scientific framework that `snapred` is built on.
  It is rarely called directly by users.

When documenting a workflow: **start with what the user calls in `snapwrap`,
then explain what `snapred` does, then only go as deep as Mantid when
necessary**.

## Intake workflow

1. Pick one target skill topic.
2. Gather source evidence from snapwrap first, then snapred, then Mantid.
3. Fill the context packet template in this document.
4. Review for missing assumptions, edge cases, and failure modes.
5. Hand off packet to skill-authoring step.

## Priority topic order (reduction first)

1. sns-snap-reduction-workflow-overview
2. sns-snap-calibration-and-geometry
3. sns-snap-reduction-diagnostics

After these, extend to additional reduction topics, then non-reduction topics.

## Context packet template

Copy and complete this template per skill:

```md
# Context Packet: <skill-name>

## 1. Scope
- Intended use:
- Out of scope:
- Data phase: reduction | analysis | acquisition | troubleshooting

## 2. Source map
- snapwrap modules/files (primary — what users call):
- snapred modules/files (backend logic snapwrap delegates to):
- Mantid algorithms/APIs (framework internals, for edge cases):
- External docs or notebooks:

## 3. Canonical workflow
1. Step:
2. Step:
3. Step:

## 4. Inputs and configuration
- Required inputs:
- Optional inputs:
- Default values:
- Units and coordinate conventions:

## 5. Quality gates and diagnostics
- Success criteria:
- Metrics/plots to inspect:
- Warning signs:
- Failure signatures and likely causes:

## 6. Edge cases
- Sparse statistics:
- Missing/invalid metadata:
- Calibration mismatch:
- Masking/background anomalies:

## 7. Provenance and evidence
- Evidence 1: <file, function, command, doc section>
- Evidence 2:
- Evidence 3:

## 8. Open questions
- Q1:
- Q2:
```

## Minimum evidence standard

For each skill packet, provide at least:

- One concrete workflow reference from snapwrap (the user-facing call)
- One concrete workflow reference from snapred (what snapwrap delegates to)
- One Mantid algorithm/API reference (only needed for diagnostics/edge cases)
- One diagnostic or troubleshooting reference

## Evidence formatting guidelines

When sharing references, include:

- Repository name
- File path
- Function/class name
- Short quote or paraphrase of behavior
- Why it matters to the target skill

Also classify each claim using one of the following labels:

- `consensus`: broadly valid cross-instrument concept.
- `instrument-team convention`: local policy/default currently used for SNAP.
- `open interpretation`: plausible scientific alternatives exist; document tradeoffs.

Example:

- Repo: snapred
- File: path/to/reducer.py
- Symbol: build_reduction_plan
- Behavior: Applies calibration then normalization before binning.
- Relevance: Defines canonical operation order for reduction workflow skill.

## Authoring handoff checklist

Before turning a context packet into SKILL.md:

- Scope and out-of-scope are explicit.
- Provenance map is ordered snapwrap → snapred → Mantid.
- Workflow steps are written from the snapwrap user perspective.
- Diagnostics include specific failure signatures.
- Open questions are either resolved or called out in the skill text.
- User-facing language avoids internal SNAPRed cooking metaphors.
- If output labels are discussed, both valid pathways are represented:
  - use `diagnostic` output for exploratory work, or
  - calibrate and rerun for final `reduced` output.

## Extension path for non-reduction SNAP skills

When you are ready to expand beyond reduction, reuse the same packet format and
set Data phase to one of:

- analysis
- acquisition
- experiment-planning
- troubleshooting

This keeps one consistent authoring process across all future SNAP topics.
