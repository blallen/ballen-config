# Ponytail Self-Review Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Ponytail to Codex desired state, route one bounded Ponytail simplicity pass through project-quality review without changing the self-review v1 artifact, and produce ignored self-review evidence for every MR bookmark in the resulting train.

**Architecture:** Keep Ponytail as a native marketplace plugin for Claude Code and Codex. `review-project-quality` owns the external `ponytail-review` sub-pass and normalizes its output through a small machine-readable reference contract; `conduct-self-review` still aggregates exactly four common v1 specialist results. Deliver the prerequisite bookmark from `main`, rebase the unpushed forge stack onto it, refresh rewritten identities, and review each explicit bookmark pair sequentially.

**Tech Stack:** YAML desired-state catalogs, Markdown agent skills, JSON review contracts, Python 3.12, Pydantic v2, pytest, mypy, pre-commit, and Jujutsu.

---

## File Map

| File | Responsibility |
| --- | --- |
| `assistants/shared/plugins/catalog.yaml` | Declare Ponytail for Claude Code and Codex without storing runtime state. |
| `tests/assistants/test_desired_state.py` | Prove production target projection includes Ponytail only for supported native agents. |
| `tests/assistants/test_codex.py` | Prove exact Codex marketplace/plugin planning and installed-state no-ops. |
| `assistants/shared/skills/review-project-quality/references/ponytail-review-v1.json` | Define bounded invocation, tag normalization, availability, transition, and failure effects. |
| `assistants/shared/skills/review-project-quality/SKILL.md` | Own and normalize one Ponytail diff-review sub-pass. |
| `assistants/shared/skills/conduct-self-review/SKILL.md` | Preserve four-reviewer aggregation and prevent a second Ponytail invocation. |
| `tests/assistants/test_review_contracts.py` | Validate the structured Ponytail reference and unchanged four-reviewer artifact contract. |
| `tests/assistants/test_skills.py` | Prove the quality skill links the reference while catalog dependencies remain repository-owned. |
| `docs/superpowers/specs/2026-07-30-forge-review-response-design.md` | Refresh rewritten capability commit identities after the rebase. |
| `docs/superpowers/specs/2026-07-30-reusable-review-workflows-roadmap-design.md` | Record the prerequisite and refreshed train checkpoint. |

Use `/private/tmp/ballen-config-ponytail-venv-20260731` for the root project environment and `/private/tmp/ballen-config-uv-cache-20260731` for the uv cache. Do not create `.venv`, caches, review output, or plugin payloads inside a managed source tree.

### Task 1: Add Ponytail to Codex Desired State

**Files:**

- Modify: `tests/assistants/test_desired_state.py:159-205`
- Modify: `tests/assistants/test_codex.py:98-127`
- Modify: `assistants/shared/plugins/catalog.yaml:18-21`
- Modify: `assistants/shared/plugins/catalog.yaml:74-79`

- [ ] **Step 1: Extend the production projection test first**

In `test_shared_plugin_catalog_parses_against_targeted_models`, require the
Codex projection to contain the Ponytail marketplace and plugin while keeping
the exact sorted order:

```python
assert tuple(marketplace.name for marketplace in projection.marketplaces) == (
    "bigspinai",
    "claude-plugins-official",
    "context-mode",
    "ponytail",
    "superpowers-marketplace",
)
assert tuple(plugin.id for plugin in projection.native_plugins) == (
    "bigspin@bigspinai",
    "context-mode@context-mode",
    "frontend-design@claude-plugins-official",
    "github@claude-plugins-official",
    "logfire@claude-plugins-official",
    "ponytail@ponytail",
    "superpowers-developing-for-claude-code@superpowers-marketplace",
    "superpowers@claude-plugins-official",
)
assert tuple(marketplace.targets for marketplace in projection.marketplaces) == (
    (AgentName.CODEX,),
) * 5
assert tuple(plugin.targets for plugin in projection.native_plugins) == (
    (AgentName.CODEX,),
) * 8

cursor_projection = project_plugin_catalog(
    catalog,
    target=AgentName.CURSOR,
    profiles=("default",),
)
cursor_ids = {
    plugin.id
    for plugin in (
        *cursor_projection.cursor_marketplace_plugins,
        *cursor_projection.cursor_local_plugins,
    )
}
assert "ponytail@ponytail" not in cursor_ids
```

