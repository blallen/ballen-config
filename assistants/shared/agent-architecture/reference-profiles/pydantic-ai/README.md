# PydanticAI Reference Profile

> **Status:** Conditional reference profile. Adopt this guidance only when a
> repository has selected PydanticAI or a compatible integration.

This profile maps the framework-neutral core to PydanticAI implementation
choices. It does not replace the [framework-neutral core](../../core/architecture-levels.md),
the [delegation contracts](../../delegation/isolation-matrix.md), or local
repository policy.

## Reviewed Versions

- pydantic-ai-slim 2.18.0
- subagents-pydantic-ai 0.2.7
- Reviewed on 2026-07-31

Version-sensitive guidance is tied to these reviewed releases. Repositories
using a different version need to verify symbols and behavior against that
version's official documentation and release history.

## Adoption Boundary

Requirement: A repository adopting this profile MUST record its selected PydanticAI package version and the local configuration that constructs each agent.

Rationale: Construction behavior, tool registration, and delegated-run features
can change between package releases.

Scope: Repositories that implement agents with PydanticAI.

Exceptions: Exploratory examples can state a temporary version inline when
they are not installed or published as repository guidance.

Repository configuration takes precedence over this profile when it defines a
more specific construction, dependency, model, or lifecycle contract. Such a
local override still needs to satisfy the framework-neutral core requirements.

## Profile Documents

- [Construction](construction.md) covers fixed agents, dynamic factories,
  configuration, outputs, and test seams.
- [Services and dependencies](services-and-dependencies.md) covers
  `RunContext`, typed dependencies, public service boundaries, and resources.
- [Tools and capabilities](tools-and-capabilities.md) covers registration,
  scoped authority, shared mutation, and dynamic subagents.

## Core and Profile Responsibilities

The core defines portable outcomes: explicit inputs and outputs, bounded
authority, deliberate context transfer, observable errors, and owned
lifecycle. This profile explains how PydanticAI types and APIs can realize
those outcomes. Package-specific symbols belong here, not in core documents.

## References

- [PydanticAI installation documentation](https://ai.pydantic.dev/install/#slim-install)
- [PydanticAI release history](https://github.com/pydantic/pydantic-ai/releases)
- [subagents-pydantic-ai documentation](https://github.com/vstorm-co/subagents-pydantic-ai#readme)
- [subagents-pydantic-ai release history](https://github.com/vstorm-co/subagents-pydantic-ai/releases)
