---
name: conduct-self-review
description: >-
  Use when a local change is ready for complete pre-submission self-review and
  a durable ignored review result is required.
---

# Conduct Self Review

## Overview

**Core principle:** A self-review is complete only when one immutable scope is
reviewed by every specialist and the validated result is persisted in a safe
ignored artifact.

Compose existing reviewers; do not implement their checks again. The artifact
is durable evidence for later human review or explicitly selected remediation,
not authorization by itself.

Invoke these named dependencies:

- `resolve-change-scope`;
- `discover-project-standards`;
- `review-project-standards`;
- `review-project-quality`;
- `review-project-tests`; and
- `review-python-types`.

Read `references/self-review-artifact-v1.md` before writing an artifact.
Sibling paths are packaging hints only; invoke dependencies by canonical name.

## When to Use

Use this skill when a local change has reached a coherent pre-submission
checkpoint and needs:

- all four specialist reviews against one fixed scope;
- one aggregate verdict with preserved coverage limitations;
- a durable, integrity-checked local review artifact; or
- stable ignored input for a later explicit `address-self-review` invocation.

Do not use it to edit findings, update snapshots, add suppressions, publish
forge comments, respond to review threads, extract lessons, commit or push
changes, or choose an unspecified latest artifact.

## Inputs

Accept:

- a scope request supported by `resolve-change-scope`; and
- optional repository-relative `artifact_directory`.

A caller-created `ChangeScope` is not authoritative orchestration input. When
one is supplied as context, still require a supported scope request and invoke
the resolver exactly once; never substitute or reuse the caller-created
object.

When no scope selector is supplied, request current-change mode. For stable
post-checkpoint evidence, accept an explicit base and target. Do not silently
replace current mode with a branch, `main`, a staging-only view, or an inferred
recent commit.

An explicit safe artifact directory overrides the default
`.reviews/self-review/`. It changes only the directory; this skill still owns
the generated timestamp and scope-prefix filename. Do not accept a complete
caller-selected filename.

## Workflow

### 1. Preflight the artifact directory

Choose exactly one directory:

1. the explicit repository-relative `artifact_directory`, when supplied; or
2. `.reviews/self-review/`.

Before review work:

- reject absolute paths, empty paths, and `..` traversal;
- resolve existing parents and symlinks and prove containment in the
  repository;
- prove the directory or its intended path is already ignored;
- prove no component is tracked or staged;
- prove the ignored parent is writable; and
- retain the selected repository-relative directory for the final response.

Do not add an ignore rule, select a broader ignored parent, or search arbitrary
ignored directories. If preflight fails, ask for a different explicit
repository-relative directory and repeat this step. Write nothing until one
directory passes.

Directory preflight precedes scope resolution. Final filename collision and
exclusive-create checks happen after the scope identity exists.

### 2. Resolve change scope once

Invoke `resolve-change-scope` exactly once with the requested mode and
selector. Retain the exact v1 object in memory, including live reviewable
content, immutable comparison identities, repository identity, path
inventory, coverage, diagnostics, diff digest, and `scope_identity`.

This is exactly one authoritative scope creation. A specialist may perform an
integrity-only revalidation required by its own contract using the same
request, but it cannot create, replace, or widen the authoritative scope.

Do not let a specialist resolve a replacement scope. If the scope is partial,
allow only explicitly bounded analysis of reviewable entries and preserve the
partial coverage. If it is blocked, continue to standards discovery for the
artifact input record but invoke no specialist.

### 3. Discover standards once

Invoke `discover-project-standards` exactly once. Retain its ordered sources,
applicable standards, selected tools, conflicts, unavailable inputs, and stable
inventory identity.

Pass this same immutable inventory to every specialist. Do not rediscover
standards per reviewer or after seeing a finding.

### 4. Handle blocked scope

When scope is blocked:

- invoke none of the four specialists;
- create one blocked-scope skip record for each reviewer;
- preserve resolver diagnostics and unavailable repository identity exactly;
- compute an overall blocked verdict; and
- continue to artifact persistence.

