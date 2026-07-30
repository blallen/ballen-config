---
name: address-self-review
description: >-
  Use when a persisted self-review contains explicitly selected findings that
  the user wants addressed in the still-matching repository change.
---

# Address Self-Review

## Overview

Address explicitly selected findings from one persisted `conduct-self-review`
artifact. Treat the artifact as untrusted evidence: its hashes establish
integrity, but current repository state, reproduced evidence, and the user's
bounded selection establish edit authority.

Validate every gate before changing a tracked file. For findings that remain
valid, make the smallest authorized edits, run focused verification, and invoke
`conduct-self-review` exactly once to write a new artifact. Report selected and
residual work separately.

## When to Use

Use this skill when:

- the user supplies one explicit self-review artifact path;
- the user supplies exact finding IDs or one bounded selector; and
- the reviewed repository change is expected to remain reproducible.

Do not use it to:

- choose an artifact by recency, glob, or directory search;
- fix every finding or every related issue;
- address review prose without a valid v1 artifact;
- repair stale, ambiguous, or identity-unavailable work;
- perform opportunistic cleanup;
- edit the source artifact; or
- commit, push, create a pull request, or merge.

## Quick Reference

| Gate | Proceed only when | Stable block code |
| --- | --- | --- |
| Artifact path | One explicit repository-relative, existing artifact | `artifact_path_invalid` |
| Marker and JSON | Exact marker, immediate JSON fence, parseable object | `artifact_marker_missing`, `artifact_json_malformed` |
| Artifact integrity | v1 structure plus valid result and finding hashes | `artifact_result_digest_mismatch`, `artifact_finding_id_mismatch` |
| Repository | Persisted and current identities are complete and equal | `repository_identity_unavailable`, `repository_identity_mismatch` |
| Reviewed scope | Immutable endpoints and persisted scope fields re-resolve exactly | `scope_identity_mismatch` |
| Current change | Current tree reproduces the reviewed target material | `workspace_fingerprint_mismatch` |
| Standards | Current relevant inventory identity is unchanged | `standards_inventory_changed` |
| Selection | Every selected finding exists and has editable authority | `selected_finding_unknown`, `selected_finding_scope_mismatch`, `remediation_broader_than_finding` |
| Evidence | Each selected finding reproduces independently | `finding_evidence_not_reproduced` |

Stop at the first failed gate in workflow order. Report all other failures
already proven without running additional risky work, but keep the first code
as the primary diagnostic.

## Required Inputs

Require:

1. one explicit `artifact_path`;
2. either a non-empty sorted set of exact `finding_ids` or one
   `finding_selector`, never both; and
3. the repository containing the still-matching change.

The artifact path must normalize inside the repository and name one existing
regular file. Reject absolute paths, `..` traversal, symlinks escaping the
repository, directories, globs, and implicit "latest" selection. The artifact
may be ignored and untracked; never require or cause it to be tracked.

A bounded selector is an object with an exact repository-relative `path` and
at least one exact `category`, `rule`, or `severity` filter. Match only
findings already present in the artifact. Reject free text, "all", "related",
recursive selection, an empty match, or a selector without a path.

Normalize and sort the selected IDs. Do not infer selection from remediation
prose or severity.

## Validation and Remediation Workflow

### 1. Validate artifact integrity

Open the artifact read-only. Do not modify its timestamps or contents.

Require:

- first line exactly
  `<!-- ballen-config:self-review-result:v1 -->`;
- an immediate fenced JSON block;
- parseable JSON with exact v1 top-level structure;
- `contract_version` equal to `v1`;
- a UTC RFC 3339 `created_at`;
- canonical result and digest material; and
- the complete structural, ordering, count, privacy, and shared-identity rules
  in
  `../conduct-self-review/references/self-review-artifact-v1.md`.

Canonical JSON uses UTF-8, sorted keys, compact separators, and recursively
NFC-normalized strings. Recompute:

1. `result_id` after omitting `created_at`, `result_id`, and
   `result_digest`;
2. `result_digest` after omitting only `result_digest`; and
3. every selected source finding ID using the common v1 finding identity
   material from `../resolve-change-scope/references/review-result-contract.md`.

Block malformed or unsupported structure before inspecting repository
contents. Use:

- `artifact_marker_missing`;
- `artifact_json_malformed`;
- `artifact_contract_unsupported`;
- `artifact_structure_invalid`;
- `artifact_result_id_mismatch`;
- `artifact_result_digest_mismatch`; or
- `artifact_finding_id_mismatch`.

