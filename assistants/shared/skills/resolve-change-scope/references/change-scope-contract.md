# Change-Scope Contract v1

This reference defines the logical v1 handoff produced by
`resolve-change-scope`. It is a portable data contract, not a command transcript
or persistence format.

## Canonical encoding

Canonical identity material is JSON encoded as UTF-8 with:

- lexicographically sorted object keys;
- compact `,` and `:` separators;
- Unicode emitted directly rather than ASCII-escaped;
- NFC-normalized repository-relative POSIX paths; and
- arrays sorted when their source order has no semantic meaning.

Hashes are lowercase SHA-256 hexadecimal values. Identity material excludes
timestamps, diagnostic detail, absolute paths, raw remote URLs, user
information, query strings, fragments, command-output order, and transient
tool output.

## Top-level object

The object has exactly these keys:

| Key | Required shape |
| --- | --- |
| `contract_version` | Exact string `v1` |
| `status` | `resolved`, `empty`, `partial`, or `blocked` |
| `source` | `git`, `jujutsu`, or `supplied` |
| `request` | Request object |
| `repository_identity` | Repository-identity object |
| `comparison` | Comparison object |
| `workspace_fingerprint` | Lowercase SHA-256 or `null` |
| `changes` | Ordered change-entry array |
| `reviewable_diff` | Reviewable-diff object |
| `coverage` | Coverage object |
| `diagnostics` | Ordered diagnostic array |
| `scope_identity` | Lowercase SHA-256 |

### Request

`request` contains:

| Key | Shape |
| --- | --- |
| `mode` | `current`, `explicit`, or `supplied` |
| `selector` | `null` or `{base, target}` for an explicit request |

Both selector values are the caller's normalized selector strings. They are
request evidence, not immutable comparison identity.

### Repository identity

`repository_identity` contains:

| Key | Shape |
| --- | --- |
| `state` | `complete` or `unavailable` |
| `vcs` | `git`, `jujutsu`, or `supplied` |
| `value` | Lowercase SHA-256 or `null` |
| `code` | Stable diagnostic code or `null` |

Select the single tracked remote first, then `origin`, then the only configured
remote. Multiple tracked candidates are unavailable immediately. With no
tracked remote, multiple non-`origin` remotes are ambiguous. Do not fall
through an ambiguous higher-precedence choice.

Parse the selected remote locally. Normalize:

- VCS kind;
- lowercase host with default port removed; and
- NFC namespace with leading and trailing slashes and terminal `.git`
  removed, preserving path case.

Hash the canonical `{vcs, host, namespace}` object. Never retain the raw URL,
user information, query, fragment, or local checkout path. Use
`repository_identity_unparseable`, `repository_identity_ambiguous`, or
`repository_identity_no_remote` when identity is unavailable.

### Comparison

`comparison` contains:

| Key | Shape |
| --- | --- |
| `kind` | Comparison-kind enum |
| `base_identities` | Ordered comparison-identity array |
| `target_identity` | One comparison identity |
| `resolved_selector` | Resolved endpoint object or `null` |

Comparison kinds are:

- `git-head-to-worktree`;
- `jujutsu-merged-parents-to-working-copy`;
- `explicit-range`;
- `supplied-files`; and
- `supplied-patch`.

Each comparison identity is `{state, value}`. `state` is `resolved` or
`unavailable`; `value` is a full VCS-native immutable ID or `null`. Sort
multi-parent base identities by full immutable ID. For current Git work, the
target identity is unavailable and the workspace fingerprint identifies the
captured target state. For current Jujutsu work, the snapshotted working-copy
commit ID is the resolved target.

The Jujutsu change inventory comes from its native comparison of `@` with the
automatic merge of all parents. A union, intersection, or preferred side of
per-parent diffs is not equivalent and must not be used. When that native
comparison is unavailable, the scope is blocked with `diff_unavailable`.

`resolved_selector` is `null` outside explicit mode. In explicit mode it
contains canonical `base` and `target` immutable IDs plus Jujutsu change and
parent IDs when applicable.

For explicit endpoint resolution, zero matches use `selector_not_found` and
more than one match uses `range_endpoint_not_singleton`.
`selector_ambiguous` is reserved for a backend that rejects the selector as
ambiguous without returning an enumerable result set.

### Change entry

Each item in `changes` has exactly:

| Key | Shape |
| --- | --- |
| `path` | NFC repository-relative POSIX path |
| `change_type` | `add`, `modify`, `delete`, or `rename` |
| `previous_path` | Previous repository-relative path or `null` |
| `content_kind` | Content-kind enum |
| `diff_state` | Diff-state enum |
| `content_digest` | Lowercase SHA-256 or `null` |

Content kinds are `text`, `binary`, `symlink`, `submodule`, `conflict`, and
`unknown`. Diff states are `complete`, `binary-marker`, and `unavailable`.

For an add, modify, or rename, `content_digest` hashes the captured target
content. For a delete, it hashes the captured base content. A symlink hashes
its link target; a submodule hashes its object ID. Use `null` when trustworthy
content is unavailable. Preserve native rename relationships only.

