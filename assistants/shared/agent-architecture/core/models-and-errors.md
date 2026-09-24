# Models, Results, and Errors

Models make Agent boundaries inspectable. Use validated boundary models for
data and runtime dependency containers for live resources.
Separate expected non-completion from exceptional faults.
Represent partial failure explicitly and perform exception translation where
public semantics are owned.

## Validated boundary models

Use validated boundary models for data that crosses a package, process,
protocol, persistence, or delegation boundary. Typical examples are Agent
inputs, structured outputs, tool results, handoffs, and resumable checkpoints.

### Validate crossing data

Requirement: Data that crosses an Agent or orchestration boundary MUST have an
explicit schema and validation point.

Rationale: Boundary validation prevents malformed or stale data from becoming
implicit context inside a model run.

Scope: Public entry points, tool calls, delegated work, stored checkpoints, and
external adapters.

Exceptions: A private in-process helper can accept an ordinary typed value when
the caller and callee share one implementation boundary.

Boundary models should contain data, stable identifiers, and durable artifact
references. They should not contain open files, database sessions, network
clients, callbacks, or framework run objects.

## Runtime dependency containers

Runtime dependency containers carry live resources needed during execution:
clients, stores, clocks, transaction handles, caches, and scoped configuration.
They are typed for construction and testing, not serialized as business data.

### Keep live resources out of boundary data

Requirement: Runtime resources MUST NOT be embedded in serialized input,
output, handoff, or checkpoint models.

Rationale: Live objects have process-bound lifecycle and authority that cannot
be reconstructed safely from serialized data.

Scope: Every resource with connection state, credentials, mutable handles, or
process-local behavior.

Exceptions: A durable resource identifier can cross the boundary when the
receiver resolves it through its own explicitly granted dependency.

## Structured result variants

A public result should distinguish successful completion, expected
non-completion, and partial completion. A tagged variant or discriminated union
usually communicates this more reliably than optional fields whose combinations
are undocumented.

Useful result fields include:

- a stable outcome kind;
- the validated payload available for that outcome;
- bounded human-readable detail;
- machine-readable reason codes;
- durable artifact references; and
- continuation or retry metadata when applicable.

### Make result states unambiguous

Requirement: A public Agent result MUST make its outcome variant identifiable
without interpreting free-form prose.

Rationale: Callers need deterministic branching, metrics, and recovery even
when the content was produced by a model.

Scope: Agent services, tool results, handoffs, protocol responses, and stored
outcomes.

Exceptions: A pure transformation with exactly one successful return shape can
use that shape directly and reserve exceptions for faults.

## Expected non-completion and exceptional faults

Expected non-completion is a valid domain outcome: insufficient evidence,
approval declined, unsupported input, no match, or a quality gate that did not
pass. Exceptional faults mean the contract could not be evaluated normally:
dependency outage, invariant violation, malformed framework response, or
unexpected implementation failure.

### Return expected outcomes

Requirement: Expected non-completion MUST be represented as a typed result
rather than raised as an exceptional fault.

Rationale: A caller can branch, report, or retry expected outcomes without
conflating them with broken infrastructure or code.

Scope: Domain conditions that callers are expected to handle during normal
operation.

Exceptions: None when non-completion is part of the documented contract.

### Raise or translate unexpected faults

Requirement: Exceptional faults SHOULD retain their causal chain until a
service or protocol boundary translates them.

Rationale: Preserving the cause supports diagnosis while boundary translation
prevents internal exception types from leaking into public contracts.

Scope: Dependency failures, invariant violations, framework failures, and
unexpected implementation errors.

Exceptions: A security boundary can replace sensitive details immediately while
retaining a safe reason code and internal causal record.

## Partial failure

A partial failure occurs when some requested work completed and some did not.
The result should name completed items, failed items, and whether retrying only
the failed subset is safe.

### Preserve completed work explicitly

Requirement: A partial failure result MUST identify durable completed outputs,
failed units, and the permitted recovery action.

Rationale: Discarding successful work wastes cost; treating partial completion
as total success hides missing output.

Scope: Batch tools, fan-out delegation, multi-artifact generation, and
multi-stage operations that return before all units succeed.

Exceptions: An atomic operation can roll back and report one fault when its
contract guarantees that no partial state remains.

## Exception translation

Exception translation belongs at the boundary that understands both internal
failure and public semantics. A domain service can translate a database-specific
absence into a domain result; an external adapter can translate a service fault
into a protocol error.

### Translate once at the owning boundary

Requirement: Each exception SHOULD be translated at the first boundary that
can assign a stable public meaning while retaining the original cause for
diagnostics.

Rationale: Repeated wrapping loses meaning, while leaking low-level exceptions
couples callers to implementation details.

Scope: Service entry points, tool wrappers, MCP wrappers, HTTP handlers, queue
consumers, and orchestration boundaries.

Exceptions: A boundary can re-raise a documented domain exception unchanged
when it is already part of the public API.