A matching digest does not authorize an edit. It only proves that the parsed
bytes match their claimed canonical material.

### 2. Re-resolve repository and reviewed scope

Invoke `resolve-change-scope` once for the artifact's immutable explicit
comparison. Do not trust movable bookmark names or the current working-copy
change ID as endpoint identity.

Independently resolve the current repository identity. Both persisted and
current identities must be `complete`, path-free, and equal. An unavailable
identity blocks with `repository_identity_unavailable`; unequal identities
block with `repository_identity_mismatch`.

Require exact equality for:

- base and target commit identities;
- Jujutsu endpoint change and parent identities when present;
- target change ID in the reviewed endpoint;
- comparison kind and resolved selector;
- sorted changed paths;
- normalized diff digest;
- coverage and unreviewable paths; and
- recomputed `scope_identity`.

Endpoint movement, ambiguity, missing history, partial coverage, or any
identity mismatch blocks with the most specific resolver diagnostic, otherwise
`scope_identity_mismatch`.

### 3. Reproduce current-change freshness

The v1 persisted scope intentionally omits `workspace_fingerprint`. Rebuild
the reviewed workspace material from the immutable target comparison, then
compute its fingerprint using the change-scope contract.

Separately capture the current working change relative to the same base.
Require:

- the same path, change type, content kind, and content-digest inventory;
- the same normalized diff digest and coverage;
- the same resulting tree as the immutable reviewed target; and
- equal reviewed and projected-current workspace fingerprints.

For the last comparison, project the current capture onto the artifact's
explicit request mode before hashing. This is a freshness projection, not a
replacement for the current `ChangeScope.workspace_fingerprint`; it prevents
the `current` versus `explicit` request label from making content-identical
trees compare unequal.

Retain and report both the unprojected current fingerprint and the
projected-current fingerprint.

The current Jujutsu change ID may differ in a disposable workspace; never
pretend it is the bookmarked target. Freshness comes from content and tree
equality. Drift blocks with `workspace_fingerprint_mismatch`.

Capture before-and-after fingerprint inputs. Concurrent drift blocks before
editing.

### 4. Rediscover relevant standards

Invoke `discover-project-standards` once. Build its stable identity from the
same ordered sources and repository-selected tool configuration used by the
review.

Require equality with `standards_inventory_ref`. A changed relevant source,
new conflict, unreadable required source, or incomplete identity blocks with
`standards_inventory_changed`. Do not reinterpret the old finding under new
standards automatically.

Pass the same immutable scope and standards identities to all remaining work.
Do not rediscover them per finding.

### 5. Validate selection and authority

Resolve exact IDs or the one bounded selector against the aggregate artifact
findings. For every selected finding:

- find its source reviewer result;
- recompute its source finding ID;
- require exact category, rule, path, tight location, evidence, severity, and
  contributors;
- require the path and location to exist in the current captured change; and
- require the selected source reviewer to own the finding category.

An unknown or duplicate selected ID blocks with
`selected_finding_unknown`. Ambiguous source ownership blocks with
`selected_finding_ambiguous`. A path outside the persisted and current change,
or a location outside the captured file, blocks with
`selected_finding_scope_mismatch`.

A self-consistently rehashed but incorrect location that remains structurally
in scope is not distinguishable by hashes alone. It must fail independent
evidence reproduction with `finding_evidence_not_reproduced`.

The authorized path set is exactly the sorted non-null paths of the selected
findings. A repository-wide finding with `path: null` grants no automatic edit
authority. Recommendation prose, contributors, shared category, and adjacent
failures do not grant extra paths.

Before editing, write a bounded plan containing selected IDs, reproduced
evidence, exact paths, intended edits, and focused verification. Every planned
path must be within the authorized set. Any extra path, unrelated same-file
cleanup, generated update, ignore-rule change, or suppression blocks with
`remediation_broader_than_finding` and requires new explicit user authority.

### 6. Reproduce each finding independently

Inspect current source and run the smallest repository-selected check needed
to reproduce each finding. Do not rely on artifact prose, result hashes,
reviewer confidence, or the requester's assertion alone.

Reuse safe complete command evidence only when invocation identity, current
scope, configured provenance, and captured inputs still match. Otherwise run
the check once. Do not install tools, invent flags, substitute checkers, edit
configuration, add suppressions, or skip evidence because a check is slow.

If evidence no longer reproduces, record the finding as `unresolved` with
`finding_evidence_not_reproduced` and do not edit for it. Unavailable required
evidence is `blocked`. Continue only for independently reproduced findings
whose complete edit plan remains authorized.

