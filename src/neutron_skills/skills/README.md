# Curated neutron-scattering skills

Each subdirectory of this folder is a **domain**. Inside each domain, each
skill is its own subdirectory containing at minimum a `SKILL.md` file that
follows the [Agent Skills specification](https://agentskills.io/specification).

## Layout

```
skills/
├── general-scattering/
├── sans/
├── diffraction/
├── reflectometry/
├── inelastic/
└── spectroscopy/
```

## Authoring rules

- Skill directory name **must match** the `name:` field in the frontmatter
  (lowercase, hyphens only).
- Keep `SKILL.md` under ~500 lines. Move long reference material to a
  `references/` subdirectory.
- Put scripts in `scripts/`, templates / data in `assets/`.
- Add `metadata.tags`, `metadata.instruments`, and `metadata.techniques`
  lists — these feed the deterministic retriever's scoring.
- If the skill relies on specific tools, list them in `allowed-tools`
  (space-separated).

## Instrument-specific skills (SNS and HFIR)

The project is expected to scale to instrument-specific skills across SNS and
HFIR. To keep retrieval behavior stable, use the conventions below.

### Naming and layout

- Use the global naming pattern `facility-instrument-topic` for
  instrument-specific skills (for example `sns-snap-reduction-diagnostics`).
- Keep all runnable skills at the flat path:
  `src/neutron_skills/skills/<domain>/<skill-name>/SKILL.md`.
- Do not place skill `SKILL.md` files under nested trees like
  `.../instruments/<facility>/<instrument>/...`; those paths can infer the
  wrong domain during retrieval.

### Metadata contract

For instrument-specific skills, populate the usual retrieval fields and the
recommended extension fields:

- Required in practice:
  - `metadata.instruments`
  - `metadata.techniques`
  - `metadata.tags`
- Recommended for scale and provenance:
  - `metadata.facility` (for example `SNS` or `HFIR`)
  - `metadata.software` (for example `Mantid`, `snapred`, `snapwrap`)
  - `metadata.data_phase` (for example `reduction`, `analysis`, `acquisition`)
  - `metadata.beamline` (for example `BL3` when relevant)

### SNAP rollout policy

- Initial SNAP scope is data-reduction skills.
- Reduction skills should state workflow provenance in the body (whether
  guidance comes from Mantid, `snapred`, `snapwrap`, or a combined flow).
- Additional non-reduction SNAP skills are allowed later; the naming and layout
  scheme above remains the same.

### Calibration policy for TOF instruments

When writing calibration skills for SNS/HFIR TOF instruments:

- Separate content into two layers:
  - Core TOF calibration principles (cross-instrument and reusable).
  - Instrument-specific implementation (for example SNAP-specific state behavior).
- Mark claims by confidence class in author notes and evidence packets:
  - `consensus`: broadly valid physical/analysis constraints.
  - `instrument-team convention`: currently adopted local workflow/defaults.
  - `open interpretation`: legitimate scientific disagreement or active development.
- Keep historical sources explicit when they are concept-only references rather
  than current production implementations.
- For SNAP, use plain language in user-facing skills; keep SNAPRed cooking
  metaphors internal to contributor notes.

### Instrument-specific ingestion helpers

If an instrument needs custom code to discover, ingest, or enrich source material
for skill development, put that code under:

- `src/neutron_skills/instruments/<facility>/<instrument>/`

Examples:

- SNAP-specific ingestion helpers live under
  `src/neutron_skills/instruments/sns/snap/`

If small, stable reference artifacts are useful to keep with a skill, store
those snapshots in that skill's `assets/` directory. Keep the evolving,
full-scale source artifact external and ingest it via the instrument helper.

Keep shared registry/retrieval logic out of this tree unless it is truly reusable
across instruments.

See [docs/ground_truths.md](../../../docs/ground_truths.md) for the decision
record and rationale.

## SNAP starter template (reduction-first)

Use this template when creating a new SNAP reduction skill:

For planning what context to collect before writing the skill, use
[docs/instruments/sns-snap-skill-context-intake.md](../../../docs/instruments/sns-snap-skill-context-intake.md).

```md
---
name: sns-snap-<topic>
description: <One-sentence intent and when-to-use guidance.>
metadata:
  facility: SNS
  beamline: BL3
  instruments: [SNAP, SNS]
  software: [snapwrap, snapred, Mantid]
  data_phase: reduction
  techniques: [diffraction, powder-diffraction, time-of-flight, data-reduction]
  tags: [<tag-1>, <tag-2>, <tag-3>]
---

# <Title>

## Provenance map

- snapwrap (user interface — fill first):
  - List the snapwrap calls users write in their reduction scripts.
- snapred (backend logic):
  - List snapred operations that snapwrap delegates to.
- Mantid (framework — for diagnostics/edge cases):
  - List Mantid algorithms invoked internally.

## Workflow

1. Step one
2. Step two
3. Step three

## Diagnostics and quality gates

- Metric/check 1
- Metric/check 2

## Required context from user

- Run numbers or dataset identifiers
- Calibration inputs and validity window
- Known masking/background constraints
```

Validate with:

```bash
neutron-skills validate src/neutron_skills/skills/<domain>/<skill-name>
```