- [ ] **Step 2: Add exact Codex planner tests**

Add these tests after
`test_plugin_actions_are_exact_ordered_and_profile_independent`:

```python
def test_codex_plans_ponytail_marketplace_before_plugin(
    codex_projection: PluginCatalogProjection,
) -> None:
    """Install the Ponytail marketplace before its required plugin."""
    actions = plan_codex_plugins(codex_projection, installed=frozenset())
    component_ids = [action.component_id for action in actions]
    marketplace_id = "codex.marketplace.ponytail"
    plugin_id = "codex.plugin.ponytail@ponytail"

    assert component_ids.index(marketplace_id) < component_ids.index(plugin_id)
    by_id = {action.component_id: action for action in actions}
    assert by_id[marketplace_id].argv == (
        "codex",
        "plugin",
        "marketplace",
        "add",
        "DietrichGebert/ponytail",
        "--json",
    )
    assert by_id[plugin_id].argv == (
        "codex",
        "plugin",
        "add",
        "ponytail@ponytail",
        "--json",
    )
    assert by_id[marketplace_id].required
    assert by_id[plugin_id].required


def test_registered_ponytail_entries_are_noops(
    codex_projection: PluginCatalogProjection,
) -> None:
    """Do not reinstall native Ponytail entries already registered by Codex."""
    actions = plan_codex_plugins(
        codex_projection,
        installed=frozenset({"ponytail@ponytail"}),
        known_marketplaces=frozenset({"ponytail"}),
    )

    component_ids = {action.component_id for action in actions}
    assert any(
        marketplace.name == "ponytail"
        for marketplace in codex_projection.marketplaces
    )
    assert any(
        plugin.id == "ponytail@ponytail"
        for plugin in codex_projection.native_plugins
    )
    assert "codex.marketplace.ponytail" not in component_ids
    assert "codex.plugin.ponytail@ponytail" not in component_ids
```

- [ ] **Step 3: Run the focused tests and verify the intended failure**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen pytest tests/assistants/test_desired_state.py::test_shared_plugin_catalog_parses_against_targeted_models tests/assistants/test_codex.py::test_codex_plans_ponytail_marketplace_before_plugin tests/assistants/test_codex.py::test_registered_ponytail_entries_are_noops -q
```

Expected: FAIL because the Codex projection has no Ponytail marketplace or
plugin.

- [ ] **Step 4: Make the minimal catalog change**

Change only the existing Ponytail records:

```yaml
  - name: ponytail
    source: DietrichGebert/ponytail
    targets: [claude-code, codex]
    profiles: [default]
```

```yaml
  - kind: native-marketplace
    id: ponytail@ponytail
    marketplace: ponytail
    targets: [claude-code, codex]
    profiles: [default]
    required: true
```

Do not add a Cursor target, copy plugin files, or change adapter code.

- [ ] **Step 5: Run focused desired-state and native adapter tests**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen pytest tests/assistants/test_desired_state.py tests/assistants/test_codex.py tests/assistants/test_claude.py -q
```

Expected: PASS, including unchanged Cursor behavior through the desired-state
suite.

- [ ] **Step 6: Commit the desired-state change and advance the bookmark**

Run:

```bash
rtk jj commit -m "feat: add Ponytail to Codex desired state"
rtk jj bookmark move review-foundation-ponytail --to @-
```

Expected: the bookmark points at the new commit and the working copy is an
empty child.

### Task 2: Define the Ponytail Quality Contract

**Files:**

- Create: `assistants/shared/skills/review-project-quality/references/ponytail-review-v1.json`
- Modify: `tests/assistants/test_review_contracts.py:3-13`
- Modify: `tests/assistants/test_review_contracts.py` after the common review-result fixture tests

- [ ] **Step 1: Write the failing structured-contract test**

