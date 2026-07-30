# Review-Result Contract v1

This reference defines the common logical result returned by every
review-foundation specialist. Specialist skills own their checks and finding
categories, while this envelope keeps composition deterministic.

## Canonical encoding

Canonical identity material follows the change-scope contract:

- UTF-8 JSON;
- lexicographically sorted object keys;
- compact `,` and `:` separators;
- Unicode emitted directly;
- recursively NFC-normalized strings; and
- stable ordering for semantically unordered arrays.

Hashes are lowercase SHA-256 hexadecimal values. Identity material excludes
timestamps, diagnostic prose, absolute paths, raw command output, credentials,
and command-output order.

## Top-level object

The result has exactly:

| Key | Required shape |
| --- | --- |
| `contract_version` | Exact string `v1` |
| `reviewer` | Canonical specialist skill name |
| `scope_identity` | Exact supplied scope SHA-256 |
| `standards_inventory_ref` | Exact supplied inventory SHA-256 |
| `applicability` | Applicability enum |
| `outcome` | Outcome enum |
| `coverage` | Coverage object |
| `findings` | Ordered finding array |
| `skips` | Ordered skip array |
| `commands` | Ordered sanitized command array |
| `summary` | Counts and verdict |

The envelope contains no creation timestamp. Persisted orchestration artifacts
may record time outside this semantic object.

## Applicability and outcome

`applicability` is:

- `applicable` when the specialist owns at least one relevant check;
- `not_applicable` only when evidence proves its domain is absent; or
- `unknown` when applicability could not be established.

`outcome` is:

- `completed` when every required applicable input and check completed;
- `incomplete` when usable evidence exists but coverage is truncated or
  partial;
- `unavailable` when a required input, command, or tool cannot be accessed; or
- `blocked` when the supplied scope or integrity boundary is untrustworthy.

A nonzero check exit that reports violations is `completed`, not
`unavailable`. A timeout, truncated result, or early abort is `incomplete`. A
missing executable is `unavailable`. Unsafe work that cannot be skipped
without losing required coverage makes the result incomplete, unavailable, or
blocked according to its effect.

## Coverage

`coverage` has:

| Key | Shape |
| --- | --- |
| `scope` | `complete`, `partial`, or `unavailable` |
| `inputs` | `complete`, `partial`, or `unavailable` |
| `checks` | Ordered check-coverage array |

Each check-coverage item has:

| Key | Shape |
| --- | --- |
| `check` | Stable specialist-owned check name |
| `required` | Boolean |
| `selected_scope` | `changed`, `full`, or `none` |
| `completion` | `completed`, `incomplete`, `unavailable`, or `skipped` |

Sort checks by stable check name, then selected scope. A full-repository
command may still provide complete changed-scope coverage when its output
examines every changed path. Failures outside the supplied scope are not
changed-scope findings.

## Findings

Each finding has exactly:

| Key | Shape |
| --- | --- |
| `finding_id` | Stable lowercase SHA-256 |
| `category` | Stable specialist-owned category |
| `severity` | `blocker`, `actionable`, or `advisory` |
| `source_severity` | Original tool or standards label, or `null` |
| `path` | Repository-relative path or `null` |
| `location` | Tight line object or `null` |
| `rule` | Stable rule or check identifier, or `null` |
| `evidence` | Concise sanitized evidence |
| `remediation` | Concise recommendation or `null` |
| `contributors` | Ordered canonical reviewer names |

A location is `{start_line, end_line}` with positive inclusive line numbers.
When no path exists, location is null. Normalize paths to NFC
repository-relative POSIX form.

Severity means:

- `blocker`: unsafe to merge or impossible to trust;
- `actionable`: a material correction is required; and
- `advisory`: optional improvement that does not block the change.

Retain an original label such as `error`, `warning`, `Critical`,
`Suggestion`, or `Nit` in `source_severity` when it helps interpretation.

### Stable finding identity

Normalize evidence newlines to LF, normalize it to NFC, and hash its exact
UTF-8 bytes. Call that value `evidence_digest`.

Hash canonical JSON containing exactly:

```text
reviewer
category
rule
location
evidence_digest
```

`location` is null for a finding without a path. Otherwise it contains
`path`, nullable `start_line`, and nullable `end_line`. Severity, remediation,
and contributors are excluded so normalization and later aggregation do not
change the finding's semantic identity.

Sort findings by normalized severity precedence (`blocker`, `actionable`,
`advisory`), path, start line, rule, then finding ID.

## Skips

Each skip has:

| Key | Shape |
| --- | --- |
| `check` | Stable check name |
| `reason` | Concise sanitized reason |
| `effect` | `none`, `incomplete`, `unavailable`, or `blocked` |

Use `none` only when the skipped operation is outside the specialist's
ownership or is provably optional. Delegation to another named specialist is
not a skip when this specialist fully completed its own inventory duty.

Sort skips by check, effect, then reason.

## Command evidence

Each command record has:

| Key | Shape |
| --- | --- |
| `invocation_id` | Stable lowercase SHA-256 |
| `provenance` | Repository-relative configuration or standards source |
| `selected_scope` | `changed`, `full`, or `none` |
| `completion` | `completed`, `incomplete`, `unavailable`, or `skipped` |
| `exit_status` | Integer or `null` |
| `evidence` | Concise redacted summary |
| `unrun_reason` | Concise reason or `null` |

For a completed command, `exit_status` is present and `unrun_reason` is null.
For every other completion state, `unrun_reason` is present. A nonzero exit may
be completed when the command successfully reports violations.

Derive `invocation_id` from canonical semantic command material held during
execution: stable check name, repository-relative provenance, selected scope,
and sanitized configured invocation. Do not persist the full invocation when
it contains local paths or sensitive values.

Command evidence never stores raw output, absolute paths, environment dumps,
remote URLs, credentials, or more output than is needed to support findings
and limitations. Sort commands by provenance, selected scope, then
invocation ID.

## Summary and verdict

`summary` contains:

| Key | Shape |
| --- | --- |
| `counts` | Exact `blocker`, `actionable`, and `advisory` finding counts |
| `verdict` | Verdict enum |

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

Apply the first matching condition:

1. blocked scope, integrity, input, check, or skip effect;
2. unavailable required input, check, or skip effect;
3. incomplete outcome or coverage, unknown applicability, or an incomplete
   required skip/check;
4. one or more blocker findings;
5. one or more actionable findings;
6. one or more advisory findings; or
7. clean.

`clean` requires resolved or empty scope with complete required coverage,
every reviewer accounted for, no findings, no unknown applicability, no skips,
no unavailable checks, and no blocked work. A specialist result may be clean
only for its owned domain; orchestration recomputes the aggregate verdict.

## Privacy and integrity

The result refers to the exact supplied `scope_identity` and
`standards_inventory_ref`. A reviewer that cannot validate those inputs
returns blocked or unavailable rather than rediscovering a different scope
silently.

No result object contains an absolute path, raw diff, raw command output,
credential, session state, trust state, or generated plugin state.
