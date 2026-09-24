# Orchestration Anti-Patterns

These patterns hide control, authority, or state across Director, Act, and Scene
boundaries. Each remedy restores an explicit contract rather than prescribing a
particular framework.

## Ambient capabilities

Symptom: An Act receives an inherited tool registry, broad dependency bundle,
or capability-bearing client unrelated to its declared objective.

Why it fails: Effective authority becomes transitive and difficult to name,
deny, or review.

Remedy: Pass typed domain values and only explicitly granted infrastructure. An
intentional shared run workspace remains valid when its scope is visible and
restricted capabilities still require separate grants.

## Implicit workspace handoffs

Symptom: A downstream Act scans shared storage to infer which files or values a
previous Act produced.

Why it fails: Storage layout becomes an undocumented protocol, so testing and
resume depend on ambient prior state.

Remedy: Return a typed payload with durable artifact references. Use shared
storage for bytes, not as the handoff contract.

## Hidden history sharing

Symptom: A Scene or delegated Agent reads the parent's message history or the
workflow outcome log to discover its actual input.

Why it fails: The real context boundary is invisible, grows without control,
and cannot be reproduced from the function signature.

Remedy: Derive bounded feedback in the owning control layer and pass it as
explicit input. Share selected history only through a named contract.

## Mixed policy and mechanism

Symptom: Transition code decides what should happen while persisting state,
scheduling work, and performing unrelated side effects.

Why it fails: Decision behavior cannot be tested independently, and a partial
effect can leave policy state ambiguous.

Remedy: Compute intent, target, and reason first; validate and apply that
decision through a separate mechanism.

## Untyped handoffs

Symptom: Acts exchange free-form dictionaries, prompts, or prose whose required
fields and status meanings are implicit.

Why it fails: Producers and consumers can drift silently, and invalid state is
discovered only after another stage starts.

Remedy: Define validated envelopes with closed statuses, typed payloads,
artifact references, and status-specific invariants.

## Unbounded retries

Symptom: A failed Scene reruns until it happens to pass, without attempt identity,
limit, or escalation policy.

Why it fails: Persistent faults consume time and cost indefinitely and can
repeat effects whose previous outcome is unknown.

Remedy: Use a finite retry policy, explicit attempt identity, safe feedback,
and a declared escalation or stop outcome.

## Persisted live resources

Symptom: A checkpoint contains clients, sessions, open handles, callbacks, or
framework context objects.

Why it fails: Process-local lifecycle and authority cannot be reconstructed
reliably after restart.

Remedy: Persist validated data and durable identifiers, then rebuild live
resources through explicitly scoped runtime dependencies.

## Agent for every layer

Symptom: Director, every Act, and every Scene become separate model Agents even
when their responsibility is deterministic routing or validation.

Why it fails: Model calls add variability, latency, cost, and context boundaries
without adding a model-appropriate decision.

Remedy: Implement each role with the smallest sufficient mechanism. Keep model
Agents only where semantic judgment or tool selection is part of the contract.

## Review rule

### Require explicit orchestration boundaries

Requirement: An orchestration review MUST reject ambient authority, hidden
handoffs, unbounded retry, and non-resumable state unless the design documents a
bounded alternative.

Rationale: These failures compound across stages and are expensive to recover
after workflows become durable or externally consequential.

Scope: New orchestration designs and changes to Director, Act, Scene, handoff,
transition, or persistence behavior.

Exceptions: A disposable local experiment can accept reduced durability when it
has no consequential effects and is clearly labeled as an experiment.