Add this test to `tests/assistants/test_review_contracts.py`:

```python
def test_ponytail_quality_contract_is_bounded_and_canonical(
    repo_root: Path,
) -> None:
    """Keep Ponytail normalization explicit without expanding artifact v1."""
    path = (
        repo_root
        / "assistants/shared/skills/review-project-quality/references"
        / "ponytail-review-v1.json"
    )
    contract = json.loads(path.read_text(encoding="utf-8"))

    assert contract == {
        "contract_version": "v1",
        "reviewer": "ponytail-review",
        "invocation": {
            "check": "ponytail-review-native",
            "count": 1,
            "mode": "diff",
            "scope": "supplied-change-scope",
        },
        "lean_signal": "Lean already. Ship.",
        "tags": {
            "delete": {"rule": "ponytail/delete", "severity": "actionable"},
            "native": {"rule": "ponytail/native", "severity": "actionable"},
            "shrink": {"rule": "ponytail/shrink", "severity": "advisory"},
            "stdlib": {"rule": "ponytail/stdlib", "severity": "actionable"},
            "yagni": {"rule": "ponytail/yagni", "severity": "actionable"},
        },
        "availability": {
            "claude-code": "required",
            "codex": "required",
            "cursor": "not_applicable",
        },
        "outcomes": {
            "lean": "completed",
            "malformed_or_unbounded": "incomplete",
            "missing_required_skill": "unavailable",
            "scope_drift": "blocked",
        },
        "transition": {
            "check": "ponytail-review-published-contract",
            "completion": "completed",
            "native_claim": False,
            "required": True,
            "selected_scope": "changed",
            "source_commit": "16f29800fd2681bdf24f3eb4ccffe38be3baec6b",  # pragma: allowlist secret
            "source_path": "skills/ponytail-review/SKILL.md",
        },
    }

    assert len(_SELF_REVIEWER_ORDER) == 4
    assert "ponytail-review" not in _SELF_REVIEWER_NAMES
```

- [ ] **Step 2: Run the test and verify the missing-contract failure**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen pytest tests/assistants/test_review_contracts.py::test_ponytail_quality_contract_is_bounded_and_canonical -q
```

Expected: FAIL with `FileNotFoundError` for
`ponytail-review-v1.json`.

- [ ] **Step 3: Create the exact reference contract**

Create `ponytail-review-v1.json` with:

```json
{
  "contract_version": "v1",
  "reviewer": "ponytail-review",
  "invocation": {
    "check": "ponytail-review-native",
    "count": 1,
    "mode": "diff",
    "scope": "supplied-change-scope"
  },
  "lean_signal": "Lean already. Ship.",
  "tags": {
    "delete": {"rule": "ponytail/delete", "severity": "actionable"},
    "native": {"rule": "ponytail/native", "severity": "actionable"},
    "shrink": {"rule": "ponytail/shrink", "severity": "advisory"},
    "stdlib": {"rule": "ponytail/stdlib", "severity": "actionable"},
    "yagni": {"rule": "ponytail/yagni", "severity": "actionable"}
  },
  "availability": {
    "claude-code": "required",
    "codex": "required",
    "cursor": "not_applicable"
  },
  "outcomes": {
    "lean": "completed",
    "malformed_or_unbounded": "incomplete",
    "missing_required_skill": "unavailable",
    "scope_drift": "blocked"
  },
  "transition": {
    "check": "ponytail-review-published-contract",
    "completion": "completed",
    "native_claim": false,
    "required": true,
    "selected_scope": "changed",
    "source_commit": "16f29800fd2681bdf24f3eb4ccffe38be3baec6\u0062",
    "source_path": "skills/ponytail-review/SKILL.md"
  }
}
```

- [ ] **Step 4: Run the contract and unchanged artifact tests**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen pytest tests/assistants/test_review_contracts.py -q
```

Expected: PASS; the existing example still contains exactly four reviewers.

Do not commit yet. The structured contract and the skill instructions in Task
3 form one logical review-integration change.

### Task 3: Route Ponytail Through Project-Quality Review

**Files:**

