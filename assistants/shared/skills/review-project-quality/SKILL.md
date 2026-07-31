---
name: review-project-quality
description: >-
  Use when a resolved change needs review against repository-selected lint,
  formatting, documentation, build, or related quality checks.
---

# Review Project Quality

## Overview

**Core principle:** Run only repository-selected safe checks and attribute
their evidence to the resolved change.

Use `resolve-change-scope` and `discover-project-standards` by name when valid
inputs were not supplied. Read the canonical contracts packaged with the scope
resolver:

- `../resolve-change-scope/references/change-scope-contract.md`;
- `../resolve-change-scope/references/review-result-contract.md`; and
- their JSON examples when a structural reference is needed.

Sibling paths are packaging hints only. Invoke dependencies by canonical name.

Read `references/ponytail-review-v1.json` before review. It is authoritative
for the Ponytail invocation count, host availability, rule and severity
mapping, transition provenance, and coverage states. `ponytail-review` is an
external provider-owned skill, not a repository-owned shared-skill dependency.

## When to Use

Use this skill when a resolved or resolvable change needs repository-selected
lint, formatting-check, documentation, build-validation, or related quality
review.

Do not use it to execute Python type checks, judge test quality, decide
docstring appropriateness, remediate findings, or produce an aggregate
multi-reviewer verdict. Those responsibilities belong to their related skills.

## Inputs

Accept:

- one v1 `ChangeScope`, including its live in-memory reviewable diff;
- one discovered standards and tool inventory with a stable identity; and
- optional complete command evidence already produced for the identical scope.

On Claude Code and Codex, the Ponytail simplicity sub-pass is required. Use the
native `ponytail-review` skill or, only for the bounded transition encoded in
its contract, the pinned published contract. Ponytail is not applicable on
Cursor. An unknown or undetected host is unavailable; never infer that it is
Cursor.

Reuse supplied inputs only when their versions, identities, repository
identity, path inventory, and digests validate. Otherwise invoke the named
dependencies once. Never silently replace a supplied scope with a new one.

If scope is blocked, return a blocked result without running checks. Partial
scope may support bounded analysis, but the review outcome and verdict remain
incomplete. Empty complete scope is valid and may produce a clean
specialist result.

## Workflow

### 1. Establish applicability

Quality review is applicable when the selected change contains source,
configuration, build, documentation, or other files covered by a
repository-selected quality check. Prove `not_applicable` from the scope and
inventory. If either is insufficient, use `unknown`; do not guess.

Record the exact `scope_identity` and `standards_inventory_ref` before any
command runs.

### 2. Discover repository-selected checks

Use the discovered standards inventory and inspect only repository-owned
configuration needed to resolve declared checks. Sources may include:

- pre-commit configuration;
- project and package-manager configuration;
- repository scripts;
- task-runner or build files;
- checked-in contributor guidance; and
- checked-in CI configuration.

Inventory lint, formatting-check, documentation, build-validation, and related
quality commands. Retain repository-relative provenance for each. Do not
invent a tool, command, flag, generic default, or configuration.

Inventory configured type-check tooling and its provenance, then delegate its
execution and findings to `review-python-types`. Completing that inventory is
not a skip. Do not run the Python type checker in this specialist, even when
the requester asks for one combined pass/fail answer.

### 3. Preflight command safety

Run only checks that are read-only for tracked project files. A supported
check or dry-run mode is safe; a formatter, fixer, generator, dependency
installer, or command with unknown mutation behavior is not.

Do not install a missing executable or dependencies. Do not invoke package
manager behavior that may download a missing tool. Do not add suppressions,
ignore rules, generated baselines, or configuration.

Classify every required command before execution:

- runnable and scoped;
- runnable but full-repository only;
- unavailable;
- unsafe; or
- outside this specialist's ownership.

An unavailable required executable produces unavailable command evidence and
an unavailable outcome. An unsafe required command is skipped with its actual
coverage effect. Never claim either check ran.

### 4. Select changed or full scope

Prefer a changed-scope invocation only when the repository declares it or the
installed command's local interface proves the exact scoped form. Do not
derive flags from memory.

