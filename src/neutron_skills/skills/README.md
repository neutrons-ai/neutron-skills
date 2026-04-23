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

Validate with:

```bash
neutron-skills validate src/neutron_skills/skills/<domain>/<skill-name>
```
