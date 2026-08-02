# Coding-Agent Desired-State Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Cursor, Claude Code, and Codex one strict repository source for portable skills and plugin intent while planning, applying, and diagnosing each agent independently.

**Architecture:** A target-aware Pydantic catalog preserves native identifiers and projects one immutable, profile-filtered view per agent. A preflight-loaded `AssistantDesiredState` is passed to native adapters before any runner call or configuration write. Cursor marketplace plugins remain manual checklist entries; reviewed Cursor local plugins use the existing atomic managed-tree engine.

**Tech Stack:** Python 3.12, Pydantic 2.8, PyYAML, pytest fixtures, Jujutsu 0.43, Cursor/Claude Code/Codex native interfaces, Ruff, mypy, pre-commit

## Global Constraints

- Complete `2026-07-26-pr2-agent-review-fixes.md` first.
- Start from a conflict-free `laptop-bootstrap-agent-consolidation` stacked on
  the updated `laptop-bootstrap-review`.
- Prefix every shell command with `rtk`.
- Use `apply_patch` for repository edits.
- Use Jujutsu for status, commits, bookmarks, and pushes.
- Use Python 3.12, Pydantic 2.8, strict type hints, and Google-style docstrings.
- Write tests with pytest fixtures and parameterization.
- Load and validate all assistant desired state before any native runner call
  or configuration mutation.
- Never inspect or copy Cursor private databases, plugin caches, cross-tool
  import state, authentication, sessions, histories, memories, or trust state.
- Keep adapters native; do not synthesize one universal plugin command.
- Keep production Cursor marketplace and local-plugin lists empty until a
  separate reviewed selection names an intended plugin.
- Every task ends with a passing focused suite and a logical commit.

---

## File Map

### Create

| Path | Responsibility |
| --- | --- |
| `assistants/shared/plugins/catalog.yaml` | One target-aware plugin declaration source. |
| `src/ballen_config/assistants/desired_state.py` | Catalog loading, projection, and immutable invocation state. |
| `src/ballen_config/assistants/orchestrator.py` | Preflight cache and adapter composition. |
| `src/ballen_config/assistants/cursor_plugins.py` | Reviewed local-plugin trees and manual marketplace actions. |
| `tests/assistants/test_desired_state.py` | Shared catalog validation, projection, and preflight tests. |
| `tests/assistants/test_cursor_plugins.py` | Cursor plugin source, collision, and manual-action tests. |

### Modify

| Path | Responsibility |
| --- | --- |
| `src/ballen_config/assistants/models.py` | Target-aware declarations and projected native models. |
| `src/ballen_config/assistants/inventory.py` | Catalog validation without flattened ID mirrors. |
| `src/ballen_config/assistants/__init__.py` | Public exports for the orchestrator and new models. |
| `src/ballen_config/assistants/claude.py` | Consume a preprojected native catalog. |
| `src/ballen_config/assistants/codex.py` | Consume a preprojected native catalog. |
| `src/ballen_config/assistants/cursor.py` | Consume a preloaded extension catalog. |
| `src/ballen_config/assistants/skills.py` | Consume a preloaded skill catalog and expose bounded skill-name parsing. |
| `src/ballen_config/cli.py` | Run assistant preflight before candidates, inspection, confirmation, or mutation. |
| `assistants/inventory.yaml` | Reference shared catalogs once, without `item_ids`. |
| `tests/assistants/*.py` | Adapter, inventory, model, checks, and integration behavior. |
| `tests/test_cli.py` | Preflight ordering and stable failure outcome. |
| `README.md` | Source-of-truth and independent-adapter rationale. |
| `docs/manual-steps.md` | Cursor manual marketplace instructions. |
| `docs/promoting-shared-skills.md` | Shared-skill versus local-plugin collision boundary. |
| `docs/superpowers/specs/2026-07-25-laptop-migration-bootstrap-design.md` | Remove superseded Cursor plugin wording. |

### Delete after native adapters consume projections

- `assistants/claude/plugins.yaml`
- `assistants/codex/plugins.yaml`

## Task 1: Define the Target-Aware Catalog and Projection

**Files:**

- Modify: `src/ballen_config/assistants/models.py:203-278`
- Create: `src/ballen_config/assistants/desired_state.py`
- Create: `assistants/shared/plugins/catalog.yaml`
- Modify: `tests/assistants/test_models.py`
- Create: `tests/assistants/test_desired_state.py`
- Mechanically modify imports in:
  - `src/ballen_config/assistants/claude.py`
  - `src/ballen_config/assistants/codex.py`
  - `src/ballen_config/assistants/inventory.py`
  - their focused tests

**Interfaces:**

- Produces `PluginCatalog`.
- Produces `PluginCatalogProjection`.
- Produces
  `project_plugin_catalog(catalog, target, profiles) -> PluginCatalogProjection`.
- Preserves the old single-agent shape as `NativePluginCatalog` until Task 2
  removes path-based loading.

- [ ] **Step 1: Write strict model and projection tests**

Add these tests:

```python
def test_plugin_catalog_accepts_shared_native_and_cursor_variants() -> None:
    catalog = PluginCatalog.model_validate(
        {
            "marketplaces": [
                {
                    "name": "official",
                    "source": "owner/repository",
                    "targets": ["claude-code", "codex"],
                    "profiles": ["default"],
                }
            ],
            "plugins": [
                {
                    "kind": "native-marketplace",
                    "id": "example@official",
                    "marketplace": "official",
                    "targets": ["claude-code", "codex"],
                    "profiles": ["default"],
                    "required": True,
                },
                {
                    "kind": "cursor-marketplace",
                    "id": "cursor-example",
                    "targets": ["cursor"],
                    "profiles": ["default"],
                    "required": False,
                    "scope": "user",
                    "verification": "manual",
                },
                {
                    "kind": "cursor-local",
                    "id": "local-example",
                    "source": "assistants/shared/plugins/local/local-example",
                    "targets": ["cursor"],
                    "profiles": ["default"],
                    "required": True,
                },
            ],
        }
    )
    assert len(catalog.plugins) == 3
```

Add parameterized failures for:

```python
@pytest.mark.parametrize(
    "targets",
    [[], ["shared"], ["cursor", "cursor"]],
)
def test_plugin_catalog_rejects_invalid_target_sets(
    targets: list[str],
) -> None:
    payload = {
        "marketplaces": [
            {
                "name": "official",
                "source": "owner/repository",
                "targets": targets,
                "profiles": ["default"],
            }
        ],
        "plugins": [],
    }
    with pytest.raises(ValidationError):
        PluginCatalog.model_validate(payload)
```

Add exact relationship tests:

```python
def test_plugin_catalog_rejects_duplicate_identity_for_overlapping_target() -> None:
    payload = {
        "marketplaces": [
            {
                "name": "official",
                "source": "owner/one",
                "targets": ["claude-code", "codex"],
            },
            {
                "name": "official",
                "source": "owner/two",
                "targets": ["codex"],
            },
        ],
        "plugins": [],
    }
    with pytest.raises(ValidationError, match="duplicate marketplace identity"):
        PluginCatalog.model_validate(payload)


def test_disjoint_targets_may_reuse_marketplace_name() -> None:
    catalog = PluginCatalog.model_validate(
        {
            "marketplaces": [
                {
                    "name": "official",
                    "source": "owner/claude",
                    "targets": ["claude-code"],
                },
                {
                    "name": "official",
                    "source": "owner/codex",
                    "targets": ["codex"],
                },
            ],
            "plugins": [],
        }
    )
    assert len(catalog.marketplaces) == 2


@pytest.mark.parametrize(
    ("marketplace", "plugin", "message"),
    [
        pytest.param(
            {
                "name": "official",
                "source": "owner/repository",
                "targets": ["claude-code"],
            },
            {
                "kind": "native-marketplace",
                "id": "example@official",
                "marketplace": "official",
                "targets": ["codex"],
            },
            "not covered",
            id="target",
        ),
        pytest.param(
            {
                "name": "official",
                "source": "owner/repository",
                "targets": ["claude-code"],
                "profiles": ["default"],
            },
            {
                "kind": "native-marketplace",
                "id": "example@official",
                "marketplace": "official",
                "targets": ["claude-code"],
                "profiles": ["work"],
            },
            "profiles must be a subset",
            id="profile",
        ),
    ],
)
def test_native_plugin_requires_marketplace_coverage(
    marketplace: dict[str, object],
    plugin: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        PluginCatalog.model_validate(
            {"marketplaces": [marketplace], "plugins": [plugin]}
        )


def test_native_plugin_suffix_matches_marketplace_alias() -> None:
    with pytest.raises(ValidationError, match="suffix mismatch"):
        PluginCatalog.model_validate(
            {
                "marketplaces": [
                    {
                        "name": "official",
                        "source": "owner/repository",
                        "targets": ["claude-code"],
                    }
                ],
                "plugins": [
                    {
                        "kind": "native-marketplace",
                        "id": "example@other",
                        "marketplace": "official",
                        "targets": ["claude-code"],
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    "kind",
    ["cursor-marketplace", "cursor-local"],
)
def test_cursor_variants_reject_non_cursor_targets(kind: str) -> None:
    plugin: dict[str, object] = {
        "kind": kind,
        "id": "example",
        "targets": ["claude-code"],
    }
    if kind == "cursor-marketplace":
        plugin.update(scope="user", verification="manual")
    else:
        plugin["source"] = "assistants/shared/plugins/local/example"
    with pytest.raises(ValidationError, match="target only cursor"):
        PluginCatalog.model_validate({"marketplaces": [], "plugins": [plugin]})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("scope", "workspace", id="scope"),
        pytest.param("verification", "automatic", id="verification"),
    ],
)
def test_cursor_marketplace_requires_manual_user_selection(
    field: str,
    value: str,
) -> None:
    plugin = {
        "kind": "cursor-marketplace",
        "id": "example",
        "targets": ["cursor"],
        "scope": "user",
        "verification": "manual",
        field: value,
    }
    with pytest.raises(ValidationError):
        PluginCatalog.model_validate({"marketplaces": [], "plugins": [plugin]})
```

Add the dependency-eligibility invariant to the existing skill model tests:

```python
@pytest.mark.parametrize(
    ("dependency_targets", "dependency_profiles", "message"),
    [
        pytest.param(
            ["cursor"],
            ["default", "work"],
            "dependency targets",
            id="target",
        ),
        pytest.param(
            ["cursor", "codex"],
            ["default"],
            "dependency profiles",
            id="profile",
        ),
    ],
)
def test_skill_dependencies_cover_dependent_eligibility(
    dependency_targets: list[str],
    dependency_profiles: list[str],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        SkillCatalog.model_validate(
            {
                "skills": [
                    {
                        "name": "base",
                        "source": "assistants/shared/skills/base",
                        "targets": dependency_targets,
                        "profiles": dependency_profiles,
                        "dependencies": [],
                        "provenance": "reviewed",
                        "portability_status": "reviewed-generic",
                    },
                    {
                        "name": "dependent",
                        "source": "assistants/shared/skills/dependent",
                        "targets": ["cursor", "codex"],
                        "profiles": ["default", "work"],
                        "dependencies": ["base"],
                        "provenance": "reviewed",
                        "portability_status": "reviewed-generic",
                    },
                ]
            }
        )


def test_shared_skill_dependency_may_cover_more_targets_and_profiles() -> None:
    catalog = SkillCatalog.model_validate(
        {
            "skills": [
                {
                    "name": "base",
                    "source": "assistants/shared/skills/base",
                    "targets": ["cursor", "claude-code", "codex"],
                    "profiles": ["default", "work"],
                    "dependencies": [],
                    "provenance": "reviewed",
                    "portability_status": "reviewed-generic",
                },
                {
                    "name": "dependent",
                    "source": "assistants/shared/skills/dependent",
                    "targets": ["cursor", "codex"],
                    "profiles": ["work"],
                    "dependencies": ["base"],
                    "provenance": "reviewed",
                    "portability_status": "reviewed-generic",
                },
            ]
        }
    )
    assert catalog.skills[1].dependencies == ("base",)
```

Add this projection assertion:

```python
def test_project_plugin_catalog_returns_one_concrete_target() -> None:
    projection = project_plugin_catalog(
        _targeted_catalog(),
        target=AgentName.CLAUDE,
        profiles=("default",),
    )
    assert projection.target is AgentName.CLAUDE
    assert all(
        marketplace.targets == (AgentName.CLAUDE,)
        for marketplace in projection.marketplaces
    )
    assert all(
        plugin.targets == (AgentName.CLAUDE,) for plugin in projection.native_plugins
    )
    assert projection.cursor_marketplace_plugins == ()
    assert projection.cursor_local_plugins == ()
```

- [ ] **Step 2: Run the new tests and verify missing-type failures**

Run:

```bash
rtk uv run --frozen pytest tests/assistants/test_models.py tests/assistants/test_desired_state.py -q
```

Expected: collection or import failures identify the missing target-aware
models and projection.

- [ ] **Step 3: Add the final declaration models**

Add this strict alias beside `ConcreteTargets` and use it everywhere a single
resolved agent is required:

```python
type ConcreteAgentName = Literal[
    AgentName.CURSOR,
    AgentName.CLAUDE,
    AgentName.CODEX,
]
```

Keep the existing per-agent models under these names:

```python
class NativeMarketplace(BaseModel):
    """One marketplace after target and profile projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    profiles: tuple[str, ...] = Field(default=("default",), min_length=1)


class NativePlugin(BaseModel):
    """One native plugin after target and profile projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    marketplace: str = Field(min_length=1)
    profiles: tuple[str, ...] = Field(default=("default",), min_length=1)
    required: bool = True


class NativePluginCatalog(BaseModel):
    """One concrete native target's selected marketplace state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    marketplaces: tuple[NativeMarketplace, ...]
    plugins: tuple[NativePlugin, ...]
```

Add the target-aware models:

```python
class Marketplace(BaseModel):
    """A marketplace available to one or more native agents."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    targets: ConcreteTargets = Field(min_length=1)
    profiles: tuple[str, ...] = Field(default=("default",), min_length=1)


class NativeMarketplacePlugin(BaseModel):
    """A Claude Code or Codex marketplace plugin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["native-marketplace"]
    id: str = Field(min_length=1)
    marketplace: str = Field(min_length=1)
    targets: ConcreteTargets = Field(min_length=1)
    profiles: tuple[str, ...] = Field(default=("default",), min_length=1)
    required: bool = True


class CursorMarketplacePlugin(BaseModel):
    """A manual user-scoped Cursor marketplace selection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["cursor-marketplace"]
    id: str = Field(pattern=r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
    targets: ConcreteTargets = Field(min_length=1)
    profiles: tuple[str, ...] = Field(default=("default",), min_length=1)
    required: bool = True
    scope: Literal["user"]
    verification: Literal["manual"]


class CursorLocalPlugin(BaseModel):
    """A reviewed Cursor plugin tree managed below the native local root."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["cursor-local"]
    id: str = Field(pattern=r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
    source: PurePosixPath
    targets: ConcreteTargets = Field(min_length=1)
    profiles: tuple[str, ...] = Field(default=("default",), min_length=1)
    required: bool = True


PluginSpec = Annotated[
    NativeMarketplacePlugin | CursorMarketplacePlugin | CursorLocalPlugin,
    Field(discriminator="kind"),
]


class PluginCatalog(BaseModel):
    """Validated target-aware plugin declarations for every agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    marketplaces: tuple[Marketplace, ...]
    plugins: tuple[PluginSpec, ...]

    @model_validator(mode="after")
    def validate_marketplaces(self) -> Self:
        """Reject ambiguous or inconsistent target-aware declarations."""
        marketplace_by_target: dict[tuple[AgentName, str], Marketplace] = {}
        for marketplace in self.marketplaces:
            if AgentName.CURSOR in marketplace.targets:
                raise ValueError("native marketplaces cannot target cursor")
            for target in marketplace.targets:
                identity = (target, marketplace.name)
                if identity in marketplace_by_target:
                    raise ValueError(
                        f"duplicate marketplace identity: {target}:{marketplace.name}"
                    )
                marketplace_by_target[identity] = marketplace

        plugin_identities: set[tuple[AgentName, str]] = set()
        for plugin in self.plugins:
            if isinstance(plugin, NativeMarketplacePlugin):
                if AgentName.CURSOR in plugin.targets:
                    raise ValueError("native marketplace plugins cannot target cursor")
                if plugin.id.rpartition("@")[1:] != (
                    "@",
                    plugin.marketplace,
                ):
                    raise ValueError(f"plugin marketplace suffix mismatch: {plugin.id}")
                for target in plugin.targets:
                    marketplace = marketplace_by_target.get(
                        (target, plugin.marketplace)
                    )
                    if marketplace is None:
                        raise ValueError(
                            "plugin target is not covered by marketplace: "
                            f"{target}:{plugin.id}"
                        )
                    if not set(plugin.profiles).issubset(marketplace.profiles):
                        raise ValueError(
                            "plugin profiles must be a subset of marketplace "
                            f"profiles: {plugin.id}"
                        )
            elif plugin.targets != (AgentName.CURSOR,):
                raise ValueError("Cursor plugin variants must target only cursor")

            for target in plugin.targets:
                identity = (target, plugin.id)
                if identity in plugin_identities:
                    raise ValueError(f"duplicate plugin identity: {target}:{plugin.id}")
                plugin_identities.add(identity)
        return self
```

Update `_validate_concrete_targets()` to reject duplicates as well as
`AgentName.SHARED`.

Extend `SkillCatalog.validate_graph()` immediately after unknown-dependency
validation:

```python
for skill in self.skills:
    for dependency_name in skill.dependencies:
        dependency = by_name[dependency_name]
        if not set(skill.targets).issubset(dependency.targets):
            raise ValueError(
                f"dependency targets do not cover {skill.name}: {dependency_name}"
            )
        if not set(skill.profiles).issubset(dependency.profiles):
            raise ValueError(
                f"dependency profiles do not cover {skill.name}: {dependency_name}"
            )
```

`PluginCatalog.validate_marketplaces()` must build identities for every
concrete target and enforce:

- marketplaces and `native-marketplace` records target only Claude Code or
  Codex;
- Cursor variants target exactly Cursor;
- `(target, marketplace.name)` is unique;
- `(target, plugin.id)` is unique across all plugin variants;
- native target and profile sets are subsets of the matching marketplace;
- the suffix after `@` equals the marketplace name for every native record.

- [ ] **Step 4: Implement the pure projection**

In `desired_state.py`, add:

```python
class PluginCatalogProjection(BaseModel):
    """One immutable profile-filtered catalog for one concrete target."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target: ConcreteAgentName
    marketplaces: tuple[Marketplace, ...]
    native_plugins: tuple[NativeMarketplacePlugin, ...]
    cursor_marketplace_plugins: tuple[CursorMarketplacePlugin, ...]
    cursor_local_plugins: tuple[CursorLocalPlugin, ...]


def project_plugin_catalog(
    catalog: PluginCatalog,
    *,
    target: ConcreteAgentName,
    profiles: tuple[str, ...],
) -> PluginCatalogProjection:
    """Project a validated shared catalog to one target and profile set."""
    active = set(profiles)
    native = tuple(
        plugin.model_copy(update={"targets": (target,)})
        for plugin in catalog.plugins
        if isinstance(plugin, NativeMarketplacePlugin)
        and target in plugin.targets
        and active.intersection(plugin.profiles)
    )
    referenced = {plugin.marketplace for plugin in native}
    marketplaces = tuple(
        marketplace.model_copy(update={"targets": (target,)})
        for marketplace in catalog.marketplaces
        if target in marketplace.targets
        and marketplace.name in referenced
        and active.intersection(marketplace.profiles)
    )
    cursor_marketplace = tuple(
        plugin.model_copy(update={"targets": (target,)})
        for plugin in catalog.plugins
        if isinstance(plugin, CursorMarketplacePlugin)
        and target in plugin.targets
        and active.intersection(plugin.profiles)
    )
    cursor_local = tuple(
        plugin.model_copy(update={"targets": (target,)})
        for plugin in catalog.plugins
        if isinstance(plugin, CursorLocalPlugin)
        and target in plugin.targets
        and active.intersection(plugin.profiles)
    )
    return PluginCatalogProjection(
        target=target,
        marketplaces=tuple(sorted(marketplaces, key=lambda item: item.name)),
        native_plugins=tuple(sorted(native, key=lambda item: item.id)),
        cursor_marketplace_plugins=tuple(
            sorted(cursor_marketplace, key=lambda item: item.id)
        ),
        cursor_local_plugins=tuple(sorted(cursor_local, key=lambda item: item.id)),
    )
```

