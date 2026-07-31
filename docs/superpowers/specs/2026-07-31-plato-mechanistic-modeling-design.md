# Plato Mechanistic Modeling Library Design

## Status

The conceptual sibling-library design and this written specification are
approved. The passive reference library is implemented in `ballen-config`
under the
[implementation plan](../plans/2026-07-31-plato-mechanistic-modeling.md).
Its current semantic and privacy approval state is recorded in the
[provenance manifest](2026-07-31-plato-mechanistic-modeling-provenance.yaml).

This specification defines a passive, implementation-neutral mechanistic
modeling reference library for `ballen-config`. It adapts the generic model,
runtime, and composition concepts currently documented in Plato and its
canonical design sources. The reference library records the intended
architecture; its existence does not imply that the target architecture is
implemented in Plato or any other consuming system. This work does not change
Plato or copy Plato source code.

## Context

The existing `assistants/shared/agent-architecture/` library explains how
agents and deterministic components are structured, delegated to, sequenced,
and resumed. It also preserves the Director/Act/Scene vocabulary for agentic
orchestration.

Mechanistic modeling is a different architecture concern. It defines the
artifact that a workflow may author, review, compose, simulate, validate, and
hand off. Nesting those semantics under agent architecture would imply that a
mechanistic model is an agent pattern. The model remains useful without agents,
and agentic workflows remain useful without mechanistic models.

Plato currently contains a strong generic mental model for a structured
mechanistic model and a forward-looking design that joins that data model to a
deterministic evaluator, a composition boundary, a numerical solver, and a
solution artifact. The same sources also contain implementation-specific
package layouts, Python APIs, framework choices, internal migration state, and
QSP examples. This work preserves the architectural mechanics while removing
those repository-specific details.

The result is a sibling reference library that answers five questions:

1. What is a `MechanisticModel`, and how do `Interaction`, `Variable`,
   `MathTerm`, `Block`, `Parameter`, and `ConservationLaw` relate?
2. How does a deterministic runtime evaluate the model without generating a
   second authoritative representation?
3. How does a composer connect one or more models, scenarios, interventions,
   and solver behavior?
4. Which information is persistent and serializable, and which state exists
   only while a model is running?
5. Which validation layer owns each kind of failure?

## Goals

1. Add a passive reference library under
   `assistants/shared/mechanistic-modeling/`.
2. Preserve the domain terminology `MechanisticModel`, `Interaction`,
   `Variable`, `MathTerm`, `Block`, `Parameter`, `ConservationLaw`,
   `MechanisticModelComposer`, and `ModelSolution`.
3. Explain the data, runtime, and composition layers in plain technical prose.
4. Explain evaluator, solver, serialization, and package mechanics at a
   generic architectural level.
5. Preserve the distinction between targeted variables and externally read
   variables without introducing an ownership model that conflicts with
   additive dynamical-system composition.
6. Make persistent data, scenario data, and transient runtime state visibly
   different.
7. Define layered validation responsibilities from artifact construction
   through scientific review.
8. Cross-link the library to agent architecture without placing either
   architecture under the authority of the other.
9. Record source provenance and portability decisions outside the canonical
   reader-facing Markdown tree.
10. Keep Plato unchanged and prove that boundary before and after delivery.

## Non-Goals

- Copy source code, method signatures, type declarations, import paths, or
  concrete package layouts from Plato.
- Require Python, Pydantic, a specific expression evaluator, a specific
  numerical solver, or any other implementation framework.
- Teach QSP, PK/PD, receptor binding, ecological modeling, or another
  particular scientific domain.
- Preserve Plato, AMi, Avogadro, QSP Autopilot, ticket, merge-request, or local
  repository references in reader-facing documents.
- Describe internal migration, compatibility, or coordinated cutover work as
  part of the generic architecture.
- Assert that target behavior documented by the canonical design is already
  implemented in Plato.
- Define a complete export and legacy-compatibility layer in V1.
- Define a parameter-curation system or a scientific knowledge base.
- Define model merge, diff, aliasing, compilation, or cache-invalidation APIs.
- Turn the library into always-loaded engineering standards or executable
  agent instructions.

## Design Decisions

### A parallel passive library

Mechanistic modeling becomes a sibling of `agent-architecture`, not a child of
it:

