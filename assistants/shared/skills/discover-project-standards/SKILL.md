---
name: discover-project-standards
description: >-
  Use when you need to locate human-written project standards and lesson
  archives in a repository and return a concise inventory for downstream
  review skills, without analyzing application code.
---

<!-- markdownlint-disable -->

# Discover Project Standards

Discover human-written standards and lesson files for the current repository.
This skill is a shared primitive for review workflows; it does not analyze code.

## Instructions

Probe the paths below. Read every path that exists. Do not infer standards from
missing files.

| Category | Locations |
|----------|-----------|
| Cursor workspace rules | `.cursor/rules/*.mdc`, `.cursor/rules/*.md` |
| Agent instructions | `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `COPILOT.md`, `.github/copilot-instructions.md` |
| Contribution and docs standards | `CONTRIBUTING.md`; under `docs/`, discover style or coding guides by name (glob or filename keywords such as `style`, `standard`, `guide`, `conventions`) |
| Accumulated lessons | `lessons_learned.mdc` or similarly named lesson archives under `.cursor/rules/` |

Do not treat another repository’s checked-in `assistants/shared/standards/` tree
(or any personal managed-standards mirror) as an implicit standard for the
target project unless that tree is part of the project under review.

## Output Contract

Return a compact inventory with:

1. **Found files** by category
2. **Missing expected locations** by category
3. **Prioritized files to read first** (when many files exist)
4. **Coverage note** (for example: "No lessons file found; proceeding with rule files only")

Use this structure:

```markdown
## Standards Discovery Inventory

### Found
- Cursor workspace rules: `.cursor/rules/104_python_style_guide.mdc`, ...
- Agent instructions: `CLAUDE.md`
- Contribution/docs standards: `CONTRIBUTING.md`
- Accumulated lessons: `.cursor/rules/lessons_learned.mdc`

### Missing
- Agent instructions: `AGENTS.md`, `GEMINI.md`, `COPILOT.md`

### Prioritized Read Order
1. `.cursor/rules/104_python_style_guide.mdc`
2. `.cursor/rules/test_rules_micro.mdc`
3. `CLAUDE.md`

### Coverage Note
No lesson archive beyond `lessons_learned.mdc` found.
```

When no applicable standards files exist, say so plainly, leave Found empty or
nearly empty, list Missing expected locations, and stop after the inventory.

## Boundaries

- Do not review code or diffs.
- Do not emit code-quality findings.
- Do not decide pass/fail.
- Do not edit files.
- Do not copy repository instructions into persistent personal state.

## Related Commands

- `review-project-standards` — Apply discovered standards to code under review
