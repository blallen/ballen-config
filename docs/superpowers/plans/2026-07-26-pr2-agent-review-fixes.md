# PR2 Coding-Agent Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove abandoned Piste plugin declarations and promote the reviewed `jujutsu-workflow` skill for Cursor, Claude Code, and Codex without mixing the later catalog architecture into PR2.

**Architecture:** Insert two commits immediately after `laptop-bootstrap-agents` so Jujutsu restacks PR3 and the consolidation branch automatically. The first commit removes declarative installation only; the second uses the existing shared-skill catalog and managed-tree machinery without changing production Python.

**Tech Stack:** Jujutsu 0.43, Python 3.12, Pydantic 2.8, PyYAML, pytest fixtures, Ruff, pre-commit

## Global Constraints

- Prefix every shell command with `rtk`.
- Use `apply_patch` for repository edits.
- Use Jujutsu, not Git, for status, history edits, commits, bookmarks, and pushes.
- Do not uninstall any currently installed local plugin.
- Do not copy plugin caches, authentication, sessions, histories, memories, or SSH material.
- Preserve `self-review-laptop-bootstrap-review.md` as historical evidence.
- Run tests against temporary homes only.
- Keep the two content changes in separate commits.

---

## File Map

### Commit 1: remove abandoned Piste declarations

Modify:

- `assistants/claude/plugins.yaml`
- `assistants/codex/plugins.yaml`
- `assistants/inventory.yaml`
- `README.md`
- `docs/manual-steps.md`
- `tests/assistants/fakes.py`
- `tests/assistants/test_claude.py`
- `tests/assistants/test_codex.py`
- `tests/assistants/test_integration.py`

### Commit 2: promote `jujutsu-workflow`

Create:

- `assistants/shared/skills/jujutsu-workflow/SKILL.md`
- `assistants/shared/skills/jujutsu-workflow/reference.md`

Modify:

- `assistants/shared/skills/catalog.yaml`
- `assistants/inventory.yaml`
- `docs/promoting-shared-skills.md`
- `tests/assistants/test_instructions.py`
- `tests/assistants/test_skills.py`
- `tests/assistants/test_integration.py`

Source files copied byte-for-byte:

- `/Users/ballen/Projects/plato/skills/jujutsu-workflow/SKILL.md`
- `/Users/ballen/Projects/plato/skills/jujutsu-workflow/reference.md`

### Expected descendant conflict resolution

Resolve after both PR2 commits:

- `docs/manual-steps.md`
- `tests/assistants/test_skills.py`

## Task 1: Remove the Abandoned Piste Plugin Declarations

**Files:**

- Modify: `tests/assistants/test_claude.py:82-118`
- Modify: `tests/assistants/test_codex.py:92-130`
- Modify: `tests/assistants/test_integration.py:459-514`
- Modify: `assistants/claude/plugins.yaml`
- Modify: `assistants/codex/plugins.yaml`
- Modify: `assistants/inventory.yaml`
- Modify: `tests/assistants/fakes.py:35-47`
- Modify: `README.md:64-84`
- Modify: `docs/manual-steps.md:8-15`

**Interfaces:**

- Consumes: existing `plan_claude_plugins()` and `plan_codex_plugins()` behavior.
- Produces: default and work projections with no Piste marketplace or plugin action.
- Preserves: every non-Piste native plugin identifier and profile.

- [ ] **Step 1: Insert a new commit directly after the PR2 bookmark**

Run:

```bash
rtk jj status
rtk jj new --insert-after laptop-bootstrap-agents
```

Expected: the working copy is an empty commit between
`laptop-bootstrap-agents` and the rebased `laptop-bootstrap-review`.

- [ ] **Step 2: Change the focused tests to require Piste-free work plans**

In `test_plugin_actions_are_scoped_ordered_and_profile_aware`, replace the
work-only optional assertions with:

```python
work_actions = plan_claude_plugins(
    repo_root / "assistants/claude/plugins.yaml",
    profiles=("default", "work"),
    installed=frozenset(),
)
assert work_actions == default_actions
assert all(
    "piste" not in action.component_id and "piste" not in " ".join(action.argv)
    for action in work_actions
)
```

In `test_plugin_actions_are_exact_ordered_and_profile_aware`, require the same
for Codex:

```python
work_actions = plan_codex_plugins(
    repo_root / "assistants/codex/plugins.yaml",
    profiles=("default", "work"),
    installed=frozenset(),
)
assert work_actions == default_actions
assert all(
    "piste" not in action.component_id and "piste" not in " ".join(action.argv)
    for action in work_actions
)
```

Rename `test_plugin_catalog_explicitly_declares_every_profile` to
`test_plugin_catalog_explicitly_declares_default_profile` and use:

```python
assert all(item["profiles"] == ["default"] for item in source["marketplaces"])
assert all(item["profiles"] == ["default"] for item in source["plugins"])
```

Rename the integration test to
`test_work_profile_adds_only_work_agent_settings` and replace the Piste
presence assertions with:

```python
    for runner in (default_runner, work_runner):
        assert not any("piste" in " ".join(command) for command in runner.commands)
    for result in (default_result, work_result):
        assert not any("piste" in outcome for outcome in result.report.outcomes)
```

- [ ] **Step 3: Run the tests and confirm that current work plans fail**

Run:

```bash
rtk uv run --frozen pytest tests/assistants/test_claude.py::test_plugin_actions_are_scoped_ordered_and_profile_aware tests/assistants/test_codex.py::test_plugin_actions_are_exact_ordered_and_profile_aware tests/assistants/test_codex.py::test_plugin_catalog_explicitly_declares_default_profile tests/assistants/test_integration.py::test_work_profile_adds_only_work_agent_settings -q
```

Expected: failures show the current Piste marketplace or its two plugins in
the work profile.

- [ ] **Step 4: Remove the declarations atomically**

Use `apply_patch` to delete:

```yaml
- name: piste
  source: git@gitlab.com:flagship-informatics/internal-open-source/piste.git
  profiles: [work]
```

and both of these plugin records from each native catalog:

```yaml
- id: ami-qsp-tools@piste
  marketplace: piste
  profiles: [work]
  required: false
- id: fieldkit@piste
  marketplace: piste
  profiles: [work]
  required: false
```

Remove these two IDs from both flattened inventory lists:

```yaml
- ami-qsp-tools@piste
- fieldkit@piste
```

Remove the Piste source mapping from `StatefulAssistantFake`:

```python
"git@gitlab.com:flagship-informatics/internal-open-source/piste.git": "piste",
```

- [ ] **Step 5: Update operational documentation**

In `README.md`, make the coding-agent paragraph state that native plugin
identifiers are installed from reviewed catalogs, without a Piste exception.

In `docs/manual-steps.md`, end the SSH step after the link to
`docs/ssh-transfer.md`; remove the Piste marketplace refresh instruction.

Do not edit `self-review-laptop-bootstrap-review.md`.

- [ ] **Step 6: Run focused and policy verification**

Run:

```bash
rtk uv run --frozen pytest tests/assistants/test_claude.py tests/assistants/test_codex.py tests/assistants/test_integration.py -q
rtk uv run --frozen ruff check tests/assistants/fakes.py tests/assistants/test_claude.py tests/assistants/test_codex.py tests/assistants/test_integration.py
rtk uv run --frozen ruff format --check tests/assistants/fakes.py tests/assistants/test_claude.py tests/assistants/test_codex.py tests/assistants/test_integration.py
rtk uv run --frozen python -m ballen_config.policy
rtk rg -n 'piste|ami-qsp-tools|fieldkit' assistants README.md docs/manual-steps.md
```

Expected:

- focused tests, Ruff, and policy pass;
- the final search returns no matches in declarative or operational sources.

- [ ] **Step 7: Commit the removal**

Run:

```bash
rtk jj diff --summary
rtk jj describe -m "fix: remove abandoned Piste plugins"
```

Expected: one described commit containing only the removal, its tests, and its
operational documentation.

## Task 2: Promote the Portable `jujutsu-workflow` Skill

**Files:**

- Modify: `tests/assistants/test_skills.py:782-809`
- Modify: `tests/assistants/test_instructions.py`
- Modify: `tests/assistants/test_integration.py`
- Create: `assistants/shared/skills/jujutsu-workflow/SKILL.md`
- Create: `assistants/shared/skills/jujutsu-workflow/reference.md`
- Modify: `assistants/shared/skills/catalog.yaml`
- Modify: `assistants/inventory.yaml:20-30`
- Modify: `docs/promoting-shared-skills.md`

**Interfaces:**

- Consumes: `SkillCatalog`, `skills.configuration()`, `ManagedTreeSpec`, and
  the existing Cursor compatibility-root collision rules.
- Produces: three independently managed native copies from one canonical source.
- Produces resource IDs:
  - `shared-skill-jujutsu-workflow-codex`
  - `shared-skill-jujutsu-workflow-claude-code`
  - `shared-skill-jujutsu-workflow-cursor`

- [ ] **Step 1: Insert the second PR2 commit before the descendants**

Run:

```bash
rtk jj new --insert-after @
```

Expected: a second empty commit follows the Piste-removal commit, and PR3 plus
the consolidation branch are rebased after it.

- [ ] **Step 2: Replace the empty-catalog test with the promoted-skill contract**

Replace `test_initial_catalog_and_inventory_remain_empty_and_synchronized`
with:

```python
def test_promoted_jujutsu_workflow_catalog_and_inventory_are_synchronized(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Declare one reviewed skill and plan all three native destinations."""
    inventory = load_inventory(repo_root / "assistants/inventory.yaml", repo_root)
    catalog = yaml.safe_load(
        (repo_root / "assistants/shared/skills/catalog.yaml").read_text()
    )
    resource = next(
        item for item in inventory.resources if item.id == "shared.skills.catalog"
    )

    assert catalog == {
        "skills": [
            {
                "name": "jujutsu-workflow",
                "source": "assistants/shared/skills/jujutsu-workflow",
                "targets": ["cursor", "claude-code", "codex"],
                "profiles": ["default"],
                "dependencies": [],
                "provenance": (
                    "Promoted from the reviewed Plato jujutsu workflow skill."
                ),
                "portability_status": "reviewed-generic",
            }
        ]
    }
    assert isinstance(resource, CatalogResource)
    assert resource.owner is AgentName.SHARED
    assert resource.item_ids == ("jujutsu-workflow",)

    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    contribution = configuration(
        _resolved_setup("cursor", "claude-code", "codex"),
        paths,
    )
    destinations = {spec.id: spec.destination for spec in contribution.specs}
    assert destinations == {
        "shared-skill-jujutsu-workflow-codex": Path(".agents/skills/jujutsu-workflow"),
        "shared-skill-jujutsu-workflow-claude-code": Path(
            ".claude/skills/jujutsu-workflow"
        ),
        "shared-skill-jujutsu-workflow-cursor": Path(".cursor/skills/jujutsu-workflow"),
    }
```

Update the instruction inventory test to require:

```python
assert catalog.item_ids == ("jujutsu-workflow",)
```

- [ ] **Step 3: Add the aggregate copy and skip test**

Add an integration test that runs the real configure path and compares both
files:

```python
def test_jujutsu_workflow_converges_to_enabled_native_skill_roots(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    """Copy identical reviewed skill trees without relying on cross-tool import."""
    result = run_with_assistants(
        ("configure", "--skip", "codex"),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )
    source = repo_root / "assistants/shared/skills/jujutsu-workflow"
    for relative in (
        Path(".cursor/skills/jujutsu-workflow"),
        Path(".claude/skills/jujutsu-workflow"),
    ):
        destination = temporary_home / relative
        assert (destination / "SKILL.md").read_bytes() == (
            source / "SKILL.md"
        ).read_bytes()
        assert (destination / "reference.md").read_bytes() == (
            source / "reference.md"
        ).read_bytes()
    assert not (temporary_home / ".agents/skills/jujutsu-workflow").exists()
    assert result.exit_code == 0
```

