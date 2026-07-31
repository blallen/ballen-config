# Tools and Capabilities

Tools present operations to a model. Capabilities define which operations and
resources an Agent can reach. Keeping those concepts separate makes behavior
reusable while keeping authority explicit. Prefer thin tool wrappers over
embedding reusable business logic in model-facing functions.

## Thin tool wrappers

A tool exposes a precise name, typed arguments, a complete behavioral
description, and a structured result. Reusable domain behavior belongs in a
service or pure function below the tool wrapper.

### Keep tools narrow

Requirement: A tool SHOULD expose one coherent operation and delegate reusable
business logic to a lower layer.

Rationale: Narrow tools are easier for a model to select, easier to authorize,
and easier to test independently of model behavior.

Scope: Model-callable functions and specialist-agent tools.

Exceptions: Closely related read-only operations can share a tool when one
typed operation and result remain clearer than several near-duplicates.

### Document observable behavior

Requirement: A tool description MUST state purpose, argument meaning, result
shape, relevant side effects, and expected non-completion outcomes.

Rationale: The model selects a tool from its visible contract, not from hidden
implementation details.

Scope: Every model-callable tool.

Exceptions: None. Generated descriptions are acceptable when the generated
contract contains the same information.

## Capability grants

A capability is a named, reviewable grant of behavior or access. It can mount
one tool, a toolset, a scoped resource, or reusable orchestration behavior. The
same implementation can be granted to one role and withheld from another.

### Grant explicitly

Requirement: An Agent MUST receive capabilities explicitly during construction
or run setup.

Rationale: Ambient registration makes the effective permission set difficult
to audit and can expose unrelated side effects.

Scope: Tools, filesystems, delegated workers, network access, messaging, and
other effect-bearing resources.

Exceptions: Process-wide pure utilities with no external effects or mutable
state need not be modeled as capabilities.

## Effect classes

Classify tools by their externally observable effect:

| Effect | Meaning | Typical control |
| --- | --- | --- |
| Read | Observes data without changing it | Scope and data-access review |
| Write | Mutates a repository, store, or local artifact | Idempotency and validation |
| External message | Communicates with another person or system | Preview or explicit authorization |
| Destructive | Deletes, overwrites, revokes, or makes recovery difficult | Narrow target and confirmation |

One tool can have more than one effect. Classify it by every effect callers must
reason about, not by its most convenient label.

### Declare consequential effects

Requirement: Tools with Write, External message, or Destructive effects MUST
declare those effects in their contract and capability grant.

Rationale: Consequential operations require different approval, retry, and
audit policy from observation-only tools.

Scope: Any tool that changes durable or externally visible state.

Exceptions: None. A hidden side effect is still a side effect.

## Idempotency and retry safety

Idempotency means replaying the same operation with the same identity does not
create additional unintended effects. A non-idempotent tool should expose an
operation key, precondition, or explicit reconciliation path.

### Define replay behavior

Requirement: An effect-bearing tool MUST document whether retry is safe and how
duplicate execution is detected or reconciled.

Rationale: Agent and orchestration runtimes can retry after timeouts where the
original outcome is unknown.

Scope: Writes, messages, destructive operations, and externally billed actions.

Exceptions: A tool can prohibit automatic retry when it returns a distinct
unknown-outcome result for caller-directed recovery.

## Timeout and cancellation

A timeout bounds waiting; cancellation requests that work stop. These are
different outcomes. Long-running tools should propagate cancellation to their
dependencies when safe and describe what state can remain afterward.

### Bound tool execution

Requirement: Tools that can block on external work SHOULD define Timeout and
Cancellation behavior, including the state visible after interruption.

Rationale: Callers cannot coordinate cost, recovery, or shutdown without an
execution bound and a clear interrupted state.

Scope: Network calls, jobs, model calls, delegated work, and large local
operations.

Exceptions: A proven bounded pure operation does not need a separate timeout or
cancellation contract.

## Approval boundaries

Approval belongs before the consequential effect. A preview should identify the
target, proposed change, and expected impact without performing the action.

### Separate proposal from execution

Requirement: A tool requiring Approval MUST expose enough structured preview
information for the approving actor to understand the exact effect.

Rationale: Approval over an opaque instruction is not meaningful control.

Scope: External messages, destructive actions, broad writes, financial effects,
and actions whose authority comes from a human decision.

Exceptions: A previously approved policy can authorize a bounded repeated
operation when its target, limits, and revocation path are explicit.

## Errors and structured results

Tools return expected outcomes as structured results and reserve exceptions for
faults that prevent contract completion. Error messages should be actionable
for the model without exposing secrets or internal infrastructure.

### Keep result shapes deterministic

Requirement: Tool results MUST have deterministic machine-readable shapes for
success, expected non-completion, and recoverable partial failure.

Rationale: A model can reason more reliably about explicit variants than about
free-form exception text.

Scope: Every tool used in an Agent run.

Exceptions: A pure scalar-returning tool can return the scalar directly when it
has no expected alternate outcome.
