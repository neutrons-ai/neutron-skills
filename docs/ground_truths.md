# Ground Truths

This file records stable project decisions that should guide future skill
contributions and retrieval behavior.

## 2026-04-29: Instrument-specific schema for SNS/HFIR scale

Decision:

- Use instrument-specific skill names in the form `facility-instrument-topic`.
- Keep skill file layout flat by domain:
  `src/neutron_skills/skills/<domain>/<skill-name>/SKILL.md`.
- Do not store runnable skill files in nested instrument trees.

Rationale:

- Domain inference and staged retrieval rely on the domain folder in the
  canonical flat path.
- Flat placement avoids ambiguous domains and keeps deterministic and LLM-backed
  retrieval behavior aligned.
- A global naming pattern scales to SNS and HFIR as the registry grows toward
  all instruments.

## Facility data models

Facility-level data model facts (source type, event format, NeXus schema,
Mantid workspace types) live in `docs/facilities/`:

- [docs/facilities/sns.md](facilities/sns.md) — SNS pulsed source, event mode, TOF
- [docs/facilities/hfir.md](facilities/hfir.md) — HFIR steady-state source, event mode

## 2026-04-29: Instrument knowledge ingestion workflow

Decision:

- Instrument skills are authored via a multi-phase ingestion process: docs-first baseline,
  then facility-specific (red for calibration, wrap for user workflows), then script-corpus
  pattern mining, then skill authoring.
- Each phase produces evidence anchors that skills must cite for traceability and
  maintainability.
- Public docs are treated as candidate truth and validated against current source code
  before skill writing begins.

Consequences:

- Skills include explicit evidence links: source page, code repository, commit-pinned locations.
- Drift between public docs and code is tracked in per-instrument Phase 0 validation reports.
- Calibration is ingested as a separate track from user-workflow ingestion, since
  calibration lives in SNAPRed (backend) while user scripts call SNAPWrap (frontend).
- Script-corpus analysis is deferred until after calibration and wrap-API baselines are
  stable, reducing rework from API drift.

Next phases:

- Phase 1: Calibration foundation (red-rooted)
- Phase 2: Wrap API baseline
- Phase 3: Script corpus mini-phase
- Phase 4: Skill authoring feed

## 2026-04-29: TOF calibration skill layering and evidence classes

Decision:

- Calibration skill content is split into:
  - Core TOF principles (cross-instrument reusable), and
  - Instrument-specific implementation guidance.
- Calibration claims should be tagged during authoring as one of:
  - consensus,
  - instrument-team convention,
  - open interpretation.
- Historical sources can be used for conceptual precedent, but must not be used
  to assert current production implementation behavior unless corroborated.

Consequences:

- The skill set can scale across SNS/HFIR instruments while preserving scientific nuance.
- Differing expert opinions are represented explicitly instead of hidden as false certainty.
- SNAP user-facing skills remain plain-language and operational, while internal
  metaphor-heavy source code terminology remains contributor-only context.

## 2026-04-29: Instrument-specific ingestion helpers live with instrument code

Decision:

- Instrument-specific ingestion and acquisition helpers live under the package path:
  `src/neutron_skills/instruments/<facility>/<instrument>/`.
- Generic registry and retrieval code stays at the top-level `neutron_skills` package.
- CLI entry points may call instrument-specific ingestion helpers, but the implementation
  should remain in the instrument namespace.

Consequences:

- Instruments can evolve custom ingestion pipelines without polluting the shared core.
- SNAP-specific corpus ingestion can grow under `neutron_skills.instruments.sns.snap`.
- Future HFIR/SNS instruments can follow the same pattern for custom discovery,
  enrichment, and evidence-building tooling.

## 2026-04-29: Ingestion helper location vs skill assets snapshots

Decision:

- Keep instrument ingestion helper code in
  `src/neutron_skills/instruments/<facility>/<instrument>/`.
- Keep primary, evolving corpus artifacts external to this repository.
- Allow small, stable reference snapshots under a skill's `assets/` folder when
  those files are useful for reproducible examples or future reference.

Rationale:

- Maintains a clean boundary between executable ingestion code and large/evolving
  external datasets.
- Supports maintainer preference that helpful reference material may live with
  skills without coupling the code path to repository-bound data files.

## 2026-04-30: Prototype human-review metadata convention for skills

Decision:

- Skills may include an optional `review` frontmatter block during prototype-stage
  curation.
- Recommended fields are:
  - `status`
  - `reviewer`
  - `reviewed_on`
  - `basis`
  - `notes`
- This metadata records human review provenance, but is not itself a cryptographic
  authenticity mechanism.

Rationale:

- Keeps review state visible in the skill file without changing loader behavior.
- Fits the current parser, which preserves extra frontmatter fields.
- If stronger authentication is needed later, use signed git commits or tags
  rather than in-file signatures.

## 2026-05-01: High-pressure analysis requires pressure-state indexing

Decision:

- For high-pressure analysis-stage skills, ambient-pressure structures are
  treated as starting guesses only.
- Rietveld workflows should pre-index the measured high-pressure lattice
  before full refinement when peak shifts are significant.
- Background extraction methods that depend on Bragg-peak locations must use
  pressure-appropriate peak positions rather than ambient references.

Rationale:

- Pressure can induce anisotropic and non-uniform peak shifts, especially in
  low-symmetry and layered structures.
- Seeding refinement from ambient parameters alone can lead to unstable or
  biased fits.
- Incorrect peak masks can bias peak/background deconvolution and downstream
  refined parameters.

Reference:

- [src/neutron_skills/skills/diffraction/sns-snap-high-pressure-data-interpretation/SKILL.md](../src/neutron_skills/skills/diffraction/sns-snap-high-pressure-data-interpretation/SKILL.md)

## Instrument-specific decisions

Decisions that are scoped to a single instrument live in `docs/instruments/`.
See [docs/instruments/sns-snap.md](instruments/sns-snap.md) for SNAP.
