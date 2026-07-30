---
name: review-project-tests
description: >-
  Use when a resolved change adds, removes, or relies on tests and behavioral
  coverage, theatre, mocks, snapshots, duplication, or test documentation may
  affect confidence.
---

# Review Project Tests

## Overview

**Core principle:** Every test must be able to fail for a meaningful regression
in behavior the repository owns.

Review the fixed change scope and its relevant tests as one behavioral system.
Return evidence-located findings in the common result contract; do not reduce
the review to line coverage or a conversational approval.

Use `resolve-change-scope` and `discover-project-standards` by name when valid
inputs were not supplied. Read the canonical scope and result contracts
packaged with `resolve-change-scope`. Sibling paths are packaging hints only;
invoke dependencies by canonical name.

## When to Use

Use this skill when a resolved or resolvable change:

- adds, changes, removes, or reorganizes tests;
- changes repository-owned behavior that should have regression coverage;
- changes fixtures, doubles, snapshots, or generated-output contracts; or
- needs focused review for theatre, duplication, parameterization, or test
  documentation.

Do not use it to run or interpret Python type checking, report mechanical lint
or Ruff docstring violations, decide general API documentation style, edit
tests, update snapshots, remediate findings, or compute an aggregate
multi-reviewer verdict.

## Inputs

Accept:

- one v1 `ChangeScope`, including its live in-memory reviewable diff;
- one discovered standards and tool inventory with a stable identity; and
- optional complete test or coverage evidence for the identical scope.

Reuse supplied inputs only when their versions, identities, repository
identity, path inventory, and digests validate. Otherwise invoke the named
dependencies once. Never replace a supplied scope silently or rediscover a
more convenient comparison.

If scope is blocked, return a blocked result without reviewing files. Partial
scope permits only bounded analysis with an incomplete outcome. Empty complete
scope is valid and normally makes this specialist not applicable.

## Workflow

### 1. Establish applicability

Test review is applicable when the selected change contains tests, test
support, or repository-owned behavior whose coverage may have changed. A
source-only change can therefore be applicable when relevant tests are absent.
A test-only change remains applicable even when production code is unchanged.

Prove `not_applicable` from complete scope and standards evidence, such as a
documentation-only change with no executable behavior or tests. Use `unknown`
when partial inputs cannot establish applicability. Record the exact
`scope_identity` and `standards_inventory_ref` before analysis.

### 2. Inventory changed behavior

Describe repository-owned behavior added, changed, removed, or relied upon by
the selected change. Include observable:

- success paths and important side effects;
- error, cancellation, and recovery behavior;
- branches, boundaries, and input classes;
- serialization or generated-output contracts;
- asynchronous collaboration; and
- regressions named by the change or its existing tests.

Do not infer behavior solely from filenames, mirrored directory layouts, test
names, or coverage percentages. For a test-only scope, identify the behavior
each changed test claims to protect and record any source-inspection
limitation.

### 3. Map behavior to relevant tests

Map each changed behavior to the smallest relevant unit, integration, or
end-to-end evidence. Inspect changed tests and unchanged nearby tests when
needed to determine whether coverage already exists, overlaps, or regresses.

Record a coverage gap when material changed behavior has no meaningful test or
when deleted tests remove its only protection. Do not require one test file per
source file or assume a repository layout that its standards do not declare.
Line execution without a behavioral assertion does not close a gap.

Reuse supplied test or coverage command evidence only when its scope identity,
provenance, completion, and digest match exactly. A green suite supports
execution evidence; it does not prove test value. If command evidence is
absent, record that limitation rather than inventing or running an undeclared
command.

### 4. Review assertions, fixtures, and doubles

For every relevant test, identify the observable outcome or important side
effect that would change under a real regression. Prefer direct behavioral
assertions over assertions that repeat implementation steps.

Review fixture ownership and visibility. Flag global mutable setup or fixture
graphs that hide the behavior under test when they materially reduce
confidence.

Review changed test execution policy when it is present or implicated:

- the default suite remains deterministic and fast for its feedback loop;
- expensive, networked, or nondeterministic checks are explicit opt-in;
- expected failures are strict, have a current reason, and fail on an
  unexpected pass;
- skips have a condition the suite can explain;
- core unit tests do not import unused heavy optional dependencies;
- test signatures remain typed; and
- plain test functions are preferred unless class-owned setup makes a class
  clearer.

For doubles and patches, verify:

- the patch replaces the name resolved at the use site;
- awaitable collaborators use async-aware doubles;
- synchronous collaborators use synchronous doubles;
- the subject under test is not mocked;
- a fake or mock models only the boundary behavior the test needs; and
- production control flow still determines the observed result.

Passing assertions manufactured entirely by mocks are not regression
evidence.

### 5. Detect test theatre

Report a theatre finding when a test cannot fail for a meaningful regression
in repository-owned behavior. Theatre includes tests that:

- execute code without a meaningful assertion;
- reproduce a framework or dependency guarantee, such as bare Pydantic
  `BaseModel` population of declared attributes;
- reassert configuration already covered by behavior tests;
- use tautological, weak existence-only, or status-only assertions;
- over-mock inputs, control flow, and outcomes until production behavior is
  disconnected;
- approve a snapshot mechanically without a reviewed contract; or
- pin human-authored documentation, instructions, or prompt prose with
  substrings or opaque digests that production does not consume.

Do not misclassify repository-owned Pydantic validators, transformations,
serialization, custom methods, or consumer-facing representations as
dependency guarantees. Name the exact owned behavior a useful replacement
test would protect.

