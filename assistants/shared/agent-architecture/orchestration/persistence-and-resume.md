# Persistence and Resume

Persistence captures enough durable state to reconstruct an orchestration
decision without serializing live runtime machinery. Resume feeds that state
back through the same control loop used by a new run.

## Durable workflow position

A durable workflow position names the current Act and, when needed, the current
Scene. Store it with terminal results already produced, typed handoff references,
the last transition outcome, and the workflow-definition version.

### Persist meaning, not stack frames

Requirement: Resumable orchestration MUST persist a durable workflow position
and the typed outcomes needed to evaluate the next transition.

Rationale: Process stack frames and framework run objects cannot be relied on
after restart, deployment, or migration.

Scope: Runs expected to survive process loss, pause for human action, or resume
after a delayed dependency.

Exceptions: A short atomic run can omit persistence when restarting from the
beginning is explicitly acceptable.

## Checkpoint boundaries

Prefer checkpoints after validated Scene completion, before applying the next
consequential transition. A checkpoint records completed work once and provides
a stable base for retry or resume.

### Align checkpoints with completed work

Requirement: A durable checkpoint SHOULD correspond to Scene completion or
another explicitly atomic boundary.

Rationale: Mid-operation snapshots often cannot prove which effects completed
and make replay ambiguous.

Scope: Scene outcomes, Act envelopes, and consequential tool operations.

Exceptions: A long-running operation can expose its own documented sub-checkpoint
protocol when restarting the entire Scene is too expensive.

## Resume through the same control loop

Resume loads durable state, validates it, reconstructs runtime dependencies,
and enters the same control loop that handles new execution. It does not jump
directly into a downstream function or duplicate transition rules in a recovery
path.

### Reuse transition policy

Requirement: Resume MUST use the same control loop and transition policy as a
new run after restoring validated state.

Rationale: A separate resume path drifts from ordinary execution and creates
states that have never been exercised by normal tests.

Scope: Automatic recovery, manual continuation, and delayed escalation
resolution.

Exceptions: Data migration can precede entry into the shared loop when an older
checkpoint version requires explicit conversion.

## Validate restored state

Validation confirms that the position exists, required handoffs are present,
artifact references resolve under the declared store, and the workflow version
can interpret the state.

### Reject a stale resume target

Requirement: A stale resume target MUST be rejected or migrated before any new
Scene is scheduled.

Rationale: Continuing from a removed or semantically changed boundary can apply
valid work to invalid assumptions.

Scope: Renamed Acts or Scenes, changed handoff schemas, missing artifacts, and
incompatible workflow versions.

Exceptions: An explicit compatibility map can translate the old target and
handoffs to a validated current position.

## Retry context and attempt identity

Retry context contains the prior attempt's bounded failure feedback, the next
attempt identity, and any idempotency key required by effect-bearing tools. It
does not grant the Scene access to the entire outcome log.

### Make attempts distinct and traceable

Requirement: Each automatic retry MUST have a stable attempt identity and
explicit feedback derived from the preceding outcome.

Rationale: Attempt identity supports observability and duplicate protection;
explicit feedback preserves context isolation.

Scope: Scene retries and delegated work retried by orchestration policy.

Exceptions: A deterministic pure check can reuse the same input without failure
feedback when no state or effect differs between attempts.

## Idempotent replay

Idempotent replay applies a previously persisted decision without producing an
additional unintended effect. Persist decision identity before or atomically
with scheduling where the runtime permits it.

### Protect replayed effects

Requirement: Idempotent replay MUST be defined for every persisted transition
that can schedule an external or state-changing operation.

Rationale: Recovery can occur after a decision was persisted but before the
caller learned whether its effect completed.

Scope: Scheduling, messages, writes, billing operations, and destructive tools.

Exceptions: A non-idempotent operation can stop with an unknown-outcome state
that requires reconciliation before any retry.

## Reconstruct live dependencies

Persistence stores data and stable resource identifiers, not live dependency
objects. Resume reconstructs clients, stores, clocks, toolsets, and scoped
permissions from the current runtime configuration.

### Keep runtime resources ephemeral

Requirement: Checkpoints MUST NOT serialize live dependency objects, open
connections, callbacks, credentials, or framework run contexts.

Rationale: Those objects carry process-local state and authority that cannot be
restored safely from a checkpoint.

Scope: Agent dependencies, tool resources, protocol clients, and orchestration
runtime handles.

Exceptions: A serializable durable identifier can be stored and resolved by an
explicitly granted runtime dependency during resume.
