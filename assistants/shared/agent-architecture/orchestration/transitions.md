# Orchestration Transitions

A transition records one decision about what the orchestration loop does next.
The terms below are conceptual outcomes, not required code symbols. An
implementation can use different names while preserving their semantics and
audit fields.

## Outcome model

| Intent | Meaning |
| --- | --- |
| Advance | Move to a named next Scene or Act. |
| Retry | Run the same Scene again with explicit failure feedback. |
| Escalate | Pause automated progress and request a human or external policy decision. |
| Stop | End the current Act or overall run with an explicit terminal outcome. |

Every outcome carries intent, target, and reason. Advance identifies the next
target. Retry identifies the current target and next attempt. Escalate identifies
the decision owner or queue. Stop identifies the terminal status.

### Record a complete decision

Requirement: Every transition outcome MUST include a stable intent, a valid
target or terminal status, and a bounded human-readable reason.

Rationale: Persisted decisions remain auditable after the policy code and model
context that produced them are no longer running.

Scope: Scene-level and Act-level transition decisions.

Exceptions: A Stop outcome does not need a next execution target when it names
the terminal status explicitly.

## Policy and mechanism

Policy computes intent, target, and reason from typed state and the most recent
outcome. The mechanism applies that decision by routing control, recording
state, scheduling work, or pausing for escalation.

### Keep policy pure where practical

Requirement: Transition policy SHOULD compute an outcome without performing
persistence, scheduling, or external side effects.

Rationale: Pure policy is directly testable against state and outcome fixtures,
while the execution mechanism can be tested separately for reliable effects.

Scope: Rules that decide advance, retry, escalation, or stop.

Exceptions: A small local Workflow can combine them in one function when it
retains distinct decision and application phases that tests can observe.

## Advance

Advance moves to a named eligible target after the current result passes its
validation and gate. The target must exist and be reachable from the current
position under the workflow definition.

### Validate advance targets

Requirement: An Advance outcome MUST name an eligible target and MUST be
rejected before scheduling when that target is missing, terminal, or invalid for
the current state.

Rationale: Invalid targets otherwise turn a policy error into a later routing or
resume failure.

Scope: Cross-Scene and cross-Act progress.

Exceptions: None. Dynamic workflow definitions still validate against the
definition active for the run.

## Retry

Retry repeats the same bounded Scene with explicit feedback from the failed
attempt. It preserves successful work outside that Scene and increments a stable
attempt identity.

### Bound retry

Requirement: Retry MUST have a finite policy, explicit attempt identity, and a
defined outcome when the limit is reached.

Rationale: Unbounded retry hides persistent failure, spends resources without a
decision point, and can repeat side effects.

Scope: Automated retries at Scene or tool boundaries.

Exceptions: A human-operated repair loop can remain open-ended when each new
attempt requires an explicit human action rather than automatic scheduling.

## Escalate

Escalate pauses automated progress and emits the evidence required for a person
or external policy to decide. It does not silently convert into Retry.

### Name escalation ownership

Requirement: Escalate MUST identify who or what owns the next decision and what
information is required to resolve it.

Rationale: An ownerless paused run is operationally indistinguishable from a
hang.

Scope: Human approval, ambiguity resolution, unsupported cases, and policy
exceptions.

Exceptions: A system-wide incident queue can be the owner when individual
routing is intentionally centralized.

## Stop

Stop ends the relevant control loop successfully or unsuccessfully. A terminal
outcome contains the final status, reason, and durable outputs accumulated so
far.

### Converge on explicit terminals

Requirement: Stop MUST produce one declared terminal status and MUST NOT rely on
falling through unmatched transition guards.

Rationale: Explicit terminals prevent silent hangs and make every end state
observable.

Scope: Act completion and overall workflow completion.

Exceptions: None. A runtime exception can interrupt execution, but recovery must
translate it into a persisted fault or a resumed control-loop decision.

## Applying transitions

The mechanism validates the outcome, persists it when durability is required,
and then applies the routing effect. If persistence succeeds but scheduling
does not, recovery re-applies the same idempotent decision rather than computing
a different one from incomplete state.
