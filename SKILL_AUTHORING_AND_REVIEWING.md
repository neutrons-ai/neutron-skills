# Skill Authoring And Reviewing

This guide is the contributor-facing reference for creating, validating, and
human-reviewing skills in this repository. It complements
[docs/ground_truths.md](docs/ground_truths.md), which records the stable project
decisions behind this process.

## When To Use This Guide

Use this document when you are:

- creating a new skill;
- migrating an existing skill to `version: 2`;
- preparing a skill for human review; or
- running a documented human review campaign.

## Skill Layout

Skills live at:

`src/neutron_skills/skills/<domain>/<skill-name>/SKILL.md`

Rules:

- `<skill-name>` should be lowercase-hyphen and should match the frontmatter
  `name` field.
- Keep the skill layout flat by domain rather than nesting runnable skills under
  instrument-specific package trees.
- Place longer reference material in `assets/` only when it helps reproducible
  examples or future maintenance.
- Place executable helpers under `scripts/` when the skill needs tool-callable
  Python functions.

Typical layout:

```text
src/neutron_skills/skills/diffraction/example-skill/
  SKILL.md
  assets/
    reference-notes.md
  scripts/
    tools.py
```

## Skill Schema

Skills migrated to `version: 2` follow a workflow-first anatomy:

This repository's v2 skill anatomy is adapted from the workflow-oriented
skill structure documented in the
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)
project, then narrowed to this repository's validation and review needs.

1. `Overview`
2. `When to Use`
3. `Process`
4. `Rationalizations`
5. `Red Flags`
6. `Verification`

Required behavior:

- `Process` must contain actionable workflow steps, not background prose.
- `Rationalizations` must capture common excuses or weak shortcuts and rebut
  them.
- `Verification` must require concrete evidence such as validation commands,
  tests, runtime checks, or build outputs.
- Extended references should stay in `assets/` unless they are required for the
  main execution path.

## Frontmatter Contract

Minimum expected frontmatter:

```yaml
---
name: example-skill
description: Guides agents through the example workflow; use when the task matches the example scenario.
version: 2
metadata:
  facility: SNS
  instruments: [SNAP]
  techniques: [diffraction]
  tags: [example, workflow]
---
```

Authoring rules:

- `name` is the canonical identifier and should match the directory name.
- `description` should be brief and task-oriented.
- `version: 2` should be used for skills following the v2 anatomy.
- Extra metadata is allowed when the parser can preserve it.

Optional review block during human curation:

```yaml
review:
  status: human-reviewed
  reviewer: Malcolm Guthrie
  reviewed_on: 2026-05-07
  basis: [docs, code, instrument-science-review]
  notes: Clarified workflow boundaries and updated validation guidance.
```

Recommended review fields:

- `status`
- `reviewer`
- `reviewed_on`
- `basis`
- `notes`

## Authoring Workflow

1. Choose the correct domain and create the new skill directory.
2. Set the canonical frontmatter fields: `name`, `description`, `version`, and
   repository-appropriate metadata.
3. Draft the v2 anatomy in order: `Overview`, `When to Use`, `Process`,
   `Rationalizations`, `Red Flags`, `Verification`.
4. Keep `Process` procedural and verifiable. If a step matters, define how the
   agent or reviewer will know it succeeded.
5. Move long references, tables, or supporting notes into `assets/`.
6. Add `scripts/` helpers only if the skill benefits from executable tool
   calling.
7. Validate the skill before requesting review.

## Validation

Use the repository-standard validation command:

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src python -m neutron_skills.cli validate <target>
```

Examples:

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src python -m neutron_skills.cli validate src/neutron_skills/skills
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src python -m neutron_skills.cli validate src/neutron_skills/skills/diffraction/example-skill
```

Do not rely on an implicit pixi environment or omit `PYTHONPATH=src`.

## Human Review Workflow

Use this process when a skill is receiving a documented human review.

1. Validate the skill locally and fix structural issues first.
2. Review the content against current evidence: docs, code, and domain-science
   expectations.
3. Record review provenance in the skill frontmatter using the `review` block.
4. For diffraction v2 campaigns, keep review scope to one skill per commit.
5. Create a matching review tag in the form `review/<skill-name>-v2` once the
   review is approved.
6. Update the campaign tracker when one is in use, such as
   [docs/diffraction-v2-human-review-queue.md](docs/diffraction-v2-human-review-queue.md).
7. Preserve deferred skills explicitly as deferred rather than silently mixing
   them into the reviewed set.

## Human Review Checklist

- The skill validates cleanly.
- The `name` matches the directory name.
- The `description` is concise and use-oriented.
- The v2 anatomy is complete and ordered correctly.
- `Process` contains operational steps and checkpoints.
- `Verification` contains concrete evidence checks.
- Domain facts and implementation details are consistent with current sources.
- The `review` block reflects what was actually reviewed.

## Quick Start Template

```markdown
---
name: example-skill
description: Guides agents through the example workflow; use when the task matches the example scenario.
version: 2
metadata:
  facility: SNS
  instruments: [SNAP]
  techniques: [diffraction]
  tags: [example, workflow]
---

# Example Skill

## Overview

State the task, operating context, and evidence boundaries.

## When to Use

State the situations where this skill should be retrieved or applied.

## Process

1. Perform the first actionable step.
2. Check the result before continuing.
3. Complete the workflow with explicit exit criteria.

## Rationalizations

- "We can skip validation because the workflow is obvious."
  No. Validation is part of the deliverable.

## Red Flags

- Required evidence is missing.
- The workflow depends on assumptions that were not checked.

## Verification

- Run the repository validation command.
- Confirm the referenced evidence still matches the current workflow.
```

## Related References

- [README.md](README.md)
- [docs/ground_truths.md](docs/ground_truths.md)
- [docs/diffraction-v2-human-review-queue.md](docs/diffraction-v2-human-review-queue.md)