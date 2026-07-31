# Data Layer

This document defines the durable `MechanisticModel` artifact and the
scientific declarations that travel with it. The data layer owns persistent
identity and serialization; it does not evaluate expressions, compose runnable
systems, advance time, or judge scientific fitness.

## Process-Centered Model

A `MechanisticModel` is the complete structured artifact. Its central unit of
causal description is an `Interaction`: a named process that declares which
quantities it changes, which quantities it reads, and the individual
contributions it makes to change.

This process-centered representation is the source of truth for both structure
and mathematics. Equations and model topology are different views of the same
declarations, not parallel artifacts that must be synchronized by hand. Model
construction can therefore be incremental without allowing a diagram, equation
list, or generated executable to become a competing authority.

## Targeted and External Variables

A `Variable` is a named quantity that may be changed, read, or observed. Its
role is contextual:

- targeted variables receive one or more mathematical contributions from an
  `Interaction`;
- external variables are read by that process without receiving change from
  it; and
- observed variables may be reported or derived without becoming independent
  solver state.

These roles do not grant exclusive ownership. A `Variable` may be targeted by
several interactions or several models, and an interaction may both depend on
shared quantities and contribute to shared equations. The complete model's
targeted set is the union of quantities that receive contributions. A quantity
that is only external within one model remains an explicit unresolved
dependency until composition supplies it.

## Atomic `MathTerm` Contributions

A `MathTerm` is one atomic contribution to one target equation. It carries
enough stable identity and description to attribute that contribution in
diagnostics, conservation analysis, documentation, and review.

Atomicity keeps additive structure visible. When several mechanisms affect one
target, the model records several contributions rather than hiding them inside
one compound expression. The same process can still affect several targets,
but each target receives its own attributable contribution.

Mathematical magnitude and topology remain separate. The expression describes
the contribution's magnitude; a sign, direction, or other structural weight
describes how that magnitude enters its target. This separation allows one
named process rate to support several structural effects without duplicating
or obscuring the underlying mathematics.

## `Block`, `Parameter`, and `ConservationLaw`

A `Block` groups related model content. It may represent any useful
organizational boundary, but grouping does not change the meaning of an
`Interaction`, `Variable`, or `MathTerm`.

A `Parameter` supplies a named quantity used by the mathematics. Its stable
identity, units, description, and provenance belong to the model. Its resolved
runtime value may vary by scenario without creating a different parameter or
rewriting model identity.

A `ConservationLaw` declares a conserved relationship. It is an explicit piece
of scientific intent rather than a relationship silently inferred from
topology. Later layers may aggregate declarations or calculate residuals, but
the durable declaration stays with the model.

## Entity Provenance

Entity provenance travels with the scientific model. It gives a stable place
to explain why a block, variable, interaction, parameter, contribution, or
conservation relationship exists and what evidence supports it. Provenance is
part of the model's interpretability, not a transient runtime annotation.

Extraction provenance serves a different purpose: it audits how this generic
reference library was adapted from its sources. Extraction provenance does not
travel with a scientific model. Both forms require privacy review, and neither
should expose access secrets, confidential source content, private local
paths, or uncurated research material.

## Derived Views

Derived equations, topology, a variable registry, and a parameter registry are
projections of the canonical `MechanisticModel`. They make the artifact easier
to evaluate, inspect, document, or visualize without becoming independent
sources of wiring or mathematical truth.

A derived view should be reproducible from the same model version and should
retain stable links to the entities from which it was assembled. If a derived
view conflicts with the stored declarations, the declarations win and the view
must be regenerated.

## Serialization

The data layer is the durable serialization boundary. A serialized model
preserves:

- stable entity identities and relationships;
- mathematical declarations, topology, and units;
- blocks, parameter identities, and conservation declarations;
- descriptive metadata and entity provenance; and
- a schema version or equivalent compatibility marker.

Serialization does not persist a second equation object or generated
executable as another authority. Scenario-specific parameter values,
authoritative initial conditions, interventions, solver settings, compiled
evaluators, callbacks, caches, and live resources stay outside model identity.
If the model carries default initial-value suggestions, composition must still
resolve the authoritative values for a particular run.

Schema compatibility is explicit. A reader either understands the serialized
contract, applies a reviewed migration, or reports that it cannot interpret the
artifact; it does not silently discard unknown scientific meaning.

## Construction Boundary

Data construction validates what one artifact can know locally. It checks such
properties as stable identity, valid references, target consistency, atomic
contribution shape, unit declarations, grouping references, and
serializability. Invalid local structure fails before the artifact is treated
as a complete `MechanisticModel`.

Construction does not resolve cross-model external variables, scenario values,
authoritative initial conditions, or solver configuration. It also cannot prove
that expressions evaluate successfully for a runtime state, that integration
will complete, or that results are scientifically plausible. Those checks
belong to composition, runtime, solver, and scientific validation boundaries.
