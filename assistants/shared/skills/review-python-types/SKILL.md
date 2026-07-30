---
name: review-python-types
description: >-
  Use when a resolved change contains Python and type contracts, structured
  mappings, validated models, callers, or serialization boundaries may have
  changed.
---

# Review Python Types

## Overview

**Core principle:** Treat types as executable contracts across producers,
callers, validation, and serialization, and use only repository-selected
checker evidence.

Review the fixed Python change without refactoring it. Return evidence-located
findings in the common result contract, including unavailable or incomplete
checker evidence exactly as observed.

Use `resolve-change-scope` and `discover-project-standards` by name when valid
inputs were not supplied. Read the canonical scope and result contracts
packaged with `resolve-change-scope`. Sibling paths are packaging hints only;
invoke dependencies by canonical name.

## When to Use

Use this skill when a resolved or resolvable change contains Python and may
affect:

- annotations, aliases, protocols, or public call contracts;
- controlled mapping shapes;
- dataclasses, validated models, or trust boundaries;
- downstream callers, implementations, or tests;
- validation, serialization, or consumer-facing representations; or
- repository-selected Python type-check evidence.

Do not use it for a complete non-Python-only scope, general lint or formatting,
test-design review, code refactoring, suppressions, checker migration, or an
aggregate multi-reviewer verdict.

## Inputs

Accept:

- one v1 `ChangeScope`, including its live in-memory reviewable diff;
- one discovered standards and tool inventory with a stable identity; and
- optional complete type-check evidence for the identical scope.

Reuse supplied inputs only when their versions, identities, repository
identity, path inventory, and digests validate. Otherwise invoke the named
dependencies once. Never silently replace a supplied scope or use a different
comparison to obtain cleaner checker output.

A checker name, conversational summary, or pasted diagnostic without matching
provenance, invocation identity, scope identity, and output digest is not
reusable command evidence. Preserve its limitation; never fill missing fields
with plausible values.

If scope is blocked, return a blocked result without inspecting or checking
code. Partial scope permits bounded analysis only and forces an incomplete
outcome.

## Workflow

### 1. Establish Python applicability

This specialist is applicable only when the selected change contains Python
source, tests, stubs, or Python configuration whose type contracts may change.
Inspect the complete path and content-kind inventory rather than inferring from
the request.

Return `not_applicable` only when complete scope evidence proves there is no
Python change. Do not run a checker for a non-Python-only scope. Use `unknown`
when partial or unavailable scope cannot establish applicability.

Record the exact `scope_identity` and `standards_inventory_ref` before
analysis.

### 2. Inventory changed contracts

For each changed Python path, identify affected:

- function and method parameters, returns, yields, and raised-error contracts;
- class, protocol, abstract, and callback interfaces;
- aliases, unions, literals, enums, generics, and optional values;
- controlled mappings and named return shapes;
- dataclasses, ordinary classes, and validated models;
- parsing, validation, normalization, and serialization boundaries; and
- direct and downstream callers, implementations, and tests.

Trace the contract far enough in both directions to understand what produces
the value, what consumes it, and what representation crosses a boundary.
Changed annotations alone do not establish compatibility.

### 3. Review annotations and public contracts

Assess annotations against repository instructions and executable
configuration. Prefer precise types over broad `Any` when the shape is known,
but do not demand annotations the repository does not require.

Check that:

- optionality distinguishes omission, explicit null, and an actual value;
- return contracts match every reachable path;
- callback, async, iterator, and context-manager contracts match use;
- overrides and protocol implementations remain substitutable;
- aliases and named return types communicate stable meaning; and
- public contract changes are reflected in callers and tests.

Do not prescribe a mechanical syntax rewrite or a repository-wide annotation
policy. Report the concrete mismatch and its consumer impact.

### 4. Review controlled mapping shapes

Find free-form mappings whose keys and value types are actually controlled.
Use the repository's standards to decide whether the contract should remain a
mapping, use `TypedDict`, or cross a validated-model boundary.

For a trusted internal mapping, review:

- required versus omittable keys;
- omitted keys versus present nullable values;
- nested and repeated value shapes;
- read-only versus mutable use;
- stable key spelling across producers and consumers; and
- whether a named mapping improves the public contract.

`NotRequired` describes omission; `T | None` describes a present nullable
value. Do not replace every dictionary with a validated model, and do not
leave a public `dict[str, Any]` unexamined when its shape is controlled.

### 5. Review class and model boundaries

Choose the boundary mechanism according to trust and lifecycle:

- `TypedDict`, a dataclass, or an ordinary class can represent trusted
  in-memory data without repeated runtime validation;
- a validated Pydantic model is appropriate when external, serialized, or
  otherwise untrusted data crosses a boundary; and
- a transport representation and a domain object may need separate types when
  they evolve for different reasons.

Apply repository-selected Pydantic and validation standards rather than
inventing model configuration. Review field constraints, cross-field
invariants, validator phase and determinism, secret redaction, redundant
derived state, and separation of validation from business workflows.

Do not infer safety from successful model construction alone. Verify what
trusted typed representation moves inward after parsing and validation.

### 6. Inspect callers, tests, and serialization

Inspect direct callers and the smallest relevant downstream chain. Check
construction, mutation, forwarding, narrowing, error handling, and
serialization at the actual use sites.

Review tests for repository-owned contracts such as:

- validators and normalization;
- omission versus null behavior;
- serialization modes, aliases, exclusions, and redaction;
- consumer-facing wire or stored representations;
- custom model methods and derived values; and
- caller behavior after validation or type-contract changes.