```text
assistants/shared/
|-- agent-architecture/
`-- mechanistic-modeling/
```

The library is passive documentation. It is read intentionally when a task
involves a structured dynamical-system artifact, model execution, or model
composition. It does not load into every coding-agent prompt and does not
silently impose scientific modeling requirements on unrelated repositories.

### Domain terminology remains explicit

The extraction keeps the source vocabulary because the terms name stable
conceptual boundaries rather than incidental classes:

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

Generic alternatives may appear as translations, but they do not replace the
primary terminology.

The exact terms and capitalization are normative vocabulary for the library.
Reader-facing definitions and headings must use them consistently. Plain-language
translations may clarify a term, but may not rename it, collapse it into a more
generic label, or substitute a parallel vocabulary. Structural tests enforce
the required names, and manual review verifies that their meanings remain
distinct.

These PascalCase names identify conceptual roles in this library. They do not
require a programming language, class name, method name, package API, or file
layout. In particular, `MechanisticModelComposer` means the composition
boundary and `ModelSolution` means the durable result artifact, regardless of
how a concrete implementation names or represents them.

### Mechanically explanatory, implementation-neutral

The library retains what each mechanism does, why it exists, what it consumes,
what it produces, and where its responsibility ends. It omits only incidental
implementation choices.

For example, the runtime document explains a restricted deterministic
evaluation environment, atomic term evaluation, topology-weighted
accumulation, named intermediate rates, and explicit missing-input failures. It
does not prescribe one expression language, standard library, function call,
or concrete evaluator implementation.

Likewise, the composition document explains state-space construction,
cross-model wiring, scenario resolution, numerical integration, event
boundaries, and solution persistence. It does not prescribe one solver package,
array library, tolerance, or method signature.

### Target architecture is not current implementation evidence

The canonical design sources describe a desired end state. The Plato package
README contains both durable contracts and target-state material, while the
integration-status document distinguishes landed, in-review, and planned work.

The generic library presents a coherent reference architecture. It does not
use implementation status as a portability criterion and does not state that
Plato currently provides every described layer. Provenance records which
claims are source contracts, target design, or status evidence.

### Canonical ownership stays separated

The two shared libraries own different contracts:

| Library | Owns | Does not own |
| --- | --- | --- |
| `agent-architecture` | Agent boundaries, delegation, orchestration, handoffs, retry, persistence, and resume | Mechanistic model semantics or numerical execution |
| `mechanistic-modeling` | Model semantics, evaluation, composition, solving, serialization, and validation layers | Agent sequencing, delegation, or workflow control |

Cross-links explain the integration point: an Act or Scene may author, review,
compose, simulate, or pass a versioned `MechanisticModel`, while the model
library defines the artifact being handled.

## Target Architecture

Implementation creates this reader-facing tree:

```text
assistants/shared/mechanistic-modeling/
|-- README.md
|-- data-layer.md
|-- runtime-layer.md
|-- composition-layer.md
`-- validation-boundaries.md
```

The documents have the following responsibilities:

| Document | Responsibility |
| --- | --- |
| `README.md` | Mental model, terminology, package-layer map, dependency direction, and relationships to agent architecture |
| `data-layer.md` | Persistent model artifact, entity semantics, identity, provenance, conservation, derived views, and construction boundary |
| `runtime-layer.md` | Deterministic evaluator, evaluation namespace, atomic rate contributions, accumulation, runtime failures, and transient state |
| `composition-layer.md` | Composer, wiring, scenarios, initial conditions, interventions, solver lifecycle, solution artifact, and persistence boundary |
| `validation-boundaries.md` | Ownership of data, composition, evaluator, solver, and scientific validation failures |

Implementation also adds audit metadata outside the canonical tree:

```text
docs/superpowers/specs/
`-- 2026-07-31-plato-mechanistic-modeling-provenance.yaml
```

### Package dependency direction

The generic package model is layered:

1. The data layer defines stable, serializable declarations.
2. The runtime layer reads those declarations and evaluates one model at a
   particular state.
3. The composition layer reads data and runtime contracts, connects one or
   more models, and advances the combined system through time.
4. Documentation, diagrams, code generation, and other exports are downstream
   views over the same structured data.

Foundational layers do not depend on downstream orchestration. A top-level
model facade may expose thin convenience operations, but substantive evaluator,
solver, composition, and export logic remains owned by the corresponding
layer. This keeps persistent model semantics understandable without loading a
runtime and keeps runtime mechanisms replaceable without changing the model
contract.

## Data Layer

### Mental model

Think of a mechanistic model as a collection of named processes. Each
`Interaction`:

- changes one or more targeted `Variable`s;
- may read additional external `Variable`s;
- contributes one or more atomic `MathTerm`s to each targeted variable; and
- carries enough identity, units, grouping, and provenance to be interpreted
  without a second authoritative representation.

The `MechanisticModel` aggregates interactions, standalone variables,
parameters, blocks, conservation declarations, and metadata. Equations,
variable registries, parameter registries, and topology are derived views over
those canonical declarations.

### Targeted and external variables

Variable roles are explicit at the interaction boundary:

- a targeted variable receives at least one `MathTerm` contribution from the
  interaction; and
- an external variable is read by the interaction but is not changed by it.

There is no exclusive variable ownership at the interaction or model level. A
variable may receive contributions from several interactions or several models.
Identity belongs to the `Variable` declaration, and all declarations of the
same variable must agree on the identity needed to compose them safely.

The model-level boundary is derived:

- targeted variables are the union of variables targeted by any interaction;
- external variables are variables read but not targeted anywhere in that
  model; and
- all variables are the union of targeted, external, and standalone variables.

### Atomic math terms

A `MathTerm` represents one attributable contribution to one target equation.
Additive right-hand-side behavior is represented as several terms rather than
one opaque compound expression.

The rate expression and its topology remain separate:

- the expression determines the contribution's magnitude from current values;
  and
- topology determines its direction, sign, or multiplicity for a particular
  target.

This separation makes equations, named rates, structural relationships,
conservation accounting, diagrams, and individual edits derivable without
parsing an opaque block of generated code.

### Blocks, parameters, conservation, and entity provenance

A `Block` is a domain-general grouping. It may represent a compartment, module,
population, spatial region, or another organizational boundary. Grouping does
not change the fundamental interaction and variable semantics.

A `Parameter` is a named quantity referenced by model mathematics. Its runtime
value may vary by scenario even when its identity, units, description, and
provenance remain stable.

A `ConservationLaw` is an explicit declaration of a relationship to track. V1
does not require automatic inference from topology. Conservation declarations
may include enough semantic information for later composition and diagnostic
layers to aggregate the relationship correctly.

Entity provenance is first-class metadata on model entities. It explains why a
block, variable, interaction, or term exists and where its supporting evidence
came from. The generic architecture does not prescribe a particular citation
schema, but non-trivial structural choices must have a stable place to carry
their source and justification.

Entity provenance is distinct from the extraction provenance manifest defined
later in this specification. Entity provenance travels with a scientific model;
extraction provenance audits how generic guidance was adapted into
`ballen-config`. Both surfaces require privacy review. Serialized references
must not expose personal data, confidential source content, access tokens,
private local paths, or uncurated raw research material.

### Persistence and serialization

The data layer is the durable serialization boundary. A persisted model should
carry:

- canonical entity identities and relationships;
- mathematical declarations and units;
- blocks, parameters, and conservation declarations;
- provenance and descriptive metadata; and
- a schema version or equivalent compatibility marker.

The model does not persist a second equation object or generated executable as
another authority. Those forms are derived when needed. Scenario-specific
parameter values, authoritative initial conditions, solver settings, and
runtime caches do not become part of model identity merely because they are
needed to run it.

### Construction boundary

Data-layer construction validates invariants that can be known from one model:

- entity identity is stable and consistent;
- targeted and external roles are unambiguous;
- each `MathTerm` is atomic and attached to a valid target;
- repeated variable declarations agree;
- blocks and conservation declarations refer to known entities; and
- the artifact can report structural or mathematical incompleteness.

Construction deliberately does not require every external variable to be
resolved. A model authored in isolation cannot know every future peer or
scenario. Wiring belongs to composition.

## Runtime Layer

### Evaluator responsibility

The runtime evaluates one `MechanisticModel` at one point in time. It receives:

- current values for variables;
- runtime values for required parameters and constants; and
- the model's interactions and atomic math terms.

The evaluator creates a restricted, deterministic name environment from
approved mathematical operations, parameters, and current variable values. It
then walks the model's interactions and evaluates each atomic term.

For each term, the evaluator:

1. computes the term's rate magnitude;
2. records a stable named intermediate contribution;
3. applies the term's topology for its target; and
4. accumulates that weighted contribution into the target variable's change.

The result is both a per-variable change map and a named rate ledger. The
change map drives numerical integration. The ledger supports diagnostics,
conservation analysis, documentation, and diagrams without becoming a second
wiring mechanism.

### Determinism and identity

Stable entity and term identities make evaluator traversal and named outputs
reproducible. Function expressions, current-state keys, diagnostics, and
derived documentation must resolve to the same variable identities.

The architecture requires deterministic semantics, not one particular
interpreter. A future compiled evaluator may replace an interpreted evaluator
for performance as long as it preserves the same inputs, outputs, errors, and
named contributions.

### Runtime failures

Missing names do not silently become zero. An absent variable or parameter
indicates invalid wiring, incomplete scenario data, or an evaluator defect and
must fail with enough interaction, term, and variable context to diagnose the
problem.

The runtime also distinguishes:

- an expression that cannot be evaluated;
- a result that is undefined or non-finite;
- a name collision that makes interpretation ambiguous; and
- a model that is structurally valid but not ready for execution.

These are runtime or upstream configuration failures. They are not scientific
validation results.

### Transient runtime state

Evaluation namespaces, callbacks, compiled expressions, caches, and in-flight
rate ledgers are transient. They may be reconstructed from the serialized model
and scenario. Persisting them as part of the model would couple durable data to
one runtime implementation and create another synchronization problem.

## Composition Layer

### Composer responsibility

A `MechanisticModelComposer` turns one or more models plus scenario data into a
runnable system. It is the boundary that has enough context to resolve
relationships a standalone model cannot know.

The composer receives:

- a named collection of `MechanisticModel` artifacts;
- runtime parameter values;
- scenario-level initial-condition overrides;
- interventions or other supported scenario inputs; and
- solver configuration.

At construction, it:

1. builds the union of all targeted variables;
2. verifies shared variable identities are compatible;
3. resolves every external variable from a peer model or declared scenario
   input;
4. verifies required parameter coverage;
5. records variables with contributions from several models; and
6. aggregates conservation declarations and diagnostic metadata.

Only targeted variables enter the composed state vector. A variable that is
external-only across the full composition is an exogenous input, not a hidden
state. It must be supplied by a declared constant, parameter, or supported
time-varying scenario input. Initial-condition overrides do not satisfy
external reads. Every referenced external input must resolve during composition
construction; otherwise composition fails before evaluation begins.

Multiple models targeting the same variable is valid and often expected. The
composed change for that variable is the natural sum of every contributing
model's result. An informational diagnostic may call attention to shared
contributors without treating them as an ownership conflict.

### Scenario boundary

Initial conditions and interventions describe a run, not the durable identity
of a model. A model may carry a default initial value, but the scenario may
override it without creating a new model artifact.

The generic resolution order is:

1. an explicit scenario override;
2. one compatible model-provided default; and
3. an explicit domain policy recorded in the composition specification.

If a required targeted state has no resolved initial value and no explicit
domain policy permits a fallback, composition fails. Conflicting model defaults
also fail unless the scenario supplies an authoritative override. A fallback
must never be silently invented by the generic runtime.

Discrete interventions create state changes at known boundaries. Continuous
inputs and time-varying covariates may use different numerical mechanisms, but
they belong to the same scenario-input family and remain outside model
identity.

### Solver responsibility

The solver advances the composed state through time by repeatedly requesting
the combined per-variable change from the composer. It owns numerical
integration mechanics, including:

- time grids and integration settings;
- event or intervention boundaries;
- segmenting and restarting around discontinuous state changes;
- propagation of solver diagnostics; and
- explicit reporting when integration cannot complete reliably.

Solver settings are runtime scenario configuration. They do not rewrite the
model's interactions or equations.

One-model and multi-model simulations follow the same public composition path.
A one-model composition is a normal case, not a separate shortcut with a
different validation or diagnostic surface.

"Public composition path" is an architectural entry boundary, not a required
method name or package API. Implementations may expose it through any interface
that preserves the same validation, scenario, solver, and diagnostic behavior.

### Model solution

The solver returns a `ModelSolution` containing the durable core of a run:

- sampled times;
- named state trajectories and units;
- state ordering or equivalent stable identity information;
- applied interventions; and
- solver outcome metadata needed to interpret the result;
- model and composition identities plus schema versions;
- the resolved initial conditions, parameter values, and scenario inputs, or
  immutable references and integrity digests for them; and
- runtime compatibility information needed to understand the evaluation and
  solver semantics.

Diagnostics, named-rate views, and conservation or mass-balance reports may be
computed lazily from the solution and its originating composition. The core
trajectory can be serialized without persisting runtime callbacks or closures.
Derived diagnostics can be persisted as snapshots or recomputed later when the
original model, scenario, and compatible runtime remain available.

A serialized `ModelSolution` must remain independently interpretable even when
it is not independently rerunnable. If it stores references instead of complete
model and scenario snapshots, those references must be immutable, resolvable,
and integrity-checked. A solution artifact records what happened; a
reproducibility bundle contains everything required to run it again.

### Composition serialization

The composition specification is data. It should be possible to serialize the
chosen models, parameter values, scenario defaults, interventions, and relevant
solver configuration sufficiently to reproduce a run.

Serialization excludes transient evaluator state, live solver objects,
callbacks, closures, and caches. Those objects are reconstructed at execution
time.

A reproducibility bundle therefore consists of versioned model artifacts, the
complete composition or scenario specification, resolved initial conditions
and parameters, interventions, solver configuration, runtime compatibility
information, and integrity metadata. The persisted solution core may accompany
that bundle as the expected or historical result. A `ModelSolution` alone is a
result artifact; it becomes a rerunnable bundle only when all required inputs
and compatible execution semantics are included or immutably referenced.

## Validation Boundaries

Validation is layered because no single object has enough context to establish
every form of correctness.

| Layer | Owns | Representative failures |
| --- | --- | --- |
| Data construction | Intra-model identity, role, atomicity, references, and completeness | Conflicting variable identity, invalid target, compound term, unknown block |
| Composition construction | Cross-model identity, wiring, parameter coverage, and scenario compatibility | Unresolved external variable, incompatible shared variable, missing parameter |
| Runtime evaluation | Name resolution and deterministic term evaluation | Missing name, ambiguous namespace, invalid expression, non-finite rate |
| Solver execution | Numerical integration and intervention handling | Integration failure, invalid event boundary, unstable or incomplete trajectory |
| Scientific validation | Dimensional, conservation, behavioral, causal, and plausibility claims | Unit mismatch, conservation residual, impossible state, implausible response |

Passing an earlier layer does not imply passing a later one:

- a structurally valid model may have unresolved external inputs;
- a valid composition may fail during evaluation;
- an evaluable system may fail numerical integration; and
- a completed trajectory may still be scientifically invalid.

Error messages should identify the responsible layer and preserve enough model,
interaction, variable, and term context for correction without exposing runtime
internals as part of the public contract.

## Relationship to Agent Architecture

The mechanistic-modeling library remains usable from deterministic applications,
interactive tools, notebooks, services, or agentic workflows.

When agents are involved:

- an Act may author or refine a `MechanisticModel`;
- a Scene may validate one layer and retry the smallest failed unit;
- a handoff may carry a versioned model, composition specification, or solution
  reference;
- persistence and resume rules govern how those artifacts are checkpointed;
  and
- the mechanistic-modeling library remains the authority for artifact
  semantics.

The agent-architecture library remains the authority for orchestration. The
cross-links are informative, not an ownership merge.

## Source Authority and Disposition

The extraction uses prose sources for concepts and implementation sources only
for verification.

| Source | Manifest class | Authority role | V1 treatment |
| --- | --- | --- | --- |
| `QSP Wizard Meets Mechanistic Model` | Prose source | Canonical desired architecture and cross-layer intent | Adapt overview, goals, boundaries, and layer relationships |
| `Data layer` companion page | Prose source | Canonical target data-layer design | Adapt terminology, role split, atomic terms, provenance, serialization, and construction boundary |
| `Runtime layer` companion page | Prose source | Canonical target runtime design | Adapt evaluator, deterministic namespace, named contributions, transient state, and failures |
| `Composition layer` companion page | Prose source | Canonical target composition design | Adapt composer, solver, scenarios, solutions, and serialization boundary |
| `src/plato/mechanistic_model/README.md` | Prose source | Package contract and durable mental model | Adapt process-centered metaphor, entity semantics, derived views, and validation boundaries |
| `src/plato/mechanistic_model/INTEGRATION_STATUS.md` | Verification evidence | Current-versus-target implementation status | Qualify implementation status and prevent unsupported current-state claims |
| `src/plato/crate/mechanistic_model/README.md` | Prose source | Historical compatibility context | Corroboration only; exclude legacy API and migration mechanics |
| AGTC-1038 | Verification evidence | Delivery and dependency status | Record status only; exclude ticket language and identifiers from reader-facing documents |

Selected source and test files may be used to check whether prose describes
implemented or planned behavior. They do not become generic prose sources, and
their APIs are not copied into the library.

## Extraction Boundary

The extraction is concept-based rather than file-copy-based. One source may
inform several destination documents, and one destination may consolidate
several sources.

### Preserve

- the named entity and layer vocabulary;
- the process-centered mechanistic-model metaphor;
- targeted versus external variable roles;
- atomic math terms and separate topology;
- derived equations, topology, registries, and named rates;
- explicit blocks, parameters, conservation, and provenance;
- deterministic evaluator inputs, outputs, and failures;
- composer wiring and natural additive semantics;
- solver and intervention lifecycle;
- model, composition, and solution serialization boundaries;
- generic package ownership and dependency direction; and
- layered validation responsibilities.

### Adapt

- exact schema constraints into stable identity and consistency contracts;
- concrete safe-evaluation mechanics into a restricted deterministic
  evaluation environment;
- concrete solver behavior into generic integration and intervention semantics;
- language-specific serialization into durable versus transient state;
- framework models and validators into construction and failure boundaries;
- QSP validation gates into generic scientific-quality categories; and
- Plato package layout into layer ownership and dependency direction.

### Exclude

- executable source code and copied examples;
- field declarations, exact container types, signatures, decorators, imports,
  and exception classes;
- concrete math, array, validation, and solver libraries;
- hard-coded defaults, tolerance values, performance thresholds, and naming
  formats;
- QSP, PK/PD, TMDD, ecological, or other domain worked examples;
- Plato, AMi, Avogadro, and QSP Autopilot product or package references;
- tickets, merge requests, branch names, cutover instructions, and migration
  state;
- local filesystem paths and machine-specific configuration;
- authentication, credentials, trust, sessions, histories, and generated
  plugin state; and
- unsupported assumptions, inferred future APIs, and unreviewed V2 features.

## Provenance

Implementation adds:

`docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-provenance.yaml`

The manifest is audit metadata, not a runtime catalog. It records:

- the Plato repository and pinned source revision;
- the canonical design source titles and retrieval dates;
- the design document governing the extraction;
- every source and its authority role;
- every destination document and its contributing sources;
- current-contract, target-design, or status-evidence classification;
- transformation notes and explicit exclusions; and
- the final portability and privacy review result.

### Manifest schema

The manifest has these top-level fields:

- `schema_version` for the audit format;
- `design` for this specification's repository-relative path;
- `source_repositories` for repository name, pinned revision, and review date;
- `design_sources` for canonical page title, retrieval date, and a
  privacy-reviewed internal locator;
- `sources` for prose source entries;
- `verification_evidence` for code, tests, or status files used only to check
  claims;
- `destinations` for reader-facing document entries; and
- `review` for portability, privacy, and final approval results.

Each prose source entry records:

- a stable `id`;
- `kind`: `repository_document` or `design_page`;
- either an explicitly named repository plus repository-relative `path`, or a
  privacy-reviewed internal `locator`, according to source kind;
- `authority`: `target_design`, `package_contract`, or `corroboration`;
- `disposition`: `adapt`, `qualify`, `exclude`, or `verify_only`;
- destination IDs when the source contributes reader-facing concepts; and
- concise transformation, status, and exclusion notes.

Each destination entry records:

- its repository-relative `path` under `ballen-config`;
- document kind and authority status;
- contributing source IDs and their roles;
- transformation notes;
- explicit exclusions; and
- semantic and privacy review status.

Verification evidence is separate from prose sources. Repository-file evidence
records a pinned repository, relative path, revision, and the specific claim or
status boundary checked. Work-item evidence records a privacy-reviewed internal
locator, review date, and the status boundary checked. Verification evidence
cannot be listed as a source of generic wording and does not need a
destination.

Repository paths are relative POSIX paths with no traversal and are interpreted
against an explicitly named repository root. No absolute local path is valid.
Internal locators remain in audit metadata, contain no authentication material,
and do not appear in the canonical reader-facing tree. Every prose source
appears exactly once in the source inventory, and every destination document
has exactly one provenance entry even when it consolidates several sources.

## Extraction Workflow

1. Pin one clean Plato revision and record source retrieval dates.
2. Record every approved source and authority role in provenance.
3. Build destination outlines from the approved layer boundaries.
4. Draft the reader-facing documents from concepts rather than source text.
5. Preserve terminology while removing implementation-specific APIs and
   internal references.
6. Keep target design distinct from verified current behavior.
7. Cross-link mechanistic modeling and agent architecture without merging their
   authority.
8. Run structural, privacy, link, Markdown, and semantic verification.
9. Confirm Plato is unchanged and the `ballen-config` working copy is clean
   after recording each logical change.

## Failure and Ambiguity Handling

- When target design conflicts with current implementation, the generic
  architecture follows the approved target design and provenance records the
  distinction.
- When the package README and a canonical companion page differ, the companion
  page owns the target layer and the README remains contract or corroborating
  evidence.
- When a concrete mechanism contains a durable architectural contract, retain
  the contract in plain text instead of deleting the mechanism entirely.
- When abstraction would remove an important input, output, failure, or
  responsibility boundary, keep that boundary and remove only incidental API
  detail.
- When a claim is unsupported or source status is ambiguous, omit or qualify
  it rather than inferring a generic rule.
- Framework-specific guidance does not leak into the generic core.
- Export and legacy behavior beyond derived-view principles remains deferred
  until separately reviewed.

## Validation Strategy

### Structural tests

Implementation adds focused coverage under
`tests/assistants/test_mechanistic_modeling.py` for machine-checkable
invariants:

- the expected five-document library tree exists;
- no symlinks or special files occur in the managed tree;
- the root index links every child document exactly once;
- all local relative links resolve;
- each destination document has exactly one provenance entry;
- each prose source has one explicit authority role and disposition;
- each verification-evidence entry names the exact claim or status boundary it
  checks;
- required terminology and layer headings are present;
- the layer dependency order is represented consistently;
- the mechanistic-modeling and agent-architecture libraries cross-link without
  duplicating authority;
- reader-facing documents contain no Plato paths, package imports, ticket or
  merge-request identifiers, internal source links, or prohibited sensitive
  state; and
- reader-facing documents contain no executable source-code examples copied
  from Plato.

### Manual semantic review

Manual review verifies boundaries that substring tests cannot establish:

- `Interaction`, `Variable`, `MathTerm`, and `Block` retain their intended
  meanings;
- targeted and external roles are distinct;
- no interaction or model receives false exclusive ownership of a variable;
- evaluator, solver, serialization, and package mechanics remain explanatory
  rather than disappearing;
- implementation-neutral prose does not prescribe a hidden Python API;
- data, composition, runtime, solver, and scientific validation remain
  separate;
- scenario values and interventions do not become model identity;
- one-model and multi-model execution share one composition path;
- persistent artifacts are distinct from transient callbacks, caches, and live
  runtime objects;
- target architecture is not presented as verified current Plato behavior;
  and
- agent architecture and mechanistic modeling remain parallel authorities.

### Fresh verification

Before delivery, run:

- focused mechanistic-modeling structural tests;
- the complete repository test suite;
- configured Markdown lint;
- local relative-link validation;
- repository lint and type checks required by current configuration;
- a Markdown-only range and diff review;
- `jj diff` and clean working-copy checks; and
- before-and-after Plato revision and status checks.

## Delivery and Change Management

The design specification and provenance manifest remain planning and audit
artifacts. The reader-facing library is one cohesive reference set and should
be reviewed as a unit, even if implementation records logical commits for the
tree, layer documents, provenance, and tests.

Implementation planning must decide the exact commit and bookmark sequence,
but it must preserve these gates:

1. no reader-facing document lands without provenance;
2. no target-state claim is presented as current implementation evidence;
3. focused verification runs after each coherent slice;
4. full verification runs before publication; and
5. Plato remains read-only throughout the work.

## Success Criteria

V1 is complete when:

1. the five-document mechanistic-modeling library exists as a sibling of
   `agent-architecture`;
2. data, runtime, composition, solver, serialization, package, and validation
   mechanics are explained in plain implementation-neutral prose;
3. the approved terminology and responsibility boundaries are preserved;
4. agent architecture and mechanistic modeling have explicit but non-owning
   cross-links;
5. every source and destination has auditable provenance;
6. reader-facing documents contain no copied source code, internal
   implementation details, or sensitive state;
7. current and target claims remain distinguishable;
8. structural, Markdown, link, privacy, and full repository checks pass;
9. the final diff contains only approved `ballen-config` changes; and
10. Plato's revision and clean working-copy state are unchanged.
