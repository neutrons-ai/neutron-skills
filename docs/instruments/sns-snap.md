# SNS SNAP (BL3) — Instrument-Specific Decisions

SNAP is a time-of-flight powder diffractometer at Beamline 3 of the
Spallation Neutron Source (SNS).

## Key references

- SNS facility data model (event mode, TOF, NeXus format, `EventWorkspace`):
  [docs/facilities/sns.md](../facilities/sns.md)
- Context-collection guide for authoring SNAP skills:
  [sns-snap-skill-context-intake.md](sns-snap-skill-context-intake.md)
- Phase 0 validation (docs-vs-code drift and evidence anchors):
  [sns-snap-phase0-validation.md](sns-snap-phase0-validation.md)

---

## 2026-04-29: Initial rollout scope

Decision:

- Initial SNAP skill contributions focus on data reduction.
- Future non-reduction SNAP skills (acquisition, planning, troubleshooting) are
  explicitly allowed; they follow the same naming and layout conventions.

Rationale:

- Reduction-first delivers immediate value while keeping the schema open.
- Provenance documentation improves trust and maintainability of skill
  instructions.

---

## 2026-04-29: Software stack layering

Decision:

- `snapwrap` is the primary human interface during reduction. Users write
  Python scripts that import and call `snapwrap`. All user-facing reduction
  calls go through `snapwrap`.
- `snapred` is the backend application that `snapwrap` wraps. Direct calls to
  `snapred` are not the user workflow.
- Mantid is the foundational framework that `snapred` is built on. It is a
  backend-to-the-backend and is rarely called directly by users.

Consequences for skill authoring:

- Skill instructions and workflow steps must be expressed in terms of
  `snapwrap` calls, because that is what users write.
- `snapred` context explains *why* `snapwrap` behaves as it does and what
  parameters are meaningful.
- Mantid context explains deep algorithmic behavior for diagnostics and edge
  cases; it should not appear in primary workflow steps.
- Provenance maps in skill bodies follow the order:
  `snapwrap` → `snapred` → Mantid.
