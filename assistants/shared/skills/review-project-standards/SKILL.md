---
name: review-project-standards
description: >-
  Use when reviewing code against the repository’s human-written coding
  standards and accumulated lessons. Invoke discover-project-standards first,
  then map those rules to a supplied diff or changed-file set.
---

# Review Project Standards

Apply human-written project rules and accumulated lessons to code under review.
Invoke `discover-project-standards` by name before review; do not assume fixed
project-specific paths. A sibling install may expose
`../discover-project-standards/SKILL.md` as a packaging hint only.

## Instructions

Treat each discovered instruction or standards file as authoritative prose.
Derive review checks only from what those documents say — no repo-agnostic
boilerplate checklist unless the rules themselves imply it.

Repository-selected tools from discovery provide context, but their executable
configuration is not narrative standards. Automated tooling owns its checks.

## Workflow

### Step 1 — Discover standards

Invoke `discover-project-standards` first and reuse its inventory. Before
analyzing code, report its ordered instruction sources, applicable standards,
repository-selected tools, conflicts, and unavailable sources. Do not
re-implement discovery procedure here.

### Step 2 — Receive code to review

Accept a supplied diff or changed-file set, including:

- Explicit file paths
- Inline code or diffs supplied by the user or another skill

If scope is unclear, ask which files or supplied diff apply. This skill does not
resolve Git/Jujutsu change scopes.

### Step 3 — Analyze

Read the discovered rule files and map their guidance to the supplied code.
Cite the violating rule by source file (and section heading when it helps).
Call out conflicts between sources or gaps where the repository is silent. If
discovery found no applicable standards or is incomplete, report that outcome
without fabricating a review.

### Step 4 — Report

For actionable findings, report:

| Field | Content |
| --- | --- |
| Severity | `Critical` — blocking; `Suggestion` — meaningful improvement; `Nit` — optional polish |
| Location | File and line (or diff hunk) when applicable |
| Rule | The specific rule or lesson violated (relevant standard) |
| Evidence | Short explanation tied to that rule |

Distinguish clearly:

- No applicable standards discovered
- Incomplete discovery (inventory incomplete or unreadable sources)
- Clean review (standards present; no actionable findings)
- Actionable findings (with severity)

This skill is read-only by default. Offer to implement fixes and wait for
explicit approval before editing files.

## Related Commands

- `discover-project-standards` — Discover standards and lessons inventory
