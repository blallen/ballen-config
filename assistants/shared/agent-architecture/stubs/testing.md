# Agent Testing Outline

> **Status:** Non-normative draft. This stub preserves only source-supported
> testing layers; it does not define a compliance standard.

The layers below identify distinct kinds of evidence that an agent component
can need. Their exact application depends on architecture category, effects,
risk, and repository policy.

## Unit

Exercise deterministic functions in isolation: validation, mapping, transition
policy, error classification, prompt assembly, and service logic. Model and
external-service behavior can use controlled substitutes.

## Contract

Check stable boundaries such as tool schemas, MCP requests and responses,
handoff models, persistence records, and public service results. These tests
focus on producer-consumer agreement rather than implementation internals.

## Integration

Connect the framework adapter to representative dependency implementations and
verify construction, tool registration, resource lifecycle, and translated
errors across the boundary.

## Evaluation

Measure behavioral quality separately from software correctness. Candidate
dimensions include task success, groundedness, tool selection, safety,
efficiency, and reproducibility, selected for the component's actual purpose.

## End-to-end

Exercise a representative user journey across the real component boundaries,
including orchestration and delegated work where applicable. Keep fixtures and
external effects bounded and observable.

## Unresolved Design Inputs

The unresolved design inputs include acceptance criteria and coverage thresholds.
The source material does not establish numeric values, required suites by maturity
level, fixture ownership, evaluation dataset governance, or release-blocking
policy. Those decisions need an explicit design and owner before this stub can
become normative guidance.
