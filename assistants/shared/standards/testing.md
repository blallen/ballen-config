# Testing

## Test levels and scope

Use test levels according to the boundary being exercised:

- Unit tests isolate one unit of behavior and replace external dependencies.
- Integration tests exercise collaboration among real internal components while
  controlling external systems.
- Functional or end-to-end tests verify user-visible workflows with the
  smallest practical amount of nondeterminism.

Keep the default suite deterministic and fast enough for its intended feedback
loop. Expensive, networked, or nondeterministic tests must be explicit opt-in
checks with a clear purpose.

## Regression-first changes

For a defect, use a regression-first sequence: reproduce the failure with a
focused test, implement the smallest sufficient fix, then run broader checks
proportional to the risk. A defect fix without a meaningful reproducer needs a
documented reason.

Use pytest fixtures for reusable setup, teardown, and domain examples. Prefer
small fixtures with visible ownership over global mutable state or fixture
graphs whose behavior is difficult to follow.

Put reusable test-data factories in shared fixtures or helpers without
prescribing a repository layout. Test deterministic control flow separately
from model or service behavior so failures identify the boundary at fault.
Unit tests for core behavior must not import unused heavy optional dependencies.

## Doubles and patching

Patch at the use site so the test replaces the name the code actually resolves.
Use async-aware mocks for awaitable callables and synchronous doubles for
synchronous callables. Model only the behavior the test needs; a double that
reimplements the dependency creates another system to debug.

Do not mock the subject under test. At integration boundaries, prefer a small
contract fake when it provides more realistic behavior than a collection of
unrelated mocks.

## Assertions and expected failures

Write behavioral assertions about observable outcomes and important side
effects. Avoid assertions that merely repeat implementation steps.

Match the exception message when it is part of the diagnostic contract, while
allowing irrelevant wording to evolve. Use strict expected failures: identify
the known reason, fail when the test unexpectedly passes, and remove the marker
when the defect is fixed. Skips require a condition the suite can explain.

## Snapshots and generated output

Use reviewed snapshots when a rich structured output is easier to understand as
a whole than as many fragmented assertions. Keep snapshots deterministic,
small, and human-reviewable; normalize unstable values before recording them.
Snapshot approval is code review, not a mechanical update.

For generated output, assert stable structural properties and representative
content rather than brittle exact prose. Opt-in evaluation may cover quality
that deterministic assertions cannot.

## Avoid test theatre

Reject test theatre: do not re-test framework guarantees, assert configuration
that existing behavior tests already cover, or create mocks whose assertions
can pass without exercising production control flow. Every test should be able
to fail for a meaningful regression in code the repository owns.
