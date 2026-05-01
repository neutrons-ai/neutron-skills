## Summary

- What changed?
- Why was this needed?

## Change Type

- [ ] Skill content update
- [ ] Python/library code change
- [ ] Tests only
- [ ] Documentation only
- [ ] Other

## Validation

- [ ] Ran relevant validation/tests
- [ ] Included command outputs in PR description when useful

Commands run:

```bash
# Example
# pixi exec --spec python=3.11 --spec click --spec pyyaml env PYTHONPATH=src python -m neutron_skills.cli validate <path>
```

## Human Skill Review (content approval only)

Complete this section when the PR includes one or more `SKILL.md` content updates.
This is separate from code/test/security/design reviews.

- [ ] `review.status` is `human-reviewed` for approved skills (or clearly `pending` if not approved yet)
- [ ] `review.reviewer`, `review.reviewed_on`, and `review.basis` are populated for approved skills
- [ ] `review.approved_commit` follows `review/<skill-name>-v1`
- [ ] Review tag exists and points to the approval commit: `review/<skill-name>-v1`

Reviewed skills and tags:

- Skill: <!-- e.g., src/neutron_skills/skills/diffraction/sns-snap-high-pressure-data-interpretation/SKILL.md -->
- Tag: <!-- e.g., review/sns-snap-high-pressure-data-interpretation-v1 -->

## Other Review Types (as applicable)

- [ ] Code review completed (implementation quality)
- [ ] Test review completed (coverage/value)
- [ ] Security review completed (vulnerabilities/secrets)
- [ ] Design review completed (architecture/UX)

## Notes for Reviewers

- Any known follow-up work?
- Any intentional limitations?
