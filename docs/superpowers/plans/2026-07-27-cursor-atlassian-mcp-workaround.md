# Cursor Atlassian MCP Workaround Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproduce the secret-free Atlassian Cursor workaround only for the work profile while continuing to reject and report every other local MCP configuration.

**Architecture:** Store one reviewed JSON document containing only Atlassian's OAuth-backed HTTPS endpoint. The Cursor adapter installs it as an exact mode-`0600` managed file for work-profile runs, while a shared strict validator lets configuration, diagnostics, and tracked-tree policy recognize only that document. Default-profile runs and any altered or additional MCP server remain outside desired state.

**Tech Stack:** Python 3.12, Pydantic 2.8 inventory models, strict JSON decoding, Pytest, Jujutsu.

---

### Task 1: Lock the exception behind failing contract tests

**Files:**
- Modify: `tests/assistants/test_models.py`
- Modify: `tests/assistants/test_cursor.py`
- Modify: `tests/assistants/test_checks.py`
- Modify: `tests/test_policy.py`

- [x] **Step 1: Add the inventory and profile-selection tests**

Add tests requiring the exact destination `.cursor/mcp.json` to be accepted while other MCP-like managed paths remain rejected. Extend the Cursor inventory contract with a `cursor.atlassian-mcp` work-only file resource, then require `configuration()` to emit:

```python
ManagedFileSpec(
    id="cursor-atlassian-mcp",
    source=repo_root / "assistants/cursor/atlassian-workaround.json",
    destination=Path(".cursor/mcp.json"),
    method=ApplyMethod.COPY,
    mode=0o600,
    component="cursor",
    validator_id="json",
)
```

only when `"work"` is present in the resolved profiles.

- [x] **Step 2: Add exact diagnostic tests**

Replace the existence-only Cursor MCP test with parameterized behavior proving:

```python
APPROVED = {
    "mcpServers": {
        "atlassian": {
            "type": "http",
            "url": "https://mcp.atlassian.com/v1/mcp/authv2",
        }
    }
}
```

is accepted for the work profile, while default-profile use, malformed JSON, duplicate keys, altered URLs, extra keys, and extra servers all retain the redacted `cursor.legacy-mcp` finding.

- [x] **Step 3: Add the narrow policy exception tests**

Require `assistants/cursor/atlassian-workaround.json` with the exact approved document to pass tracked-tree policy. Keep `.cursor/mcp.json`, any other path containing MCP declarations, and any mutation of the approved source rejected as `forbidden-mcp`.

- [x] **Step 4: Run the focused tests and verify RED**

Run:

```bash
rtk uv run --frozen pytest \
  tests/assistants/test_models.py \
  tests/assistants/test_cursor.py \
  tests/assistants/test_checks.py \
  tests/test_policy.py -q
```

Expected: failures show that the exact destination is still forbidden, the work adapter emits no managed MCP spec, the diagnostic still warns on the approved document, and policy still rejects the reviewed source.

### Task 2: Implement the exact managed workaround

**Files:**
- Create: `assistants/cursor/atlassian-workaround.json`
- Create: `src/ballen_config/assistants/cursor_mcp.py`
- Modify: `assistants/inventory.yaml`
- Modify: `src/ballen_config/assistants/models.py`
- Modify: `src/ballen_config/assistants/cursor.py`
- Modify: `src/ballen_config/assistants/checks.py`
- Modify: `src/ballen_config/assistants/orchestrator.py`
- Modify: `src/ballen_config/policy.py`

- [x] **Step 1: Add one strict document validator**

Define immutable typed constants for the approved document and source path. Implement:

```python
def is_approved_atlassian_mcp(source: bytes) -> bool:
    try:
        document = strict_json_loads(source)
    except (StrictJsonError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return document == APPROVED_ATLASSIAN_MCP
```

No diagnostic may include source bytes or decoded values.

- [x] **Step 2: Add the reviewed source and inventory declaration**

Create the canonical JSON file with only the Atlassian HTTP server. Add `cursor.atlassian-mcp` as a work-only Cursor file resource targeting `.cursor/mcp.json`. Permit only that exact destination through the managed-state path guard.

- [x] **Step 3: Add the work-profile managed spec**

Validate the reviewed source before producing configuration. Append an exact-copy `ManagedFileSpec` only for work-profile Cursor runs; default and skipped-Cursor runs remain unchanged.

- [x] **Step 4: Narrow diagnostics and policy**

Pass resolved profiles into `assistant_checks`. Suppress `cursor.legacy-mcp` only when the work profile is active and the live bytes pass the strict validator. In policy, exempt only the canonical source path when its bytes pass the same validator; every other match keeps the existing rule.

- [x] **Step 5: Run the focused tests and verify GREEN**

Run the Task 1 command. Expected: all focused tests pass with no warnings or unexpected output.

### Task 3: Document, verify, converge, and commit

**Files:**
- Modify: `README.md`
- Modify: `docs/manual-steps.md`
- Modify: `docs/superpowers/specs/2026-07-25-laptop-migration-bootstrap-design.md`

- [x] **Step 1: Document the constrained exception**

Explain that Playwright and GitLab remain excluded, while the work profile temporarily manages one secret-free Atlassian OAuth endpoint because Cursor's official Atlassian integration is unreliable. State that authentication remains destination-local and that additional MCP entries are rejected as drift.

- [x] **Step 2: Run the complete verification**

Run:

```bash
rtk uv run --frozen pre-commit run --all-files
rtk uv run --frozen mypy
rtk uv run --frozen pytest
rtk ./bootstrap plan --profile work --include mactex
rtk ./bootstrap configure --profile work --include mactex
rtk ./bootstrap doctor --profile work --include mactex
```

Expected: all hooks, types, and tests pass; configuration adopts or preserves the current exact file; doctor reports no legacy MCP warning.

- [x] **Step 3: Verify the repository and create one quick-fix commit**

Run:

```bash
rtk jj status
rtk jj diff --summary
rtk jj describe -m "fix: retain Cursor Atlassian workaround"
rtk jj bookmark set main -r @
```

Expected: one focused described change on local `main`, with the working copy tree matching the verified implementation.