- Modify: `tests/assistants/test_skills.py` after `test_review_foundation_skills_have_navigation_sections` (currently around line 1195)
- Modify: `assistants/shared/skills/review-project-quality/SKILL.md:12-211`
- Modify: `assistants/shared/skills/conduct-self-review/SKILL.md:112-145`

- [ ] **Step 1: Write the failing skill-routing test**

Add this test after
`test_review_foundation_skills_have_navigation_sections`:

```python
def test_quality_skill_routes_ponytail_without_expanding_self_review(
    repo_root: Path,
) -> None:
    """Link the external quality sub-pass without creating a fifth reviewer."""
    quality = (
        repo_root
        / "assistants/shared/skills/review-project-quality/SKILL.md"
    ).read_text(encoding="utf-8")
    conduct = (
        repo_root
        / "assistants/shared/skills/conduct-self-review/SKILL.md"
    ).read_text(encoding="utf-8")

    assert "references/ponytail-review-v1.json" in quality
    assert "`ponytail-review`" in quality
    assert "Do not invoke Ponytail as a fifth specialist" in conduct
    assert _REVIEW_FOUNDATION_DEPENDENCIES["review-project-quality"] == (
        "resolve-change-scope",
        "discover-project-standards",
    )
```

The final assertion is deliberate: `ponytail-review` is supplied by a native
plugin, while the checked-in skill catalog permits dependencies only on other
repository-owned shared skills.

- [ ] **Step 2: Run the routing test and verify it fails on missing guidance**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen pytest tests/assistants/test_skills.py::test_quality_skill_routes_ponytail_without_expanding_self_review -q
```

Expected: FAIL because neither skill currently links or routes Ponytail.

- [ ] **Step 3: Add the external contract to project-quality inputs**

In the quality skill overview, require reading the structured reference:

```markdown
Read `references/ponytail-review-v1.json` before invoking Ponytail. It is the
authoritative mapping for invocation count, host availability, normalized
rules, severities, transition evidence, and coverage effects. The external
skill remains provider-owned; do not add it to the repository skill catalog.
```

Add to the inputs section:

```markdown
When the active host is Claude Code or Codex, also require one available
`ponytail-review` skill or the approved transition-batch published contract.
Cursor is evidence-backed not applicable under the structured reference.
```

- [ ] **Step 4: Add one bounded Ponytail workflow step**

Insert a new workflow section after the existing owned-quality review and
renumber final revalidation and normalization sections:

```markdown
### 7. Run the Ponytail simplicity sub-pass

Invoke `ponytail-review` exactly once in diff mode. Supply the same immutable
`ChangeScope`, `scope_identity`, standards inventory, and changed-path set used
by this specialist. Never invoke Ponytail audit or let the reviewer resolve a
new scope.

Accept only a concrete changed-path observation with a tight line location
when available, one tag declared in `references/ponytail-review-v1.json`,
bounded evidence, and a specific deletion or replacement. Normalize its rule
and default severity from that reference. Keep correctness, security,
performance, and test-design concerns outside this sub-pass.

The exact lean signal completes the check with no finding. Missing required
native capability is unavailable. Malformed, unbounded, or out-of-scope output
is incomplete. Scope drift is blocked under final revalidation.

For the approved transition batch only, the exact published skill contract may
supply equivalent instructions from the source commit and path declared in the
reference. Record one required, completed, changed-scope coverage check named
`ponytail-review-published-contract`; never claim a native invocation. Do not
persist raw Ponytail output or its net-line score.
```

Update `Output`, `Quick Reference`, `Boundaries`, `Common Mistakes`, and
`Related Skills` so they consistently state that Ponytail is owned inside the
single `review-project-quality` result and never applies fixes.

- [ ] **Step 5: Protect four-reviewer aggregation**

After the ordered specialist list in `conduct-self-review`, add:

```markdown
`review-project-quality` owns and normalizes its one Ponytail simplicity
sub-pass inside that specialist result. Do not invoke Ponytail as a fifth
specialist, add a fifth reviewer record, or run the sub-pass again during
aggregation.
```

In command ownership, clarify that the same no-duplicate rule applies to the
Ponytail skill invocation even though it is not shell command evidence.

- [ ] **Step 6: Run skill and review-contract tests**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen pytest tests/assistants/test_skills.py tests/assistants/test_review_contracts.py -q
```

