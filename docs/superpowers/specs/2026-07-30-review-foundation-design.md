# Review Foundation Detailed Design

## Status

Approved focused design for the review-foundation train in the
[reusable review workflows roadmap](2026-07-30-reusable-review-workflows-roadmap-design.md).
This document defines the shared contracts, six-MR delivery sequence,
verification evidence, and stacked GitHub merge procedure required before
implementation begins.

## Purpose

Build a portable, local-first review foundation in `ballen-config`. The
foundation must resolve one trustworthy change scope, apply repository-owned
standards and checks, persist a review result, and address explicitly selected
findings without importing Plato-specific commands or provider state.

The train contains six strictly serial MRs:

1. `resolve-change-scope`;
2. `review-project-quality`;
3. `review-project-tests`;
4. `review-python-types`;
5. `conduct-self-review`; and
6. `address-self-review`.

The first five skills do not edit tracked project source or configuration.
`conduct-self-review` writes only its required verified ignored artifact.
`address-self-review` is the only skill in this train authorized to edit
tracked project files.

## Goals

- Define one Git/Jujutsu-neutral change-scope contract.
- Make the current non-ignored local change the useful default scope.
- Give every specialist reviewer one common result envelope.
- Resolve change scope and standards once during composed self-review.
- Preserve skill-owned judgment instead of creating a central review engine.
- Persist every self-review in a verified ignored repository workspace.
- Separate review from remediation through `address-self-review`.
- Dogfood structural review and remediation on real `ballen-config` changes.
- Merge the six GitHub PRs sequentially without relying on automatic
  downstream retargeting.

## Non-Goals

- Forge review publication or response
- Review-thread normalization, lesson extraction, or lesson promotion
- Plato cleanup or source deletion
- Plugin packaging or generic skill retirement
- A `ty` migration
- A central executable review application
- Automatic commits, pushes, PR mutation, or merges
- Migration of authentication, trust, sessions, history, permissions, personal
  project paths, caches, indexes, worktrees, or generated plugin state

## Architecture

### Shared envelope with skill-owned checks

`resolve-change-scope` owns the shared scope vocabulary. Each specialist owns
its applicability rules, evidence, findings, and limitations. The common
contract standardizes composition without centralizing reviewer judgment.

Standalone reviewers invoke named dependencies unless the caller supplies
valid, current results. `conduct-self-review` invokes scope resolution and
standards discovery once, then passes the same immutable results to every
consumer.

`address-self-review` consumes a persisted self-review result, revalidates its
scope and standards, applies explicitly selected findings, verifies the
resulting change, and performs one fresh self-review. It never recursively
addresses new findings.

### Catalog dependency graph

| Skill | Direct named dependencies |
| --- | --- |
| `resolve-change-scope` | None |
| `review-project-standards` | `resolve-change-scope`, `discover-project-standards` |
| `review-project-quality` | `resolve-change-scope`, `discover-project-standards` |
| `review-project-tests` | `resolve-change-scope`, `discover-project-standards` |
| `review-python-types` | `resolve-change-scope`, `discover-project-standards` |
| `conduct-self-review` | `resolve-change-scope`, `discover-project-standards`, and the four reviewers |
| `address-self-review` | `resolve-change-scope`, `discover-project-standards`, `conduct-self-review` |

Direct dependencies name the skills that a consumer invokes. Transitive
installation remains useful but is not used to hide an invocation dependency.
The catalog continues to enforce target/profile eligibility, unknown
dependencies, and cycles.

### Rejected alternatives

Loose Markdown conventions were rejected because aggregation and remediation
would have to infer result state from prose. A central review engine was
rejected because it would duplicate repository-selected tools, absorb
skill-owned judgment, and turn a focused skill migration into an application.

## Change-Scope Contract

### Inputs

`resolve-change-scope` accepts a repository root and one of three modes:

| Mode | Meaning |
| --- | --- |
| `current-change` | Current non-ignored local work; default when no selector is supplied |
| `explicit-range` | One resolved base endpoint and one resolved target endpoint |
| `supplied` | Caller-provided file set and/or diff without a required VCS comparison |

