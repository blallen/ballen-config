# Streamlit Agent Demo Apps

> **Status:** Conditional reference profile. Adopt this guidance only for a
> repository that uses Streamlit to prototype or demonstrate an agent.

- streamlit 1.54.0
- Reviewed on 2026-07-31

A demo app shortens the feedback loop around agent behavior. It is a thin
presentation adapter, not a second implementation of agent or service logic.

## Minimal Demo Shape

Requirement: A Streamlit demo MUST keep input, invocation, and result rendering visible in one self-contained flow.

Rationale: A reviewer can understand and run a small demo without reconstructing
hidden state or navigating production integration code.

Scope: Local prototypes, behavior reviews, and lightweight stakeholder demos.

Exceptions: A multi-step interaction can use session state when each stored
field and reset condition is explicit.

## Runnable Snippet

The following is a **Runnable snippet** after replacing the example service
module with the repository's public agent entry point:

```python
import streamlit as st

from my_demo.agent_service import run_agent

prompt = st.text_area("Prompt")
if st.button("Run") and prompt:
    with st.spinner("Running agent"):
        result = run_agent(prompt)
    st.write(result)
```

The direct import keeps the UI thin: gather input, call one public service
function, and render its domain result or translated error.

## Direct import versus MCP

Requirement: A demo SHOULD use a direct import when the UI and agent service share one repository, one runtime, and one trust boundary.

Rationale: A direct import minimizes setup and gives the fastest local feedback
when no process boundary is required.

Scope: In-process prototypes whose dependencies can be created by the local
service entry point.

Exceptions: Use [MCP](../core/mcp.md) when the demo is specifically evaluating
a tool boundary or must call an independently owned process or service.

Requirement: An MCP-backed demo SHOULD invoke a stable tool contract rather than reproduce the remote agent's construction locally.

Rationale: Keeping the boundary real lets the demo test the same input, output,
error, and authority contract as other MCP clients.

Scope: Demos crossing a deliberate process or ownership boundary.

Exceptions: A visual-only mock can substitute a deterministic local result when
it is clearly labeled and does not claim end-to-end behavior.

## Illustrative Snippet

The following is an **Illustrative snippet** showing the shape of an MCP call;
the client API depends on the repository's selected MCP implementation:

```python
result = mcp_client.call_tool("run_agent", {"prompt": prompt})
st.write(result)
```

## Sample Labels

Requirement: Every code sample MUST be labeled as a Runnable snippet or an Illustrative snippet.

Rationale: Readers need to know whether a sample can execute as shown or only
communicates architecture and control flow.

Scope: Python, configuration, and pseudocode in a demo guide.

Exceptions: A one-line API signature can be described inline when it is not
presented as a complete sample.

## Limits

Requirement: A demo guide MUST remain separate from production deployment and operational architecture guidance.

Rationale: Prototype ergonomics do not establish requirements for a durable,
multi-user, or internet-facing service.

Scope: This profile and repository demo READMEs derived from it.

Exceptions: A demo can link to separately owned operational documentation
without duplicating it.

## References

- [Streamlit documentation](https://docs.streamlit.io/)
- [Streamlit 2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