Expected: PASS with the existing artifact v1 example unchanged.

- [ ] **Step 7: Commit the quality-review integration and advance the bookmark**

Run:

```bash
rtk jj commit -m "feat: integrate Ponytail with project quality review"
rtk jj bookmark move review-foundation-ponytail --to @-
```

Expected: the prerequisite bookmark contains the design, plan, desired-state,
contract, skill, and test commits.

### Task 4: Verify and Self-Review the Prerequisite MR

**Files:**

- Write ignored artifact only: `.reviews/self-review/<generated>.md`

- [ ] **Step 1: Run focused verification in the Ponytail workspace**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen pytest tests/assistants/test_desired_state.py tests/assistants/test_codex.py tests/assistants/test_claude.py tests/assistants/test_skills.py tests/assistants/test_review_contracts.py -q
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen mypy
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 uv lock --check --project .
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen --no-sync python -m ballen_config.policy
rtk zsh -n bootstrap
```

Expected: all focused tests, mypy, lock validation, policy, and shell syntax
pass. Run hooks directly here because a secondary Jujutsu workspace has no
`.git` directory for pre-commit discovery.

- [ ] **Step 2: Run the full repository test suite**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen pytest -q
```

Expected: PASS.

- [ ] **Step 3: Invoke `conduct-self-review` for the prerequisite scope**

Use the repository skill with this exact request:

```yaml
scope_request:
  mode: explicit
  selector:
    base: main
    target: review-foundation-ponytail
artifact_directory: .reviews/self-review/
```

Follow the skill in full: preflight the already ignored directory, resolve
scope once, discover standards once, invoke the four specialists against the
same immutable inputs, include the approved published Ponytail contract within
project-quality review, persist with exclusive-create semantics, read back,
rehash, and verify the artifact is ignored and absent from Jujutsu status.

Expected: one validated ignored artifact. Report its exact verdict, counts,
limitations, and path. Do not remediate findings in this task.

- [ ] **Step 4: Confirm the prerequisite bookmark and workspace are clean**

Run:

```bash
rtk jj status
rtk jj log -r 'main::review-foundation-ponytail' --no-graph -T 'bookmarks ++ " | " ++ commit_id.short() ++ " " ++ description.first_line() ++ "\n"'
```

Expected: no tracked changes; the ignored artifact is absent from status and
the bookmark points to the implementation tip.

### Task 5: Rebase the Forge Train and Refresh Its Checkpoint

**Files:**

- Modify: `docs/superpowers/specs/2026-07-30-forge-review-response-design.md:19-44`
- Modify: `docs/superpowers/specs/2026-07-30-reusable-review-workflows-roadmap-design.md:20-33`

- [ ] **Step 1: Verify that the forge bookmarks remain local**

Run from the original workspace:

```bash
rtk jj bookmark list
```

Expected: every `forge-review-*` bookmark still reports `@origin (not created
yet)`. Stop and use the pushed-history recovery procedure if that is no longer
true.

- [ ] **Step 2: Rebase the complete forge train once**

Run:

```bash
rtk jj rebase -s 'roots(main..forge-review-train-checkpoint)' -d review-foundation-ponytail
```

Expected: the forge root and all descendants are rewritten onto the
prerequisite bookmark with no conflict.

- [ ] **Step 3: Verify bookmark order and collect full current identities**

Run:

```bash
rtk jj log -r 'review-foundation-ponytail::forge-review-train-checkpoint' --no-graph -T 'bookmarks ++ " | " ++ change_id ++ " " ++ commit_id ++ " " ++ description.first_line() ++ "\n"'
rtk jj status
```

Expected: all seven capability bookmarks and the docs checkpoint are ordered
above `review-foundation-ponytail`; no revision is conflicted.

- [ ] **Step 4: Refresh the checkpoint documents**