The resolver never silently selects `main`, `HEAD~1`, a staging-only view, or a
branch name.

### Current-change semantics

For Git, current change means:

- staged tracked changes relative to `HEAD`;
- unstaged tracked changes relative to `HEAD`; and
- non-ignored untracked files represented as additions.

No single Git diff or status command is treated as sufficient when it omits one
of those categories. A repository without `HEAD` cannot form this default
comparison and returns a blocked result.

For Jujutsu, current change means `@` relative to the automatic merge of all
its parents. Normal Jujutsu snapshot bookkeeping is allowed so the review sees
current content. `--ignore-working-copy` is not the default because it may
produce a stale scope.

Ignored files are excluded without enumerating them. The resolver does not read
ignored paths merely to prove their exclusion.

### Explicit and supplied scopes

An explicit endpoint must resolve to exactly one revision. The result records
immutable Git object IDs or Jujutsu commit IDs where available. Jujutsu results
also retain change IDs and all parent commit IDs rather than inventing one base
for a multi-parent change.

A supplied scope may carry caller-provided identities, but those identities are
marked unverified. A supplied file list without a reviewable diff is partial. A
valid supplied patch with consistently parsed paths may be resolved. Invalid,
contradictory, or unparseable supplied input is blocked.

### Logical result

The v1 `ChangeScope` contains:

- contract version;
- status and source;
- requested mode and selector;
- path-free repository identity;
- comparison kind;
- base and target identity states;
- resolved selector;
- ephemeral workspace fingerprint where needed;
- repository-relative change entries;
- the exact reviewable diff or an explicit binary/unavailable marker;
- diff state and digest;
- coverage;
- diagnostics; and
- one deterministic scope identity.

`reviewable_diff` is a distinct in-memory field with state, format, content,
digest, and unavailable paths. It contains the exact normalized patch when
textual review coverage is complete. Binary or unavailable content is
represented by explicit path-level markers rather than coerced text. The
persisted self-review artifact retains the digest and coverage but omits the
full patch.

Each change entry contains:

- current path;
- add, modify, delete, or native rename classification;
- previous path when the backend supplies one;
- text, binary, symlink, submodule, conflict, or unknown content kind; and
- complete, binary-marker, or unavailable diff state.

Native rename information is preserved. If a backend does not provide a rename
relationship, v1 retains add/delete entries instead of applying a cross-VCS
similarity heuristic.

### Scope states

| State | Meaning |
| --- | --- |
| `resolved` | Complete, non-empty comparison |
| `empty` | Valid, complete comparison with no changes |
| `partial` | Trustworthy scope exists, but required coverage is incomplete |
| `blocked` | No trustworthy comparison can be established |

Unreviewable binary content makes the result partial. Missing or ambiguous
endpoints, unavailable VCS commands, missing Git `HEAD`, unresolved conflicts,
invalid supplied content, or a checkout that changes during capture block the
result.

Stable diagnostics use machine-oriented codes such as:

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
- `diff_unavailable`; and
- `binary_diff_unreviewable`.

Neither partial nor blocked scope can produce a clean review verdict.

### Canonical identities

Identity material uses UTF-8 canonical JSON with lexicographically sorted keys,
compact separators, NFC-normalized repository-relative POSIX paths, and stable
ordering for unordered arrays. SHA-256 produces lowercase hexadecimal IDs.
Timestamps, diagnostic prose, absolute paths, and command-output ordering are
excluded from scope identity material.

Repository identity has `complete` or `unavailable` state. Remote selection
uses this precedence:

1. the single remote tracked by the current bookmark or branch;
2. `origin`;
3. the only configured remote; or
4. unavailable when none exists or selection remains ambiguous.

Multiple candidates at a higher-precedence step make identity unavailable;
selection does not fall through to a lower-precedence guess.

The selected remote is parsed locally. Host names are lowercased, default ports
are removed, namespace/path is NFC-normalized with leading and trailing slashes
and a terminal `.git` removed, and path case is preserved. The normalized host,
namespace/path, and VCS kind are hashed. Raw URLs, user information, query
strings, fragments, and local paths never enter the identity. An unparseable
remote produces unavailable identity rather than a guessed fallback.

