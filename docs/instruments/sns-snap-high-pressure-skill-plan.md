# SNAP High-Pressure Skill Plan

Date: 2026-04-29
Status: Approved scope, ready for drafting

## Objective

Supplement SNAP reduction skills with scientific skills that capture high-pressure measurement realities (sample environment, physics-driven artifacts, and interpretation constraints), with SNAP-first scope.

## Scope Decisions

- Rollout mode: SNAP-only first.
- Initial skill set: all four skills below.
- New skill frontmatter policy: include `version: 1`.

## Skills To Author

1. `sns-snap-high-pressure-data-interpretation`
- Purpose: distinguish physical signal from sample-environment artifact in reduced data.
- Must include: SEEMeta-first interpretation for `assembly.dac` and `assembly.pe`.
- Core checks: broadening/splitting, structured background, Q-range loss, pressure-shift behavior.
- Cross-links: SNAP diagnostics + calibration skills.

2. `sns-snap-high-pressure-masking-strategy`
- Purpose: convert contamination/environment constraints into defensible masking actions.
- Core coverage: DAC/PE/gasket/media contamination classes; mask vs keep vs recalibrate decisions.
- Include conservative mask validation checks to avoid removing key sample reflections.
- Cross-links: reduction workflow + diagnostics skills.

3. `high-pressure-sample-environment-planning`
- Purpose: pre-measurement planning for sample environment tradeoffs and expected data constraints.
- SNAP-grounded but written as transferable planning guidance.
- Include required user inputs and expected planning outputs.

4. `high-pressure-basics`
- Purpose: compact scientific primer used by the three applied skills.
- Core concepts: nonhydrostaticity, attenuation, parasitic scattering, preferred orientation, pressure-media effects.
- Keep concise to prevent duplication.

## Authoring Order

1. `sns-snap-high-pressure-data-interpretation`
2. `sns-snap-high-pressure-masking-strategy`
3. `high-pressure-sample-environment-planning`
4. `high-pressure-basics`

## Quality and Evidence Requirements

- Use existing SNAP skill style: evidence tracking, explicit decision points, and operationally useful checklists.
- Classify claims where needed as: consensus, instrument-team convention, open interpretation.
- Keep explicit references to assembly context, especially `assembly.dac` and `assembly.pe`.

## Verification Checklist

1. Validate each new skill with `python -m neutron_skills.cli validate <skill-path>`.
2. Run `pytest tests/ -q -o addopts=""`.
3. Run retrieval smoke checks for queries: high-pressure, DAC, PE, assembly.dac, assembly.pe, nonhydrostatic.
4. Confirm each new skill has frontmatter `version: 1` and required metadata fields.

## Out of Scope For This Pass

- Broad SNS/HFIR multi-instrument expansion.
- Edits to unrelated skills owned by others.
