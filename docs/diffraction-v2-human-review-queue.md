# Diffraction v2 Human Review Queue

This queue covers all skills in the diffraction domain.

Review policy for this queue:

- One skill review per commit.
- One tag per review commit (`review/<skill-name>-v2`).
- Update only that skill's `review` frontmatter block for each review commit.
- Start each review commit from a clean commit boundary (`git status --short`).

## Scope (8 skills)

1. `sns-snap-reduction-workflow-overview`
2. `sns-snap-reduction-diagnostics`
3. `sns-snap-calibration-and-geometry`
4. `sns-snap-sample-environment-reduction-special-cases`
5. `sns-snap-high-pressure-data-interpretation`
6. `sns-snapred-developer-guide`
7. `sns-snapwrap-developer-guide`
8. `rietveld-refinement-workflow`

## Tracking table

| Skill | Status | Reviewed on | Commit | Tag | Notes |
|---|---|---|---|---|---|
| sns-snap-reduction-workflow-overview | completed | 2026-05-05 | 72025a0 | review/sns-snap-reduction-workflow-overview-v2 | v2 human review approved |
| sns-snap-reduction-diagnostics | completed | 2026-05-05 | 7762b9e | review/sns-snap-reduction-diagnostics-v2 | v2 human review approved |
| sns-snap-calibration-and-geometry | completed | 2026-05-05 | d1bbb7a | review/sns-snap-calibration-and-geometry-v2 | expanded to 4 workflow branches A-D |
| sns-snap-sample-environment-reduction-special-cases | completed | 2026-05-05 | 4aef3b6 | review/sns-snap-sample-environment-reduction-special-cases-v2 | v2 human review approved; artifact-gathering flow clarified |
| sns-snap-high-pressure-data-interpretation | completed | 2026-05-05 |  | review/sns-snap-high-pressure-data-interpretation-v2 | v2 human review approved |
| sns-snapred-developer-guide | pending |  |  |  |  |
| sns-snapwrap-developer-guide | completed | 2026-05-07 | e036451 | review/sns-snapwrap-developer-guide-v2 | v2 technical accuracy: cleanTheTree, bin-mask naming, config layer, hook lifecycle |
| rietveld-refinement-workflow | completed | 2026-05-07 | — | review/rietveld-refinement-workflow-v2 | v2 parameter release order; software capability notes; metric interpretation guidance |

## Per-skill review sequence

For each skill below, do this sequence after you complete the human content review and update frontmatter:

0. Confirm clean boundary with `git status --short`.
1. Validate the skill.
2. Stage only that `SKILL.md`.
3. Re-check staged set with `git status --short` (only one skill file staged).
4. Commit with `Review <skill-name> skill (v2)`.
5. Tag with `review/<skill-name>-v2`.
6. Push branch and tag.

### 1) sns-snap-reduction-workflow-overview

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src \
  python -m neutron_skills.cli validate src/neutron_skills/skills/diffraction/sns-snap-reduction-workflow-overview

git add src/neutron_skills/skills/diffraction/sns-snap-reduction-workflow-overview/SKILL.md
git status --short
git commit -m "Review sns-snap-reduction-workflow-overview skill (v2)"
git tag review/sns-snap-reduction-workflow-overview-v2
git push origin <branch>
git push origin review/sns-snap-reduction-workflow-overview-v2
```

### 2) sns-snap-reduction-diagnostics

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src \
  python -m neutron_skills.cli validate src/neutron_skills/skills/diffraction/sns-snap-reduction-diagnostics

git add src/neutron_skills/skills/diffraction/sns-snap-reduction-diagnostics/SKILL.md
git status --short
git commit -m "Review sns-snap-reduction-diagnostics skill (v2)"
git tag review/sns-snap-reduction-diagnostics-v2
git push origin <branch>
git push origin review/sns-snap-reduction-diagnostics-v2
```

### 3) sns-snap-calibration-and-geometry

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src \
  python -m neutron_skills.cli validate src/neutron_skills/skills/diffraction/sns-snap-calibration-and-geometry

git add src/neutron_skills/skills/diffraction/sns-snap-calibration-and-geometry/SKILL.md
git status --short
git commit -m "Review sns-snap-calibration-and-geometry skill (v2)"
git tag review/sns-snap-calibration-and-geometry-v2
git push origin <branch>
git push origin review/sns-snap-calibration-and-geometry-v2
```

### 4) sns-snap-sample-environment-reduction-special-cases

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src \
  python -m neutron_skills.cli validate src/neutron_skills/skills/diffraction/sns-snap-sample-environment-reduction-special-cases

git add src/neutron_skills/skills/diffraction/sns-snap-sample-environment-reduction-special-cases/SKILL.md
git status --short
git commit -m "Review sns-snap-sample-environment-reduction-special-cases skill (v2)"
git tag review/sns-snap-sample-environment-reduction-special-cases-v2
git push origin <branch>
git push origin review/sns-snap-sample-environment-reduction-special-cases-v2
```

### 5) sns-snap-high-pressure-data-interpretation

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src \
  python -m neutron_skills.cli validate src/neutron_skills/skills/diffraction/sns-snap-high-pressure-data-interpretation

git add src/neutron_skills/skills/diffraction/sns-snap-high-pressure-data-interpretation/SKILL.md
git status --short
git commit -m "Review sns-snap-high-pressure-data-interpretation skill (v2)"
git tag review/sns-snap-high-pressure-data-interpretation-v2
git push origin <branch>
git push origin review/sns-snap-high-pressure-data-interpretation-v2
```

### 6) sns-snapred-developer-guide

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src \
  python -m neutron_skills.cli validate src/neutron_skills/skills/diffraction/sns-snapred-developer-guide

git add src/neutron_skills/skills/diffraction/sns-snapred-developer-guide/SKILL.md
git status --short
git commit -m "Review sns-snapred-developer-guide skill (v2)"
git tag review/sns-snapred-developer-guide-v2
git push origin <branch>
git push origin review/sns-snapred-developer-guide-v2
```

### 7) sns-snapwrap-developer-guide

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src \
  python -m neutron_skills.cli validate src/neutron_skills/skills/diffraction/sns-snapwrap-developer-guide

git add src/neutron_skills/skills/diffraction/sns-snapwrap-developer-guide/SKILL.md
git status --short
git commit -m "Review sns-snapwrap-developer-guide skill (v2)"
git tag review/sns-snapwrap-developer-guide-v2
git push origin <branch>
git push origin review/sns-snapwrap-developer-guide-v2
```

### 8) rietveld-checklist

```bash
pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src \
  python -m neutron_skills.cli validate src/neutron_skills/skills/diffraction/rietveld-checklist

git add src/neutron_skills/skills/diffraction/rietveld-checklist/SKILL.md
git status --short
git commit -m "Review rietveld-checklist skill (v2)"
git tag review/rietveld-checklist-v2
git push origin <branch>
git push origin review/rietveld-checklist-v2
```