The workspace fingerprint hashes:

- source and mode;
- sorted base identities;
- sorted change entries;
- per-entry content or diff digests; and
- diff coverage.

The scope identity hashes contract version, source, mode, repository-identity
state/value, comparison identities, workspace fingerprint, diff digest, and
coverage. Full identities remain in the result. Filenames use the shortest
unique prefix of at least 12 hexadecimal characters and never overwrite an
existing artifact.

Fixture vectors freeze canonical serialization, workspace fingerprints, scope
identities, and filename prefixes for both resolver and remediation tests.
Single-remote, tracked-upstream, `origin` fallback, ambiguous multi-remote, and
no-remote cases are all represented.

## Shared Review-Result Contract

### Envelope

Each reviewer returns a logical v1 envelope with:

| Field | Meaning |
| --- | --- |
| `contract_version` | Result schema version |
| `reviewer` | Skill that owns the result |
| `scope_identity` | Exact immutable scope supplied to the reviewer |
| `standards_inventory_ref` | Exact discovered standards inventory |
| `applicability` | `applicable`, `not_applicable`, or `unknown` |
| `outcome` | `completed`, `incomplete`, `unavailable`, or `blocked` |
| `coverage` | Scope, input, and check coverage |
| `findings` | Normalized specialist findings |
| `skips` | Explicit unperformed work and its effect |
| `commands` | Sanitized repository-selected command evidence |
| `summary` | Finding counts and verdict |

A reviewer may be `not_applicable` only with evidence, such as no Python files
in scope. Unexamined applicability remains `unknown` and prevents a clean
result.

### Findings

Every finding contains:

- a deterministic ID within the review result;
- category;
- normalized severity;
- original source severity when present;
- repository-relative path and tight location when available;
- applicable rule;
- concise evidence; and
- optional remediation guidance.

Normalized severities are:

| Severity | Meaning |
| --- | --- |
| `blocker` | Unsafe to merge or impossible to trust |
| `actionable` | Material correction or improvement is required |
| `advisory` | Optional improvement that does not block the change |

Existing `Critical`, `Suggestion`, and `Nit` labels remain visible as source
severities and map into the normalized vocabulary.

### Outcomes and verdicts

`clean` is a verdict, not an execution state. It requires:

- resolved or empty scope with complete required coverage;
- every applicable reviewer completed;
- every non-applicable reviewer accounted for with evidence;
- no findings;
- no unknown applicability;
- no skips;
- no unavailable checks; and
- no blocked work.

Overall precedence is:

```text
blocked
unavailable
incomplete
blockers_found
needs_attention
advisories
clean
```

A command that exits nonzero because it found violations completed and
produces findings. A missing executable or unreadable required input is
unavailable. Truncated, timed-out, or partially usable execution is incomplete.
An unsafe or inherently mutating command is skipped and prevents complete
coverage when the check is required.

### Command evidence

Command records contain sanitized invocation identity, provenance, selected
scope, completion state, exit status when available, concise redacted evidence,
and an unrun reason when applicable. They do not persist raw credentials,
absolute personal paths, or large command output.

When a composed review would run an identical configured command twice,
`conduct-self-review` reuses complete evidence rather than repeating the
command.

## Specialist Reviewer Responsibilities

### `review-project-standards`

This existing skill is aligned with the shared result envelope in MR 5. It:

- maps discovered repository instructions and lessons to the supplied scope;
- preserves source severity labels;
- reports conflicts and incomplete discovery;
- accepts a supplied scope and standards inventory without rediscovering them;
  and
- no longer offers an internal fix phase.

Standalone invocation uses its named resolver and discovery dependencies.

### `review-project-quality`

This skill:

- discovers repository-selected lint, formatting, documentation, build, and
  related quality checks;
- prefers supported scope-aware invocations;
- uses safe full configured checks when no scoped mode exists;
- separates out-of-scope diagnostics from changed-scope findings;
- records a limitation when an external failure prevents examination of the
  changed scope;
