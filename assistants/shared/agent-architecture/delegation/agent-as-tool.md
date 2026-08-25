# Agent as Tool

Agent-as-tool delegation exposes a predeclared specialist through a typed tool boundary.
The parent knows the specialist's purpose and contract at construction
time, even though the model can decide whether and when to call it.

## Static specialist contract

The tool accepts explicit input, starts a separately bounded specialist run,
and returns structured output. The specialist can use a different model,
instructions, dependencies, tools, or permissions from the parent.

### Declare the specialist statically

Requirement: An agent-as-tool capability MUST bind a named specialist and its
typed input and output contract before the parent run can invoke it.

Rationale: A predeclared surface is reviewable, testable, and suitable for
stable capabilities whose purpose does not change at runtime.

Scope: Fixed specialist Agents exposed to a parent as callable tools.

Exceptions: Runtime-created specialists follow the dynamic-subagent contract
instead.

## Isolation defaults

The delegated call is a separate run:

- message history is not inherited unless selected messages are mapped into
  the specialist input;
- dependencies are not inherited unless the caller constructs or maps a child
  dependency container;
- resources are not inherited unless a named resource-sharing contract grants
  them; and
- permissions are not inherited unless the child capability set grants them.

### Make sharing explicit

Requirement: A parent MUST map every shared context value, dependency,
resource, tool, and permission into the specialist boundary explicitly.

Rationale: Implicit inheritance makes the child's effective context and
authority depend on hidden parent state.

Scope: Every agent-as-tool invocation.

Exceptions: Immutable process-wide utilities with no authority or state can be
available to both runs without per-call mapping.

## Input and structured output

Input should contain the complete task, relevant evidence, constraints, and
selected context. The result should use a stable variant for success, expected
non-completion, or partial failure. Do not require the parent to parse a child
transcript to discover the result.

### Keep the child transcript private by default

Requirement: An agent-as-tool call SHOULD return structured output rather than
automatically appending the full child message history to the parent.

Rationale: A bounded result preserves context isolation and controls token and
privacy costs.

Scope: Parent consumption of delegated results.

Exceptions: A review or debugging tool can return a selected transcript when
the transcript is part of its declared output and is safe to share.

## Timeout, cancellation, and error translation

The tool boundary owns timeout, cancellation propagation, and error translation
between the child run and parent-visible result. Cancellation is a request to
stop, not proof that every downstream effect rolled back.

### Bound delegated execution

Requirement: An agent-as-tool wrapper MUST define timeout, cancellation, and
error translation behavior for the specialist run.

Rationale: The parent needs deterministic recovery when a child blocks, fails,
or finishes after the parent no longer needs its result.

Scope: Synchronous and background specialist invocation.

Exceptions: A proven bounded pure specialist can rely on the parent's documented
run deadline when the same bound applies to both.

## Architecture category

Calling a fixed specialist does not make the parent an Orchestrator. The parent
remains an Agent when it owns no general worker selection, lifecycle,
concurrency, or cross-specialist coordination policy.

### Classify by coordination responsibility

Requirement: A system SHOULD classify a fixed agent-as-tool call independently
from its overall Workflow, Agent, or Orchestrator category.

Rationale: Delegation mechanism describes how work is invoked; architecture
category describes which control responsibility the system owns.

Scope: Architecture diagrams, README descriptions, and design reviews.

Exceptions: The parent is an Orchestrator when coordination becomes a
first-class responsibility even if every specialist was known at startup.

## When to use

Choose agent-as-tool delegation for stable specialists with reviewable
capability boundaries, repeatable typed interfaces, and no need for runtime
creation. Prefer an ordinary service tool when the delegated behavior does not
need a separate model run.
