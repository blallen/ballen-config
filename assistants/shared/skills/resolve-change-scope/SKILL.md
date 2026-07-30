---
name: resolve-change-scope
description: >-
  Use when a review needs an exact Git, Jujutsu, explicit, or caller-supplied
  change scope and comparison ambiguity or working-copy drift could make
  review evidence unreliable.
---

# Resolve Change Scope

Resolve one deterministic, read-only change scope before any reviewer analyzes
code. Give every downstream reviewer the same contract object and exact
in-memory textual diff. Do not let individual reviewers rediscover or widen
the comparison.

Read [references/change-scope-contract.md](references/change-scope-contract.md)
before resolving a scope. It defines the v1 fields, enums, identity material,
coverage rules, and diagnostic codes. Use the checked-in JSON example and
vectors as structural fixtures, not as substitutes for inspecting the current
repository.

## Overview

Resolve one immutable, repository-relative comparison before any reviewer
reads the change. The result is a shared v1 contract: downstream reviewers
reuse its scope, identities, path inventory, and reviewable evidence instead
of rediscovering or widening the boundary.

## When to Use

Use this skill when:

- a review needs an exact Git, Jujutsu, explicit-endpoint, or caller-supplied
  change scope;
- staged, unstaged, untracked, rename, binary, or working-copy state could
  make review evidence incomplete; or
- multiple downstream reviewers must share one deterministic comparison.

Do not use it to:

- inspect or edit tracked files;
- choose a branch, `main`, `HEAD~1`, or a first parent from conversation
  context;
- infer a scope after VCS failure or replace one backend with another; or
- let an individual reviewer rediscover or widen the comparison.

## Inputs and precedence

Require a repository root and accept exactly one request mode:

1. `supplied` when the caller explicitly provides changed paths or a patch;
2. `explicit` when the caller provides both comparison endpoints; or
3. `current` when neither supplied content nor an explicit selector exists.

Reject mixed modes, a one-sided explicit range, contradictory supplied paths,
or a selector that resolves differently between capture steps. Never infer
`main`, `HEAD~1`, a first parent, a staging-only comparison, or a branch from
conversation context.

Treat an explicitly supplied empty path list as an empty supplied request only
when the caller clearly intended an empty scope. Missing input is not the same
as an empty list.

## Workflow

### 1. Detect the repository and VCS

Resolve the repository root without emitting its absolute path. If `.jj/`
exists, use Jujutsu semantics, including for colocated repositories. Otherwise,
use Git only when the root is a Git work tree. Do not fall back from one VCS to
another after a command failure.

Capture the tool version and command availability as ephemeral evidence.
Unavailable required commands block the scope with
`vcs_command_unavailable`; unsupported roots block with
`unsupported_repository`.

Derive repository identity from configured remotes locally. Select:

1. the single tracked remote for the current bookmark or branch;
2. `origin`;
3. the sole configured remote; or
4. no remote when none exists or selection remains ambiguous.

Multiple tracked candidates are ambiguous and do not fall through to
`origin`. Never emit a remote URL, user information, query, fragment, local
path, or credential-bearing value.

### 2. Resolve current Git work

Verify that `HEAD` exists. If it does not, return `blocked` with
`git_head_missing`; do not invent an empty-tree comparison.

Capture all of these relative to the same `HEAD`:

- staged tracked changes;
- unstaged tracked changes;
- tracked working-tree deletions; and
- non-ignored untracked files as additions.

Use machine-readable, NUL-delimited status output where available. A single
staging diff, unstaged diff, or status summary is insufficient. Preserve native
rename metadata when Git reports it. Do not run similarity heuristics after
capture.

Ignored paths are outside scope. Ask the VCS whether a candidate is ignored;
do not enumerate or read ignored files to prove their exclusion.

### 3. Resolve current Jujutsu work

Resolve `@`, all `parents(@)`, and the current change ID. Use Jujutsu's native
`@` diff so a multi-parent working-copy commit is compared with the automatic
merge of all parents. Never select the first parent.

Do not reconstruct the automatic merge by taking the union, intersection, or
preferred side of per-parent diffs. Pairwise deltas do not establish the
merged-parent tree. If the native merged-parent comparison cannot be captured,
return `blocked` with `diff_unavailable` instead of inferring an inventory.

Allow ordinary Jujutsu snapshot bookkeeping so the captured content is
current. Do not default to `--ignore-working-copy`, because it can silently
review an older snapshot. Record every parent commit ID and retain the change
ID as non-identity context when useful.

Collect native summary and patch representations for the same `@`. Preserve
conflicts, binary markers, symlinks, and submodule states rather than
flattening them into text.

### 4. Resolve explicit endpoints

Resolve each base and target selector independently and require exactly one
result per endpoint:

- for Git, resolve a commit object and retain its full object ID;
- for Jujutsu, require one commit and retain its full commit ID, change ID, and
  parent commit IDs.

Missing selectors produce `selector_not_found`; multiple results produce
`range_endpoint_not_singleton`. Use `selector_ambiguous` only when the backend
rejects a selector as ambiguous before it can enumerate matching revisions.
Do not choose the first record. Diff the two resolved immutable endpoints, not
their original names.

### 5. Validate supplied scope

Normalize every supplied path to NFC repository-relative POSIX form. Reject
absolute paths, `..` traversal, empty paths, contradictory duplicate entries,
and paths outside the repository.

A supplied file-only request must provide structured entries with `path`,
`change_type`, and `previous_path` when the type is `rename`. A bare path list
cannot satisfy the change-entry contract and is `blocked` with
`supplied_scope_invalid`. Structured entries without reviewable patch content
are `partial`; use `unknown` content kind, `unavailable` diff state, and a null
content digest when those values cannot be verified.