- reports configured Ruff docstring findings when the repository enables them;
- inventories type-check tooling but delegates Python type-check execution and
  findings to `review-python-types`; and
- never invents installation, commands, suppressions, or generic tool defaults.

It assesses whether changed documentation remains accurate and useful.
Repository-specific docstring presence and style remain standards-review
concerns.

### `review-project-tests`

This skill maps changed behavior to relevant tests and examines:

- behavioral value and regression coverage;
- meaningful assertions;
- fixtures, doubles, and patch-at-use behavior;
- async-aware mock behavior where applicable;
- snapshots and generated-output intent;
- source/test coverage gaps;
- test names and short behavioral docstrings;
- near-duplicate tests that should be consolidated; and
- repeated behavior matrices that should use explicit parameterization.

It preserves separate tests when they communicate materially different
scenarios more clearly.

Test-theatre detection includes tests that:

- execute code without proving owned behavior;
- reproduce guarantees supplied by a framework or dependency, such as testing
  that Pydantic `BaseModel` populates declared attributes;
- reassert configuration already covered by behavior tests;
- use tautological or weak status-only assertions;
- over-mock until production control flow is not exercised; or
- pin human-authored documentation or prompt prose with substrings or opaque
  digests that production does not consume.

Every test must be able to fail for a meaningful regression in code the
repository owns. The skill never updates snapshots or rewrites tests.

### `review-python-types`

This skill applies only when Python changes are present. It reviews:

- annotations and public contracts;
- controlled mapping shapes;
- `TypedDict`, dataclass, and validated-model boundaries;
- downstream callers and tests;
- validation and serialization boundaries; and
- repository-selected type-check evidence.

It is the sole owner of Python type-check execution and type-check findings.
Other reviewers may reuse its evidence but do not rerun the command. It is
checker-agnostic. Initial dogfooding uses the repository's current strict mypy
configuration. It does not add suppressions, refactor code, prescribe checker
flags, or introduce `ty`.

### Docstring ownership

The canonical documentation standard requires Google-style docstrings for
every public module, class, function, and method. The testing standard requires
every test to have a short behavioral docstring.

Use a concise one-line docstring when the purpose is straightforward and no
additional contract detail is useful. Expand to Google-style sections when
parameters, return semantics, raised exceptions, side effects, or invariants
add context.

Ownership is split deliberately:

- quality review reports configured Ruff `D` violations;
- standards review assesses required presence and one-line versus expanded
  appropriateness; and
- test review assesses whether test names and docstrings state meaningful
  repository-owned behavior.

The reusable Ruff starter enables all docstring rules except `D401` and selects
the Google convention. Ballen-config's active Ruff selection does not currently
enable `D`; aligning that executable configuration is a separate follow-up.

## Self-Review Orchestration

`conduct-self-review` accepts a scope request and an optional
repository-relative `artifact_directory`. An explicit directory takes
precedence over the default `.reviews/self-review/`. The skill does not search
for arbitrary ignored directories.

When the selected directory fails preflight, the skill asks for a different
repository-relative ignored directory and repeats validation before reviewing.
It never accepts an absolute destination or edits ignore rules.

`conduct-self-review` performs this sequence:

1. Preflight the ignored review-artifact destination.
2. Resolve the requested change scope once.
3. Discover standards once.
4. On blocked scope, skip specialist invocation and persist the blocked result.
5. Pass the same scope identity and standards inventory to every reviewer.
6. Allow clearly limited analysis on partial scope while forcing an incomplete
   result.
7. Invoke standards, quality, tests, and Python types where applicability is
   established.
8. Deduplicate overlapping findings.
9. Persist the complete review artifact.
10. Return a concise inline summary and artifact path.

Deduplication groups the same rule/category, location, and evidence while
retaining every contributing reviewer. It does not erase materially different
specialist reasoning.

The orchestrator aggregates results and commands. It does not implement another
checker, perform edits, or claim authority over native
`verification-before-completion` and code-review workflows.

## Review Artifact Contract

