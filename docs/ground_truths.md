# Ground Truths

This file captures key findings, decisions, and verified facts discovered during development. It serves as a persistent knowledge base that AI assistants (like GitHub Copilot) and developers can reference across sessions.

**Why this matters:** AI assistants don't remember previous conversations. By recording important discoveries here, you ensure that context isn't lost between sessions. When Copilot reads this file, it can make better suggestions based on what's already been learned about your project.

## How to Use This File

- **Add entries as you discover important facts** — things like API quirks, configuration requirements, performance constraints, or design decisions.
- **Include the date and context** so future-you (or Copilot) understands why something was noted.
- **Link to relevant code or docs** when helpful.
- Copilot is instructed to update this file automatically when it discovers key findings during development.

## Findings

### 2026-04-23: Project identity and package layout
- Distribution name: `neutron-skills`. Python import name: `neutron_skills`
  (hyphens are invalid in Python module names).
- The package is a curated registry of **Agent Skills** (per
  [agentskills.io/specification](https://agentskills.io/specification)) for
  neutron scattering, consumable by other agents via a `retrieve()` API and a
  Click-based CLI.

### 2026-04-23: Skill discovery sources
- Two discovery sources supported: (a) skills **bundled** with the package
  under `src/neutron_skills/skills/<domain>/<skill-name>/` and (b) additional
  **external** paths supplied by the caller/CLI.
- Name collisions: project-level/external paths override bundled skills; log a
  warning on shadowing (per the client-implementation guide).

### 2026-04-23: Meaning of "tools" in `retrieve()`
- `retrieve(query) -> (skills, tools)` returns:
  - `skills`: a list of matched `Skill` objects (name, description, body, path).
  - `tools`: the union of `allowed-tools` tokens parsed from each matched
    skill's frontmatter (space-separated string per spec, split into a list).
- No MCP/tool-object abstraction at this stage — just the `allowed-tools`
  strings from the YAML frontmatter.

### 2026-04-23: Retrieval strategies
- Two retrieval backends, both supported:
  1. **Deterministic** (default, offline, zero extra deps): keyword/tag scoring
     over `name`, `description`, and `metadata` (tags/instruments/techniques).
     Used as the fallback and for tests.
  2. **LLM-based** (preferred when available): send only the skill *catalog*
     (name + description — tier 1 of progressive disclosure) to an LLM and
     have it select relevant skill names. Full bodies are only loaded for the
     selected skills. Backend is pluggable via a small `LLMSelector` protocol
     so callers can inject their own client (OpenAI, Anthropic, local, etc.)
     without the package taking a hard dependency.
- Public API: `retrieve(query, *, method="auto"|"deterministic"|"llm", selector=None, extra_paths=None, top_k=5)`.
  `"auto"` uses LLM if a selector is provided, else deterministic.

### 2026-04-23: Spec constraints to enforce
- `SKILL.md` requires YAML frontmatter with `name` (≤64 chars, lowercase
  alphanumerics + single hyphens, matching parent directory) and `description`
  (≤1024 chars). Optional: `license`, `compatibility`, `metadata`,
  `allowed-tools` (experimental, space-separated).
- Lenient validation per the client-implementation guide: warn but load when
  `name` mismatches the directory or exceeds length; skip only when YAML is
  unparseable or `description` is missing.
- Keep `SKILL.md` under ~500 lines; detailed content belongs in
  `references/` / `scripts/` / `assets/`.