- [ ] **Step 4: Run the tests and confirm the catalog is still empty**

Run:

```bash
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_promoted_jujutsu_workflow_catalog_and_inventory_are_synchronized tests/assistants/test_integration.py::test_jujutsu_workflow_converges_to_enabled_native_skill_roots -q
```

Expected: failures show the empty catalog or missing canonical source.

- [ ] **Step 5: Add the reviewed source and declaration**

Use `apply_patch` to add byte-identical copies of:

```text
/Users/ballen/Projects/plato/skills/jujutsu-workflow/SKILL.md
/Users/ballen/Projects/plato/skills/jujutsu-workflow/reference.md
```

at:

```text
assistants/shared/skills/jujutsu-workflow/SKILL.md
assistants/shared/skills/jujutsu-workflow/reference.md
```

Set `assistants/shared/skills/catalog.yaml` to:

```yaml
skills:
  - name: jujutsu-workflow
    source: assistants/shared/skills/jujutsu-workflow
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: Promoted from the reviewed Plato jujutsu workflow skill.
    portability_status: reviewed-generic
```

Set the inventory catalog list to:

```yaml
item_ids:
  - jujutsu-workflow
```

Replace the placeholder example in `docs/promoting-shared-skills.md` with the
same real declaration.

- [ ] **Step 6: Verify byte identity and focused behavior**

Run:

```bash
rtk cmp /Users/ballen/Projects/plato/skills/jujutsu-workflow/SKILL.md assistants/shared/skills/jujutsu-workflow/SKILL.md
rtk cmp /Users/ballen/Projects/plato/skills/jujutsu-workflow/reference.md assistants/shared/skills/jujutsu-workflow/reference.md
rtk uv run --frozen pytest tests/assistants/test_skills.py tests/assistants/test_instructions.py tests/assistants/test_integration.py -q
rtk uv run --frozen python -m ballen_config.policy
```

Expected: both `cmp` commands and all tests pass.

- [ ] **Step 7: Commit the skill promotion and move PR2**

Run:

```bash
rtk jj diff --summary
rtk jj describe -m "feat: seed shared jujutsu workflow skill"
rtk jj bookmark move laptop-bootstrap-agents --to @
```

Expected: `laptop-bootstrap-agents` now points to the second new commit.

## Task 3: Reconcile the Descendant Stack and Update PR2

**Files:**

- Resolve if conflicted: `docs/manual-steps.md`
- Resolve if conflicted: `tests/assistants/test_skills.py`
- Preserve unchanged: `self-review-laptop-bootstrap-review.md`

**Interfaces:**

- Consumes: the two new PR2 commits.
- Produces: conflict-free `laptop-bootstrap-review` and
  `laptop-bootstrap-agent-consolidation` descendants.
- Preserves: PR3's owner assertion and historical review report.

- [ ] **Step 1: Inspect the restacked descendants**

Run:

```bash
rtk jj log -r 'laptop-bootstrap-agents::laptop-bootstrap-agent-consolidation'
rtk jj log -r 'conflicts() & (laptop-bootstrap-agents::laptop-bootstrap-agent-consolidation)'
```

Expected: a linear stack. The second command is empty or identifies the
expected downstream documentation/test conflict.

- [ ] **Step 2: Resolve any conflicted descendant at its source**

If the conflict query is nonempty, list the roots with immutable commit IDs:

```bash
rtk jj log --no-graph -r 'roots(conflicts() & (laptop-bootstrap-agents::laptop-bootstrap-agent-consolidation))' -T 'commit_id ++ "\n"'
```

Copy exactly one ID from that output and edit that one conflicted revision:

```bash
rtk jj edit <one-exact-commit-id-from-the-previous-command>
```

Never pass the whole multi-revision revset to `jj new`; more than one root
would create an unintended merge commit. Use `apply_patch` so this one
revision's resolved result:

- removes Piste guidance from `docs/manual-steps.md`;
- retains `resource.owner is AgentName.SHARED`;
- retains the promoted `jujutsu-workflow` catalog, inventory, and three
  destinations in `tests/assistants/test_skills.py`;
- leaves `self-review-laptop-bootstrap-review.md` unchanged.

Then run:

```bash
rtk uv run --frozen pytest tests/assistants/test_skills.py tests/assistants/test_integration.py -q
rtk jj status
rtk jj log -r 'conflicts() & (laptop-bootstrap-agents::laptop-bootstrap-agent-consolidation)'
```

Repeat the ID-list, single-revision `jj edit`, resolution, and focused
verification sequence only while the final query identifies another
conflicted descendant. Return to the consolidation tip only after the query
is empty.

- [ ] **Step 3: Run complete local verification**

Return to a clean child of the consolidation tip:

```bash
rtk jj new laptop-bootstrap-agent-consolidation
rtk uv run --frozen pytest -q
rtk uv run --frozen ruff check .
rtk uv run --frozen ruff format --check src tests
rtk uv run --frozen mypy
rtk uv run --frozen pre-commit run --all-files
rtk jj status
```

Expected: all checks pass and the working copy is empty.

- [ ] **Step 4: Retarget PR2 and push the complete stack safely**

Run:

```bash
rtk gh pr edit 2 --base main
rtk jj git fetch
rtk jj git push --bookmark laptop-bootstrap-agents --bookmark laptop-bootstrap-review --bookmark laptop-bootstrap-agent-consolidation
```

Expected:

- PR2 targets `main`;
- PR3 still targets `laptop-bootstrap-agents`;
- all three remote bookmarks match the verified local stack.

- [ ] **Step 5: Verify GitHub state and resolve addressed review threads**

Run:

```bash
rtk gh pr view 2 --json baseRefName,headRefName,mergeable,state,url
rtk gh pr view 3 --json baseRefName,headRefName,mergeable,state,url
rtk gh pr diff 2 --name-only
rtk gh pr checks 2
```

Expected:

- PR2 base/head are `main` / `laptop-bootstrap-agents`;
- PR3 base/head are `laptop-bootstrap-agents` /
  `laptop-bootstrap-review`;
- the PR2 diff contains the two focused changes;
- required checks pass.

Read the unresolved PR2 threads and their exact node IDs:

```bash
rtk gh api graphql -F owner=blallen -F name=ballen-config -F number=2 -f query='
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 20) {
            nodes { author { login } body url }
          }
        }
      }
    }
  }
}' --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)'
```

Match the returned body, path, and URL against the six Piste-removal requests
and the shared-skill request. For each confirmed node ID, run this mutation
with that exact ID:

```bash
rtk gh api graphql -F thread='<confirmed-thread-node-id>' -f query='
mutation($thread: ID!) {
  resolveReviewThread(input: {threadId: $thread}) {
    thread { id isResolved }
  }
}'
```

Do not select threads by position or resolve any thread whose body does not
match one of those seven addressed requests. Re-run the read query and verify
that only the broader consolidation thread remains unresolved. Keep that
unresolved thread's node `id` from the query and reply without resolving it:

```bash
rtk gh api graphql -F thread='<confirmed-unresolved-thread-node-id>' -F body='The target-aware consolidation is tracked on `laptop-bootstrap-agent-consolidation` and will land as the next stacked PR.' -f query='
mutation($thread: ID!, $body: String!) {
  addPullRequestReviewThreadReply(
    input: {pullRequestReviewThreadId: $thread, body: $body}
  ) {
    comment { id url body }
  }
}'
```

Re-run the read query once more and verify the broader thread is still
unresolved and its latest reply is the consolidation pointer.