When no supported scoped form exists, run the safe configured full command.
Record `selected_scope: full`; do not rewrite it into an invented file-list
form. Keep the supplied change-path set available for diagnostic
classification.

Reusing prior command evidence is allowed only when its invocation identity,
scope identity, provenance, completion, and output digest are exact matches.
Never reuse incomplete or stale evidence.

### 5. Execute and classify evidence

Capture exit status and only the concise evidence needed to establish
coverage, findings, and limitations. Do not persist raw command output.

Treat a nonzero exit that successfully reports violations as completed.
Classify each diagnostic:

- a diagnostic on a changed path is eligible for an in-scope finding;
- a diagnostic wholly outside the supplied path set is out of scope; and
- a global diagnostic is in scope only when evidence ties it to the selected
  change or a repository-wide invariant the change invalidates.

Record out-of-scope diagnostics in sanitized command evidence, not as findings.
They do not offset or amplify an in-scope finding. A full check with only
unrelated failures may still complete changed-scope coverage when the command
examined every changed path.

If an unrelated failure aborts, truncates, or prevents examination of changed
paths, mark the command and result incomplete. Do not convert missing evidence
into a clean result.

### 6. Review owned quality concerns

Report repository-selected:

- lint and formatting-check violations;
- documentation build or validation failures;
- build-validation failures attributable to the selected change;
- configured Ruff docstring violations when that rule family is enabled; and
- inaccurate, stale, or unhelpful changed documentation with concrete
  evidence.

Ruff owns mechanical docstring-rule output here. The standards reviewer owns
whether a documented API or test needs a one-line versus expanded Google-style
docstring. Do not duplicate Python type-check findings, test-quality findings,
or broader human-authored standards findings.

Use blocker severity only when quality evidence makes the change unsafe or
untrustworthy. Use actionable for material corrections and advisory for
optional improvements. Preserve the source severity and rule when available.

### 7. Run the Ponytail simplicity sub-pass

On Claude Code and Codex, invoke `ponytail-review` exactly once in diff mode.
Supply the same immutable `ChangeScope`, `scope_identity`, standards inventory,
and changed-path set used by this specialist. Never ask Ponytail to audit the
repository, resolve a new scope, or review paths outside that set.

Accept only output with changed-path findings, tight repository-relative
locations, one declared Ponytail tag per finding, concrete evidence, and
bounded remediation. Normalize tags exactly as the contract declares:

| Ponytail tag | Rule | Severity |
| --- | --- | --- |
| `delete` | `ponytail/delete` | actionable |
| `stdlib` | `ponytail/stdlib` | actionable |
| `native` | `ponytail/native` | actionable |
| `yagni` | `ponytail/yagni` | actionable |
| `shrink` | `ponytail/shrink` | advisory |

The exact lean signal `Lean already. Ship.` must be the sole semantic output to
complete the sub-pass with no finding. An empty response, or that signal mixed
with a finding, is malformed and incomplete. A missing required native skill
is unavailable. Malformed, unbounded, unknown-tag, or out-of-scope output is
incomplete; discard every candidate finding from that response rather than
salvaging a partial result. Scope identity drift is blocked: mark the check
coverage incomplete, add one skip for the same check with `effect: blocked`,
and discard every candidate finding. Preserve these states in this
specialist's outcome and verdict.

On Cursor, do not invoke Ponytail. Record `ponytail-review-native` as a
non-required check with `selected_scope: none` and `completion: skipped`; add
no skip record, no finding, and no clean-verdict limitation for this
not-applicable host. Treat an unknown host as unavailable required coverage.

For a transition run that began before the native plugin could load, require
the exact `explicit-pre-plugin-transition-request` selector before this skill
starts, then use only the contract's pinned source commit and path. Record one
required, completed, changed-scope coverage check named
`ponytail-review-published-contract` and do not claim native invocation. The
pre-start selector is the caller's authoritative transition assertion; no
later missing-skill observation can create it. Host availability takes
precedence, so Cursor remains not applicable and an unknown host remains
unavailable even when the selector is present. The transition has zero native
invocations and exactly one published-contract check. Do not represent it as a
skip.

