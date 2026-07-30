---
name: discover-project-standards
description: >-
  Use when you need to locate repository instruction sources, human-written
  standards, and repository-selected tools for downstream review skills,
  without analyzing application code.
---

# Discover Project Standards

Discover repository instruction sources and human-written standards for the
current repository. This shared primitive does not analyze code.

## Instructions

Probe every supported location below. Read each existing instruction or
standards file. Do not infer standards from missing files.

| Category | Locations |
| --- | --- |
| Cursor workspace rules | `.cursorrules`, `.cursor/rules/*.mdc`, `.cursor/rules/*.md` |
| Agent instructions | `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `COPILOT.md`, `.github/copilot-instructions.md` |
| Contribution and docs standards | `CONTRIBUTING.md`; under `docs/`, discover style or coding guides by name (glob or filename keywords such as `style`, `standard`, `guide`, `conventions`) |
| Accumulated lessons | `lessons_learned.mdc` or similarly named lesson archives under `.cursor/rules/` |

Discover repository-local executable tool configuration (for example,
`pyproject.toml`, `package.json`, `Makefile`, CI workflows, formatter, linter,
or test-runner configuration) as evidence of repository-selected tools. Record
the selected tools and their source paths, but do not treat tool configuration
as narrative standards.

Record applicable precedence when the repository instructions or active agent
declare it. Do not invent a universal precedence: report conflicting or
unresolved precedence in **Conflicts**.

Do not treat another repository’s checked-in `assistants/shared/standards/` tree
(or any personal managed-standards mirror) as an implicit standard for the
target project unless that tree is part of the project under review.

## Output Contract

Return this stable logical result for downstream consumers:

```markdown
## Standards Discovery Inventory

### Ordered Instruction Sources
1. `AGENTS.md` — repository-declared precedence
2. `.cursor/rules/engineering.mdc` — no conflicting declaration

### Applicable Standards
- `CONTRIBUTING.md` — contribution requirements
- `docs/style-guide.md` — documentation style

### Repository-Selected Tools
- Ruff — `pyproject.toml`
- pytest — `pyproject.toml`

### Conflicts
- No conflict found.

### Unavailable Sources
- `GEMINI.md`, `COPILOT.md`, and lesson archives were not found.
```

When no applicable standards exist, say so explicitly in **Applicable
Standards** and stop after the inventory. When a source is unreadable or
discovery cannot cover a relevant location, record incomplete coverage in
**Unavailable Sources**.

## Boundaries

- Do not review code or diffs.
- Do not emit code-quality findings.
- Do not decide pass/fail.
- Do not edit files.
- Do not copy repository instructions into persistent personal state.

## Related Commands

- `review-project-standards` — Apply discovered standards to code under review
