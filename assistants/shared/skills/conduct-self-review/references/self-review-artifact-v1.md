# Self-Review Artifact Contract v1

This reference defines the durable local result written by
`conduct-self-review`. It composes four common v1 reviewer results without
becoming a review engine or remediation authority.

## Destination preflight

The default directory is `.reviews/self-review/`. A caller may supply a
different repository-relative `artifact_directory`; an override changes only
the directory.

Before resolving review scope, prove that the selected directory:

- resolves inside the repository after normalization and symlink resolution;
- is already ignored by the repository;
- is untracked and unstaged;
- is writable or can be created below a writable ignored parent; and
- is not selected through an absolute path or `..` traversal.

Do not add or edit ignore rules. Do not search for an arbitrary ignored
directory when the selected directory is unsafe. Ask for a different explicit
repository-relative directory and repeat preflight.

After scope resolution, construct:

```text
<timestamp>-<scope-id-prefix>.md
```

The timestamp is UTC and filename-safe. The scope prefix is the shortest prefix
that distinguishes the full scope identity from identities already present in
the selected directory, with a minimum of 12 lowercase hexadecimal
characters. The complete scope identity remains in the JSON.

Open the final file with exclusive-create semantics. Never overwrite or append
to an existing artifact. If the same scope and timestamp collide, capture a
later UTC timestamp or fail safely; do not invent a suffix or replace the file.

## File layout

The first line is exactly:

```text
<!-- ballen-config:self-review-result:v1 -->
```

The next line opens a fenced JSON block:

````text
```json
```
````

The complete JSON object follows, then the closing fence. Human-readable
Markdown follows the fence. No blank line, heading, or prose may precede the
marker or intervene between the marker and opening fence.

The JSON block is authoritative. The Markdown summary may restate the verdict,
counts, important blockers, and limitations for humans, but cannot add,
override, or reinterpret machine fields.

## Canonical encoding and hashes

Canonical semantic material is JSON encoded as UTF-8 with:

- object keys sorted lexicographically;
- compact `,` and `:` separators;
- Unicode emitted directly rather than ASCII-escaped;
- strings recursively normalized to NFC; and
- arrays in the canonical order defined by their owning contract.

Hashes are lowercase SHA-256 hexadecimal values.

Compute `result_id` from the full top-level object with `created_at`,
`result_id`, and `result_digest` omitted. This makes the ID stable for
identical semantic review content.

Compute `result_digest` after `result_id` and `created_at` are final. Hash the
full top-level object with only `result_digest` omitted. The digest therefore
covers the timestamp and result ID.

## Top-level object

The JSON object has exactly these keys:

| Key | Shape |
| --- | --- |
| `contract_version` | Exact string `v1` |
| `result_id` | Stable lowercase SHA-256 |
| `created_at` | UTC RFC 3339 timestamp ending in `Z` |
| `result_digest` | Integrity lowercase SHA-256 |
| `repository_identity` | Path-free repository identity |
| `scope` | Persisted scope projection |
| `standards_inventory_ref` | Exact lowercase SHA-256 identity |
| `reviewers` | Four reviewer results or four blocked-scope skip records |
| `findings` | Ordered deduplicated common finding objects |
| `commands` | Ordered deduplicated common command objects |
| `skips` | Ordered aggregate skip objects |
| `diagnostics` | Ordered aggregate diagnostic objects |
| `summary` | Exact finding counts and overall verdict |

### Repository identity

`repository_identity` is copied from `ChangeScope` and contains exactly
`state`, `vcs`, `value`, and `code`. It retains only the path-free hashed
identity or its stable unavailable code. It never stores a checkout path,
remote URL, username, query, or fragment.

### Persisted scope

`scope` has:

| Key | Shape |
| --- | --- |
| `status` | `resolved`, `empty`, `partial`, or `blocked` |
| `source` | `git`, `jujutsu`, or `supplied` |
| `request` | Canonical request object from `ChangeScope` |
| `comparison` | Canonical comparison object from `ChangeScope` |
| `target_change_id` | Full Jujutsu change ID or `null` |
| `scope_identity` | Exact lowercase SHA-256 |
| `changed_paths` | Sorted repository-relative path array |
| `diff_digest` | Exact normalized diff SHA-256 or `null` |
| `coverage` | Canonical scope coverage object |

Copy comparison identities and resolved explicit endpoints without
abbreviation. `target_change_id` records the resolved Jujutsu target change ID
when applicable and is null for Git or supplied scope.

