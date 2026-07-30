---
name: review-project-standards
description: >-
  Use when a resolved change must be reviewed against repository-authored
  coding standards or accumulated lessons.
---

# Review Project Standards

## Overview

**Core principle:** Apply only discovered repository-authored rules to the
fixed reviewable scope, with a citation for every finding.

Executable configuration provides context but is not narrative standards.
Automated tooling owns its checks; this specialist owns human-authored rules
and accumulated lessons.

Use `resolve-change-scope` and `discover-project-standards` by name when valid
inputs were not supplied. Sibling paths are packaging hints only; invoke
dependencies by canonical name.

## When to Use

Use this skill when a resolved or resolvable change needs review against:

- repository instructions and engineering standards;
- accumulated lessons or local conventions;
- documentation presence and style requirements; or
- conflicts and gaps among applicable human-authored rules.

Do not use it to invent repo-agnostic rules, execute lint or type checking,
judge general test design, remediate findings, or compute an aggregate
multi-reviewer verdict.

## Inputs

Accept:

- one v1 `ChangeScope`, including its live in-memory reviewable diff; and
- one discovered standards and tool inventory with a stable identity.

Reuse supplied inputs only when their versions, identities, repository
identity, path inventory, and digests validate. Otherwise invoke the named
dependencies once. Never silently replace the supplied scope or rediscover
standards to obtain a different answer.

If scope is blocked, return a blocked common result without analyzing code.
For partial scope, review only entries with trustworthy content and force an
incomplete outcome.

## Workflow

### 1. Validate shared inputs

Record the exact `scope_identity` and `standards_inventory_ref`. Confirm the
scope status, coverage, path inventory, content evidence, and every ordered
instruction or standards source.

Report discovery conflicts and unavailable sources as coverage evidence.
Never reimplement either dependency's discovery or scope-selection algorithm.

### 2. Establish applicability

Standards review is applicable when at least one discovered human-authored rule
governs a reviewable changed entry. Prove `not_applicable` only from complete
scope and standards evidence. Use `unknown` when partial scope or incomplete
discovery prevents the decision.

An empty complete scope can be not applicable. Missing or unreadable required
standards make the result incomplete or unavailable according to the common
contract; they do not justify a clean review.

### 3. Map rules to reviewable entries

Treat each discovered instruction, standards file, and accumulated lesson as
authoritative within its precedence and scope. Derive checks only from what
those sources say.

For each reviewable entry:

1. identify the applicable rule and its source;
2. inspect only the trustworthy changed content and necessary local context;
3. cite the repository-relative source file and section when useful;
4. record concrete changed-code evidence; and
5. distinguish a violation from a repository-silent gap.

Do not inspect unreviewable binary or unavailable content as though it were
text. Preserve that limitation and prevent a clean result.

### 4. Review docstring appropriateness

Apply discovered documentation and testing standards exactly. When they
require Google-style docstrings, assess required presence and whether the
content is appropriately concise or expanded.

Use a one-line docstring when the purpose is straightforward and no additional
contract detail helps. Expanded sections are appropriate when parameters,
return semantics, raised exceptions, side effects, invariants, or other
non-obvious contract details add useful context.

For tests, apply any discovered requirement that every test have a short
behavioral docstring. `review-project-tests` owns whether the name and
docstring communicate meaningful repository-owned behavior. This specialist
owns required presence and one-line versus expanded style appropriateness.

Configured Ruff docstring diagnostics belong to `review-project-quality`.
Do not duplicate them as tool findings, though the same changed code may
independently violate a cited human-authored standard.

### 5. Normalize findings

Preserve the source label while mapping it into the common severities:

| Source severity | Normalized severity |
| --- | --- |
| `Critical` | `blocker` |
| `Suggestion` | `actionable` |
| `Nit` | `advisory` |

Set `source_severity` to the cited source label. Each finding contains a tight
repository-relative location, rule citation, concise evidence, bounded
remediation, and `review-project-standards` as its contributor.

Do not escalate a repository `Suggestion` or `Nit` merely because the deadline
is near. Keep materially different rule reasoning separate even when another
specialist reports a similar location.

### 6. Normalize the common result

Return exactly one v1 review-result envelope for
`review-project-standards`. Use stable finding IDs from the shared contract and
preserve canonical ordering.

Verdict precedence is:

```text
blocked
unavailable
incomplete
blockers_found
needs_attention
advisories
clean
```

`clean` requires complete resolved or empty scope coverage, complete inputs and
owned checks, known applicability, no findings, no skips, no unavailable
checks, and no blocked work.

## Output

Return one common v1 review-result envelope with the supplied scope and
standards identities, applicability, outcome, owned coverage, normalized
findings, explicit skips, sanitized command evidence, counts, and specialist
verdict.

Never return only prose findings or offer to implement fixes. The orchestrator
owns aggregation, and `address-self-review` owns any separately authorized
remediation.

## Quick Reference

| Situation | Required handling |
| --- | --- |
| Valid scope and inventory supplied | Reuse both unchanged |
| Required input invalid or absent | Invoke the named dependency once |
| Scope is partial | Review trustworthy entries; outcome remains incomplete |
| Rule source is unavailable | Preserve unavailable coverage; do not invent it |
| Public contract is straightforward | A required one-line docstring may suffice |
| Contract details add useful context | Require the discovered expanded style |
| Ruff reports a docstring rule | Delegate the tool finding to quality review |
| Same location has distinct rule reasoning | Keep the findings separate |

## Boundaries

This skill is report-only. Never edit tracked files, implement fixes, add
standards, run automated checker commands, widen scope, or retain raw diffs,
raw output, absolute paths, credentials, sessions, trust state, or generated
plugin state.

## Common Mistakes

- Reviewing a loose file list after a valid immutable scope was supplied.
- Re-running standards discovery per file or per reviewer.
- Applying generic preferences that no discovered repository rule supports.
- Reading an unreviewable entry and then claiming complete coverage.
- Treating every present docstring as appropriate, or expanding a simple
  contract with sections that add no useful information.
- Duplicating Ruff diagnostics instead of citing an independent human-authored
  requirement.
- Losing `Critical`, `Suggestion`, or `Nit` when normalizing severity.
- Offering to fix findings from a report-only specialist.

## Related Skills

- `resolve-change-scope` owns immutable comparison and drift detection.
- `discover-project-standards` owns ordered standards and tool discovery.
- `review-project-quality` owns configured lint and documentation checks.
- `review-project-tests` owns behavioral test quality and documentation
  meaning.
- `review-python-types` owns Python type-check execution and findings.
- `conduct-self-review` supplies shared inputs and aggregates this result.
