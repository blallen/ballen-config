# Dynamic Subagents

Dynamic subagents support runtime creation or selection of specialists. The
parent or orchestration layer can define a role, choose from a registry, or
create a one-shot worker based on the current task.

## Runtime identity

Each subagent has an independent run identity, instructions, input, result,
capability set, lifecycle state, and usage record. A reusable worker can also
have a stable registry identity distinct from an individual run.

### Name dynamically created workers

Requirement: Every dynamic subagent MUST have an identity that distinguishes
its role and run from the parent and from sibling workers.

Rationale: Identity is required for result collection, cancellation,
observability, retry, and persistence.

Scope: Runtime-created, runtime-selected, one-shot, and reusable subagents.

Exceptions: A single synchronous one-shot worker can use an invocation identity
when no reusable registry identity is needed.

## Context mapping and isolation

Dynamic delegation starts from isolation:

- message history is not inherited unless selected messages are included by an
  explicit context mapping;
- dependencies are not inherited unless the worker factory constructs or maps
  them;
- resources are not inherited unless a resource-sharing policy grants them; and
- permissions are not inherited unless the worker receives explicit capability
  grants.

### Construct child context deliberately

Requirement: Dynamic delegation MUST define context mapping, dependency
construction, resource sharing, and capability grants for each worker role.

Rationale: Runtime flexibility otherwise turns parent state into ambient child
authority and makes worker behavior irreproducible.

Scope: Worker factories, registries, delegation toolsets, and nested subagent
creation.

Exceptions: A platform can provide reviewed immutable defaults, but each role
still names any additional context or authority it receives.

## Concurrency

Workers can run synchronously, in the background, or under an automatic mode
chosen by policy. The owner of concurrency also owns limits, result joining,
ordering assumptions, and partial completion.

### Bound concurrent workers

Requirement: Concurrent dynamic delegation MUST define a worker limit, result
collection rule, and behavior when only a subset completes.

Rationale: Unbounded fan-out can exhaust model, network, and memory budgets and
leave uncollected work running.

Scope: Background and parallel subagent execution.

Exceptions: A single synchronous worker needs no concurrency limit beyond its
ordinary run bound.

## Cancellation

Cancellation can target one worker, a group, or all descendants. The caller
records whether cancellation was requested, acknowledged, or too late because
the worker already completed.

### Propagate cancellation ownership

Requirement: The component that creates a dynamic worker MUST retain a way to
cancel or deliberately detach it, with descendant behavior defined explicitly.

Rationale: Runtime-created work without lifecycle ownership becomes orphaned
cost and can continue consequential effects after its result is unwanted.

Scope: Synchronous, background, nested, and reusable workers.

Exceptions: A deliberately detached durable job can transfer cancellation
ownership to another named control plane.

## Retry

Retry creates a new attempt under the same logical task identity. Policy decides
which failures are transient, whether prior messages are retained, and whether
effect-bearing tools are safe to replay.

### Preserve retry semantics

Requirement: Dynamic subagent Retry MUST distinguish logical task identity from
attempt identity and apply an explicit transient-failure policy.

Rationale: Blind retry can repeat side effects or turn a deterministic failure
into repeated cost.

Scope: Worker-run and delegated-tool retry.

Exceptions: A pure read-only one-shot worker can use the caller's ordinary retry
policy when task and attempt identity remain observable.

## Persistence

Persistence records worker definitions needed for reuse, active task identity,
terminal results, and any durable continuation data. It does not serialize live
clients or framework run objects.

### Persist resumable worker state

Requirement: A dynamic worker that can outlive its parent process MUST persist
enough state for a named owner to inspect, cancel, collect, or resume it.

Rationale: A background worker without durable ownership becomes unreachable
after restart.

Scope: Persisted registries, background tasks, and nested durable workers.

Exceptions: A synchronous worker whose lifetime is strictly bounded by the
parent call does not require independent persistence.

## Orchestrator boundary

Dynamic delegation makes coordination a first-class Orchestrator responsibility
when the system chooses worker roles, manages concurrent lifecycles, coordinates
results, or persists worker state. Runtime construction alone is not a reason to
share parent context or authority.