In the original workspace, run `rtk jj workspace update-stale` if needed, then
replace every old abbreviated capability head in the forge design checkpoint
table with the current rewritten commit ID. Update the roadmap checkpoint to
name `review-foundation-ponytail` as the prerequisite MR and state that the
forge train is based on it.

Do not claim live forge mutation or native plugin invocation. Preserve the
existing explicit deferral of live GitHub and GitLab writes.

- [ ] **Step 5: Fold the identity refresh into the docs-only checkpoint**

Run:

```bash
rtk jj squash
rtk jj status
```

Expected: the refreshed docs are part of `forge-review-train-checkpoint`, its
bookmark follows the rewritten commit, and the working copy is empty.

- [ ] **Step 6: Run post-rebase full verification in the original workspace**

Run:

```bash
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen pytest -q
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 uv run --project . --frozen mypy
rtk env UV_CACHE_DIR=/private/tmp/ballen-config-uv-cache-20260731 UV_PROJECT_ENVIRONMENT=/private/tmp/ballen-config-ponytail-venv-20260731 PRE_COMMIT_HOME=/private/tmp/ballen-config-pre-commit /private/tmp/ballen-config-ponytail-venv-20260731/bin/pre-commit run --all-files
```

Expected: full pytest, mypy, and every pre-commit hook pass from the colocated
workspace.

### Task 6: Run Self-Review on Every Forge MR Boundary

**Files:**

- Write ignored artifacts only: `.reviews/self-review/<generated>.md`

- [ ] **Step 1: Dispatch sequential bounded reviewers**

Use one fresh read-only subagent per target, configured as Luna with extra-high
reasoning. Dispatch sequentially so Jujutsu snapshot operations and exclusive
artifact writes cannot race. Each subagent may write only its generated
ignored artifact and must use the exact `conduct-self-review` workflow.

Invoke these explicit requests in order:

```yaml
- base: review-foundation-ponytail
  target: forge-review-github-draft
- base: forge-review-github-draft
  target: forge-review-github-publish
- base: forge-review-github-publish
  target: forge-review-prepare-response
- base: forge-review-prepare-response
  target: forge-review-github-response
- base: forge-review-github-response
  target: forge-review-gitlab-draft
- base: forge-review-gitlab-draft
  target: forge-review-gitlab-publish
- base: forge-review-gitlab-publish
  target: forge-review-gitlab-response
- base: forge-review-gitlab-response
  target: forge-review-train-checkpoint
```

For every item, the full request is:

```yaml
scope_request:
  mode: explicit
  selector:
    base: <base>
    target: <target>
artifact_directory: .reviews/self-review/
```

Expected: eight additional validated artifacts. A blocked, unavailable,
incomplete, or finding-bearing verdict is still a completed report when the
artifact persists and verifies; never relabel it clean.

- [ ] **Step 2: Verify each artifact and collect a concise matrix**

For each exact returned path, confirm the marker, JSON digest, scope base and
target identities, reviewer order, Ponytail quality coverage, verdict, counts,
ignored status, and absence from Jujutsu status. Do not select an unspecified
latest artifact.

Build this handoff matrix in the final response, not in a tracked file:

```text
target | verdict | blockers | actionable | advisory | limitation | artifact
```

- [ ] **Step 3: Confirm final source-control state**

Run:

```bash
rtk jj status
rtk jj bookmark list
rtk jj log -r 'main::forge-review-train-checkpoint' --no-graph -T 'bookmarks ++ " | " ++ commit_id.short() ++ " " ++ description.first_line() ++ "\n"'
```

Expected: both workspaces are clean, all nine MR bookmarks are ordered, review
artifacts remain ignored and uncommitted, and no remote bookmark was created.

## Completion Boundary

Completion means the Ponytail prerequisite MR is implemented and verified, the
local forge train is rebased with current checkpoint identities, and all nine
explicit MR scopes have validated ignored self-review artifacts. It does not
authorize plugin installation into the current user profile, hook trust,
remote bookmark creation, PR creation, review publication, remediation, or
live GitHub/GitLab mutation.
