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

## 2026-05-05: Skill architecture v2 is workflow-first and verifiable

Decision:

- Skills migrated to `version: 2` follow a consistent anatomy:
  - `Overview`
  - `When to Use`
  - `Process`
  - `Rationalizations`
  - `Red Flags`
  - `Verification`
- Frontmatter keeps the canonical identity contract:
  - `name`: lowercase-hyphen skill identifier matching directory name.
  - `description`: concise "guides agents through ... use when ..." intent.
- `Process` is mandatory workflow content, not background prose. It must include
  actionable steps and should include checkpoints and exit criteria where
  appropriate.
- `Rationalizations` is mandatory anti-rationalization content: common excuses
  and explicit rebuttals.
- `Verification` is mandatory and evidence-driven: completion requires concrete
  checks (validation commands, test/build/runtime evidence), not subjective
  confidence.
- Progressive disclosure is the default: keep `SKILL.md` focused on execution,
  and load extended references/assets only when needed.

Rationale:

- A fixed anatomy improves retrieval and agent execution consistency.
- Workflow-first structure reduces omission risk and makes behavior auditable.
- Anti-rationalization plus explicit verification hardens quality gates.
- Progressive disclosure controls token usage while preserving depth on demand.

Source:

- Architecture pattern adapted from: https://github.com/addyosmani/agent-skills
- Project-local adoption context: refactors marked `version: 2` in
  `src/neutron_skills/skills/diffraction/*/SKILL.md`.
- Contributor-facing operational guide:
  [SKILL_AUTHORING_AND_REVIEWING.md](../SKILL_AUTHORING_AND_REVIEWING.md)

## 2026-05-05: Skill validation commands use explicit pixi specs and PYTHONPATH

Decision:

- Validate skills with explicit pixi specs and source-path import context:

  `pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src python -m neutron_skills.cli validate <target>`

- Do not rely on implicit/default pixi environment selection for validation
  commands in this repository.

Rationale:

- In this repository, `pixi exec` without explicit specs can fail environment
  solving (`No candidates were found for env *`).
- Running without `PYTHONPATH=src` can fail module discovery for
  `python -m neutron_skills.cli`.
- The explicit command shape has been repeatedly successful and is now the
  stable validation baseline.

Reference:

- [src/neutron_skills/cli.py](../src/neutron_skills/cli.py)
- [SKILL_AUTHORING_AND_REVIEWING.md](../SKILL_AUTHORING_AND_REVIEWING.md)

## 2026-05-05: Diffraction v2 human reviews are tracked as one-skill-per-commit

Decision:

- For diffraction-domain v2 human skill reviews, each reviewed skill is recorded
  with exactly one review commit and one matching review tag.
- Tag format: `review/<skill-name>-v2`.
- Review tracking and copy/paste command sequence are maintained in:
  `docs/diffraction-v2-human-review-queue.md`.

Rationale:

- One-skill-per-commit keeps review provenance auditable and easy to roll back
  or inspect.
- Per-skill tags make approved versions explicit for downstream references.
- A single queue document reduces process drift during multi-skill review waves.

Operational outline:

- The contributor-facing review procedure, checklist, and frontmatter examples
  are maintained in
  [SKILL_AUTHORING_AND_REVIEWING.md](../SKILL_AUTHORING_AND_REVIEWING.md).

Reference:

- [docs/diffraction-v2-human-review-queue.md](diffraction-v2-human-review-queue.md)

## Instrument-specific decisions

Decisions that are scoped to a single instrument live in `docs/instruments/`.
See [docs/instruments/sns-snap.md](instruments/sns-snap.md) for SNAP.
