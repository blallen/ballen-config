# Agent Architecture Reference Profiles

> **Status:** Conditional reference profile index. Profiles become authoritative
> only when a repository explicitly adopts the corresponding technology or use
> case.

Reference profiles translate portable architecture requirements into
technology-specific guidance. The core contracts still apply after a profile
is adopted; a profile cannot weaken their boundaries.

## Adoption

Requirement: A repository adopting a profile MUST record the decision, the reviewed package version, and any local overrides beside its executable configuration.

Rationale: Explicit adoption prevents optional framework guidance from being
mistaken for a universal repository standard.

Scope: Any repository that relies on one of the profiles below.

Exceptions: A throwaway experiment can cite the profile inline when it does not
install shared guidance or claim production support.

Repository configuration takes precedence when it is more specific. The local
choice still needs to preserve the framework-neutral contracts for authority,
state, errors, lifecycle, and delegation.

## Available Profiles

- [PydanticAI](pydantic-ai/README.md) maps agent construction, dependencies,
  tools, and delegated runs to reviewed PydanticAI packages.
- [Logfire](logfire.md) defines bounded, privacy-reviewed observability for
  agent runs.
- [Streamlit demo apps](streamlit-demo-apps.md) defines a small prototyping
  pattern and the boundary between direct imports and MCP.
