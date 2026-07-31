# Composition Layer

This document defines how models and scenario data become one runnable system
and how that system produces a durable `ModelSolution`. The composition layer
owns cross-model resolution, solver boundaries, and run specifications; it does
not rewrite the scientific declarations stored in a `MechanisticModel`.

## `MechanisticModelComposer`

A `MechanisticModelComposer` assembles one or more `MechanisticModel` artifacts
and explicit scenario data into one runnable system. Composition preserves each
model's declarations, stable identities, and provenance while resolving the
connections that only become visible when models are used together.

The union of all targeted `Variable` identities forms the targeted state to be
advanced. A variable that is read but not targeted by any included model is
external-only: it is a required input, not hidden solver state. If compatible
models contribute to the same targeted variable, their rates form a natural
sum while the individual contributions remain traceable in the runtime ledger.
`ConservationLaw` declarations and diagnostic metadata are aggregated as
composed views while retaining the identity of their originating declarations.

Composition is a conceptual responsibility rather than a required class or
interface shape. An implementation may expose it through any suitable package
mechanism as long as the ownership and validation rules remain clear.

## Composition Validation

Before a run is created, composition establishes that:

- every external read is resolved by a compatible target from a peer model or
  by a declared scenario input;
- every required `Parameter` has one resolved value and retains its stable
  model identity across scenarios;
- every targeted state variable has an initial value;
- shared variables have compatible meaning, units, and shape; and
- each `ConservationLaw` and diagnostic declaration can be evaluated against
  the composed namespace.

An initial-condition override supplies a starting value; it does not satisfy an
external value that must remain available throughout evaluation. Missing
values do not silently become zero. Defaults may be used only through a stated
policy, and conflicting defaults from otherwise compatible inputs fail rather
than being resolved by incidental ordering.

## Scenario Boundary

The model describes scientific structure. A scenario describes one intended
use of that structure: parameter values, initial conditions, declared
exogenous inputs, run horizon, interventions, and permitted numerical choices.
Changing a scenario value does not create a new `Parameter` or rewrite the
model that declared it.

Resolution precedence must be deterministic and visible. A scenario override
may replace a declared default where the run contract permits it, but it cannot
change entity identity or conceal disagreement between source models. The
composed result records which value source won and why.

## Solver Boundary

The solver owns advancement through time. It chooses and applies the numerical
integration method, state ordering, time grid, step control, tolerances, and
integration diagnostics. At each requested time point it supplies the current
state and resolved inputs to the evaluator, which returns instantaneous rates.

This boundary keeps numerical policy out of `MechanisticModel` content. A
solver may adapt its internal steps without changing model identity, while the
reported method and settings remain part of the run record.

## Events and Interventions

Events and interventions describe declared changes at or in response to a time
boundary, such as replacing an input, changing a parameter value, or applying a
state discontinuity. The run specification states their trigger, ordering, and
effect; the solver owns locating the boundary and advancing consistently across
it.

Applied interventions are recorded in the solution with their effective time
and identity. They do not become unrecorded mutations of the durable model or
scenario.

## One Composition Path

A single model follows the same composition path as several models. It still
resolves parameters, initial conditions, external inputs, state ordering,
events, evaluator construction, and solver configuration. This avoids a
special single-model runtime whose semantics can drift from multi-model runs.

## `ModelSolution`

A `ModelSolution` carries named simulation results and derived diagnostics. It
should be independently interpretable: a reader can understand what was run
and what each result means without access to a live evaluator or solver. A
solution normally carries:

- sampled times and named variable trajectories with units;
- stable variable identities and the state ordering used by the solver;
- applied interventions and event outcomes;
- solver method, settings, completion status, and diagnostics;
- model, scenario, and composition identities with schema versions;
- resolved input identities and either their values or immutable references
  and digests; and
- derived diagnostics, including conservation information where applicable;
  and
- runtime compatibility information needed to interpret evaluator and solver
  semantics.

Named-rate, conservation, and other derived diagnostics may be stored as
snapshots or recomputed when the originating composition and a compatible
runtime remain available.

Independent interpretation is not the same as guaranteed rerun capability. A
full reproducibility bundle also contains the serialized model, the complete
run specification, required immutable external artifacts, and enough runtime
compatibility information to reconstruct the calculation rather than only
interpret it.

## Composition Serialization

Composition serialization is the durable run specification. It records model
identities or immutable model references, scenario identity and resolved
values, state and input mappings, solver policy, events, interventions, and the
schema version needed to interpret them. It also preserves provenance for
external artifacts without embedding private retrieval state.

Live solver objects, evaluator namespaces, callbacks, caches, and in-flight
steps are transient and are excluded. The serialized composition plus its
referenced model artifacts should be sufficient to reconstruct the same
runnable system under a compatible runtime.
