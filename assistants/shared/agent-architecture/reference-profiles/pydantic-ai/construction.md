# PydanticAI Agent Construction

> **Status:** Conditional reference profile. Apply this document only after a
> repository selects PydanticAI.

PydanticAI supports both startup-fixed agent definitions and intentionally
dynamic construction. Prefer the stable form unless request-specific variation
is part of the product contract.

## Fixed and Dynamic Construction

Requirement: A long-lived service SHOULD construct a startup-fixed `Agent` when its instructions, tools, dependency type, and output type are stable.

Rationale: One visible construction point makes the effective agent contract
easy to review and avoids rebuilding an identical graph for every request.

Scope: Services whose agent definition does not vary by request or run.

Exceptions: Use a dynamic factory when the model, provider, instructions,
tools, or output schema intentionally depend on validated run input.

A dynamic factory is an explicit architecture choice, not a convenience for
hiding configuration. It returns a fully configured `Agent[Deps, Output]` and
keeps construction separate from execution.

## Model and Provider Selection

Requirement: Agent construction MUST make model and provider selection explicit through repository-owned configuration.

Rationale: Explicit selection preserves testability and lets operators audit
which external service a run invokes without prescribing one universal model.

Scope: Fixed constructors and dynamic factories.

Exceptions: A caller can supply an already validated model object when the
public service contract deliberately delegates selection to that caller.

This profile does not prescribe a model name, provider, credential source, or
environment layout.

## Typed Results

Requirement: An agent that returns application data SHOULD declare a structured result model and validate it before crossing the service boundary.

Rationale: A typed `output_type` separates model-generated data from transport
text and gives callers a stable contract.

Scope: Results consumed by code, persisted state, or another workflow stage.

Exceptions: Conversational text can remain text when no downstream component
depends on a structured shape.

## Construction-Time and Run-Time Inputs

Requirement: Agent construction MUST keep construction-time configuration distinct from run-time input and dependencies.

Rationale: Stable instructions and tools are easier to review when user input,
request metadata, and live resources enter only through the run call.

Scope: Agent constructors, factories, and public execution functions.

Exceptions: Validated request data can shape a dynamic factory when the
variation itself is documented as part of the service contract.

## Service Errors

Requirement: A public execution function MUST perform exception translation from PydanticAI failures into repository-owned error types.

Rationale: Callers should not need framework-specific exception knowledge to
decide whether to retry, report, or stop.

Scope: Boundaries between agent infrastructure and application services.

Exceptions: Internal diagnostic helpers can expose original exceptions when
they are not public service interfaces and preserve the causal chain.

## Test Seams

Requirement: Construction SHOULD provide a test seam for substituting the model and dependency values without changing production instructions or tools.

Rationale: Deterministic substitutes let tests exercise validation, error
mapping, and orchestration without a live provider.

Scope: Repository-owned constructors, factories, and service entry points.

Exceptions: A pure configuration snapshot test can inspect construction output
without executing the agent.

## References

- [PydanticAI agents](https://ai.pydantic.dev/agents/)
- [PydanticAI models](https://ai.pydantic.dev/models/overview/)
- [PydanticAI testing](https://ai.pydantic.dev/testing/)
- [PydanticAI release history](https://github.com/pydantic/pydantic-ai/releases)