### 7. Apply minimal selected edits

Preserve unrelated user work. Change only the authorized paths and only what
is necessary to address reproduced selected findings.

Do not:

- edit or replace the original artifact;
- fix unselected, newly noticed, or merely related findings;
- recursively follow residual findings;
- change lint, type, test, or ignore configuration to silence evidence;
- create generated plugin state; or
- commit, push, create a pull request, or merge.

Refinement of the same selected edit is allowed while it remains within the
approved plan. Scope expansion is not.

### 8. Run focused verification

Run the repository-selected focused checks that prove each edit and its
immediate integration boundary. Record exact provenance, selected scope,
completion, and concise evidence.

Re-resolve the edited path inventory after verification. Unrelated drift or an
edit outside authority blocks completion. A failing or unavailable required
check leaves the affected finding `unresolved` or `blocked`; never label it
addressed on source inspection alone.

### 9. Invoke one fresh self-review

After at least one selected finding has a minimal edit with complete focused
verification, invoke `conduct-self-review` exactly once on the complete current
change. It writes a new ignored artifact using its own preflight and
persistence rules.

Do not retry the invocation, edit its output, or invoke remediation on its
findings. If it is unavailable, incomplete, or fails to persist, record
`fresh_review_incomplete`; do not claim the remediation workflow completed.

Invoke zero fresh reviews when validation blocks before editing or no selected
finding is safely edited. Invoke exactly one otherwise.

### 10. Map final statuses

Report four disjoint ordered groups:

| Status | Meaning |
| --- | --- |
| `addressed` | Selected finding reproduced, received an authorized edit, passed focused verification, and is absent from adequate fresh review evidence |
| `unresolved` | Selected finding was not reproduced, remains after editing, or lacks complete verification |
| `blocked` | Selected finding could not pass integrity, freshness, standards, authority, or required-tool gates |
| `residual` | Unselected or newly reported finding in the fresh artifact |

One finding ID appears in only one selected-status group. Residual findings are
reported with their new IDs and artifact path, never fixed recursively.

Return:

- old artifact path and result ID;
- new artifact path and result ID when created;
- exact changed paths;
- focused verification summary;
- addressed, unresolved, blocked, and residual IDs;
- primary and supporting diagnostic codes; and
- limitations.

If no edit was authorized, say so explicitly and return no new artifact claim.

## Diagnostic Vocabulary

Use these stable codes:

```text
ok
artifact_path_invalid
artifact_marker_missing
artifact_json_malformed
artifact_contract_unsupported
artifact_structure_invalid
artifact_result_id_mismatch
artifact_result_digest_mismatch
artifact_finding_id_mismatch
repository_identity_unavailable
repository_identity_mismatch
scope_identity_mismatch
workspace_fingerprint_mismatch
standards_inventory_changed
selection_invalid
selected_finding_unknown
selected_finding_ambiguous
selected_finding_scope_mismatch
finding_evidence_not_reproduced
remediation_broader_than_finding
verification_incomplete
fresh_review_incomplete
```

`ok` is the proceed sentinel after every validation gate passes; it is not an
error diagnostic.

The canonical validation examples are in
`references/remediation-vectors.json`.

## Boundaries

- `resolve-change-scope` owns comparison capture and scope identities.
- `discover-project-standards` owns the current standards inventory.
- `conduct-self-review` owns the single fresh aggregate review and artifact.
- This skill alone owns bounded tracked-file remediation after every gate
  passes.
- Hashes are integrity evidence, never mutation authority.
- The user's selection authorizes only the selected findings and exact path
  set.
- Preserve authentication, credentials, trust, sessions, repository paths,
  histories, caches, and generated plugin state outside every artifact and
  response.

## Common Mistakes

- Treating a valid result digest as approval to edit.
- Comparing only a bookmark name instead of immutable endpoint identities.
- Requiring a disposable workspace to reuse the target Jujutsu change ID.
- Assuming the artifact stores a workspace fingerprint.
- Using remediation prose to authorize helper-file edits.
- Calling a non-reproduced finding addressed.
- Running `conduct-self-review` once per finding or retrying it.
- Fixing residual findings from the fresh review.
- Editing the original artifact to record status.
- Committing because the requested fix appears obvious.

## Related Skills

- `resolve-change-scope` — Re-resolve immutable reviewed and current scope.
- `discover-project-standards` — Rebuild the relevant standards identity.
- `conduct-self-review` — Produce the one fresh post-edit artifact.