Sort entries by normalized current path, nullable previous path, then change
type. `previous_path` is non-null only for `rename`.

Supplied file-only input consists of structured entries containing at least
`path`, `change_type`, and `previous_path` for renames. When content evidence
is absent, set `content_kind` to `unknown`, `diff_state` to `unavailable`, and
`content_digest` to `null`; the scope is partial. A bare string path list is
invalid because it cannot distinguish add, modify, delete, and rename.

For patch-only supplied input, validated unified-diff headers establish the
entry inventory. `/dev/null` establishes add or delete, native rename headers
establish rename, and other paired paths establish modify. When both
structured entries and a patch are supplied, their inventories and change
types must match exactly.

### Reviewable diff

`reviewable_diff` contains:

| Key | Shape |
| --- | --- |
| `state` | `complete`, `partial`, or `unavailable` |
| `format` | `unified`, `supplied-unified`, or `none` |
| `content` | Exact normalized patch string or `null` |
| `digest` | Lowercase SHA-256 or `null` |
| `unavailable_paths` | Ordered repository-relative path array |

The live handoff retains exact normalized textual patch content. Its digest is
computed from the UTF-8 patch bytes. Empty complete comparisons use an empty
patch and its SHA-256 digest. When some paths are binary or unavailable, retain
the exact reviewable textual subset, mark the state `partial`, and list every
unavailable path. If no trustworthy patch exists, use `unavailable`, `none`,
and a null digest.

A persisted projection always sets `content` to `null`; this omission does not
change the recorded digest or scope identity.

### Coverage

`coverage` contains:

| Key | Shape |
| --- | --- |
| `entries` | `complete`, `partial`, or `unavailable` |
| `textual_diff` | `complete`, `partial`, or `unavailable` |
| `overall` | `complete`, `partial`, or `unavailable` |
| `unreviewable_paths` | Ordered repository-relative path array |

`entries` describes path and change-classification coverage.
`textual_diff` describes exact patch coverage. `overall` is the least complete
of the required dimensions. A binary marker makes textual and overall coverage
partial even when the entry and content digest are complete.

### Diagnostic

Each diagnostic has exactly:

| Key | Shape |
| --- | --- |
| `code` | Stable machine-oriented code |
| `path` | Repository-relative path or `null` |
| `detail` | Concise sanitized explanation |

Sort diagnostics by code, nullable path, then detail. Diagnostic detail is
excluded from all identities.

The v1 vocabulary is:

- `unsupported_repository`;
- `vcs_command_unavailable`;
- `git_head_missing`;
- `selector_not_found`;
- `selector_ambiguous`;
- `range_endpoint_not_singleton`;
- `working_copy_changed_during_capture`;
- `supplied_scope_invalid`;
- `supplied_diff_unparseable`;
- `conflict_unresolved`;
- `diff_unavailable`;
- `binary_diff_unreviewable`;
- `content_unavailable`;
- `repository_identity_unparseable`;
- `repository_identity_ambiguous`; and
- `repository_identity_no_remote`.

## Status rules

Use:

- `resolved` for a complete non-empty comparison;
- `empty` for a complete valid comparison with zero changes;
- `partial` when the comparison and changed paths are trustworthy but required
  content or textual coverage is incomplete; and
- `blocked` when no trustworthy comparison can be established.

Binary or unavailable diff content is partial. A missing Git `HEAD`, missing or
ambiguous endpoint, unresolved conflict, invalid supplied scope, unavailable
required VCS command, or capture drift is blocked. Partial and blocked results
cannot support a clean review verdict.

## Identity material

### Workspace fingerprint

Hash one canonical object containing:

- `source`;
- request `mode`;
- sorted full base identity values;
- sorted change entries, including content digests;
- diff coverage; and
- no diagnostic prose or local path.

When capture drift or missing evidence prevents a trustworthy fingerprint, use
`null`.

### Scope identity

Hash one canonical object containing:

- `contract_version`;
- `source`;
- request `mode`;
- repository-identity `state` and `value`;
- comparison kind, base identities, target identity, and resolved selector;
- workspace fingerprint;
- reviewable-diff digest; and
- coverage.

Do not include status, diagnostic prose, timestamps, raw diff content, or
command-output ordering. Those values describe handling or presentation rather
than the semantic comparison.

Keep the full scope identity in the contract. Artifact filenames use the
shortest prefix that selects only that full identity among existing artifacts,
with a minimum length of 12 hexadecimal characters. Never overwrite an
existing filename.

## Drift and privacy boundary

Capture the workspace fingerprint inputs before and after reading content. Any
semantic difference blocks the result with
`working_copy_changed_during_capture`; do not return a stale candidate scope.

The resolver does not modify tracked files, stage changes, create commits,
write ignore rules, or inspect ignored-file contents. It never emits absolute
paths, raw remote URLs, credentials, session state, trust state, or generated
plugin state.