- [ ] **Step 5: Create the exact shared catalog**

Create `assistants/shared/plugins/catalog.yaml`:

```yaml
marketplaces:
  - name: bigspinai
    source: bigspinai/toolkit
    targets: [claude-code, codex]
    profiles: [default]
  - name: claude-context-mode
    source: mksglu/claude-context-mode
    targets: [claude-code]
    profiles: [default]
  - name: claude-plugins-official
    source: anthropics/claude-plugins-official
    targets: [claude-code, codex]
    profiles: [default]
  - name: context-mode
    source: mksglu/claude-context-mode
    targets: [codex]
    profiles: [default]
  - name: ponytail
    source: DietrichGebert/ponytail
    targets: [claude-code]
    profiles: [default]
  - name: prime-radiant-marketplace
    source: prime-radiant-inc/prime-radiant-marketplace
    targets: [claude-code]
    profiles: [default]
  - name: superpowers-marketplace
    source: obra/superpowers-marketplace
    targets: [claude-code, codex]
    profiles: [default]

plugins:
  - kind: native-marketplace
    id: bigspin@bigspinai
    marketplace: bigspinai
    targets: [claude-code, codex]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: context-mode@claude-context-mode
    marketplace: claude-context-mode
    targets: [claude-code]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: context-mode@context-mode
    marketplace: context-mode
    targets: [codex]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: frontend-design@claude-plugins-official
    marketplace: claude-plugins-official
    targets: [claude-code, codex]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: github@claude-plugins-official
    marketplace: claude-plugins-official
    targets: [codex]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: iterative-development@prime-radiant-marketplace
    marketplace: prime-radiant-marketplace
    targets: [claude-code]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: logfire@claude-plugins-official
    marketplace: claude-plugins-official
    targets: [claude-code, codex]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: ponytail@ponytail
    marketplace: ponytail
    targets: [claude-code]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: pydantic-ai@claude-plugins-official
    marketplace: claude-plugins-official
    targets: [claude-code]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: superpowers@claude-plugins-official
    marketplace: claude-plugins-official
    targets: [claude-code, codex]
    profiles: [default]
    required: true
  - kind: native-marketplace
    id: superpowers-developing-for-claude-code@superpowers-marketplace
    marketplace: superpowers-marketplace
    targets: [claude-code, codex]
    profiles: [default]
    required: true
```

Do not add a Cursor plugin record in this task.

- [ ] **Step 6: Preserve current adapter behavior under renamed native models**

Update Claude, Codex, and inventory imports so the two existing native YAML
files still parse as `NativePluginCatalog`. Do not yet change adapter
signatures or production inventory paths.

Run:

```bash
rtk uv run --frozen pytest tests/assistants/test_models.py tests/assistants/test_desired_state.py tests/assistants/test_claude.py tests/assistants/test_codex.py tests/assistants/test_inventory.py -q
rtk uv run --frozen mypy
```

Expected: all focused tests and strict typing pass.

- [ ] **Step 7: Commit the target-aware model**

Run:

```bash
rtk jj diff --summary
rtk jj describe -m "feat: add target-aware shared plugin catalog"
rtk jj bookmark move laptop-bootstrap-agent-consolidation --to @
rtk jj new
```

## Task 2: Cut Over to One Preflight-Loaded Desired State

**Files:**

- Modify: `src/ballen_config/assistants/desired_state.py`
- Create: `src/ballen_config/assistants/orchestrator.py`
- Modify: `src/ballen_config/assistants/inventory.py`
- Modify: `src/ballen_config/assistants/models.py`
- Modify: `src/ballen_config/assistants/__init__.py`
- Modify: `src/ballen_config/assistants/claude.py`
- Modify: `src/ballen_config/assistants/codex.py`
- Modify: `src/ballen_config/assistants/cursor.py`
- Modify: `src/ballen_config/assistants/skills.py`
- Modify: `src/ballen_config/cli.py`
- Modify: `assistants/inventory.yaml`
- Delete: `assistants/claude/plugins.yaml`
- Delete: `assistants/codex/plugins.yaml`
- Modify: `tests/assistants/test_inventory.py`
- Modify: `tests/assistants/test_claude.py`
- Modify: `tests/assistants/test_codex.py`
- Modify: `tests/assistants/test_cursor.py`
- Modify: `tests/assistants/test_skills.py`
- Modify: `tests/assistants/test_integration.py`
- Modify: `tests/test_cli.py`

**Interfaces:**

- Produces `AssistantDesiredState`.
- Produces `load_desired_state(repo_root, profiles, skipped)`.
- Produces `AssistantOrchestrator.preflight()` and bound supplier methods.
- Native adapters consume `PluginCatalogProjection`, never a YAML path.
- Shared skills consume `SkillCatalog`, never reread their YAML.
- Cursor extensions consume `ExtensionCatalog`, never reread their YAML.

- [ ] **Step 1: Write the inventory de-duplication tests**

Replace the item-order synchronization test with:

```python
def test_catalog_resource_rejects_flattened_item_ids() -> None:
    with pytest.raises(ValidationError):
        CatalogResource.model_validate(
            {
                "id": "shared.plugins.catalog",
                "kind": "catalog",
                "owner": "shared",
                "source": "assistants/shared/plugins/catalog.yaml",
                "catalog_kind": "plugin",
                "targets": ["cursor", "claude-code", "codex"],
                "item_ids": ["duplicate-state"],
            }
        )
```

Add:

- `test_inventory_loads_shared_plugin_catalog_without_mirrored_ids`
- `test_load_desired_state_validates_every_catalog_before_resolution`
- `test_skipped_agent_removes_only_its_projection`
- `test_all_agent_skips_still_validate_catalogs`

For the last three cases, assert against the loaded snapshot rather than
reopening YAML: a skipped target has no projection, an enabled target retains
exactly one projection, and all three catalog model types were validated even
when every concrete agent is skipped.

- [ ] **Step 2: Write preflight ordering and no-effects tests**

