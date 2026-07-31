# Runtime Layer

This document defines deterministic evaluation of a `MechanisticModel` at one
point in time. The runtime layer owns transient rates and evaluation
diagnostics; it does not choose scenario inputs, construct solver state,
advance time, or redefine persistent model identity.

## Evaluator Responsibility

An evaluator answers one narrow question: given a complete `MechanisticModel`,
the current value of every readable `Variable`, and the resolved values needed
by the mathematics, what changes does the model prescribe at one point in
time?

The evaluator processes each `MathTerm` as an atomic contribution. It resolves
the term's inputs, evaluates its magnitude, applies any declared topology
weights, and assigns the resulting contribution to the term's target. It does
not select initial conditions, infer missing scenario inputs, advance the
clock, or decide whether a trajectory is scientifically credible.

## Restricted Mathematical Expressions

Model mathematics should be represented as restricted mathematical
expressions whose allowed names and operations are explicit and inspectable.
The evaluation namespace may contain declared variables, parameters,
constants, time, and an approved mathematical vocabulary. It must not silently
reach into ambient process state or execute arbitrary behavior.

Restriction makes dependencies auditable and failures local. An expression
that references an undeclared name, uses an unsupported operation, or cannot
produce a valid numeric contribution fails at evaluation rather than acquiring
an accidental meaning.

## Determinism and Identity

The same model identity, resolved inputs, and time point must produce the same
ordered contributions and diagnostics. Stable `MathTerm` and `Variable`
identities are carried through evaluation so that results can be compared
across runs without depending on incidental storage order.

Determinism includes a defined evaluation order and a defined accumulation
order. It does not imply that mathematically distinct terms are merged merely
because they currently evaluate to the same number.

## Rate Accumulation and Ledger

Evaluation produces two complementary views:

- a per-variable change map containing the total prescribed change for each
  targeted `Variable`; and
- a named rate ledger retaining each `MathTerm` contribution, its target, and
  the identity needed to explain the total.

When several terms target the same variable, their contributions accumulate
naturally in the change map while remaining distinct in the ledger. The map is
suited to a solver; the ledger is suited to explanation, diagnostics, and
comparison. Neither is a durable replacement for the model declarations from
which it was evaluated.

## Runtime Failures

Evaluation fails explicitly when a required value is absent, a mathematical
name or operation is unsupported, a target cannot be resolved, or a term
produces a non-finite contribution. The failure should identify the relevant
model entity and preserve enough diagnostic context to locate the bad input or
expression.

The evaluator does not repair incomplete composition, substitute silent
defaults, or reinterpret malformed model content. Those failures belong to an
earlier boundary and should be rejected before solver integration begins.

## Transient Runtime State

The evaluator's namespace, prepared expression forms, caches, in-flight
contribution records, and current ledger are transient runtime state. They may
be recreated from the durable model and resolved inputs and therefore do not
belong in the canonical `MechanisticModel` serialization.

A solver may call the evaluator repeatedly while advancing time. The solver
owns that temporal loop, step control, event handling, and integration
diagnostics; the evaluator remains a deterministic instantaneous mapping.