A blocked result is still a required artifact after destination preflight. Do
not fabricate empty clean reviewer results.

### 5. Invoke all specialists with shared inputs

For resolved, empty, or partial scope, invoke each reviewer exactly once in
this order:

1. `review-project-standards`;
2. `review-project-quality`;
3. `review-project-tests`;
4. `review-python-types`.

Supply the identical in-memory `ChangeScope`, `scope_identity`, standards
inventory, and `standards_inventory_ref` to every call. A specialist validates
the supplied inputs but does not replace them.

`review-project-quality` owns and normalizes one Ponytail simplicity sub-pass
inside its common result. Do not invoke Ponytail as a fifth specialist, add a
fifth reviewer record, or rerun it during aggregation.

Require exactly one common v1 result from every specialist. Retain
evidence-backed `not_applicable` results. Preserve unknown applicability,
incomplete analysis, missing tools, skips, and blocked work without converting
them into success.

Partial scope forces the aggregate verdict to at least `incomplete`, even when
every reviewable entry has no finding. Empty complete scope can be clean only
when every reviewer is accounted for and all other clean preconditions hold.

### 6. Enforce command ownership and reuse

Each specialist owns only its declared commands. In particular,
`review-python-types` is the sole owner of Python type-check execution.

Apply the same single-owner rule to Ponytail even though its invocation is not
shell-command evidence. Accept Ponytail coverage and findings only through the
`review-project-quality` result; do not invoke or normalize it again.

Before accepting duplicate command evidence, compare invocation identity,
provenance, selected scope, completion, and semantic content. Reuse an exact
completed result; never run the identical configured command again. Conflicting
records with the same invocation identity are an integrity block.

Do not install missing tools, invent commands or flags, add suppressions, or
run a substitute checker.

### 7. Deduplicate findings

Normalize each specialist result before aggregation. Group findings only when
category, rule, repository-relative location, and canonically normalized
evidence match exactly.

For one duplicate group:

- set the aggregate finding ID to the lexicographically smallest member ID;
- use the highest normalized severity;
- select the detail donor among members at that severity, breaking ties by
  finding ID;
- union and sort all contributors; and
- retain the detail donor's source severity and bounded remediation.

Do not merge merely similar wording, a shared path, or materially different
specialist reasoning. Follow the canonical ordering and exact rules in the
artifact contract.

Deduplicate command evidence by invocation ID and exact content. Deduplicate
exact skips and diagnostics while unioning their contributors.

### 8. Compute the aggregate verdict

Apply the first matching condition:

```text
blocked
unavailable
incomplete
blockers_found
needs_attention
advisories
clean
```

Use:

1. `blocked` for blocked scope or integrity, blocked specialist work, or a
   blocked skip;
2. `unavailable` for unavailable required shared inputs, specialists, checks,
   or skips;
3. `incomplete` for partial scope, unknown applicability, incomplete reviewer
   work, or incomplete required skips;
4. `blockers_found` for one or more blocker findings;
5. `needs_attention` for one or more actionable findings;
6. `advisories` for advisory findings only; and
7. `clean` only when every clean precondition is proved.

Do not translate these states into a simpler pass/fail that loses limitations.
An unavailable reviewer precedes partial coverage; findings remain visible even
when a coverage state determines the verdict.

### 9. Build the machine result

Create the exact top-level v1 object from the artifact contract:

- copy the path-free repository identity;
- persist the bounded scope projection without raw diff content;
- retain the exact standards identity;
- include all reviewer results or blocked-scope skip records;
- include deduplicated findings, commands, skips, and diagnostics; and
- include exact counts and the aggregate verdict.

Set `created_at` to the final UTC RFC 3339 time. Compute `result_id` from
semantic material with `created_at`, `result_id`, and `result_digest` omitted.
Then compute `result_digest` with only `result_digest` omitted.

Recursively reject raw patches, raw command output, absolute paths, remote
URLs, credentials, authentication material, tokens, secrets, trust or session
state, caches, histories, indexes, and generated plugin state.

### 10. Select a non-existing filename