### Default workspace

Every self-review attempt that passes artifact preflight writes a result,
including empty, partial, blocked, and unavailable outcomes. Without an
explicit `artifact_directory`, the default is:

```text
.reviews/self-review/<timestamp>-<scope-id>.md
```

MR 5 intentionally adds `.reviews/` to ballen-config's `.gitignore`. In another
repository, the skill uses this convention only when it is already ignored.
The caller may instead supply another repository-relative ignored directory.
An override changes only the directory; the generated
`<timestamp>-<scope-id>.md` filename and no-overwrite behavior remain the same.

Before review begins, the skill proves that the destination:

- resolves inside the repository;
- is ignored;
- is untracked;
- is writable; and
- will not overwrite an existing artifact.

A tracked or staged destination blocks the run. If no safe destination exists,
the skill requests one and writes nothing. It never changes ignore rules.

### Artifact format

The artifact begins with the exact marker:

```text
<!-- ballen-config:self-review-result:v1 -->
```

The next fenced JSON block is the canonical machine-readable result consumed by
`address-self-review`. JSON keeps structural validation in the standard
library and avoids adding a YAML dependency. Human-readable Markdown follows
the result block.

The artifact includes:

- result ID and UTC creation time;
- result digest;
- path-free repository and scope identities;
- standards inventory identity;
- scope status, changed paths, diff digest, and coverage;
- reviewer applicability and outcomes;
- findings and stable IDs;
- command evidence, skips, and diagnostics; and
- overall verdict.

It does not persist the entire raw diff or large raw command output. It retains
only the changed-file inventory, digest, and concise evidence needed to
revalidate the result.

The artifact excludes absolute project paths, authentication, credentials,
trust data, sessions, and unredacted sensitive output. The inline response
contains the verdict, finding counts, important blockers, and a clickable path.

Failure to persist the artifact means self-review did not complete and cannot
claim a clean result.

### Integrity boundary

The ignored local artifact is user-controlled input, not a signed or
tamper-proof authority. `result_digest` is SHA-256 over canonical JSON for the
machine-readable block with only `result_digest` omitted. Structural validation
plus this digest detects malformed or accidentally changed artifacts.

Finding IDs use the same canonicalization and hash reviewer, category, rule,
repository-relative location, and evidence digest. They are deterministic for
an unchanged result.

`address-self-review` never treats hashes as authorization by themselves.
Current repository containment, comparison identities, scope content, and
standards are re-resolved independently before editing.

## Addressing Self-Review

`address-self-review` accepts:

- one explicit v1 review artifact path; and
- explicit finding IDs or an explicit bounded selector such as all actionable
  findings in that result.

It never infers an unspecified "latest review."

### Pre-edit validation

Before editing, the skill validates:

- artifact marker and JSON structure;
- contract version and result integrity;
- complete, matching persisted and current repository identities;
- matching scope identities;
- current-change fingerprint;
- current standards inventory;
- selected finding IDs;
- independently reproducible evidence for each selected finding;
- affected repository-relative paths; and
- whether the requested work remains within the finding's authority.

Explicit invocation against selected findings authorizes focused edits when
scope and standards still match. The skill pauses for stale scope, ambiguous
findings, changed standards that affect the decision, materially broader work,
or unavailable repository identity. An unavailable repository identity is
valid for review but cannot authorize remediation in v1.

### Edit and verification cycle

The skill:

1. applies the smallest sufficient edits for the selected findings;
2. avoids unrelated cleanup;
3. runs repository-selected focused verification;
4. resolves the resulting current scope again;
5. invokes one fresh `conduct-self-review`;
6. writes a new review artifact; and
7. reports every selected finding as resolved, unresolved, superseded, or
   blocked.

Remaining and newly discovered findings stay visible. The skill does not
recursively fix them, change ignore rules, add suppressions without separate
approval, commit, push, or mutate a PR.

## Safety and Failure Boundaries

Observational skills never intentionally modify tracked source or
configuration. Repository-selected checks may update ignored caches or normal
Jujutsu operation metadata.

Observational commands must:

- use non-fixing or check modes;
- avoid commands known to rewrite source;
- recheck scope after execution; and
- report unexpected tracked changes as a blocker.

Missing, unsafe, or inherently mutating checks remain explicit coverage
limitations. Tool output is untrusted input and is normalized and redacted
before persistence.

Reviewers do not enumerate or inspect ignored paths as part of VCS-derived
scope. Supplied content is reviewed only within the explicit user request and
never becomes migration authority for excluded personal or generated state.

## MR Boundaries

| MR | Primary change | Required integration |
| --- | --- | --- |
| 1 | `resolve-change-scope` | Scope contract and Git/Jujutsu/supplied fixtures |
| 2 | `review-project-quality` | Common result contract and command evidence |
| 3 | `review-project-tests` | Theatre, consolidation, parameterization, and snapshot scenarios |
| 4 | `review-python-types` | Python applicability and checker-neutral scenarios |
| 5 | `conduct-self-review` | Align standards review, add `.reviews/`, compose and persist results |
| 6 | `address-self-review` | Consume artifacts, detect drift, edit selected findings, rerun review |

Each MR introduces only the contracts needed by its logical feature. The
existing `review-project-standards` alignment belongs in MR 5 because that is
where it first participates in the common orchestrated result. The change does
not create a seventh MR.

Implementation is strictly serial with one writer. Read-only audits may run in
parallel. Under the repository retrospective guidance, use Terra-low for
mechanical inventories and Terra-medium for bounded feature or review tasks.
Retire workers at logical boundaries.

## Verification Strategy

### Deterministic repository tests

Every MR verifies:

- catalog membership, dependency closure, and cycle safety;
- all-agent and profile eligibility;
- safe skill-tree copying and digest convergence;
- enabled native destinations;
- portability and prohibited-state policy;
- machine-readable contract examples and outcome invariants; and
- exact named composition edges.

The machine-readable block is production-consumed by
`address-self-review`, so structural parsing and invariant tests are
appropriate. Tests do not use substring assertions or opaque prose digests to
pretend that human-authored skill instructions behave correctly. Existing tree
digests remain valid evidence for installer convergence.

### Scenario fixtures

Scope fixtures cover:

- clean, modified, staged, unstaged, and untracked Git work;
- ignored-only Git work;
- Git rename and binary cases;
- Git repositories without `HEAD`;
- clean, modified, new-file, multi-parent, and binary Jujutsu changes;
- valid and invalid explicit ranges;
- supplied file-only, valid-patch, and malformed scopes; and
- resolved, empty, partial, and blocked outcomes.

Reviewer fixtures cover:

- repository-selected commands and unavailable tools;
- out-of-scope command failures;
- test theatre and repository-owned behavior;
- consolidation and parameterization decisions;
- one-line and expanded docstring decisions;
- Python and non-Python applicability;
- result aggregation and deduplication;
- safe and unsafe artifact destinations;
- missing markers, malformed JSON, and digest mismatches;
- tampered finding IDs, locations, and paths that must block before editing;
- unavailable or mismatched repository identities that must block before
  editing;
- stale scope and changed standards;
- bounded selected edits; and
- residual findings after remediation.

Fixtures prove contract examples and deterministic guards. They are not
presented as evidence that prompt prose performs semantically.

### Dogfooding

Behavioral evidence comes from bounded local invocation:

- MR 1 exercises Git, Jujutsu, and supplied scope cases.
- MRs 2 through 4 review their own relevant changes and targeted fixtures.
- MR 5 performs a complete self-review and leaves its artifact ignored.
- MR 6 addresses selected findings in an isolated or safely bounded change and
  proves the fresh result.

Native setup harnesses prove installation and name-based composition, not
semantic review quality.

### Verification commands

Each MR runs focused tests for changed files and contracts, followed by:

- the full pytest suite;
- strict mypy while it remains repository authority;
- the repository policy scan;
- pre-commit across the repository; and
- Jujutsu status and diff inspection.

Fresh command output is required before any completion or clean-result claim.
Review artifacts remain ignored and are never included in a commit.