`changed_paths` is derived from the canonical change-entry inventory. The
artifact does not retain file contents, content digests, the live
`reviewable_diff.content`, or the full patch. `diff_digest` retains the exact
captured digest so a later consumer can re-resolve and compare the scope.

### Reviewers

For resolved, empty, or partial scope, `reviewers` contains exactly one common
v1 `ReviewResult` for each of:

1. `review-project-standards`;
2. `review-project-quality`;
3. `review-project-tests`; and
4. `review-python-types`.

Every result carries the identical `scope_identity` and
`standards_inventory_ref`. Evidence-backed `not_applicable` results remain
present. Unknown applicability, incomplete work, and unavailable work remain
explicit.

For blocked scope, invoke no specialist. Persist four ordered records with:

| Key | Shape |
| --- | --- |
| `reviewer` | Canonical reviewer name |
| `status` | Exact string `skipped` |
| `reason` | Concise sanitized blocked-scope reason |
| `effect` | Exact string `blocked` |

Do not fabricate empty reviewer results after blocked scope.

### Findings and deduplication

Each aggregate finding uses the common finding shape. Group findings only when
all of these semantic fields match after canonical normalization:

- category;
- rule;
- repository-relative path and tight line location; and
- canonically normalized evidence.

Do not merge findings merely because they share a file or recommendation.
Materially different specialist reasoning remains separate.

For a duplicate group:

- set the aggregate `finding_id` to the lexicographically smallest member ID;
- use the highest normalized severity in the group;
- choose the detail donor among members at that severity, breaking ties by
  finding ID;
- retain the detail donor's nullable source severity and bounded remediation;
  and
- union and sort all contributor names.

This rule is deterministic and preserves every reporting reviewer. Sort
aggregate findings by normalized severity, path, location, rule, then finding
ID as defined by the common result contract.

### Commands

Reuse complete command evidence rather than running an identical configured
command twice. Aggregate command objects by `invocation_id`. Identical IDs must
have identical semantic content; disagreement blocks aggregation as an
integrity failure.

Keep only the common sanitized command fields. Never persist the full
invocation when it contains local paths or sensitive values, raw output,
environment dumps, or a second checker run.

### Skips and diagnostics

Each aggregate skip contains:

| Key | Shape |
| --- | --- |
| `check` | Stable check name |
| `reason` | Concise sanitized reason |
| `effect` | `none`, `incomplete`, `unavailable`, or `blocked` |
| `contributors` | Sorted reviewer names |

Each aggregate diagnostic contains:

| Key | Shape |
| --- | --- |
| `code` | Stable machine-oriented code |
| `path` | Repository-relative path or `null` |
| `detail` | Concise sanitized explanation |
| `contributors` | Sorted producer names |

Deduplicate exact semantic matches and union contributors. Preserve different
reasons or details separately.

### Summary and verdict

`summary` contains exact `blocker`, `actionable`, and `advisory` finding counts
plus `verdict`.

Apply the first matching verdict:

```text
blocked
unavailable
incomplete
blockers_found
needs_attention
advisories
clean
```

Blocked scope, integrity failure, blocked reviewer work, or a blocked skip
produces `blocked`. Required unavailable inputs, reviewers, checks, or skips
produce `unavailable`. Partial scope, unknown applicability, incomplete
reviewer work, or incomplete required skips produce `incomplete`. Findings
then determine `blockers_found`, `needs_attention`, or `advisories`.

`clean` requires resolved or empty complete scope, complete shared inputs,
every reviewer accounted for, completed applicable reviewers,
evidence-backed non-applicability for the rest, no findings, no unknown
applicability, no skips, no unavailable checks, and no blocked work.

## Persistence and response

Every attempt whose destination passes preflight writes an artifact, including
empty, partial, blocked, unavailable, and finding-bearing results. Build and
validate the complete object before the exclusive write.

After persistence, verify the marker, parse the JSON back, recompute both
hashes, and confirm the persisted path remains ignored and untracked. Return a
concise inline verdict, counts, important blockers or limitations, and a
clickable repository-relative artifact path.

If persistence or post-write verification fails, self-review did not complete.
Report that failure without claiming the computed verdict or a clean result.

## Privacy and authority

The artifact is ignored user-controlled evidence, not signed authorization.
It never contains:

- the raw patch or entire diff;
- large or raw command output;
- absolute project paths;
- remote URLs or user information;
- credentials, authentication material, tokens, or secrets;
- trust or session state;
- caches, histories, indexes, or generated plugin state; or
- sensitive values copied from diagnostics.

Later remediation must independently re-resolve repository containment,
comparison identities, current scope content, standards, finding evidence, and
the selected authority boundary.
