---
name: review-project-standards
description: >-
  Use when reviewing code against the repository’s human-written coding
  standards and accumulated lessons. Follow discover-project-standards first,
  then map those rules to the supplied diff or files.
---

<!-- markdownlint-disable -->

# Review Project Standards

Apply human-written project rules and accumulated lessons to code under review.
Follow the `discover-project-standards` skill by name for discovery; do not
assume fixed project-specific paths. As a packaging hint only, a sibling install
may expose `../discover-project-standards/SKILL.md` — name-based invocation is
the mechanism.

## Instructions

Treat each discovered file as authoritative prose. Derive review checks only
from what those documents say — no repo-agnostic boilerplate checklist unless
the rules themselves imply it.

Linter and type-checker configs (`ruff.toml`, `mypy.ini`, `pyproject.toml` tool
tables, etc.) may be noted as present; do not read them for narrative rules.
Automated tooling owns those checks.

## Workflow

### Step 1 — Discover standards

Invoke `discover-project-standards` first and reuse its inventory. Before
analyzing code, report the concise inventory (found, missing, prioritized read
order) from that skill. Do not re-implement discovery procedure here.

### Step 2 — Receive code to review

Accept any of:

- A git diff (branch vs default branch, working tree, or staged changes)
- Explicit file paths
- Inline code or diffs supplied by the user or another skill

If scope is unclear, ask which revision range or files apply.

### Step 3 — Analyze

Read the discovered rule files and map their guidance to the supplied code.
Cite the violating rule by source file (and section heading when it helps).
Call out conflicts between sources or gaps where the repo is silent.

### Step 4 — Report

Emit structured findings:

| Field | Content |
|-------|---------|
| Severity | `Critical` — blocking; `Suggestion` — meaningful improvement; `Nit` — optional polish |
| Location | File and line (or diff hunk) when applicable |
| Rule | The specific rule or lesson violated (relevant standard) |
| Detail | Short explanation tied to that rule |

Distinguish clearly:

- No applicable standards discovered
- Incomplete discovery (inventory incomplete or unreadable sources)
- Clean review (standards present; no actionable findings)
- Actionable findings (with severity)

This skill is read-only by default. Offer to implement fixes and wait for
explicit approval before editing files.

## Boundaries — What This Skill Does Not Do

- Deep test-quality analysis beyond what human-written standards require
- Type-safety refactors driven only by tooling config
- Automated lint or type-checker fix loops

This skill covers human-written standards and lessons above the layer automated
tooling enforces alone.

## Edge Cases

- **No standards discovered**: Say so plainly. Suggest seeding `.cursor/rules/`
  and/or `CLAUDE.md` (or `AGENTS.md`).
- **Rules without a lessons file**: Proceed with rules only; state that no
  accumulated lessons file was found.

## Related Commands

- `discover-project-standards` — Discover standards and lessons inventory
