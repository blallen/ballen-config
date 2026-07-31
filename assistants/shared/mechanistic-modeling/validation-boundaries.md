# Validation Boundaries

This document assigns failures to data construction, composition, runtime
evaluation, solving, or scientific review. Each boundary owns the checks it has
enough context to perform; a later boundary may add diagnostic context but does
not silently repair an earlier invalid artifact.

The governing rule is to reject a problem at the earliest boundary that has
enough information to identify it. Passing one boundary means only that its
contract is satisfied; it does not imply that later numerical or scientific
checks will pass.

## Data Construction

Data construction validates one durable model artifact without needing a
scenario or another model. It rejects declarations that cannot have one clear
structural meaning, including:

- a duplicate stable identity;
- an invalid target that does not resolve to a declared variable;
- a compound term that combines several conceptual contributions instead of
  representing one atomic term; and
- an unknown block referenced by content that has not been grouped into the
  model.

This boundary also checks required fields, declared relationships, identifier
stability, and the internal coherence of entity provenance. Serialization does
not make malformed content valid; the artifact must satisfy construction rules
before it is accepted as a durable model.

## Composition

Composition validates the namespace and inputs that exist only when models and
a scenario are brought together. It rejects:

- an unresolved external variable with neither a compatible peer target nor a
  declared scenario source;
- a missing parameter after the allowed default and override rules have been
  applied;
- a missing initial condition for targeted state;
- incompatible shared variables whose meanings, units, or shapes cannot be
  reconciled; and
- an ambiguous cross-model entity reference that could resolve to more than one
  compatible declaration.

Composition also checks parameter precedence, cross-model identity alignment,
event declarations, and the coverage of exogenous inputs. It may report
construction failures with broader diagnostic context, but it must send them
back to their owning boundary rather than inventing a scenario-level repair.

## Runtime Evaluation

Runtime evaluation validates the instantaneous calculation against resolved
values. It rejects an unknown mathematical name, an ambiguous mathematical
namespace, an invalid expression that cannot be evaluated within the
restricted mathematical vocabulary, and any non-finite contribution produced
by a term.

Names and expression forms should be checked earlier whenever they can be
decided statically. Runtime remains responsible for failures that depend on the
current values or active evaluation path. It identifies the relevant term,
target, inputs, and time point so that the failure is explainable without
changing the durable model.

## Solver

The solver validates temporal and numerical execution. It rejects an invalid
event boundary that cannot be located or ordered consistently and reports when
integration cannot complete reliably under the stated method and settings.
It also surfaces an unstable trajectory, exhausted step control, and other
numerical conditions that make the computed path unreliable.

Solver success means that a numerical trajectory was produced under the run
contract. It does not establish that the model structure or resulting behavior
is scientifically appropriate.

## Scientific Review

Scientific review interprets the completed model and solution in their intended
context. It examines issues such as a unit mismatch between a reported result
and its scientific interpretation, an unacceptable conservation residual, an
impossible state, or a scientifically implausible result despite successful
integration.

These checks can use domain expectations, reference evidence, acceptance
ranges, and reviewer judgment that do not belong in generic execution
mechanics. Their findings should retain links to the relevant model entities,
scenario inputs, runtime contributions, and solver diagnostics. Scientific
review may reject a technically successful run, but it must not conceal a
structural, composition, runtime, or solver failure under a plausibility label.
