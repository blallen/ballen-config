# Orchestration Handoff Contracts

A handoff is the protocol between orchestration boundaries. It names what is
known, what completed, what artifacts exist, and what the next boundary may
assume. Shared storage can hold artifacts, but storage contents are not the
handoff contract.

## Explicit entry point

Every Act has one explicit entry point for orchestration. The entry point
accepts a typed request containing its domain input, known prior packages, and
the explicitly scoped dependencies needed for that Act.

### Use one orchestration entry point

Requirement: An Act MUST expose one documented orchestration entry point that
accepts its complete typed handoff input.

Rationale: A uniform entry point gives the Director one testable contract for
initial execution and resume.

Scope: Act invocation from a Director or another orchestration boundary.

Exceptions: Internal helper functions can expose narrower operations when they
are not used as alternate orchestration entry points.

## Terminal envelope

An Act returns one terminal envelope with:

- a closed status;
- a human-readable summary;
- durable artifact references;
- an optional typed payload; and
- continuation metadata when another boundary needs it.

Use these status meanings:

| Status | Meaning |
| --- | --- |
| Succeeded | The Act satisfied its contract and produced valid output. |
| Blocked | The Act stopped for a reason a human or policy can act on. |
| Failed | The Act could not complete because contract execution failed. |

### Preserve status meaning

Requirement: An Act result MUST distinguish Succeeded, Blocked, and Failed as
machine-readable statuses.

Rationale: A Director needs different transition, escalation, and reporting
policy for valid completion, actionable non-completion, and faults.

Scope: Every terminal Act result.

Exceptions: A narrower internal Act can use a subset when its public wrapper
maps all outcomes into the complete envelope.

## Typed payload and artifact references

The typed payload carries small domain values needed by later boundaries.
Artifact references identify durable output without embedding large content or
assuming a local filesystem. References should be relative to an explicitly
named artifact store or use another portable identifier.

### Name every transferred value

Requirement: A handoff MUST identify each transferred value or artifact through
the typed payload or explicit artifact references.

Rationale: Downstream workspace scanning creates an invisible protocol and
breaks auditability, testing, and resume.

Scope: Values and artifacts produced by one boundary and consumed by another.

Exceptions: Shared immutable reference data can remain outside the handoff when
all consumers receive it through a declared dependency.

## Dependencies and capabilities

The Director passes domain data and explicitly scoped dependencies. An ambient
context object, inherited tool registry, or unrestricted capability bundle does
not cross the Act boundary merely because it is convenient.

### Scope every dependency

Requirement: An Act MUST receive explicitly scoped dependencies and capability
grants rather than inheriting the caller's ambient context.

Rationale: Explicit grants make the effective authority of each Act reviewable
and prevent accidental transitive access.

Scope: Infrastructure clients, toolsets, delegated workers, storage, and other
effect-bearing dependencies.

Exceptions: A deliberately shared run workspace can be passed explicitly as
infrastructure while each Act still receives only its permitted domain
capabilities.

## Validation and construction

Construct the terminal envelope only after validating status-specific
invariants. A successful result includes every required output. A blocked result
includes an actionable reason. A failed result includes a safe fault summary
and preserves diagnostic cause internally.

### Validate before transition

Requirement: A handoff MUST satisfy status-specific invariants before the
Director applies a transition.

Rationale: Transitioning on an invalid package moves corruption across a
boundary and makes later failure harder to localize.

Scope: Initial execution, retry completion, resume, and externally restored
handoffs.

Exceptions: None. Invalid handoffs fail at their producing boundary.

## Expected refusal and non-completion

An Act can refuse work outside its supported domain or stop because required
evidence, approval, or input is absent. These are Blocked outcomes when a human
or policy can act, not generic exceptions.

### Keep refusal actionable

Requirement: A Blocked result SHOULD include a stable reason code, bounded
summary, and the action required to continue.

Rationale: Actionable non-completion allows a Director or human to choose
escalation, correction, or termination deterministically.

Scope: Missing approval, unsupported input, insufficient evidence, and failed
quality gates.

Exceptions: A security-sensitive refusal can omit details that would disclose
protected policy while retaining a safe reason code.

## Resume inputs

Resume supplies a starting-Act marker plus all typed packages known before that
Act. The Director validates that the packages are compatible with the selected
position. An Act does not rediscover prior output by scanning storage or run
history.

### Resume from explicit packages

Requirement: Resume MUST provide the selected position and its required typed
handoffs explicitly.

Rationale: Explicit packages make resume deterministic and testable without
reconstructing ambient history.

Scope: Manual resume, automatic recovery, and replay from a checkpoint.

Exceptions: A system can resolve package identifiers from a durable store when
the identifiers themselves are part of the resume contract.

## Compatibility ownership

The producer owns the validity of its current envelope. Consumers own support
for the envelope versions they accept. A breaking field, status, or semantic
change requires coordinated compatibility handling.

### Treat handoffs as versioned interfaces

Requirement: Breaking handoff changes MUST have an explicit compatibility,
migration, and rollout decision.

Rationale: Durable runs and independently changed Acts can encounter packages
created by an older implementation.

Scope: Fields, statuses, payload semantics, artifact-reference semantics, and
validation rules.

Exceptions: An unreleased workflow with no stored runs can update all producers
and consumers atomically.