### 6. Review consolidation and parameterization

Consolidate near-duplicate tests when setup, exercised behavior, and asserted
contract are materially the same. Recommend parameterization when the same
behavior repeats across an input or outcome matrix; explicit case identifiers
must make failures understandable.

Keep tests separate when they communicate different failure stories, recovery
paths, side effects, user-visible contracts, or diagnostic obligations.
Similar syntax is not sufficient reason to merge them. Do not optimize for the
fewest test functions at the expense of behavioral clarity.

Distinguish:

- duplicate implementation that should be consolidated;
- repeated data that should be parameterized; and
- distinct scenarios that should remain separate.

### 7. Review snapshots and generated output

A useful snapshot protects deterministic, small, human-reviewable structured
output whose whole is clearer than fragmented assertions. Verify that volatile
values are normalized and that the changed snapshot expresses an intentional
repository-owned contract.

For generated output, prefer stable structure and representative content over
brittle exact prose. A snapshot or digest is not a substitute for judging
human-authored text. Never update or approve a snapshot merely to make the
review green.

### 8. Review test names and docstrings

Read each test name and docstring together. They should state the meaningful
repository-owned behavior or regression story, not merely restate the function
name, setup, framework action, or assertion.

A concise one-line behavioral docstring can fully communicate a straightforward
test. Expanded explanation is useful when it clarifies non-obvious
preconditions, parameters, side effects, invariants, or the reason separate
failure stories exist. More words are not automatically better.

This specialist judges behavioral meaning only. Delegate required presence,
one-line versus expanded Google-style appropriateness, and general API
documentation rules to `review-project-standards`. Delegate configured Ruff
docstring diagnostics to `review-project-quality`.

### 9. Record coverage and limitations

For each owned check, record complete, incomplete, unavailable, or skipped
coverage. Preserve limitations such as partial diff content, unavailable
source, missing command evidence, nondeterministic opt-in tests, or an
unreviewable generated artifact.

Use tight repository-relative locations and concise evidence. Recommended
categories include behavioral coverage, assertion, theatre, double,
snapshot, duplication, parameterization, and test documentation. Use blocker
only when the review boundary or evidence is untrustworthy, actionable for
material corrections, and advisory for optional clarity or maintainability.

### 10. Normalize the common result

Return exactly one v1 review-result envelope for `review-project-tests`. Use
stable finding IDs from the shared contract and preserve canonical ordering.

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
checks, and no blocked work. High coverage or a green suite cannot override
theatre, disconnected mocks, missing behavior, or incomplete review evidence.

## Output

Return one common v1 review-result envelope with the supplied scope and
standards identities, applicability, outcome, owned coverage, normalized
findings, explicit skips, sanitized command evidence, counts, and specialist
verdict. Each finding includes a tight location, concrete evidence, and a
bounded recommendation.

Never return only a prose review, coverage percentage, or binary
approve/request-changes decision. The caller or `conduct-self-review` owns
aggregation.

## Quick Reference

| Situation | Required handling |
| --- | --- |
| Green suite or high line coverage | Treat as execution evidence, then inspect behavioral value |
| Pydantic field-population assertion | Theatre unless repository-owned behavior is also proved |
| Same behavior with different inputs | Parameterize with explicit case identifiers |
| Same setup but different failure stories | Keep separate when the contracts differ |
| Async path uses synchronous or excessive mocks | Report the double or disconnected-control-flow gap |
| Snapshot changed | Verify deterministic owned intent; never update it |
| Straightforward meaningful test docstring | Accept the concise behavioral statement |
| Mechanical docstring or style violation | Delegate to quality or standards review |
| Changed xfail or skip | Require strict failure behavior or an explainable condition |
| Slow, networked, or nondeterministic test | Require an explicit opt-in boundary |
| Missing source or partial diff | Record the limitation and prevent clean |

## Boundaries

This skill is report-only. Never edit production code or tests, consolidate or
parameterize cases automatically, update snapshots, add coverage exclusions,
install tools, invent commands, widen scope, or retain raw diffs, raw command
output, absolute paths, credentials, sessions, trust state, or generated plugin
state.

## Common Mistakes

- Equating line coverage with behavioral confidence. Coverage does not show
  that assertions protect owned behavior.
- Calling every short test theatre. A small test is valuable when it can fail
  for a meaningful regression.
- Retesting Pydantic field assignment. Test repository validators,
  transformations, serialization, or consumer contracts instead.
- Consolidating distinct failure stories because their setup looks similar.
  Preserve materially different contracts.
- Leaving equivalent literal variants as copied tests. Parameterize the
  behavior matrix and name its cases.
- Accepting a mock-controlled outcome. Ensure production control flow reaches
  an observable boundary.
- Treating every snapshot as brittle or every snapshot update as valid. Judge
  deterministic repository-owned intent.
- Ignoring permissive xfails, unexplained skips, or nondeterminism in the
  default suite. These can hide regressions even when assertions are sound.
- Reporting docstring style from this specialist. Judge behavioral meaning and
  respect quality and standards ownership.
- Returning an informal approval without scope identity, coverage, findings,
  and limitations.

## Related Skills

- `resolve-change-scope` owns immutable comparison and drift detection.
- `discover-project-standards` owns standards and test-tool discovery.
- `review-project-quality` owns configured quality checks and Ruff findings.
- `review-project-standards` owns documentation presence and style
  appropriateness.
- `review-python-types` owns Python type-check execution and findings.
- `conduct-self-review` composes specialist results and computes the aggregate
  verdict.