## Stacked GitHub Delivery

### Initial stack

Before creating bookmarks:

1. fetch with Jujutsu and confirm `main@origin`;
2. create or rebase the first scope change on `main@origin`;
3. use `using-github` read-only to verify the target repository's default
   branch, allowed merge methods, required checks, branch protections, and
   merge-queue requirements; and
4. stop and revise the delivery strategy if merge commits are unavailable.

The six Jujutsu changes form one linear stack:

```text
main <- scope <- quality <- tests <- types <- self-review <- address
```

Each change receives one descriptive bookmark and GitHub PR. Initial PR bases
are:

| PR | Base |
| --- | --- |
| Scope | `main` |
| Quality | Scope bookmark |
| Tests | Quality bookmark |
| Types | Tests bookmark |
| Self-review | Types bookmark |
| Address | Self-review bookmark |

Downstream PR descriptions identify their predecessor and stack position. Only
the bottom PR is eligible to merge; later PRs remain draft or explicitly
dependency-blocked.

### Sequential merge loop

For each PR:

1. merge the current bottom PR into `main`;
2. fetch with Jujutsu and confirm the new `main@origin`;
3. inspect the next PR's base and explicitly retarget it to `main` unless
   GitHub has already done so after remote branch deletion;
4. re-read its repository, base, head, commits, changed files, checks, and
   unresolved conversations;
5. confirm the diff contains only that MR's intended slice;
6. rerun checks made stale by the base change;
7. promote the PR from draft and merge it; and
8. repeat until the stack is empty.

Do not rely on GitHub automatic retargeting. GitHub documents an automatic
downstream base update only when a merged PR's head branch is deleted. Changing
a base may also make review comments outdated:

- [Merging a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request)
- [Changing the base branch of a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-base-branch-of-a-pull-request)

After explicit retargeting and verification, delete the merged GitHub head
branch only when repository policy and user intent permit. Separately retire
the corresponding local Jujutsu bookmark only after confirming its remote state
and that no remaining PR or bookmark depends on it. Automatic GitHub
retargeting is never the control mechanism.

### Merge strategy and rewritten ancestry

Use merge commits for this repository, matching PR 9 and preserving stack
ancestry. If repository settings or an explicit decision use squash or rebase
merge, or if the retargeted diff includes predecessor content, pause the train.

For already pushed Jujutsu changes:

1. identify the first unmerged descendant and highest affected descendant
   bookmark;
2. duplicate only the inclusive range from that first unmerged descendant
   through the highest affected descendant;
3. do not duplicate the merged or replaced ancestor;
4. rebase the duplicated first unmerged descendant onto `main@origin`;
5. with explicit authorization, move each downstream bookmark to its
   corresponding duplicated revision and push it; and
6. revalidate every downstream PR before continuing.

This descendant-only procedure overrides a generic root-selection recipe that
would include an already squash- or rebase-merged ancestor.

## Follow-Ups

- Evaluate `ty` only after the review-foundation train. Run mypy and `ty`
  together, classify diagnostic and configuration differences, and change
  repository authority only after evidence is reviewed.
- Consider aligning ballen-config's active Ruff selection with the reusable
  starter's docstring rules as a separate configuration change.
- Design forge review/response and review-learning trains only after this train
  produces stable local review artifacts.

## Acceptance Criteria

The focused design is implemented when:

- all six skills work standalone where applicable and compose by name;
- composed reviewers echo one unchanged scope identity and standards inventory;
- complete, empty, partial, blocked, unavailable, skipped, and evidence-backed
  inapplicable states remain distinguishable;
- incomplete evidence cannot aggregate to clean;
- every completed self-review produces a valid ignored artifact;
- `address-self-review` rejects stale results and limits edits to selected
  findings;
- remediation produces one fresh review without recursively editing;
- focused, full, portability, and native-install verification pass;
- behavioral dogfooding evidence exists for review and remediation;
- all six PRs merge sequentially with each retargeted diff verified;
- Plato remains unchanged; and
- VCS-visible working state contains no review artifacts or unrelated changes.
