# Mechanistic Modeling Reference Library

This passive reference library explains how a structured mechanistic model
moves from durable scientific declarations to evaluation, composition,
simulation, and interpretable results. It defines conceptual vocabulary and
responsibility boundaries, not a required programming language or package API.

## Authority and Scope

The library is authoritative for its conceptual terminology and for the
boundaries between model data, runtime evaluation, composition, solving,
serialization, and validation. The PascalCase names below identify stable
roles. They do not require matching classes, methods, modules, or file layouts.

The documents describe a target architecture. Adoption and implementation
status must be verified in each consuming system; the target is not evidence
that every capability already exists there.

## Terminology

- a `MechanisticModel` is the complete structured artifact;
- an `Interaction` is a named process;
- a `Variable` is a quantity that may be changed, read, or observed;
- a `MathTerm` is one atomic contribution to one target equation;
- a `Block` groups related model content;
- a `Parameter` supplies a named quantity used by the mathematics;
- a `ConservationLaw` declares a conserved relationship;
- a `MechanisticModelComposer` assembles models and scenario data into one
  runnable system; and
- a `ModelSolution` carries named simulation results and derived diagnostics.

These terms keep the model's declarations, runtime contributions, composed
state, and durable results distinguishable. Plain-language translations may
clarify a role, but they do not replace or collapse the primary vocabulary.

## Layer Map

Responsibility and dependency move in one direction:

1. The [data layer](data-layer.md) defines the durable model artifact and its
   serializable scientific declarations.
2. The [runtime layer](runtime-layer.md) evaluates those declarations at one
   point in time and produces transient changes and diagnostics.
3. The [composition layer](composition-layer.md) resolves complete runnable
   state, scenarios, solver behavior, and durable results.
4. Downstream consumers use the composition boundary for applications,
   reports, or automation without redefining model semantics.
5. [Validation boundaries](validation-boundaries.md) assign failures to the
   earliest layer with enough information to detect them.

Validation is cross-cutting, but its ownership follows the same direction:
local model shape before cross-model wiring, evaluation before integration, and
numerical completion before scientific acceptance.

## Package Mechanics

The data layer is the dependency foundation. Runtime evaluation depends on the
data contract, and composition depends on both data and runtime behavior.
Downstream consumers depend on the public composition boundary. Dependencies
do not point back from data toward runtime or composition.

Each layer serializes only the durable artifacts it owns. Compiled evaluators,
callbacks, caches, in-flight rate ledgers, and live solver objects remain
transient and reconstructible. A thin public facade may expose stable concepts
from the layers, but it must not become a second source of model truth.
Optional integrations point outward from the stable boundary so that a
framework, interface, or numerical library does not define the core model.

## Relationship to Agent Architecture

The [agent architecture reference library](../agent-architecture/README.md) is
a parallel authority. Agent architecture owns orchestration, delegation,
handoffs, retry, persistence, and resume. Mechanistic modeling owns model
semantics, numerical evaluation boundaries, composition, solving, and result
interpretation.

An Act or Scene may author, validate, compose, simulate, or pass a versioned
`MechanisticModel`. That workflow relationship does not transfer ownership of
the artifact's scientific or numerical meaning to the orchestration layer.

## Reading Order

Start with the Data Layer to understand the persistent artifact. Continue with
the Runtime Layer for evaluation, then the Composition Layer for runnable
systems and solutions. Read Validation Boundaries last to see where each class
of failure belongs. Return to this index when deciding package direction or the
integration boundary with agentic workflows.