A supplied unified patch may be `resolved` when every header and changed path
parses consistently. When a separate structured inventory is supplied, the
patch-derived entries must match it exactly. When the patch is the only
supplied content, its validated headers establish the inventory and change
types: `/dev/null` establishes add or delete, native rename headers establish
rename, and other paired paths establish modify. Invalid or contradictory
content is `blocked` with `supplied_scope_invalid`; an unparseable patch uses
`supplied_diff_unparseable`.

Caller-provided revision or repository identities remain explicitly
unverified. Do not promote them to resolved VCS identities without local
verification.

### 6. Capture a stable snapshot

Capture a compact preflight fingerprint, then gather comparison identities,
status, changed paths, content classifications, content digests, and the
reviewable diff. Capture the same fingerprint again before returning.

The two fingerprints must cover the same semantic inputs used by the scope,
including parent or `HEAD` identities, status, changed paths, and per-entry
content or diff digests. If they differ, discard the candidate result and
return `blocked` with `working_copy_changed_during_capture`.

Do not hide drift by sorting away changed values. Sorting removes only
irrelevant command-output order.

### 7. Build changes and the reviewable diff

Create one ordered entry per repository-relative change with:

- `path`;
- `change_type`;
- nullable `previous_path`;
- `content_kind`;
- `diff_state`; and
- nullable `content_digest`.

Sort entries by current path, previous path, then change type after NFC path
normalization. Preserve a native rename as one rename entry. Without native
rename evidence, retain separate add and delete entries.

Keep the exact normalized textual patch in
`reviewable_diff.content` during live handoff. Mark binary, unavailable,
conflict, symlink, submodule, and unknown content explicitly. Do not coerce
binary bytes or command errors into a textual patch. A persisted projection
sets `content` to `null` while retaining state, digest, coverage, and
unavailable paths.

### 8. Canonicalize identities

Use UTF-8 JSON with lexicographically sorted keys, compact separators,
unescaped Unicode, and stable array ordering. Normalize paths to NFC before
hashing. Compute lowercase SHA-256 values exactly as the contract specifies.

Build:

- path-free repository identity from normalized VCS, host, and namespace;
- workspace fingerprint from the captured comparison and content state; and
- one scope identity from the complete semantic contract material.

Exclude timestamps, absolute paths, raw remote URLs, diagnostic detail,
command-output ordering, and other ephemeral evidence from identity material.
Never substitute a local checkout path for unavailable repository identity.

When naming an artifact, use the shortest scope-ID prefix that is unique among
existing artifacts, with a minimum of 12 hexadecimal characters. Never
overwrite a collision.

### 9. Assign status, coverage, and diagnostics

Return:

- `resolved` for a complete, non-empty comparison;
- `empty` for a valid complete comparison with no changes;
- `partial` when a trustworthy scope exists but required review coverage is
  incomplete; or
- `blocked` when no trustworthy comparison exists.

Binary or otherwise unavailable diff content is partial even when its path and
content digest are known. Missing endpoints, missing Git `HEAD`, unresolved
conflicts, invalid supplied input, unavailable required commands, or capture
drift are blocked. Neither partial nor blocked scope can support a clean review
verdict.

Use stable diagnostic codes from the contract reference. Diagnostic detail
must be concise, sanitized, and path-free except for an optional
repository-relative `path`.

### 10. Return the v1 contract

Return exactly one `ChangeScope` object with the top-level fields defined by
the contract reference. Include the live normalized patch only in memory.
Downstream reviewers receive the same object, `scope_identity`, and
`reviewable_diff.digest`; they do not rerun scope discovery.

For a persisted or logged projection, set `reviewable_diff.content` to `null`.
Report the status, scope identity, diff digest, changed-path inventory,
coverage, and diagnostic codes without raw diff content.

## Quick Reference

| Situation | Required handling |
| --- | --- |
| Supplied, explicit, or current request | Accept exactly one mode; reject mixed or one-sided input |
| Jujutsu repository | Use native merged-parent `@` semantics and retain full identities |
| Working-copy drift | Capture stable inputs before and after; block on mismatch |
| Unreviewable content | Preserve binary/conflict/unavailable state; never coerce it into text |
| Complete comparison | Return `resolved` or `empty` with shared identities and coverage |
| Missing or ambiguous evidence | Return `partial` or `blocked`; never claim clean coverage |

## Common Mistakes

- Inferring `main`, a branch, `HEAD~1`, or the first parent.
- Pairing per-parent diffs instead of using Jujutsu's merged-parent comparison.
- Capturing staged, unstaged, or untracked state against different heads.
- Sorting away meaningful working-copy drift.
- Treating a path list as a complete supplied scope without patch evidence.
- Persisting raw diffs, absolute paths, remote URLs, or sensitive state.

## Boundaries

- Remain read-only for tracked project files.
- Do not stage, commit, reset, restore, checkout, rebase, merge, or edit.
- Do not create ignore rules or inspect ignored-file contents.
- Do not install tools or retry through a different VCS.
- Do not expose absolute paths, remote URLs, credentials, sessions, trust
  state, or generated plugin state.
- Do not claim `empty`, `resolved`, or clean review coverage when evidence is
  partial or blocked.

## Related Skills

- `discover-project-standards` — Supplies the standards inventory used by
  downstream reviewers.
- `review-project-standards`, `review-project-quality`,
  `review-project-tests`, and `review-python-types` — Consume the shared
  scope without rediscovering it.
- `conduct-self-review` — Shares one scope across all specialists and
  persists the aggregate result.
- `address-self-review` — Re-resolves the reviewed scope before selected
  remediation.
