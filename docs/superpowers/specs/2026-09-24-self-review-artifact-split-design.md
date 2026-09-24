# Self-Review Artifact Split and Test Review Taxonomy Design

## Status

Approved in conversation on September 24, 2026. Addresses
[issue #33](https://github.com/blallen/ballen-config/issues/33) and adds
explicit test-theatre, TDD-residue, consolidation, and parameterization
checks to self-review.

## Context

`conduct-self-review` writes one ignored Markdown file whose first payload is a
large fenced JSON object. The trailing human summary has no required shape.
Persisted artifacts under `.reviews/self-review/` show the result: one lists
only the verdict and counts, so its six Ruff findings and four test-name
findings are readable only inside the JSON.

`review-project-tests` already describes test theatre (section 5) and
consolidation and parameterization (section 6), but it declares no named
checks, finding categories, or rules. Each run improvises them. One persisted
run recorded a single `test-quality` check, which gives no evidence that
theatre or consolidation was examined. The contract example
`self-review-result.example.md` records the same single check. Nothing in
`conduct-self-review` verifies that the tests specialist covered either
concern.

The skill also misses the two forms of test theatre that test-driven agent
work produces most:

- residue from red-green cycles that later behavioral tests subsume; and
- tests that no plausible production change can fail.

## Goals

- Persist each self-review as a human Markdown file and a sibling
  authoritative JSON file.
- Give the Markdown a fixed, verifiable shape that lists every finding
  readably.
- Let `address-self-review` accept either file of a pair and short finding-ID
  prefixes.
- Give `review-project-tests` one fixed vocabulary of checks, categories, and
  rules.
- Add explicit breaking-change and TDD-residue theatre checks.
- Make a test review that omits a required check unable to produce a clean
  aggregate verdict.

## Non-Goals

- Changing the top-level v1 JSON object, finding identity material, or hash
  rules.
- Reading, validating, or migrating existing single-file artifacts.
- Adding a deterministic renderer script or other packaged tooling.
- Running mutation-testing tools or editing tests during review.
- Adding fixed checks or rules to the other three specialists.
- Committing, publishing, or tracking review artifacts.

## Delivery Boundary

One pull request from `main` that closes issue #33. It contains this design,
the implementation plan, the skill and reference changes below, the updated
contract example and remediation vectors, and the contract test changes.

## Artifact Pair

### Filenames

Each self-review writes two files with one stem:

```text
<timestamp>-<scope-id-prefix>.json
<timestamp>-<scope-id-prefix>.md
```

The timestamp and scope-prefix rules are unchanged. Prefix uniqueness is
computed against stems already present in the selected directory. A stem is
usable only when neither file exists. On collision, capture a later timestamp
or fail safely; never invent a suffix.

### JSON file

The JSON file contains exactly the current v1 top-level object,
pretty-printed with a trailing newline. Hashes continue to use the canonical
encoding, independent of file formatting. The object keeps
`contract_version: "v1"`.

The HTML marker line and the Markdown fence are removed. `contract_version`
and the exact top-level key set identify a self-review result. The artifact
contract reference is updated in place rather than versioned, because
existing artifacts are ignored local evidence with no compatibility
requirement.

### Markdown file

The Markdown is rendered by the agent from the final JSON using this fixed
template:

```markdown
# Self-review: <verdict>

- Findings: <b> blocker, <a> actionable, <v> advisory
- Scope: <status>, <source>, <n> changed paths, scope `<scope-id-prefix>`
- Result: `<result-id-prefix>` ([machine result](<stem>.json))

## Limitations

- `<reviewer>` (<outcome>)
- `<check>` (<effect>): <reason>
- `<code>` (diagnostic): <detail>

## Blockers

- `<finding-id-prefix>` `<location>` · <category>/`<rule>` · <contributors>
  - Evidence: <evidence>
  - Remediation: <remediation>

## Actionable

## Advisories

## Coverage

| Reviewer | Applicability | Outcome | Checks |
| --- | --- | --- | --- |
| <reviewer> | <applicability> | <outcome> | <check>: <completion>, ... |
```

Rendering rules:

- Evidence, remediation, reasons, and details are copied verbatim from the
  JSON.
- Severity sections appear in blocker, actionable, advisory order; empty
  severity sections are omitted. Findings keep JSON order within a section.
- `<location>` is `<path>:<line>` for one line, `<path>:<start>-<end>` for a
  range, `<path>` without a location, and `repository` without a path.
- A null rule renders the category alone; a null remediation omits the
  Remediation line. Contributors are joined with `, ` in JSON order.
- Limitations lists reviewers whose outcome is not completed, then every
  aggregate skip, then every aggregate diagnostic, in JSON order. A
  blocked-scope skip record appends `: <reason>`; a diagnostic with a path
  renders as `` `<code>` (diagnostic, `<path>`): <detail> ``. When nothing
  qualifies, the section body is `None.`
- Coverage has one row per reviewer or blocked-scope skip record, in reviewer
  order. A skip record renders `skipped` as its outcome and `-` for
  applicability and checks.
- Scope-identity and result-ID prefixes are 12 lowercase hexadecimal
  characters. Every finding prefix in one artifact has the same length: 12, or
  the shortest longer length that makes every prefix unique.

The Markdown may not add, override, or reinterpret machine fields.

The contract reference records the upgrade path next to the template: the
Markdown is agent-rendered; if read-back verification keeps catching drift, or
rendered pairs are found inconsistent with their JSON, replace agent rendering
with a deterministic renderer script.

### Persistence and verification

Write the JSON file first, then the Markdown file, each with exclusive-create
semantics. If either write or any verification step fails, self-review did
not complete and cannot claim the computed verdict. A partial pair is left in
place and never overwritten.

Post-write verification keeps every existing JSON check and adds:

- both files exist, remain ignored, and are untracked;
- the Markdown verdict, counts, and result-ID prefix match the JSON;
- the set of finding prefixes in the Markdown equals the set of JSON finding
  IDs, with each finding appearing exactly once under its severity section;
- each finding bullet's path, lines, category, and rule match its JSON
  finding; and
- every aggregate skip and diagnostic appears under Limitations.

The inline response links the Markdown file.

## Address Self-Review

### Artifact path

`artifact_path` names either file of a pair. Derive the stem and require both
`<stem>.json` and `<stem>.md` to exist as regular files inside the repository.
Requiring the pair keeps a self-review that failed mid-persistence from
becoming remediation input. Read and validate only the JSON; never parse the
Markdown.

A wrong extension, missing sibling, directory, glob, or escaping symlink
blocks with `artifact_path_invalid`.

### Integrity gates

Remove the marker gate and the `artifact_marker_missing` diagnostic code. The
first content gate becomes a parseable JSON object, blocking with
`artifact_json_malformed`. Contract, structure, result-ID, digest, and
finding-ID gates are unchanged.

### Selection

Each `finding_ids` entry is a full finding ID or a prefix of at least 12
lowercase hexadecimal characters. An entry must match exactly one aggregate
finding in the artifact. No match, multiple matches, a shorter prefix, or two
entries that resolve to the same finding block with
`selected_finding_unknown`. Resolved entries are normalized to full IDs and
sorted; every later gate is unchanged. The bounded selector is unchanged.

### Reporting

Status groups report the same finding prefixes the Markdown renders. The
response links the old and new Markdown files alongside their result IDs.

### Remediation vectors

In `remediation-vectors.json`:

- remove the baseline `artifact_marker` and the `missing_marker` vector;
- add a missing-sibling vector that blocks with `artifact_path_invalid`;
- add a short-prefix vector that blocks with `selected_finding_unknown`; and
- add a valid 12-character prefix vector that resolves the selected finding.

## Test Review Taxonomy

### Checks and categories

`review-project-tests` declares eight required checks. Each check name is also
the finding category for findings it produces.

| Check and category | Covers |
| --- | --- |
| `behavioral-coverage` | Changed behavior without a meaningful test, removed sole protection, defect fix without a reproducer |
| `assertions` | Weak, existence-only, or status-only assertions; implementation-step assertions; exception-message contracts |
| `fixtures-doubles` | Fixture ownership and visibility, shared mutable state, patch site, sync and async doubles, mocked subject, overbuilt fakes |
| `execution-policy` | Default-suite determinism and speed, opt-in expensive checks, strict xfail, explainable skips, heavy optional imports, typed signatures, plain functions |
| `theatre` | Tests that cannot fail for a meaningful owned regression |
| `consolidation` | Near-duplicates, input matrices, case identifiers, over-merged scenarios |
| `generated-output` | Snapshots and generated-output contracts |
| `test-documentation` | Behavioral meaning of test names and docstrings |

When the specialist is applicable, every check appears in coverage. A missing
or non-completed required check makes the specialist result `incomplete`.
An evidence-backed `not_applicable` result requires no checks. Test command
evidence remains governed by the existing command rules.

### Rules

Every `review-project-tests` finding uses one fixed rule from its category.
This table replaces the current "recommended categories" sentence in section
9:

| Category | Rules |
| --- | --- |
| `behavioral-coverage` | `coverage-gap`, `protection-removed`, `missing-reproducer` |
| `assertions` | `weak-assertion`, `implementation-coupled`, `exception-contract` |
| `fixtures-doubles` | `hidden-fixture`, `shared-mutable-state`, `wrong-patch-target`, `async-mismatch`, `mocked-subject`, `overbuilt-double` |
| `execution-policy` | `nondeterministic-default`, `expensive-not-opt-in`, `non-strict-xfail`, `unexplained-skip`, `heavy-import`, `untyped-test`, `unneeded-test-class` |
| `theatre` | `test-cannot-fail`, `tdd-residue`, `expectation-rewritten`, `mock-manufactured`, `framework-guarantee`, `configuration-reasserted`, `prose-pinned` |
| `consolidation` | `consolidate-duplicate`, `parameterize-matrix`, `missing-case-ids`, `over-consolidated` |
| `generated-output` | `unreviewed-snapshot`, `volatile-snapshot`, `oversized-snapshot`, `brittle-prose` |
| `test-documentation` | `test-name-meaning`, `docstring-meaning` |

Every category also allows `unlisted`, whose evidence must name the pattern.
Recurring `unlisted` findings signal that the rule table should grow.

Fixed rules make the bounded selector usable and let a fresh review match a
still-present finding by path and rule. Finding IDs cannot do that across runs
because evidence prose is part of their identity material.

### Breaking-change probe

For every added or changed test, name the smallest plausible repository-owned
production change that would make it fail, such as removing a guard, flipping
a branch, or returning a stub value. When none exists, report a `theatre`
finding whose evidence explains why no owned change fails the test.

The probe is reasoning only. Do not run mutation tools, undeclared commands,
or edits.

### TDD residue

Report `tdd-residue` for tests left behind by red-green steps:

- existence, import, callable, signature, or return-type tests; and
- tests pinned to a stub or intermediate value.

A test is residue when every owned change that fails it also fails a retained
test. Recommend deleting it or folding its case into the behavioral test.
Incremental tests that differ only in inputs are `parameterize-matrix`
findings instead.

### Expectation rewrites

Report `expectation-rewritten` when a changed test's expected value was edited
to match new output and the change does not intend that behavior change.

### Precedence

When the breaking-change probe finds no failing owned change, the finding is
`theatre` even when the cause is a mock or weak assertion; do not report it
again under `assertions` or `fixtures-doubles`. Within `theatre`, use the
specific cause rule when one applies and `test-cannot-fail` otherwise.
Tautological assertions and tests that execute code without asserting use
`test-cannot-fail`.

`over-consolidated` reports a merged or parameterized test that hides distinct
failure stories, recovery paths, or diagnostic obligations that section 6
says to keep separate.

## Conduct Self-Review Enforcement

When `review-project-tests` is applicable, `conduct-self-review` verifies that
its coverage contains every required check declared by that skill. It
references the declaration rather than copying the list.

A missing required check produces an aggregate diagnostic with code
`reviewer_check_missing`, path `null`, a detail naming the specialist and the
missing check, and contributor `conduct-self-review`. The aggregate verdict is
then at least `incomplete`.

## Testing Standard

Add to "Avoid test theatre" in `assistants/shared/standards/testing.md`:

- every retained test has a plausible owned change that makes it fail; and
- stepping-stone tests from red-green cycles are deleted or folded once
  behavioral tests subsume them.

## Contract Example

Replace `self-review-result.example.md` with the pair
`self-review-result.example.json` and `self-review-result.example.md`. The
example's `review-project-tests` coverage lists all eight required checks, and
its hashes are recomputed. The Markdown follows the template.

The example also gains the cases a reader most needs to see rendered: a
`theatre`/`tdd-residue` finding with a line range, a pathless repository-wide
advisory, and an optional skip with effect `none` that still appears under
Limitations.

## Verification

`tests/assistants/test_review_contracts.py`:

- loads the example pair instead of the marker and fence;
- keeps every existing JSON integrity and deduplication assertion;
- validates the example Markdown line-for-line against the template rendered
  from its JSON, which covers verdict, counts, result-ID prefix, limitations,
  the one-to-one mapping of finding prefixes to severity sections, and
  coverage; and
- runs the updated remediation vectors.

Skill prose, rule tables, and check names are not pinned by tests, following
the testing standard. Run the full test suite, Ruff, and the configured
pre-commit hooks, then `./bootstrap doctor`.

## Success Criteria

- A self-review produces a Markdown file whose findings a person can read and
  act on without opening the JSON.
- `address-self-review` accepts either file of the pair and 12-character
  finding prefixes, and never reads the Markdown.
- Every applicable test review reports all eight checks with fixed categories
  and rules.
- A test review that omits a required check cannot yield a clean aggregate
  verdict.
- Breaking-change and TDD-residue theatre findings are explicit, selectable
  rules.