Persist only normalized coverage and findings. Do not retain raw Ponytail
output or its net-line score.

### 8. Revalidate scope

After commands that may refresh repository metadata or ordinary Jujutsu
snapshot state, invoke `resolve-change-scope` again with the same request.
Require the same scope identity, comparison identities, path inventory, and
diff digest.

This is an integrity comparison, not a replacement scope. Ponytail never
invokes the resolver, and all accepted Ponytail evidence remains attributed to
the originally supplied object.

If revalidation differs, discard any clean conclusion and return blocked with
integrity evidence. Do not attribute diagnostics from one scope to another.

### 9. Normalize the common result

Return exactly one v1 review-result envelope. Use stable finding IDs from the
common contract. Sort coverage checks, findings, skips, commands, and
contributors canonically.

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
checks, and no blocked work. Out-of-scope diagnostics alone are not in-scope
findings, but any failure that prevents changed-scope examination blocks a
clean verdict through incomplete coverage.

## Output

Return exactly one common v1 review-result envelope for
`review-project-quality`. Include the supplied scope and standards identities,
applicability, outcome, owned coverage, normalized findings, explicit skips,
sanitized command evidence, the normalized Ponytail sub-pass, counts, and the
specialist verdict. Never return only a conversational pass/fail or a separate
fifth reviewer result.

## Quick Reference

| Situation | Required handling |
| --- | --- |
| Declared safe scoped form exists | Run it with `selected_scope: changed` |
| Only a safe configured full form exists | Run it unchanged and classify diagnostics by supplied paths |
| Required executable is missing | Install nothing; record unavailable evidence |
| Full check reports unrelated failures | Keep them in command evidence, not findings |
| Full check aborts before changed paths | Mark coverage and outcome incomplete |
| Type checker is configured | Inventory provenance and delegate execution |
| Required host has native Ponytail | Invoke once in diff mode inside this result |
| Ponytail reports `Lean already. Ship.` | Complete the sub-pass with no finding |
| Required native Ponytail is missing | Mark its coverage unavailable |
| Ponytail output is malformed or exceeds scope | Mark its coverage incomplete |
| Cursor host | Mark Ponytail not applicable |
| Unknown host | Mark required Ponytail coverage unavailable |
| Pinned transition run | Record completed published-contract coverage; no native claim |
| Scope identity changes after a command | Block; discard the prior conclusion |

## Boundaries

This skill is report-only. Never edit tracked files, install tools, add
suppressions, widen scope, invoke Ponytail against a second scope, or retain
raw output, net-line scores, absolute paths, credentials, sessions, trust
state, or generated plugin state.

## Common Mistakes

- Inventing a file-list flag for a full-only command. Run the configured full
  form and record its scope.
- Treating every full-project diagnostic as caused by the change. Findings
  require changed-path or change-attribution evidence.
- Installing a missing checker to finish quickly. Record it as unavailable.
- Running the Python type checker here. Inventory it, then delegate.
- Returning Ponytail as a fifth reviewer or supplemental sidecar. Normalize
  its single sub-pass inside `review-project-quality`.
- Treating a pinned contract as a native invocation or a general fallback.
  The transition is bounded to the pre-existing run encoded by the contract.
- Calling a nonzero violation-reporting exit unavailable. It completed when it
  produced trustworthy diagnostics.
- Returning clean after truncated output, partial scope, unknown
  applicability, a skip, or scope drift.
- Editing files or adding suppressions during review. This skill is
  report-only.

## Related Skills

- `resolve-change-scope` owns immutable comparison and drift detection.
- `discover-project-standards` owns standards and tool inventory discovery.
- `review-project-standards` owns human-authored rule and docstring
  appropriateness review.
- `review-project-tests` owns test design and behavioral coverage.
- `review-python-types` owns Python type-check execution and findings.
- Provider-owned `ponytail-review` supplies the bounded simplicity sub-pass;
  this skill owns its invocation and normalization.
- `conduct-self-review` composes specialist results and computes the aggregate
  verdict.