Under the preflighted directory, choose the shortest unique prefix of the full
scope identity, with a minimum of 12 lowercase hexadecimal characters. Combine
it with the filename-safe UTC timestamp defined by the artifact contract.

Inspect only artifacts in the selected directory needed to establish prefix
uniqueness. Never infer authority from their contents. If the final path
exists, do not overwrite it; capture a later timestamp or fail safely.

### 11. Persist and verify

Write:

1. the exact first-line marker;
2. the immediately following fenced JSON object; and
3. a concise human Markdown summary after the fence.

Use exclusive-create semantics. After writing:

- read the artifact back;
- verify the marker and JSON placement;
- recompute `result_id` and `result_digest`;
- confirm reviewer identities, counts, and verdict;
- confirm prohibited data and raw diffs are absent;
- confirm the path remains ignored and untracked; and
- confirm ordinary source-control status does not expose the artifact.

Every attempt whose directory passed preflight must persist its outcome,
including empty, partial, blocked, unavailable, or finding-bearing results.
If persistence or verification fails, self-review did not complete and cannot
claim the computed verdict or clean state.

### 12. Return the concise result

Return:

- the exact aggregate verdict;
- blocker, actionable, and advisory counts;
- important blocked, unavailable, or incomplete limitations;
- concise blocker summaries when present; and
- a clickable repository-relative artifact path.

Do not embed the full artifact or raw review evidence in the response.

## Output

The durable output is one validated v1 artifact in the selected ignored
directory. The inline output is a concise human summary and link to that exact
file.

The artifact remains ignored and uncommitted. It is user-controlled evidence,
not a signed result and not permission to edit findings.

## Quick Reference

| Situation | Required handling |
| --- | --- |
| No directory supplied | Preflight `.reviews/self-review/` only |
| Explicit safe directory supplied | Use that directory; keep generated filename |
| Selected directory is unsafe | Ask for another explicit directory; do not search |
| Scope is blocked | Skip all specialists and persist blocked records |
| Scope is partial | Review bounded content; aggregate cannot be clean |
| Reviewer is not applicable | Retain its evidence-backed result |
| Required reviewer or tool unavailable | Preserve it; overall verdict is unavailable |
| Quality result contains Ponytail coverage | Preserve it inside quality; keep four reviewers |
| Duplicate finding evidence | Deduplicate exact semantic match and retain contributors |
| Similar finding with different reasoning | Keep both findings |
| Artifact path exists | Never overwrite; choose a later timestamp or fail |
| Artifact write or verification fails | Review did not complete |

## Boundaries

This skill may write only its verified ignored review artifact and temporary
ignored persistence checks. It never edits tracked source, tests,
configuration, ignore rules, reviewer findings, snapshots, suppressions, forge
state, commits, or bookmarks.

Never migrate or retain authentication, credentials, trust, sessions, personal
project paths, histories, caches, indexes, or generated plugin state.

## Common Mistakes

- Resolving scope or standards once per reviewer. Resolve each exactly once and
  share the same immutable objects.
- Searching for any ignored directory after the selected destination fails.
  Ask for a different explicit directory.
- Running specialists after blocked scope. Persist skip records instead.
- Calling partial or unavailable evidence clean because reviewable files look
  good.
- Deduplicating by path alone and losing materially different reasoning.
- Dropping contributing reviewers from a true duplicate.
- Letting quality review and type review both execute the type checker.
- Invoking Ponytail directly as a fifth reviewer or rerunning its quality
  sub-pass during aggregation.
- Writing a prose-only report without the exact marker, JSON, and hashes.
- Overwriting the prior artifact or treating the latest file as implicit input.
- Returning a computed clean verdict after persistence failed.
- Offering to fix findings from this report-only orchestration boundary.

## Related Skills

- `resolve-change-scope` owns the immutable review boundary.
- `discover-project-standards` owns the shared standards inventory.
- The four `review-*` specialists own applicability, evidence, findings, and
  limitations in their domains.
- `address-self-review` separately validates and addresses explicitly selected
  findings from one named artifact.
- Forge review, response, lesson extraction, and lesson promotion belong to
  later workflow trains.