Do not require tests that merely prove a framework populates declared fields.
Delegate general test-design findings to `review-project-tests`.

Keep serialization with the domain type that owns it when repository standards
require that boundary. Verify the representation consumers actually receive;
an internal model type and a serialized output are not interchangeable.

### 7. Discover the repository-selected checker

Use the supplied standards inventory and inspect only repository-owned
configuration needed to resolve the selected Python type checker and its exact
safe invocation. Sources may include project configuration, checked-in scripts,
task runners, lockfiles, contributor guidance, and CI.

This specialist solely owns Python type-check execution and type-check
findings. Other reviewers may inventory the tool but must not rerun it.

Do not substitute a globally available checker for the repository-selected
checker. Do not invent flags, scoped forms, plugins, configuration, or generic
defaults. Do not guess a configuration path or standards source. If exact
repository-relative checker provenance cannot be established, mark the
required input or check unavailable and emit no fabricated command record.
When the repository selects no checker, record that discovery and complete the
static contract review without fabricating command evidence.

### 8. Execute once and classify evidence

Run the exact repository-selected command only when it is safe and available.
Prefer a declared scoped form when one exists; otherwise use the declared full
form unchanged. Do not install the checker or dependencies, invoke behavior
that may download them, add suppressions, or edit configuration.

Classify command evidence precisely:

- a nonzero exit with complete type diagnostics is completed;
- a missing executable or required unreadable input is unavailable;
- a timeout, truncation, or abort is incomplete; and
- an unsafe command is skipped with its actual coverage effect.

Record concise redacted evidence, not raw output. Type errors on changed paths
are eligible findings. An error in an unchanged caller is also eligible when
evidence shows the selected contract change caused it. Keep unrelated
full-project errors in command evidence rather than attributing them to the
change.

Reuse supplied checker evidence only when its invocation identity, scope
identity, provenance, completion, and output digest match exactly. Record the
selected checker and its evidence once; never run a second checker for
comparison or convenience.

A requester-reported checker result may guide bounded static inspection, but
it cannot satisfy command coverage until those identities validate.

### 9. Revalidate scope

After a checker command that may refresh repository metadata or ordinary
Jujutsu snapshot state, invoke `resolve-change-scope` again with the same
request. Require the same scope identity, comparison identities, path
inventory, and diff digest.

If revalidation differs, discard any clean conclusion and return blocked with
integrity evidence. Never attach one checker's diagnostics to a different
scope.

### 10. Normalize the common result

Return exactly one v1 review-result envelope for `review-python-types`. Use
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
checks, and no blocked work. A missing repository-selected checker cannot
produce clean command coverage. A complete non-Python scope may produce a
clean, evidence-backed not-applicable specialist result without running a
checker.

## Output

Return one common v1 review-result envelope with the supplied scope and
standards identities, applicability, outcome, owned coverage, normalized
findings, explicit skips, sanitized command evidence, counts, and specialist
verdict.

Every finding includes a tight repository-relative location, concrete contract
or checker evidence, consumer impact, and a bounded recommendation. Never
return only free-form advice, a checker transcript, or a binary approval.

## Quick Reference

| Situation | Required handling |
| --- | --- |
| Complete scope has no Python changes | Return evidence-backed not applicable; run no checker |
| Controlled trusted mapping crosses a contract | Review `TypedDict`, required keys, and nullability |
| Untrusted or serialized input crosses a boundary | Review the validated model and inward typed representation |
| Model is serialized | Inspect aliases, modes, exclusions, redaction, and actual consumers |
| Repository checker is selected and available | Run its exact safe invocation once |
| Different checker is globally available | Do not substitute it |
| Selected checker is missing | Install nothing; return unavailable checker evidence |
| Checker reports diagnostics with nonzero exit | Mark the command completed and classify attributable findings |
| Full check has unrelated failures | Preserve them as command evidence, not change findings |
| Scope identity changes after checking | Block and discard the prior conclusion |

## Boundaries

This skill is report-only. Never refactor code, edit annotations or models, add
suppressions, change checker configuration, migrate checkers, install tools,
invent commands or flags, widen scope, or retain raw output, absolute paths,
credentials, sessions, trust state, or generated plugin state.

## Common Mistakes

- Treating a Markdown-only change as Python-applicable. Prove
  non-applicability from complete scope and run no checker.
- Substituting an installed checker for the repository-selected one. Report the
  selected checker as unavailable instead.
- Adding `type: ignore`, casts, or configuration exclusions to silence
  evidence. Report the contract problem without mutating it.
- Reviewing a changed annotation without its callers, tests, validation, and
  serialized consumers.
- Leaving a controlled public mapping as unexplained `dict[str, Any]`, or
  turning every trusted internal object into a validation model.
- Testing Pydantic field population instead of repository-owned validation,
  serialization, or consumer behavior.
- Calling a diagnostic-producing nonzero exit unavailable. It completed when
  its output is trustworthy.
- Running both the selected checker and a convenient alternative. This skill
  owns one repository-selected execution.
- Inventing a CI path, invocation identity, or digest for a reported checker
  result. Missing command provenance remains unavailable evidence.
- Returning prose advice without scope identity, checker coverage, findings,
  and limitations.

## Related Skills

- `resolve-change-scope` owns immutable comparison and drift detection.
- `discover-project-standards` owns standards and checker discovery.
- `review-project-quality` may inventory type tooling but delegates execution
  and findings here.
- `review-project-tests` owns test design and behavioral coverage.
- `review-project-standards` owns human-authored Python standards.
- `conduct-self-review` composes specialist results and computes the aggregate
  verdict.