Add a `preflight_suppliers` recorder to `tests/test_cli.py` and assert its
event occurs before candidate, configuration, plan inspection, confirmation,
install, configure, and doctor events.

Add this integration matrix:

```python
@pytest.mark.parametrize(
    "arguments",
    [
        ("plan",),
        ("install",),
        ("configure",),
        ("doctor",),
        ("all",),
    ],
)
def test_invalid_shared_catalog_stops_before_native_or_state_mutation(
    invalid_repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    arguments: tuple[str, ...],
) -> None:
    paths = RuntimePaths.from_roots(
        repo_root=invalid_repo_root,
        home=temporary_home,
    )
    orchestrator = AssistantOrchestrator(paths)
    result = run(
        arguments,
        repo_root=invalid_repo_root,
        home=temporary_home,
        runner=fake_runner,
        downloader=fake_runner,
        confirm=lambda _prompt: pytest.fail("confirmation after failed preflight"),
        output=lambda _message: None,
        timestamp=lambda: "20260726T120000Z",
        preflight_suppliers=(orchestrator.preflight,),
        install_action_candidate_suppliers=(orchestrator.install_action_candidates,),
        install_action_suppliers=(orchestrator.install_actions,),
        configuration_suppliers=(orchestrator.configuration,),
        doctor_check_suppliers=(orchestrator.doctor_checks,),
        plan_contributors=(orchestrator,),
    )
    assert result.exit_code == 2
    assert result.report.outcomes == ("assistant desired-state preflight failed",)
    assert fake_runner.commands == []
    assert list(temporary_home.iterdir()) == []
```

The `invalid_repo_root` fixture must copy the tracked manifests and assistant
sources into `tmp_path`, then replace
`assistants/shared/plugins/catalog.yaml` with schema-invalid YAML. It must not
write inside the real checkout.

- [ ] **Step 3: Run the new tests and verify current ordering fails**

Run:

```bash
rtk uv run --frozen pytest tests/assistants/test_inventory.py tests/assistants/test_desired_state.py tests/test_cli.py tests/assistants/test_integration.py -q
```

Expected: failures identify `item_ids`, absent desired state, and native
inspection occurring without the new preflight seam.

- [ ] **Step 4: Load inventory and catalogs into one immutable snapshot**

Delete `item_ids` from `CatalogResource`.

In `inventory.py`, replace `_catalog_ids()` with a typed loader selected by
`CatalogKind`:

```python
type CatalogDocument = ExtensionCatalog | PluginCatalog | SkillCatalog


class LoadedCatalog(BaseModel):
    """One inventory catalog parsed from one immutable file read."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_id: str
    document: CatalogDocument


class LoadedInventory(BaseModel):
    """Validated inventory plus every parsed catalog document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    inventory: AssistantInventory
    catalogs: tuple[LoadedCatalog, ...]
```

`load_inventory()` must:

1. validate inventory YAML;
2. validate every source path for containment and existence;
3. read each catalog exactly once;
4. parse it according to `CatalogKind`;
5. return `LoadedInventory` without comparing a flattened identifier list.

Update `resolve_inventory()` callers to pass `loaded.inventory`.

Change the production inventory to:

```yaml
- id: shared.skills.catalog
  kind: catalog
  owner: shared
  source: assistants/shared/skills/catalog.yaml
  catalog_kind: skill
  targets: [cursor, claude-code, codex]

- id: shared.plugins.catalog
  kind: catalog
  owner: shared
  source: assistants/shared/plugins/catalog.yaml
  catalog_kind: plugin
  targets: [cursor, claude-code, codex]
```

Keep `cursor.extensions.catalog`, without `item_ids`. Remove
`claude.plugins.catalog` and `codex.plugins.catalog`.

- [ ] **Step 5: Implement the immutable desired state**

Add:

```python
class AssistantDesiredState(BaseModel):
    """All validated assistant desired state for one resolved invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    inventory: AssistantInventory
    resolved_inventory: ResolvedInventory
    extension_catalog: ExtensionCatalog
    skill_catalog: SkillCatalog
    plugin_catalog: PluginCatalog
    plugin_projections: tuple[PluginCatalogProjection, ...]

    def plugin_projection(
        self,
        target: ConcreteAgentName,
    ) -> PluginCatalogProjection:
        """Return the one projection for an enabled concrete target."""
        matches = tuple(
            projection
            for projection in self.plugin_projections
            if projection.target is target
        )
        if len(matches) != 1:
            raise ValueError(f"missing plugin projection: {target.value}")
        return matches[0]
```

`load_desired_state()` must:

1. call `load_inventory()` once;
2. locate the already parsed extension, skill, and shared plugin documents by
   stable resource ID and asserted model type;
3. validate all three catalogs before applying skips;
4. resolve inventory profiles/skips;
5. create projections only for enabled concrete targets;
6. return one frozen `AssistantDesiredState`.

Normalize read, YAML, and Pydantic failures as:

```python
class AssistantDesiredStateError(ValueError):
    """A secret-free assistant desired-state preflight failure."""
```

Raise it with the stable message `assistant desired-state preflight failed`
without embedding YAML contents, native output, or absolute home paths.

- [ ] **Step 6: Refactor the native planners to consume projections**

Use:

```python
def plan_claude_plugins(
    catalog: PluginCatalogProjection,
    *,
    installed: frozenset[str],
    known_marketplaces: frozenset[str] = frozenset(),
) -> tuple[InstallAction, ...]:
    """Plan Claude actions from one Claude-only projection."""
```

and:

```python
def plan_codex_plugins(
    catalog: PluginCatalogProjection,
    *,
    installed: frozenset[str],
    known_marketplaces: frozenset[str] = frozenset(),
) -> tuple[InstallAction, ...]:
    """Plan Codex actions from one Codex-only projection."""
```

Each function must reject the wrong `catalog.target`, use only
`catalog.marketplaces` and `catalog.native_plugins`, and retain the existing
native command order and requiredness.

Remove YAML imports and `_catalog()` from both adapters. Their native
inspection functions must accept the projection before invoking `Runner`.

Change Cursor extension planning to accept an `ExtensionCatalog`, and change
shared-skill configuration to accept a `SkillCatalog`.

Delete:

```text
assistants/claude/plugins.yaml
assistants/codex/plugins.yaml
```

- [ ] **Step 7: Add the explicit orchestration/preflight seam**

In `cli.py`, add:

```python
type PreflightSupplier = Callable[[ResolvedSetup, RuntimePaths], None]
```

Add `preflight_suppliers` to `run()`. Invoke every preflight supplier
immediately after manifest resolution and before candidate actions,
configuration suppliers, `ResolvedInspector`, confirmation, or stage
execution.

Catch `AssistantDesiredStateError` before the broad invalid-configuration
handler and return:

```python
RunResult(
    exit_code=2,
    report=StageReport(
        outcomes=("assistant desired-state preflight failed",),
    ),
)
```

Create `AssistantOrchestrator` with:

```python
class AssistantOrchestrator:
    """Reuse one preflight-loaded desired state across assistant seams."""

    def __init__(self, paths: RuntimePaths) -> None:
        self.paths = paths
        self._desired: AssistantDesiredState | None = None
        self._key: tuple[Path, tuple[str, ...], frozenset[str]] | None = None

    def preflight(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
    ) -> None:
        """Load desired state exactly once before any assistant side effect."""

    def install_action_candidates(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
    ) -> tuple[InstallAction, ...]:
        """Return candidates from the preloaded projections."""

    def install_actions(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
        runner: Runner,
    ) -> tuple[InstallAction, ...]:
        """Inspect and plan each enabled native target."""

    def configuration(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
    ) -> ConfigurationContribution:
        """Compose target configuration from preloaded models."""

    def doctor_checks(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
        runner: Runner,
    ) -> tuple[DoctorCheck, ...]:
        """Diagnose enabled targets from preloaded models."""

    def actions(
        self,
        setup: ResolvedSetup,
    ) -> tuple[PlanAction, ...]:
        """Render resolved inventory without reopening catalogs."""
```

Every method other than `preflight()` must fail closed if `_desired is None`.
`preflight()` must reject a different `RuntimePaths` or resolved profile/skip
key after the first load.

Instantiate one orchestrator in `main()` and in
`tests.assistants.test_integration.run_with_assistants()`. Pass its bound
methods to all five supplier/contributor seams.

- [ ] **Step 8: Run focused behavior and strict typing**

Run:

```bash
rtk uv run --frozen pytest tests/assistants/test_inventory.py tests/assistants/test_desired_state.py tests/assistants/test_claude.py tests/assistants/test_codex.py tests/assistants/test_cursor.py tests/assistants/test_skills.py tests/assistants/test_integration.py tests/test_cli.py -q
rtk uv run --frozen ruff check src tests
rtk uv run --frozen ruff format --check src tests
rtk uv run --frozen mypy
rtk rg -n 'assistants/(claude|codex)/plugins.yaml|item_ids' src assistants
```

Expected:

- all tests and type checks pass;
- the final search returns no production or test references.

- [ ] **Step 9: Commit the atomic preflight cutover**

Run:

```bash
rtk jj diff --summary
rtk jj describe -m "refactor: preflight shared agent desired state"
rtk jj bookmark move laptop-bootstrap-agent-consolidation --to @
rtk jj new
```

## Task 3: Add Native Cursor Plugin Planning

**Files:**

- Create: `src/ballen_config/assistants/cursor_plugins.py`
- Modify: `src/ballen_config/assistants/skills.py`
- Modify: `src/ballen_config/assistants/desired_state.py`
- Modify: `src/ballen_config/assistants/orchestrator.py`
- Modify: `src/ballen_config/assistants/__init__.py`
- Create: `tests/assistants/test_cursor_plugins.py`
- Modify: `tests/assistants/test_checks.py`
- Modify: `tests/assistants/test_integration.py`

**Interfaces:**

- Produces `validate_cursor_local_plugin() -> Path`.
- Produces `cursor_local_plugin_configuration()`.
- Produces `cursor_marketplace_plan_actions()`.
- Produces `cursor_marketplace_doctor_checks()`.
- Reuses `ManagedTreeSpec` and `ConfigurationEngine`; creates no private
  Cursor-state reader.

- [ ] **Step 1: Write the Cursor manual-action tests**

Use a synthetic `CursorMarketplacePlugin` fixture and assert:

```python
def test_cursor_marketplace_is_always_manual_without_runner_state() -> None:
    plugin = CursorMarketplacePlugin.model_validate(
        {
            "kind": "cursor-marketplace",
            "id": "example-plugin",
            "targets": ["cursor"],
            "profiles": ["default"],
            "required": True,
            "scope": "user",
            "verification": "manual",
        }
    )
    plan = cursor_marketplace_plan_actions((plugin,))
    checks = cursor_marketplace_doctor_checks((plugin,))

    assert plan == (
        PlanAction(
            component_id="cursor.plugin.example-plugin",
            category="manual",
            action="open-cursor-customize-add-plugin",
            owner="cursor",
            required=True,
        ),
    )
    assert checks[0].id == "cursor.plugin.example-plugin"
    assert checks[0].status is FindingStatus.MANUAL
    assert checks[0].severity is CheckSeverity.INFO
    assert "required" in checks[0].message
```

Add the optional wording case. Neither function receives a runner, cache path,
database path, or acknowledgement state.

- [ ] **Step 2: Write reviewed local-tree tests**

Create a pytest fixture:

```python
@pytest.fixture
def cursor_local_plugin_source(tmp_path: Path) -> Path:
    """Create a valid reviewed local Cursor plugin tree."""
    root = tmp_path / "repo/assistants/shared/plugins/local/example-local"
    (root / ".cursor-plugin").mkdir(parents=True)
    (root / ".cursor-plugin/plugin.json").write_text(
        '{"name":"example-local"}\n',
        encoding="utf-8",
    )
    (root / "skills/example-skill").mkdir(parents=True)
    (root / "skills/example-skill/SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Example.\n---\n",
        encoding="utf-8",
    )
    return root
```

Add:

- `test_cursor_local_plugin_requires_canonical_contained_source`
- `test_cursor_local_plugin_requires_strict_matching_manifest`
- `test_cursor_local_plugin_rejects_symlink_and_special_descendants`
- `test_cursor_local_plugin_rejects_declared_skill_path_escape`
- `test_cursor_local_plugin_rejects_shared_skill_name_collision`
- `test_cursor_local_plugin_configuration_uses_native_managed_tree`
- `test_cursor_local_plugin_preserves_unmanaged_collision`
- `test_cursor_local_plugin_managed_update_backup_and_rollback`

For the contribution assertion:

```python
assert contribution.specs == (
    ManagedTreeSpec(
        id="cursor-local-plugin-example-local",
        source=source,
        destination=Path(".cursor/plugins/local/example-local"),
        component="cursor",
    ),
)
```

Exercise collision, backup, atomic replacement, and rollback through the real
`ConfigurationEngine`; do not duplicate its copy implementation.

- [ ] **Step 3: Run tests and verify the Cursor plugin module is absent**

Run:

```bash
rtk uv run --frozen pytest tests/assistants/test_cursor_plugins.py tests/assistants/test_checks.py -q
```

Expected: import or collection failures identify the missing module and
interfaces.

- [ ] **Step 4: Expose bounded skill-name parsing**

Rename `_declared_name()` in `skills.py` to:

```python
def declared_skill_name(root: Path) -> str:
    """Return a bounded, validated skill name from one regular tree."""
```

Update existing callers and preserve every current frontmatter bound and error.

- [ ] **Step 5: Implement reviewed local-plugin source validation**

In `cursor_plugins.py`, define a narrow manifest:

```python
class CursorPluginManifest(BaseModel):
    """The documented Cursor manifest fields needed by this bootstrap."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str
    skills: str | tuple[str, ...] | None = None
```

Implement:

```python
def validate_cursor_local_plugin(
    plugin: CursorLocalPlugin,
    *,
    repo_root: Path,
    shared_skill_names: frozenset[str],
) -> Path:
    """Return a safe canonical Cursor local-plugin source tree."""
```

The function must:

1. require the exact canonical path
   `assistants/shared/plugins/local/<plugin.id>`;
2. contain it beneath `repo_root` without symlinked components;
3. call `digest_tree(source)` to reject every symlink or special descendant;
4. strictly decode `.cursor-plugin/plugin.json` with `strict_json_loads`;
5. require the manifest name to equal `plugin.id`;
6. resolve default `skills/`, root `SKILL.md`, or explicit manifest skill
   paths without absolute paths or `..`;
7. use `declared_skill_name()` for every discovered skill tree;
8. reject names in `shared_skill_names` with
   `cursor local plugin skill collision: <name>`.

Implement:

```python
def cursor_local_plugin_configuration(
    plugins: tuple[CursorLocalPlugin, ...],
    *,
    repo_root: Path,
    shared_skill_names: frozenset[str],
) -> ConfigurationContribution:
    """Return atomic native local-plugin tree specifications."""
```

Return one deterministically sorted `ManagedTreeSpec` per validated plugin.

- [ ] **Step 6: Implement the manual plan and doctor projections**

Add:

```python
def cursor_marketplace_plan_actions(
    plugins: tuple[CursorMarketplacePlugin, ...],
) -> tuple[PlanAction, ...]:
    """Return deterministic user-scope Customize checklist actions."""


def cursor_marketplace_doctor_checks(
    plugins: tuple[CursorMarketplacePlugin, ...],
) -> tuple[DoctorCheck, ...]:
    """Always report Cursor marketplace entries as informational manual work."""
```

Required and optional records differ only in wording and `PlanAction.required`.
Both doctor results use `FindingStatus.MANUAL` and `CheckSeverity.INFO`.

Add marketplace results only to the orchestrator's `actions()` and
`doctor_checks()` methods. Add reviewed local-plugin `ManagedTreeSpec`s only
to `configuration()`. Do not add either variant to install candidates or
install actions; with the initial empty Cursor plugin list, all three additions
are empty.

During desired-state preflight, validate every declared local source before
any profile or skip removes its runtime projection. Use the shared skill
catalog's Cursor-targeted names for collision checks.

- [ ] **Step 7: Add integration coverage for native isolation**

Add a fixture that copies the checkout into `tmp_path`, appends one synthetic
Cursor marketplace record to the shared catalog, and returns the copied root.
Then add:

```python
def test_cursor_marketplace_never_reads_private_state_or_runs_command(
    cursor_marketplace_repo: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_roots = (
        temporary_home / ".cursor/plugins/cache",
        temporary_home / "Library/Application Support/Cursor/User/globalStorage",
    )
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if any(path == root or path.is_relative_to(root) for root in private_roots):
            pytest.fail(f"private Cursor state read: {path.name}")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    plan_output: list[str] = []
    doctor_output: list[str] = []
    planned = run_with_assistants(
        ("plan",),
        repo_root=cursor_marketplace_repo,
        home=temporary_home,
        runner=fake_runner,
        output=plan_output,
    )
    diagnosed = run_with_assistants(
        ("doctor",),
        repo_root=cursor_marketplace_repo,
        home=temporary_home,
        runner=fake_runner,
        output=doctor_output,
    )

    assert planned.exit_code == diagnosed.exit_code == 0
    assert "cursor.plugin.example-plugin" in "\n".join(plan_output)
    assert "cursor.plugin.example-plugin" in "\n".join(doctor_output)
    assert not any(
        command[0].startswith("cursor") and "plugin" in command[1:]
        for command in fake_runner.commands
    )
```

Add another copied-checkout fixture containing a canonical reviewed local
plugin and its synthetic catalog record. Then add:

```python
def test_cursor_local_plugin_converges_and_is_idempotent(
    cursor_local_plugin_repo: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    first = run_with_assistants(
        ("configure",),
        repo_root=cursor_local_plugin_repo,
        home=temporary_home,
        runner=fake_runner,
    )
    destination = temporary_home / ".cursor/plugins/local/example-local"
    first_snapshot = {
        path.relative_to(destination): path.read_bytes()
        for path in sorted(destination.rglob("*"))
        if path.is_file()
    }
    second = run_with_assistants(
        ("configure",),
        repo_root=cursor_local_plugin_repo,
        home=temporary_home,
        runner=fake_runner,
    )
    second_snapshot = {
        path.relative_to(destination): path.read_bytes()
        for path in sorted(destination.rglob("*"))
        if path.is_file()
    }
    paths = RuntimePaths.from_roots(
        repo_root=cursor_local_plugin_repo,
        home=temporary_home,
    )
    state = StateStore(paths).load()

    assert first.exit_code == second.exit_code == 0
    assert first.report.changed_count >= 1
    assert second.report.changed_count == 0
    assert second_snapshot == first_snapshot
    assert "cursor-local-plugin-example-local" in state.managed
    assert not paths.backup_root.exists()
```

Add a security-focused preflight fixture and all-stage matrix:

```python
@pytest.fixture
def invalid_cursor_local_plugin_repo(
    repo_root: Path,
    tmp_path: Path,
) -> Path:
    """Copy the checkout with a valid declaration and mismatched local tree."""
    copied = tmp_path / "invalid-cursor-local-repo"
    shutil.copytree(
        repo_root,
        copied,
        ignore=shutil.ignore_patterns(
            ".git",
            ".jj",
            ".venv",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
            "__pycache__",
        ),
    )
    source = copied / "assistants/shared/plugins/local/example-local"
    (source / ".cursor-plugin").mkdir(parents=True)
    (source / ".cursor-plugin/plugin.json").write_text(
        '{"name":"different-name"}\n',
        encoding="utf-8",
    )
    catalog_path = copied / "assistants/shared/plugins/catalog.yaml"
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    payload["plugins"].append(
        {
            "kind": "cursor-local",
            "id": "example-local",
            "source": ("assistants/shared/plugins/local/example-local"),
            "targets": ["cursor"],
            "profiles": ["default"],
            "required": True,
        }
    )
    catalog_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return copied


@pytest.mark.parametrize(
    "stage",
    ["plan", "install", "configure", "doctor", "all"],
)
@pytest.mark.parametrize("skip_all", [False, True], ids=["enabled", "all-skipped"])
def test_invalid_cursor_local_tree_fails_preflight_without_effects(
    invalid_cursor_local_plugin_repo: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    stage: str,
    skip_all: bool,
) -> None:
    arguments: tuple[str, ...] = (stage,)
    if skip_all:
        arguments += (
            "--skip",
            "cursor",
            "--skip",
            "claude-code",
            "--skip",
            "codex",
        )

    result = run_with_assistants(
        arguments,
        repo_root=invalid_cursor_local_plugin_repo,
        home=temporary_home,
        runner=fake_runner,
    )
    paths = RuntimePaths.from_roots(
        repo_root=invalid_cursor_local_plugin_repo,
        home=temporary_home,
    )

    assert result.exit_code == 2
    assert result.report.outcomes == ("assistant desired-state preflight failed",)
    assert fake_runner.commands == []
    assert not paths.state_root.exists()
    assert not paths.backup_root.exists()
    assert not (temporary_home / ".cursor/plugins/local").exists()
```

This matrix must fail for the manifest-name mismatch, not schema-invalid YAML.
It proves local-source validation happens before skips, native inspection,
confirmation, state creation, destination creation, or backup creation.

Extend the existing skill-check test so byte-identical copies in
`.cursor/skills`, `.claude/skills`, `.agents/skills`, and `.codex/skills`
produce no collision, while one changed copy produces a names-only collision.

- [ ] **Step 8: Run Cursor-focused and aggregate verification**

Run:

```bash
rtk uv run --frozen pytest tests/assistants/test_cursor_plugins.py tests/assistants/test_cursor.py tests/assistants/test_checks.py tests/assistants/test_integration.py -q
rtk uv run --frozen ruff check src/ballen_config/assistants tests/assistants
rtk uv run --frozen ruff format --check src/ballen_config/assistants tests/assistants
rtk uv run --frozen mypy
```

Expected: all checks pass without a production Cursor plugin declaration.

- [ ] **Step 9: Commit Cursor support**

Run:

```bash
rtk jj diff --summary
rtk jj describe -m "feat: add native Cursor plugin planning"
rtk jj bookmark move laptop-bootstrap-agent-consolidation --to @
rtk jj new
```

## Task 4: Document, Verify, and Publish the Consolidation Branch

**Files:**

- Modify: `README.md:64-86`
- Modify: `docs/manual-steps.md`
- Modify: `docs/promoting-shared-skills.md`
- Modify:
  `docs/superpowers/specs/2026-07-25-laptop-migration-bootstrap-design.md`
- Modify: cross-cutting tests only if documentation assertions require it

**Interfaces:**

- Produces user-facing rationale matching the approved amendment.
- Produces a clean remote branch and stacked PR based on
  `laptop-bootstrap-review`.

- [ ] **Step 1: Update the operational rationale**

Document these exact boundaries:

- `ballen-config` is the only desired-state source;
- shared declarations may target several agents, but adapters install each
  native destination independently;
- Cursor cross-tool import is neither configured nor required, and correctness
  is identical whether it is enabled or disabled;
- Cursor marketplace entries remain visible manual checklist items;
- reviewed local plugins go only to
  `~/.cursor/plugins/local/<name>`;
- caches, private databases, authentication, sessions, and histories remain
  excluded;
- new GUI installations are audited and deliberately added, never ingested
  automatically.

In `docs/manual-steps.md`, add this recommendation:

> In Cursor, open **Settings → Rules, Skills, Subagents** (or
> **Customize**) and turn off **Include Third-Party Plugins, Skills, and Other
> Configs** so each coding agent's desired state stays explicit. This is a
> recommendation, not a prerequisite: the bootstrap remains correct and
> idempotent if the setting stays enabled.

In the original 2026-07-25 design, replace the sentence that all Cursor
marketplace identifiers are merely outside bootstrap support. Link to the
approved 2026-07-26 amendment for the target-aware behavior.

- [ ] **Step 2: Run the complete automated verification**

Run:

```bash
rtk uv run --frozen pytest -q
rtk uv run --frozen ruff check .
rtk uv run --frozen ruff format --check src tests
rtk uv run --frozen mypy
rtk uv run --frozen python -m ballen_config.policy
rtk uv run --frozen pre-commit run --all-files
```

Expected: every command passes.

- [ ] **Step 3: Run read-only local smoke checks**

Run:

```bash
rtk ./bootstrap plan --profile default
rtk ./bootstrap doctor --profile default
```

Expected:

- both commands complete without authentication or mutation;
- no Piste action appears;
- `jujutsu-workflow` is planned or ready independently for enabled agents;
- no Cursor private plugin state is read;
- no marketplace plugin is falsely reported as installed.

- [ ] **Step 4: Commit documentation and record a clean tip**

Run:

```bash
rtk jj diff --summary
rtk jj describe -m "docs: explain independent agent desired state"
rtk jj bookmark move laptop-bootstrap-agent-consolidation --to @
rtk jj new
rtk jj status
```

Expected: the working copy is an empty child of the final consolidation
commit.

- [ ] **Step 5: Push and create the stacked PR**

Run:

```bash
rtk jj git fetch
rtk jj git push --bookmark laptop-bootstrap-agent-consolidation
rtk gh pr create --base laptop-bootstrap-review --head laptop-bootstrap-agent-consolidation --title "refactor: consolidate coding-agent desired state" --body "## Summary

- consolidate Claude Code, Codex, and Cursor plugin intent into one target-aware catalog
- preflight all assistant catalogs before native inspection or configuration mutation
- keep each agent independently managed and add safe Cursor manual/local plugin boundaries
- remove duplicated inventory item IDs

## Validation

- full pytest, Ruff, mypy, policy, and pre-commit suites
- read-only local plan and doctor smoke checks

Stacked on #3."
```

If a PR already exists for this head bookmark, use `gh pr edit` with the same
base, title, and body instead of creating a duplicate.

- [ ] **Step 6: Verify the final stack and checks**

Run:

```bash
rtk gh pr view laptop-bootstrap-agent-consolidation --json baseRefName,headRefName,mergeable,state,url
rtk gh pr diff laptop-bootstrap-agent-consolidation --name-only
rtk gh pr checks laptop-bootstrap-agent-consolidation
rtk jj log -r 'main::laptop-bootstrap-agent-consolidation'
rtk jj status
```

Expected:

- PR base/head are `laptop-bootstrap-review` /
  `laptop-bootstrap-agent-consolidation`;
- the diff contains only the approved consolidation stack above PR3;
- required checks pass;
- the working copy remains empty.
