# Coding-Agent Portability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recreate the portable parts of Cursor, Claude Code, and Codex on a new Mac while preserving local authentication and runtime state, supporting whole-agent skips, and giving shared skills and hooks one reviewed source.

**Architecture:** Extend the core bootstrap through its typed selection, installation, managed-file, and doctor seams. A Pydantic inventory resolves resources by profile and enabled agent; agent adapters translate reviewed shared sources into each tool's native files and CLI actions. Generated state, credentials, sessions, project trust, local MCP servers, and repository-specific tooling remain outside the generic migration.

**Tech Stack:** Python 3.12, Pydantic 2.8, PyYAML, pytest fixtures, Cursor CLI, Claude Code CLI, Codex CLI, Homebrew, Jujutsu

---

## Scope and dependency

Implement this plan only after
`docs/superpowers/plans/2026-07-25-laptop-bootstrap-core.md` is complete.
Reuse these core contracts rather than duplicating them:

- `ResolvedSetup.is_enabled(component_id)` and the whole-component skip set.
- `RuntimePaths`, `Runner`, and redacted `CommandResult`.
- `InstallAction`, including its core-owned `verified-download` variant,
  injected `Downloader`, private temporary directory, digest/size checks,
  cleanup, and required/optional failure policy.
- `ManagedFileSpec`, `ManagedTreeSpec`, and `ConfigEngine.plan()` /
  `ConfigEngine.apply()`.
- `DoctorCheck`, `DoctorFinding`, `FindingStatus`, and `run_doctor()`.
- `InstallActionSupplier`, `ConfigurationContribution`,
  `ConfigurationSupplier`, and `DoctorCheckSupplier`.
- Tracked-tree policy checks and deterministic state/report persistence.

The component IDs are `cursor`, `claude-code`, and `codex`. Skipping one of
those IDs must remove all of that agent's application, settings,
instructions, extensions/plugins, skills, hooks, manual actions, and required
doctor findings. Shared resources may still target the remaining enabled
agents.

This plan deliberately excludes:

- Session, prompt, transcript, conversation, task, history, telemetry, cache,
  database, log, and backup directories.
- OAuth tokens, API keys, cloud credentials, SSH keys, GitHub/GitLab auth,
  Codex auth, Claude auth, Cursor login state, and account identifiers.
- Codex trust entries, project paths, runtime feature state, notification
  commands, generated marketplace/cache paths, and machine-specific sandbox
  state.
- Local/global Playwright, GitLab, or Notion MCP servers. Browser automation
  uses each agent's first-party capability; GitLab uses `glab`; Notion uses
  official connectors.
- Cursor worktrees. They are disposable working state, not configuration.
- Plato plugins, Plato-qualified skills, repository instructions, and other
  repository-specific resources. Those belong in a later repo add-on.
- Memory transfer. It is post-MVP and is not represented by models, manifests,
  commands, tests, or documentation in this plan.

## File map

Create:

```text
assistants/
├── inventory.yaml
├── shared/
│   ├── hooks/
│   │   └── rtk-hook
│   ├── instructions/
│   │   ├── engineering.md
│   │   └── rtk.md
│   └── skills/
│       └── catalog.yaml
├── cursor/
│   ├── extensions.yaml
│   ├── hooks.json
│   ├── keybindings.json
│   ├── settings.base.json
│   ├── settings.work.json
│   └── user-rules.md
├── claude/
│   ├── CLAUDE.md
│   ├── plugins.yaml
│   └── settings.json
└── codex/
    ├── AGENTS.md
    ├── config.overlay.toml
    └── plugins.yaml
docs/
└── promoting-shared-skills.md
src/ballen_config/assistants/
├── __init__.py
├── checks.py
├── claude.py
├── codex.py
├── cursor.py
├── hooks.py
├── instructions.py
├── inventory.py
├── models.py
└── skills.py
tests/assistants/
├── __init__.py
├── conftest.py
├── fakes.py
├── test_checks.py
├── test_claude.py
├── test_codex.py
├── test_cursor.py
├── test_hooks.py
├── test_integration.py
├── test_inventory.py
├── test_models.py
└── test_skills.py
```

Modify:

```text
README.md
CLAUDE.md
docs/manual-steps.md
src/ballen_config/cli.py
src/ballen_config/configure.py
src/ballen_config/doctor.py
src/ballen_config/install.py
src/ballen_config/policy.py
tests/test_docs.py
tests/test_policy.py
```

Move reviewed legacy sources:

```text
cursor/settings.json
  -> assistants/cursor/settings.base.json
cursor/keybindings.json
  -> assistants/cursor/keybindings.json
claude-code/settings.json
  -> assistants/claude/settings.json
```

Delete after the replacement tests pass:

```text
cursor/extensions.txt
claude-code/
cursor/                         # only after it is empty
```

Do not copy files out of `~/.cursor`, `~/.claude`, `~/.codex`, or plugin cache
directories wholesale. Every tracked source in `assistants/` must be authored
or individually reviewed.

### Task 1: Define and resolve the coding-agent inventory

**Files:**

- Create: `src/ballen_config/assistants/__init__.py`
- Create: `src/ballen_config/assistants/models.py`
- Create: `src/ballen_config/assistants/inventory.py`
- Create: `assistants/inventory.yaml`
- Create: `assistants/shared/skills/catalog.yaml`
- Create: `tests/__init__.py`
- Create: `tests/assistants/__init__.py`
- Create: `tests/assistants/conftest.py`
- Create: `tests/assistants/fakes.py`
- Create: `tests/assistants/test_models.py`
- Create: `tests/assistants/test_inventory.py`

- [ ] **Step 1: Write the inventory-model failure tests**

Use pytest fixtures for repository and temporary-home paths:

```python
# tests/assistants/fakes.py
import json
from collections.abc import Sequence
from pathlib import Path

from ballen_config.runner import CommandResult


class StatefulAssistantFake:
    """Stateful runner and downloader for assistant integration tests."""

    def __init__(self, home: Path) -> None:
        self.home = home
        self.results: dict[tuple[str, ...], CommandResult] = {}
        self.commands: list[tuple[str, ...]] = []
        self.downloads: list[tuple[str, Path]] = []
        self.cursor_extensions: set[str] = set()
        self.claude_marketplaces: set[str] = set()
        self.claude_plugins: set[str] = set()
        self.codex_marketplaces: set[str] = set()
        self.codex_plugins: set[str] = set()
        self.payloads: dict[str, bytes] = {}
        self.downloaded_extension_ids: dict[Path, str] = {}
        self.allow_unmodeled_core_commands = False
        self.marketplace_names = {
            "anthropics/claude-plugins-official": (
                "claude-plugins-official"
            ),
            "obra/superpowers-marketplace": "superpowers-marketplace",
            "mksglu/claude-context-mode": "claude-context-mode",
            "bigspinai/toolkit": "bigspinai",
            "prime-radiant-inc/prime-radiant-marketplace": (
                "prime-radiant-marketplace"
            ),
            "DietrichGebert/ponytail": "ponytail",
            (
                "git@gitlab.com:flagship-informatics/"
                "internal-open-source/piste.git"
            ): "piste",
            "context-mode": "context-mode",
        }

    def add(
        self,
        command: tuple[str, ...],
        *,
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Register one exact command result."""
        self.results[command] = {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    def add_vsix(
        self,
        *,
        url: str,
        payload: bytes,
        extension_id: str,
    ) -> None:
        """Register verified bytes and the extension installed from them."""
        self.payloads[url] = payload
        self.downloaded_extension_ids[
            Path("vscode-jj-graph.vsix")
        ] = extension_id

    def satisfy_core_commands(self) -> None:
        """Let the already-tested core package commands succeed."""
        self.allow_unmodeled_core_commands = True

    def download(
        self,
        *,
        url: str,
        destination: Path,
        maximum_bytes: int,
    ) -> None:
        """Write registered bytes without network access."""
        payload = self.payloads[url]
        if len(payload) > maximum_bytes:
            raise ValueError("payload exceeds maximum_bytes")
        destination.write_bytes(payload)
        extension_id = self.downloaded_extension_ids[
            Path(destination.name)
        ]
        self.downloaded_extension_ids[destination] = extension_id
        self.downloads.append((url, destination))

    def _update_claude_settings(
        self,
        *,
        marketplace: tuple[str, str] | None = None,
        plugin: str | None = None,
    ) -> None:
        """Model the Claude CLI fields that configure must preserve."""
        path = self.home / ".claude/settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        document = json.loads(path.read_text()) if path.exists() else {}
        if marketplace is not None:
            name, source = marketplace
            document.setdefault("extraKnownMarketplaces", {})[name] = {
                "source": source
            }
        if plugin is not None:
            document.setdefault("enabledPlugins", {})[plugin] = True
        path.write_text(json.dumps(document, indent=2) + "\n")

    def run(self, command: Sequence[str]) -> CommandResult:
        """Run one modeled native command and update observable state."""
        normalized = tuple(command)
        self.commands.append(normalized)
        if normalized in self.results:
            return self.results[normalized]
        if normalized == ("cursor", "--list-extensions"):
            return {
                "returncode": 0,
                "stdout": "\n".join(sorted(self.cursor_extensions)),
                "stderr": "",
            }
        if normalized[:2] == ("cursor", "--install-extension"):
            operand = normalized[2]
            extension_id = self.downloaded_extension_ids.get(
                Path(operand),
                operand,
            )
            self.cursor_extensions.add(extension_id)
            return {"returncode": 0, "stdout": "", "stderr": ""}
        if normalized == ("claude", "plugin", "list", "--json"):
            payload = {
                "plugins": [
                    {"id": plugin}
                    for plugin in sorted(self.claude_plugins)
                ],
                "marketplaces": [
                    {"name": marketplace}
                    for marketplace in sorted(self.claude_marketplaces)
                ],
            }
            return {
                "returncode": 0,
                "stdout": json.dumps(payload),
                "stderr": "",
            }
        if normalized[:4] == (
            "claude",
            "plugin",
            "marketplace",
            "add",
        ):
            source = normalized[-1]
            name = self.marketplace_names.get(
                source,
                source.rsplit("/", maxsplit=1)[-1].removesuffix(".git"),
            )
            self.claude_marketplaces.add(name)
            self._update_claude_settings(marketplace=(name, source))
            return {"returncode": 0, "stdout": "", "stderr": ""}
        if normalized[:3] == ("claude", "plugin", "install"):
            plugin = normalized[-1]
            self.claude_plugins.add(plugin)
            self._update_claude_settings(plugin=plugin)
            return {"returncode": 0, "stdout": "", "stderr": ""}
        if normalized == ("codex", "plugin", "list", "--json"):
            payload = {
                "plugins": [
                    {"id": plugin}
                    for plugin in sorted(self.codex_plugins)
                ],
                "marketplaces": [
                    {"name": marketplace}
                    for marketplace in sorted(self.codex_marketplaces)
                ],
            }
            return {
                "returncode": 0,
                "stdout": json.dumps(payload),
                "stderr": "",
            }
        if normalized[:4] == (
            "codex",
            "plugin",
            "marketplace",
            "add",
        ):
            source = normalized[4]
            codex_names = {
                **self.marketplace_names,
                "mksglu/claude-context-mode": "context-mode",
            }
            self.codex_marketplaces.add(
                codex_names.get(
                    source,
                    source.rsplit("/", maxsplit=1)[-1].removesuffix(".git"),
                )
            )
            return {"returncode": 0, "stdout": "{}", "stderr": ""}
        if normalized[:3] == ("codex", "plugin", "add"):
            self.codex_plugins.add(normalized[3])
            return {"returncode": 0, "stdout": "{}", "stderr": ""}
        return {
            "returncode": (
                0 if self.allow_unmodeled_core_commands else 127
            ),
            "stdout": "",
            "stderr": "",
        }
```

```python
# tests/assistants/conftest.py
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.assistants.fakes import StatefulAssistantFake


@pytest.fixture
def fake_runner(temporary_home: Path) -> StatefulAssistantFake:
    """Provide stateful native CLI and verified-download boundaries."""
    return StatefulAssistantFake(temporary_home)


@pytest.fixture
def repo_root() -> Path:
    """Return the checkout root used by assistant tests."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def temporary_home(tmp_path: Path) -> Path:
    """Create an isolated home directory."""
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    return home


@pytest.fixture
def isolated_environment(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
) -> Iterator[Path]:
    """Point HOME at a temporary directory for one test."""
    monkeypatch.setenv("HOME", str(temporary_home))
    yield temporary_home
```

Test the discriminated resource union and inventory-wide constraints:

```python
# tests/assistants/test_models.py
import pytest
from pydantic import ValidationError

from ballen_config.assistants.models import AssistantInventory


@pytest.mark.parametrize(
    ("resource", "missing_field"),
    [
        (
            {
                "id": "cursor.settings",
                "kind": "file",
                "owner": "cursor",
                "source": "assistants/cursor/settings.base.json",
            },
            "destination",
        ),
        (
            {
                "id": "shared.rtk-hook",
                "kind": "hook",
                "owner": "shared",
                "source": "assistants/shared/hooks/rtk-hook",
                "targets": ["cursor", "claude-code"],
            },
            "event",
        ),
        (
            {
                "id": "cursor.user-rules",
                "kind": "manual",
                "owner": "cursor",
            },
            "summary",
        ),
    ],
)
def test_kind_specific_fields_are_required(
    resource: dict[str, object],
    missing_field: str,
) -> None:
    """Reject incomplete resource declarations."""
    with pytest.raises(ValidationError, match=missing_field):
        AssistantInventory.model_validate({"resources": [resource]})


def test_inventory_rejects_duplicate_ids() -> None:
    """Reject ambiguous inventory identifiers."""
    item = {
        "id": "cursor.settings",
        "kind": "file",
        "owner": "cursor",
        "source": "assistants/cursor/settings.base.json",
        "destination": "Library/Application Support/Cursor/User/settings.json",
    }
    with pytest.raises(ValidationError, match="duplicate resource id"):
        AssistantInventory.model_validate({"resources": [item, item]})


def test_inventory_has_no_mcp_resource_kind() -> None:
    """Keep local MCP servers outside the portable inventory."""
    with pytest.raises(ValidationError, match="kind"):
        AssistantInventory.model_validate(
            {
                "resources": [
                    {
                        "id": "cursor.playwright",
                        "kind": "mcp",
                        "owner": "cursor",
                    }
                ]
            }
        )


def test_plugin_catalog_rejects_unknown_marketplace() -> None:
    """Require every plugin marketplace to be declared."""
    from ballen_config.assistants.models import PluginCatalog

    with pytest.raises(ValidationError, match="unknown marketplaces"):
        PluginCatalog.model_validate(
            {
                "marketplaces": [],
                "plugins": [
                    {
                        "id": "example@missing",
                        "marketplace": "missing",
                    }
                ],
            }
        )
```

- [ ] **Step 2: Run the focused tests and confirm the red state**

Run:

```bash
rtk uv run pytest tests/assistants/test_models.py -q
```

Expected: collection fails because `ballen_config.assistants` does not exist.

- [ ] **Step 3: Implement typed, discriminated models**

Use `Literal` discriminators and Pydantic 2.8 validators:

```python
# src/ballen_config/assistants/models.py
from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentName(StrEnum):
    """Coding agents supported by the bootstrap."""

    CURSOR = "cursor"
    CLAUDE = "claude-code"
    CODEX = "codex"
    SHARED = "shared"


class ResourceBase(BaseModel):
    """Fields shared by every portable resource."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]+$")
    owner: AgentName
    profiles: tuple[str, ...] = ("default",)
    required: bool = True


class CatalogKind(StrEnum):
    """Typed subcatalogs referenced by the central inventory."""

    EXTENSION = "extension"
    PLUGIN = "plugin"
    SKILL = "skill"


class FileResource(ResourceBase):
    """A reviewed source copied through the core configuration engine."""

    kind: Literal["file"]
    source: PurePosixPath
    destination: PurePosixPath
    mode: Literal[0o600, 0o700] = 0o600
    targets: tuple[AgentName, ...] = ()
    role: Literal["direct", "render-source", "overlay", "suffix"] = "direct"


class HookResource(ResourceBase):
    """An authored hook program with native registrations."""

    kind: Literal["hook"]
    source: PurePosixPath
    event: str
    targets: tuple[AgentName, ...]


class CatalogResource(ResourceBase):
    """A typed subcatalog whose item IDs are flattened for audit."""

    kind: Literal["catalog"]
    source: PurePosixPath
    catalog_kind: CatalogKind
    targets: tuple[AgentName, ...] = ()
    item_ids: tuple[str, ...]


class ExtensionSpec(BaseModel):
    """A Cursor extension installed by ID or verified VSIX."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    condition: str | None = None
    install_mode: Literal["gallery", "vsix"] = "gallery"
    required: bool = True
    version: str | None = None
    size_bytes: int | None = Field(default=None, gt=0)
    url: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_vsix(self) -> ExtensionSpec:
        """Require immutable download metadata for VSIX resources."""
        if self.install_mode == "vsix" and not (
            self.version and self.size_bytes and self.url and self.sha256
        ):
            raise ValueError(
                "VSIX extensions require version, size_bytes, url, and sha256"
            )
        if self.install_mode == "gallery" and (
            self.version or self.size_bytes or self.url or self.sha256
        ):
            raise ValueError("gallery extensions cannot declare VSIX metadata")
        return self


class ExtensionCatalog(BaseModel):
    """Validated Cursor extension catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    extensions: tuple[ExtensionSpec, ...]


class Marketplace(BaseModel):
    """A named plugin marketplace source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    source: str
    profiles: tuple[str, ...] = ("default",)


class PluginSpec(BaseModel):
    """A plugin installed by an agent-native CLI."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    marketplace: str
    profiles: tuple[str, ...] = ("default",)
    required: bool = True


class PluginCatalog(BaseModel):
    """Validated marketplace and plugin declarations for one agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    marketplaces: tuple[Marketplace, ...]
    plugins: tuple[PluginSpec, ...]

    @model_validator(mode="after")
    def validate_marketplaces(self) -> PluginCatalog:
        """Reject plugin references to undeclared marketplaces."""
        names = {marketplace.name for marketplace in self.marketplaces}
        unknown = {
            plugin.marketplace
            for plugin in self.plugins
            if plugin.marketplace not in names
        }
        if unknown:
            raise ValueError(f"unknown marketplaces: {sorted(unknown)}")
        return self


class SkillSpec(BaseModel):
    """One canonical skill and its enabled native targets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    source: PurePosixPath
    targets: tuple[AgentName, ...]
    profiles: tuple[str, ...] = ("default",)
    dependencies: tuple[str, ...] = ()
    provenance: str
    portability_status: Literal["reviewed-generic", "agent-specific"]


class SkillCatalog(BaseModel):
    """Validated canonical-skill catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    skills: tuple[SkillSpec, ...]

    @model_validator(mode="after")
    def validate_graph(self) -> SkillCatalog:
        """Reject duplicate, unknown, and cyclic skill dependencies."""
        by_name = {skill.name: skill for skill in self.skills}
        if len(by_name) != len(self.skills):
            raise ValueError("duplicate skill name")
        for skill in self.skills:
            unknown = set(skill.dependencies).difference(by_name)
            if unknown:
                raise ValueError(
                    f"unknown skill dependencies for {skill.name}: "
                    f"{sorted(unknown)}"
                )

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError(f"skill dependency cycle at {name}")
            if name in visited:
                return
            visiting.add(name)
            for dependency in by_name[name].dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for name in sorted(by_name):
            visit(name)
        return self


class ManualResource(ResourceBase):
    """An informational setup action with no local mutation."""

    kind: Literal["manual"]
    summary: str
    source: PurePosixPath | None = None


PortableResource = Annotated[
    FileResource
    | HookResource
    | CatalogResource
    | ManualResource,
    Field(discriminator="kind"),
]


class AssistantInventory(BaseModel):
    """Validated portable-resource inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resources: tuple[PortableResource, ...]

    @model_validator(mode="after")
    def validate_references(self) -> AssistantInventory:
        """Reject duplicate inventory IDs."""
        ids = [resource.id for resource in self.resources]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate resource id")
        return self
```

Export the models from `src/ballen_config/assistants/__init__.py`.

- [ ] **Step 4: Write inventory-resolution tests**

The resolver accepts the already-resolved core profile and skip state:

```python
# tests/assistants/test_inventory.py
from pathlib import Path

import pytest

from ballen_config.assistants.inventory import load_inventory, resolve_inventory
from ballen_config.assistants.models import AgentName, AssistantInventory


@pytest.fixture
def inventory() -> AssistantInventory:
    """Create resources spanning profiles, owners, and shared targets."""
    return AssistantInventory.model_validate(
        {
            "resources": [
                {
                    "id": "cursor.default",
                    "kind": "manual",
                    "owner": "cursor",
                    "summary": "default",
                },
                {
                    "id": "cursor.work",
                    "kind": "manual",
                    "owner": "cursor",
                    "profiles": ["work"],
                    "summary": "work",
                },
                {
                    "id": "claude.default",
                    "kind": "manual",
                    "owner": "claude-code",
                    "summary": "claude",
                },
                {
                    "id": "codex.default",
                    "kind": "manual",
                    "owner": "codex",
                    "summary": "codex",
                },
                {
                    "id": "shared.hook",
                    "kind": "hook",
                    "owner": "shared",
                    "source": "assistants/shared/hooks/rtk-hook",
                    "event": "shell-command",
                    "targets": ["cursor", "claude-code", "codex"],
                },
            ]
        }
    )


def test_active_profiles_select_default_and_work(
    inventory: AssistantInventory,
) -> None:
    """Resolve the core-expanded profile tuple without duplicates."""
    resolved = resolve_inventory(
        inventory,
        profiles=("default", "work"),
        skipped=frozenset(),
    )
    ids = [resource.id for resource in resolved.resources]
    assert len(ids) == len(set(ids))
    assert "cursor.default" in ids
    assert "cursor.work" in ids


@pytest.mark.parametrize(
    ("component", "owner"),
    [
        ("cursor", AgentName.CURSOR),
        ("claude-code", AgentName.CLAUDE),
        ("codex", AgentName.CODEX),
    ],
)
def test_skip_removes_every_agent_resource(
    inventory: AssistantInventory,
    component: str,
    owner: AgentName,
) -> None:
    """Apply a whole-agent skip across every resource kind."""
    resolved = resolve_inventory(
        inventory,
        profiles=("default", "work"),
        skipped=frozenset({component}),
    )
    assert all(
        resource.owner not in {owner}
        and owner not in getattr(resource, "targets", ())
        for resource in resolved.resources
    )


def test_sources_must_resolve_inside_checkout(tmp_path: Path) -> None:
    """Reject source traversal before checking source existence."""
    path = tmp_path / "inventory.yaml"
    path.write_text(
        """
resources:
  - id: cursor.settings
    kind: file
    owner: cursor
    source: ../outside.json
    destination: Library/Application Support/Cursor/User/settings.json
""".lstrip()
    )
    with pytest.raises(ValueError, match="source escapes checkout"):
        load_inventory(path, tmp_path)
```

- [ ] **Step 5: Add the resolver and initial inventory**

Implement:

```python
# src/ballen_config/assistants/inventory.py
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from ballen_config.assistants.models import (
    AgentName,
    AssistantInventory,
    CatalogKind,
    CatalogResource,
    ExtensionCatalog,
    PluginCatalog,
    PortableResource,
    SkillCatalog,
)


class ResolvedInventory(BaseModel):
    """Resources selected for one bootstrap invocation."""

    model_config = ConfigDict(frozen=True)

    resources: tuple[PortableResource, ...]


_COMPONENT_OWNER = {
    "cursor": AgentName.CURSOR,
    "claude-code": AgentName.CLAUDE,
    "codex": AgentName.CODEX,
}


def load_inventory(path: Path, repo_root: Path) -> AssistantInventory:
    """Load an assistant inventory and validate local sources.

    Args:
        path: Inventory YAML path.
        repo_root: Checkout root used to resolve source paths.

    Returns:
        Validated assistant inventory.

    Raises:
        ValueError: A source is absent or escapes the checkout.
    """
    inventory = AssistantInventory.model_validate(yaml.safe_load(path.read_text()))
    root = repo_root.resolve()
    for resource in inventory.resources:
        source = getattr(resource, "source", None)
        if source is None:
            continue
        candidate = (root / source).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"source escapes checkout: {source}")
        if not candidate.exists():
            raise ValueError(f"source does not exist: {source}")
        if isinstance(resource, CatalogResource):
            raw_catalog = yaml.safe_load(candidate.read_text())
            if resource.catalog_kind is CatalogKind.EXTENSION:
                catalog = ExtensionCatalog.model_validate(raw_catalog)
                actual_ids = tuple(item.id for item in catalog.extensions)
            elif resource.catalog_kind is CatalogKind.PLUGIN:
                catalog = PluginCatalog.model_validate(raw_catalog)
                actual_ids = tuple(item.id for item in catalog.plugins)
            else:
                catalog = SkillCatalog.model_validate(raw_catalog)
                actual_ids = tuple(item.name for item in catalog.skills)
            if actual_ids != resource.item_ids:
                raise ValueError(
                    f"catalog item_ids differ for {resource.id}: "
                    f"{actual_ids!r}"
                )
    return inventory


def resolve_inventory(
    inventory: AssistantInventory,
    *,
    profiles: tuple[str, ...],
    skipped: frozenset[str],
) -> ResolvedInventory:
    """Resolve profile resources and whole-agent skips."""
    active_profiles = set(profiles)
    disabled_owners = {
        owner for component, owner in _COMPONENT_OWNER.items() if component in skipped
    }
    selected: list[PortableResource] = []
    for resource in inventory.resources:
        if not active_profiles.intersection(resource.profiles):
            continue
        if resource.owner in disabled_owners:
            continue
        targets = getattr(resource, "targets", ())
        if targets:
            enabled_targets = tuple(
                target for target in targets if target not in disabled_owners
            )
            if not enabled_targets:
                continue
            resource = resource.model_copy(update={"targets": enabled_targets})
        selected.append(resource)
    return ResolvedInventory(
        resources=tuple(sorted(selected, key=lambda item: item.id))
    )
```

Start `assistants/inventory.yaml` empty. Each later task adds an entry in the
same change that creates its final reviewed source, so loading the inventory is
valid at every checkpoint:

```yaml
resources:
  - id: shared.skills.catalog
    kind: catalog
    owner: shared
    source: assistants/shared/skills/catalog.yaml
    catalog_kind: skill
    targets: [cursor, claude-code, codex]
    item_ids: []
```

```yaml
# assistants/shared/skills/catalog.yaml
skills: []
```

- [ ] **Step 6: Prove the core supplier seams invoke once and preserve skips**

The prerequisite core plan already defines these exact contracts:

```python
type InstallActionSupplier = Callable[
    [ResolvedSetup, RuntimePaths, Runner],
    Sequence[InstallAction],
]
type Renderer = Callable[[bytes, bytes | None], bytes]
type SourceValidator = Callable[[Path], None]


@dataclass(frozen=True)
class ConfigurationContribution:
    """Managed specs and their named pure callbacks."""

    specs: tuple[ManagedSpec, ...]
    renderers: Mapping[str, Renderer] = field(default_factory=dict)
    validators: Mapping[str, SourceValidator] = field(default_factory=dict)


type ConfigurationSupplier = Callable[
    [ResolvedSetup, RuntimePaths],
    ConfigurationContribution,
]
type DoctorCheckSupplier = Callable[
    [ResolvedSetup, RuntimePaths, Runner],
    Sequence[DoctorCheck],
]
```

Do not add a second set of assistant-specific aliases. Add this regression test
to `tests/assistants/test_inventory.py`:

```python
from collections import Counter

from ballen_config.cli import run
from ballen_config.doctor import DoctorCheck
from ballen_config.install import InstallAction
from ballen_config.models import ResolvedSetup
from ballen_config.planning import PlanAction, PlanContributor
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths
from ballen_config.configure import (
    ConfigurationContribution,
    ManagedSpec,
)
from tests.assistants.fakes import StatefulAssistantFake


class RecordingPlanContributor(PlanContributor):
    """Record the resolved skip state received by plan."""

    def __init__(self, calls: Counter[str]) -> None:
        self.calls = calls

    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        self.calls["plan"] += 1
        assert not resolved.is_enabled("codex")
        return ()


def test_core_invokes_each_supplier_once_with_resolved_skip(
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Exercise the prerequisite core callbacks without assistant mutation."""
    calls: Counter[str] = Counter()

    def installs(
        setup: ResolvedSetup,
        paths: RuntimePaths,
        runner: Runner,
    ) -> tuple[InstallAction, ...]:
        calls["install"] += 1
        assert paths.home == temporary_home
        assert runner is fake_runner
        assert not setup.is_enabled("codex")
        return ()

    def configuration(
        setup: ResolvedSetup,
        paths: RuntimePaths,
    ) -> ConfigurationContribution:
        calls["configure"] += 1
        assert paths.home == temporary_home
        assert not setup.is_enabled("codex")
        return ConfigurationContribution(specs=())

    def checks(
        setup: ResolvedSetup,
        paths: RuntimePaths,
        runner: Runner,
    ) -> tuple[DoctorCheck, ...]:
        calls["doctor"] += 1
        assert paths.home == temporary_home
        assert runner is fake_runner
        assert not setup.is_enabled("codex")
        return ()

    common = {
        "repo_root": repo_root,
        "home": temporary_home,
        "runner": fake_runner,
        "downloader": fake_runner,
        "confirm": lambda _: True,
        "output": lambda _: None,
        "timestamp": lambda: "20260725T120000Z",
    }
    run(
        ["plan", "--profile", "work", "--skip", "codex"],
        plan_contributors=(RecordingPlanContributor(calls),),
        **common,
    )
    run(
        ["install", "--profile", "work", "--skip", "codex"],
        install_action_suppliers=(installs,),
        **common,
    )
    run(
        ["configure", "--profile", "work", "--skip", "codex"],
        configuration_suppliers=(configuration,),
        **common,
    )
    run(
        ["doctor", "--profile", "work", "--skip", "codex"],
        doctor_check_suppliers=(checks,),
        **common,
    )
    assert calls == Counter(
        {"plan": 1, "install": 1, "configure": 1, "doctor": 1}
    )
```

Import `Runner` from `ballen_config.runner` and
`StatefulAssistantFake` from `tests.assistants.fakes`. Expected: the test
passes against the completed core plan before any agent adapter is registered.

- [ ] **Step 7: Run focused tests and checkpoint**

Run:

```bash
rtk uv run pytest tests/assistants/test_models.py tests/assistants/test_inventory.py -q
rtk uv run mypy src/ballen_config/assistants tests/assistants
rtk uv run ruff check src/ballen_config/assistants tests/assistants
```

Expected: all focused tests pass.

Checkpoint:

```bash
rtk jj describe -m "feat: define coding-agent inventory"
rtk jj new
```

### Task 2: Add portable shared skills with collision safety

**Files:**

- Create: `src/ballen_config/assistants/skills.py`
- Create: `docs/promoting-shared-skills.md`
- Modify: `assistants/shared/skills/catalog.yaml`
- Modify: `assistants/inventory.yaml`
- Create: `tests/assistants/test_skills.py`
- Modify: `src/ballen_config/assistants/checks.py`

- [ ] **Step 1: Write tree-hash and target tests**

Use fixture-created skills so the initial repository catalog may remain empty:

```python
# tests/assistants/test_skills.py
import os
from pathlib import Path
import shutil

import pytest

from ballen_config.assistants.models import AgentName
from ballen_config.assistants.skills import (
    SkillCollisionError,
    hash_skill_tree,
    managed_tree_spec,
    plan_skill_copies,
)
from ballen_config.configure import ConfigEngine
from ballen_config.runtime import RuntimePaths
from ballen_config.state import BootstrapState, ManagedRecord, StateStore


@pytest.fixture
def source_skill(tmp_path: Path) -> Path:
    """Create a small portable skill tree."""
    root = tmp_path / "source" / "example-skill"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Example.\n---\n\n# Example\n"
    )
    (root / "reference.md").write_text("# Reference\n")
    return root


def test_hash_is_stable_across_creation_order(
    tmp_path: Path,
    source_skill: Path,
) -> None:
    """Hash sorted relative paths, file modes, and bytes."""
    second = tmp_path / "second"
    second.mkdir()
    (second / "reference.md").write_text("# Reference\n")
    (second / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Example.\n---\n\n# Example\n"
    )
    assert hash_skill_tree(source_skill) == hash_skill_tree(second)


def test_all_agent_destinations_are_native(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Copy shared skills to each agent's native user root."""
    actions = plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(
            AgentName.CURSOR,
            AgentName.CLAUDE,
            AgentName.CODEX,
        ),
        home=temporary_home,
        state=BootstrapState(),
    )
    assert {action.destination for action in actions} == {
        temporary_home / ".cursor/skills/example-skill",
        temporary_home / ".claude/skills/example-skill",
        temporary_home / ".agents/skills/example-skill",
    }


def test_same_name_different_hash_is_a_collision(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Refuse ambiguous skills across roots Cursor scans."""
    conflict = temporary_home / ".claude/skills/example-skill"
    conflict.mkdir(parents=True)
    (conflict / "SKILL.md").write_text("# Different\n")
    with pytest.raises(SkillCollisionError, match="example-skill"):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )


def test_previously_managed_skill_can_be_upgraded(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Treat a clean managed copy as an update, not an unmanaged collision."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Old.\n---\n"
    )
    old_digest = hash_skill_tree(destination)
    state = BootstrapState(
        managed={
            "skill:example-skill:cursor": ManagedRecord(
                resource_id="skill:example-skill:cursor",
                source_digest=old_digest,
                destination_digest=old_digest,
                destination=".cursor/skills/example-skill",
            )
        }
    )
    actions = plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(AgentName.CURSOR,),
        home=temporary_home,
        state=state,
    )
    assert len(actions) == 1
    assert actions[0].state == "update"


def test_symlink_in_source_is_rejected(
    source_skill: Path,
    tmp_path: Path,
) -> None:
    """Keep skill copies inside their reviewed source tree."""
    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    (source_skill / "escape.md").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        hash_skill_tree(source_skill)


def test_missing_skill_entrypoint_is_rejected(tmp_path: Path) -> None:
    """Require the standard skill entrypoint."""
    with pytest.raises(ValueError, match="missing SKILL.md"):
        hash_skill_tree(tmp_path)


def test_identical_destination_is_a_no_op(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Do not rewrite a byte-identical native skill."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.parent.mkdir(parents=True)
    shutil.copytree(source_skill, destination)
    assert plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(AgentName.CURSOR,),
        home=temporary_home,
        state=BootstrapState(),
    ) == ()


def test_managed_destination_drift_is_a_repair(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Distinguish local drift from a clean managed upgrade."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Locally changed.\n---\n"
    )
    state = BootstrapState(
        managed={
            "skill:example-skill:cursor": ManagedRecord(
                resource_id="skill:example-skill:cursor",
                source_digest="a" * 64,
                destination_digest="b" * 64,
                destination=".cursor/skills/example-skill",
            )
        }
    )
    actions = plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(AgentName.CURSOR,),
        home=temporary_home,
        state=state,
    )
    assert [action.state for action in actions] == ["repair"]


def test_unmanaged_destination_is_preserved(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Report a collision without changing unmanaged bytes."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.mkdir(parents=True)
    entrypoint = destination / "SKILL.md"
    entrypoint.write_text(
        "---\nname: example-skill\ndescription: Mine.\n---\n"
    )
    before = entrypoint.read_bytes()
    with pytest.raises(SkillCollisionError, match="unmanaged"):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )
    assert entrypoint.read_bytes() == before


def test_directory_and_frontmatter_names_must_match(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Reject a catalog name that differs from SKILL.md."""
    with pytest.raises(ValueError, match="name mismatch"):
        plan_skill_copies(
            source=source_skill,
            name="different-name",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )


def test_qualified_skill_names_do_not_collide(
    tmp_path: Path,
    temporary_home: Path,
) -> None:
    """Allow deliberately different agent-qualified skill names."""
    actions = []
    for name, target in (
        ("codex-example", AgentName.CODEX),
        ("claude-example", AgentName.CLAUDE),
    ):
        source = tmp_path / name
        source.mkdir()
        (source / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Qualified.\n---\n"
        )
        actions.extend(
            plan_skill_copies(
                source=source,
                name=name,
                targets=(target,),
                home=temporary_home,
                state=BootstrapState(),
            )
        )
    assert {action.resource_id for action in actions} == {
        "skill:codex-example:codex",
        "skill:claude-example:claude-code",
    }
```

- [ ] **Step 2: Run focused tests and confirm the red state**

Run:

```bash
rtk uv run pytest tests/assistants/test_skills.py -q
```

Expected: import fails because `skills.py` does not exist.

- [ ] **Step 3: Implement deterministic skill hashing and plans**

Use a typed action that the assistant configure adapter converts into core
managed-tree actions:

```python
# src/ballen_config/assistants/skills.py
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from typing import Literal

import yaml

from ballen_config.assistants.models import AgentName, SkillCatalog
from ballen_config.configure import (
    ConfigurationContribution,
    ManagedTreeSpec,
)
from ballen_config.models import ResolvedSetup
from ballen_config.runtime import RuntimePaths
from ballen_config.state import BootstrapState, StateStore


class SkillCollisionError(ValueError):
    """Raised when one skill name resolves to different content."""


@dataclass(frozen=True)
class SkillCopyAction:
    """A deterministic skill-tree convergence action."""

    source: Path
    destination: Path
    digest: str
    state: Literal["create", "update", "repair"]
    resource_id: str


_SKILL_ROOTS = {
    AgentName.CURSOR: Path(".cursor/skills"),
    AgentName.CLAUDE: Path(".claude/skills"),
    AgentName.CODEX: Path(".agents/skills"),
}
_CURSOR_SCANNED_ROOTS = (
    Path(".cursor/skills"),
    Path(".claude/skills"),
    Path(".agents/skills"),
    Path(".codex/skills"),
)
_FRONTMATTER_NAME = re.compile(r"^name:\s*([a-z0-9][a-z0-9-]+)\s*$", re.MULTILINE)


def hash_skill_tree(root: Path) -> str:
    """Hash reviewed skill paths, executable bits, and bytes.

    Args:
        root: Directory containing `SKILL.md`.

    Returns:
        Lowercase SHA-256 digest.

    Raises:
        ValueError: The skill is incomplete or contains a symlink.
    """
    if not (root / "SKILL.md").is_file():
        raise ValueError(f"missing SKILL.md in {root}")
    digest = sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"skill source contains symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(b"x" if path.stat().st_mode & 0o111 else b"-")
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _declared_name(root: Path) -> str:
    text = (root / "SKILL.md").read_text()
    match = _FRONTMATTER_NAME.search(text)
    if match is None:
        raise ValueError(f"SKILL.md lacks a valid name: {root}")
    return match.group(1)


def plan_skill_copies(
    *,
    source: Path,
    name: str,
    targets: tuple[AgentName, ...],
    home: Path,
    state: BootstrapState,
) -> tuple[SkillCopyAction, ...]:
    """Plan native copies after cross-root collision checks."""
    source_digest = hash_skill_tree(source)
    if _declared_name(source) != name:
        raise ValueError(f"skill directory/frontmatter name mismatch: {name}")
    desired_destinations = {
        home / _SKILL_ROOTS[target] / name
        for target in targets
    }
    for relative_root in _CURSOR_SCANNED_ROOTS:
        candidate = home / relative_root / name
        if not candidate.exists():
            continue
        current_digest = hash_skill_tree(candidate)
        if current_digest == source_digest:
            continue
        relative = candidate.relative_to(home).as_posix()
        records = [
            record
            for record in state.managed.values()
            if record.destination == relative
        ]
        if not records or candidate not in desired_destinations:
            raise SkillCollisionError(
                f"skill {name!r} differs at {candidate}; "
                "rename or reconcile it before migration"
            )
    actions: list[SkillCopyAction] = []
    for target in targets:
        destination = home / _SKILL_ROOTS[target] / name
        resource_id = f"skill:{name}:{target.value}"
        relative = destination.relative_to(home).as_posix()
        record = state.managed.get(resource_id)
        if not destination.exists():
            action_state: Literal["create", "update", "repair"] = "create"
        else:
            current_digest = hash_skill_tree(destination)
            if current_digest == source_digest:
                continue
            if record is None or record.destination != relative:
                raise SkillCollisionError(
                    f"unmanaged skill collision: {destination}"
                )
            action_state = (
                "update"
                if current_digest == record.destination_digest
                else "repair"
            )
        actions.append(
            SkillCopyAction(
                source=source,
                destination=destination,
                digest=source_digest,
                state=action_state,
                resource_id=resource_id,
            )
        )
    return tuple(sorted(actions, key=lambda action: str(action.destination)))
```

When applying a directory:

1. Refuse a destination symlink.
2. Stage the complete tree under the destination parent.
3. Set directories to `0700`, regular files to `0600`, and authored
   executables to `0700`.
4. Atomically rename the existing managed tree to the core backup directory.
5. Atomically rename the staged tree into place.
6. Store source digest, destination digest, targets, and resource ID in the
   core state file.
7. Preserve unmanaged conflicts and emit a manual finding.

Convert each validated skill action to the core tree primitive:

```python
def managed_tree_spec(action: SkillCopyAction) -> ManagedTreeSpec:
    """Delegate atomic tree convergence to the core configuration engine."""
    return ManagedTreeSpec(
        id=action.resource_id,
        source=action.source,
        destination=action.destination,
    )


def configuration(
    setup: ResolvedSetup,
    paths: RuntimePaths,
) -> ConfigurationContribution:
    """Resolve reviewed skills into core managed-tree specs."""
    catalog_path = paths.repo_root / "assistants/shared/skills/catalog.yaml"
    catalog = SkillCatalog.model_validate(yaml.safe_load(catalog_path.read_text()))
    state = StateStore(paths).load()
    specs: list[ManagedTreeSpec] = []
    for skill in sorted(catalog.skills, key=lambda item: item.name):
        if not set(skill.profiles).intersection(setup.profiles):
            continue
        targets = tuple(
            target
            for target in skill.targets
            if setup.is_enabled(target.value)
        )
        actions = plan_skill_copies(
            source=paths.repo_root / skill.source,
            name=skill.name,
            targets=targets,
            home=paths.home,
            state=state,
        )
        specs.extend(managed_tree_spec(action) for action in actions)
    return ConfigurationContribution(
        specs=tuple(sorted(specs, key=lambda item: item.id))
    )
```

The core `ConfigEngine` supplies mode normalization, same-parent staging,
backup/rollback, atomic publish, and ownership recording. Add this focused
integration test; the assistant adapter must never perform an independent copy
or rename:

```python
def test_managed_skill_publish_failure_rolls_back(
    source_skill: Path,
    temporary_home: Path,
    repo_root: Path,
) -> None:
    """Restore the original tree and state when atomic publish fails."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.mkdir(parents=True)
    original = destination / "SKILL.md"
    original.write_text(
        "---\nname: example-skill\ndescription: Original.\n---\n"
    )
    paths = RuntimePaths.from_roots(
        repo_root=repo_root,
        home=temporary_home,
    )
    store = StateStore(paths)
    old_digest = hash_skill_tree(destination)
    record = ManagedRecord(
        resource_id="skill:example-skill:cursor",
        source_digest=old_digest,
        destination_digest=old_digest,
        destination=".cursor/skills/example-skill",
    )
    store.record_managed(record)
    before_state = store.load()
    replacements = 0

    def fail_publish(source: Path, target: Path) -> None:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("injected publish failure")
        os.replace(source, target)

    engine = ConfigEngine(
        paths=paths,
        timestamp=lambda: "20260725T120000Z",
        replace=fail_publish,
    )
    action = plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(AgentName.CURSOR,),
        home=temporary_home,
        state=before_state,
    )[0]
    with pytest.raises(OSError, match="injected publish failure"):
        engine.apply(managed_tree_spec(action))
    assert original.read_text().endswith("description: Original.\n---\n")
    assert store.load() == before_state
```

- [ ] **Step 4: Keep the initial catalog intentionally empty**

The initial implementation creates the generic mechanism without pretending a
repo-specific skill is generic:

```yaml
# assistants/shared/skills/catalog.yaml
skills: []
```

`assistants/inventory.yaml` loads this catalog through `skills.py`; it does not
hard-code a first skill. The first promoted skill is a separate reviewed
change, following `docs/promoting-shared-skills.md`.

Add this exact entry shape to `docs/promoting-shared-skills.md`:

```yaml
skills:
  - name: example-generic-skill
    source: assistants/shared/skills/example-generic-skill
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: Promoted from a reviewed repository skill; change history records the origin.
    portability_status: reviewed-generic
```

Add this exact promotion gate immediately after the entry example:

1. Remove project names, absolute paths, project import statements, project
   tool prefixes, and repository-specific assumptions.
2. Give the skill a globally unique kebab-case name.
3. Run the portability scanner against the whole skill tree.
4. Add the source directory under `assistants/shared/skills/<name>/`.
5. Add targets and profiles to `catalog.yaml`.
6. Run collision, hash, policy, and integration tests.
7. Promote agent-specific variants only under distinct qualified names.

- [ ] **Step 5: Run focused tests and checkpoint**

Run:

```bash
rtk uv run pytest tests/assistants/test_skills.py -q
rtk uv run mypy src/ballen_config/assistants/skills.py tests/assistants/test_skills.py
rtk uv run ruff check src/ballen_config/assistants/skills.py tests/assistants/test_skills.py
```

Expected: all focused tests pass.

Checkpoint:

```bash
rtk jj describe -m "feat: add portable shared-skill infrastructure"
rtk jj new
```

### Task 3: Share authored instructions and RTK hook programs

**Files:**

- Create: `assistants/shared/instructions/engineering.md`
- Create: `assistants/shared/instructions/rtk.md`
- Create: `assistants/shared/hooks/rtk-hook`
- Create: `assistants/cursor/hooks.json`
- Create: `src/ballen_config/assistants/hooks.py`
- Create: `src/ballen_config/assistants/instructions.py`
- Create: `tests/assistants/test_hooks.py`
- Create: `tests/assistants/test_instructions.py`
- Modify: `assistants/inventory.yaml`

- [ ] **Step 1: Write adapter and rejection tests**

```python
# tests/assistants/test_hooks.py
from pathlib import Path

import pytest

from ballen_config.assistants.hooks import (
    claude_hook_fragment,
    cursor_registration,
    hook_contribution,
    validate_hook_source,
)


def test_cursor_registration_uses_native_event(
    temporary_home: Path,
) -> None:
    """Translate the shared shell event to Cursor preToolUse."""
    assert cursor_registration(temporary_home) == {
        "version": 1,
        "hooks": {
            "preToolUse": [
                {
                    "command": (
                        f"{temporary_home}/.local/share/ballen-config/"
                        "hooks/rtk-hook cursor"
                    ),
                    "matcher": "Shell",
                }
            ]
        },
    }


def test_claude_registration_uses_native_event(
    temporary_home: Path,
) -> None:
    """Return a fragment; Claude remains the sole settings-file owner."""
    assert claude_hook_fragment(temporary_home) == {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                f"{temporary_home}/.local/share/ballen-config/"
                                "hooks/rtk-hook claude"
                            ),
                        }
                    ],
                }
            ]
        }
    }


def test_hooks_never_own_claude_settings(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Keep one managed owner for every native destination."""
    contribution = hook_contribution(
        repo_root=repo_root,
        home=temporary_home,
        enabled=frozenset({"cursor", "claude-code"}),
    )
    destinations = {
        spec.destination for spec in contribution.specs
    }
    assert temporary_home / ".cursor/hooks.json" in destinations
    assert temporary_home / ".claude/settings.json" not in destinations


@pytest.mark.parametrize(
    "source",
    [
        ".claude/plugins/cache/context-mode/1.2.3/cache-heal.mjs",
        ".codex/plugins/cache/piste/plato/update-piste-plato.sh",
        "/Users/ballen/.claude/hooks/generated.sh",
    ],
)
def test_generated_or_machine_local_hook_source_is_rejected(source: str) -> None:
    """Track only reviewed repository-owned hook programs."""
    with pytest.raises(ValueError, match="reviewed source"):
        validate_hook_source(Path(source))
```

```python
@pytest.mark.parametrize(
    ("enabled", "expected_ids"),
    [
        (
            frozenset({"cursor", "claude-code"}),
            {"shared.rtk-hook", "cursor.hooks"},
        ),
        (frozenset({"cursor"}), {"shared.rtk-hook", "cursor.hooks"}),
        (frozenset({"claude-code"}), {"shared.rtk-hook"}),
        (frozenset(), set()),
        (frozenset({"codex"}), set()),
    ],
)
def test_hook_contribution_follows_supported_agent_selection(
    repo_root: Path,
    temporary_home: Path,
    enabled: frozenset[str],
    expected_ids: set[str],
) -> None:
    """Deploy only the shared program and Cursor-owned registration."""
    contribution = hook_contribution(
        repo_root=repo_root,
        home=temporary_home,
        enabled=enabled,
    )
    assert {spec.id for spec in contribution.specs} == expected_ids
```

- [ ] **Step 2: Run the focused test and confirm the red state**

Run:

```bash
rtk uv run pytest tests/assistants/test_hooks.py tests/assistants/test_instructions.py -q
```

Expected: import fails because `hooks.py` does not exist.

- [ ] **Step 3: Add the one stable shared program**

```zsh
#!/bin/zsh
# assistants/shared/hooks/rtk-hook
set -eu

case "${1:-}" in
  cursor|claude)
    exec rtk hook "$1"
    ;;
  *)
    print -u2 "usage: rtk-hook cursor|claude"
    exit 64
    ;;
esac
```

Keep `assistants/shared/instructions/engineering.md` limited to the portable
engineering rules from the root `AGENTS.md`:

```markdown
# Engineering defaults

- Use Python 3.12.
- Use type hints, TypedDict for external mappings, and Pydantic 2.8 for
  validated models.
- Use Google-style docstrings.
- Use pytest fixtures.
- Prefer Jujutsu for source control.
```

Keep `assistants/shared/instructions/rtk.md` as the reviewed, portable content
from `/Users/ballen/.codex/RTK.md`, with all absolute paths removed. It must say
that agent-run shell commands are prefixed with `rtk` and include only RTK
command patterns supported on a clean machine.

Add `instructions.py` and tests proving native files consume canonical content:

```python
# src/ballen_config/assistants/instructions.py
from __future__ import annotations

from pathlib import Path


def render_native_instructions(
    *,
    engineering: str,
    rtk: str,
    agent_suffix: str,
    rtk_include: Path | None = None,
) -> str:
    """Render canonical guidance into an agent-native instruction file."""
    sections = [engineering.rstrip()]
    if rtk_include is None:
        sections.append(rtk.rstrip())
    else:
        sections.append(f"@{rtk_include}")
    sections.append(agent_suffix.rstrip())
    return "\n\n".join(sections) + "\n"
```

```python
# tests/assistants/test_instructions.py
from pathlib import Path

from ballen_config.assistants.instructions import (
    render_native_instructions,
)


def test_cursor_and_claude_embed_canonical_sections(
    repo_root: Path,
) -> None:
    """Embed reviewed engineering and RTK text without transformations."""
    engineering = (
        repo_root / "assistants/shared/instructions/engineering.md"
    ).read_text()
    rtk = (
        repo_root / "assistants/shared/instructions/rtk.md"
    ).read_text()
    for suffix in ("# Cursor additions\n", "# Claude additions\n"):
        rendered = render_native_instructions(
            engineering=engineering,
            rtk=rtk,
            agent_suffix=suffix,
        )
        assert engineering.rstrip() in rendered
        assert rtk.rstrip() in rendered
        assert suffix.rstrip() in rendered


def test_codex_uses_absolute_rtk_include(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Reference the separately managed Codex RTK file by absolute path."""
    engineering_path = (
        repo_root / "assistants/shared/instructions/engineering.md"
    )
    rtk_path = repo_root / "assistants/shared/instructions/rtk.md"
    include = temporary_home / ".codex/RTK.md"
    rendered = render_native_instructions(
        engineering=engineering_path.read_text(),
        rtk=rtk_path.read_text(),
        agent_suffix="# Codex additions\n",
        rtk_include=include,
    )
    assert engineering_path.read_text().rstrip() in rendered
    assert f"@{include}" in rendered
    assert rtk_path.read_text().rstrip() not in rendered


def test_rendered_instructions_exclude_generated_state(
    repo_root: Path,
) -> None:
    """Keep template markers and plugin-cache paths out of native output."""
    rendered = render_native_instructions(
        engineering=(
            repo_root / "assistants/shared/instructions/engineering.md"
        ).read_text(),
        rtk=(
            repo_root / "assistants/shared/instructions/rtk.md"
        ).read_text(),
        agent_suffix="# Agent additions\n",
    )
    assert "{{" not in rendered
    assert "plugins/cache/" not in rendered
```

Use content reads only from these repository-owned paths; do not read an
existing native instruction destination. Tasks 4-6 reuse this renderer and
their adapter tests assert the same canonical sections reach Cursor, Claude,
and Codex.

Append the final shared entries to `assistants/inventory.yaml`:

```yaml
  - id: shared.engineering
    kind: file
    owner: shared
    source: assistants/shared/instructions/engineering.md
    destination: .local/share/ballen-config/instructions/engineering.md
    targets: [cursor, claude-code, codex]

  - id: shared.rtk
    kind: file
    owner: shared
    source: assistants/shared/instructions/rtk.md
    destination: .local/share/ballen-config/instructions/rtk.md
    targets: [cursor, claude-code, codex]

  - id: shared.rtk-hook
    kind: hook
    owner: shared
    source: assistants/shared/hooks/rtk-hook
    event: shell-command
    targets: [cursor, claude-code]
```

- [ ] **Step 4: Implement hook planning**

Implement `hooks.py` as a fragment/spec helper. It must never construct a
`ManagedFileSpec` for `~/.claude/settings.json`:

```python
# src/ballen_config/assistants/hooks.py
from __future__ import annotations

import json
from pathlib import Path

from ballen_config.configure import (
    ApplyMethod,
    ConfigurationContribution,
    ManagedFileSpec,
    Renderer,
)


def validate_hook_source(source: Path) -> None:
    """Accept only reviewed hook sources in this checkout."""
    parts = source.parts
    if (
        source.is_absolute()
        or parts[:3] != ("assistants", "shared", "hooks")
        or {"cache", "plugins", "generated"}.intersection(parts)
    ):
        raise ValueError("hook must use a reviewed source")


def cursor_registration(home: Path) -> dict[str, object]:
    """Render Cursor's native RTK registration."""
    command = (
        home / ".local/share/ballen-config/hooks/rtk-hook"
    ).as_posix()
    return {
        "version": 1,
        "hooks": {
            "preToolUse": [
                {"command": f"{command} cursor", "matcher": "Shell"}
            ]
        },
    }


def claude_hook_fragment(home: Path) -> dict[str, object]:
    """Return the Claude hook fragment for claude.py to merge."""
    command = (
        home / ".local/share/ballen-config/hooks/rtk-hook"
    ).as_posix()
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{command} claude",
                        }
                    ],
                }
            ]
        }
    }


def cursor_hook_renderer(home: Path) -> Renderer:
    """Build a pure renderer for Cursor's native registration."""
    def render(_: bytes, __: bytes | None) -> bytes:
        return (
            json.dumps(
                cursor_registration(home),
                indent=2,
                sort_keys=True,
            ).encode()
            + b"\n"
        )

    return render


def hook_contribution(
    *,
    repo_root: Path,
    home: Path,
    enabled: frozenset[str],
) -> ConfigurationContribution:
    """Return shared-program and Cursor registration configuration."""
    supported = enabled.intersection({"cursor", "claude-code"})
    if not supported:
        return ConfigurationContribution(specs=())
    source = Path("assistants/shared/hooks/rtk-hook")
    validate_hook_source(source)
    specs: list[ManagedFileSpec] = [
        ManagedFileSpec(
            id="shared.rtk-hook",
            source=repo_root / source,
            destination=(
                home / ".local/share/ballen-config/hooks/rtk-hook"
            ),
            method=ApplyMethod.COPY,
            mode=0o700,
        )
    ]
    renderers: dict[str, Renderer] = {}
    if "cursor" in enabled:
        specs.append(
            ManagedFileSpec(
                id="cursor.hooks",
                source=repo_root / "assistants/cursor/hooks.json",
                destination=home / ".cursor/hooks.json",
                method=ApplyMethod.RENDER,
                renderer_id="cursor-hooks",
                mode=0o600,
            )
        )
        renderers["cursor-hooks"] = cursor_hook_renderer(home)
    return ConfigurationContribution(
        specs=tuple(specs),
        renderers=renderers,
    )
```

Claude consumes only `claude_hook_fragment()` from Task 5. No hook helper
returns or applies a Claude settings spec.

Track this reviewed Cursor source:

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "command": "~/.local/share/ballen-config/hooks/rtk-hook cursor",
        "matcher": "Shell"
      }
    ]
  }
}
```

At render time, replace only the leading `~/` with the injected home path.
Do not run shell expansion.

- [ ] **Step 5: Validate authored files and checkpoint**

Run:

```bash
rtk zsh -n assistants/shared/hooks/rtk-hook
rtk uv run pytest tests/assistants/test_hooks.py tests/assistants/test_instructions.py -q
rtk uv run python -m ballen_config.policy
```

Expected: syntax, tests, and portability policy pass.

Checkpoint:

```bash
rtk jj describe -m "feat: share instructions and RTK hook adapters"
rtk jj new
```

### Task 4: Restore Cursor settings and curated extensions

**Files:**

- Create: `src/ballen_config/assistants/cursor.py`
- Create: `assistants/cursor/extensions.yaml`
- Move: `cursor/settings.json` to `assistants/cursor/settings.base.json`
- Move: `cursor/keybindings.json` to `assistants/cursor/keybindings.json`
- Create: `assistants/cursor/settings.work.json`
- Create: `assistants/cursor/user-rules.md`
- Create: `tests/assistants/test_cursor.py`
- Modify: `assistants/inventory.yaml`
- Delete: `cursor/extensions.txt`

- [ ] **Step 1: Write settings-overlay tests**

```python
# tests/assistants/test_cursor.py
from pathlib import Path

from ballen_config.assistants.cursor import deep_merge, render_settings


def test_default_settings_exclude_bedrock(repo_root: Path) -> None:
    """Keep work-only Claude environment out of the default profile."""
    rendered = render_settings(repo_root, profiles=("default",))
    assert "claudeCode.environmentVariables" not in rendered


def test_work_settings_add_only_bedrock_environment(repo_root: Path) -> None:
    """Overlay the reviewed work-only Claude environment."""
    rendered = render_settings(repo_root, profiles=("default", "work"))
    assert rendered["claudeCode.environmentVariables"] == [
        "CLAUDE_CODE_USE_BEDROCK=1",
        "AWS_REGION=us-east-1",
    ]


def test_deep_merge_replaces_lists_and_merges_objects() -> None:
    """Give overlays deterministic JSON merge semantics."""
    assert deep_merge(
        {"editor": {"fontSize": 13, "rulers": [88]}, "theme": "A"},
        {"editor": {"rulers": [100]}},
    ) == {
        "editor": {"fontSize": 13, "rulers": [100]},
        "theme": "A",
    }
```

Move the current reviewed files once:

```bash
rtk mkdir -p assistants/cursor
rtk mv cursor/settings.json assistants/cursor/settings.base.json
rtk mv cursor/keybindings.json assistants/cursor/keybindings.json
```

Then remove `claudeCode.environmentVariables` from `settings.base.json`. Put
exactly this content in the work overlay:

```json
{
  "claudeCode.environmentVariables": [
    "CLAUDE_CODE_USE_BEDROCK=1",
    "AWS_REGION=us-east-1"
  ]
}
```

Keep all other reviewed editor preferences and keybindings unchanged. Validate
both with `json.loads()` before core managed-file actions are emitted.
After `extensions.yaml` and its tests pass, delete the obsolete
`cursor/extensions.txt` with the patch tool; do not leave an untracked copy.

Create this Cursor-specific User Rules suffix:

```markdown
# Cursor additions

Repository instructions take precedence for repository-specific behavior.
Use Cursor's first-party browser capability rather than a global Playwright
MCP server. Use `glab` for GitLab operations and official application
integrations for Notion. Never copy authentication, history, worktrees,
indexes, caches, or generated plugin state between machines.
```

Append these final Cursor entries to `assistants/inventory.yaml`:

```yaml
  - id: cursor.settings
    kind: file
    owner: cursor
    source: assistants/cursor/settings.base.json
    destination: Library/Application Support/Cursor/User/settings.json
    role: render-source

  - id: cursor.settings.work
    kind: file
    owner: cursor
    source: assistants/cursor/settings.work.json
    destination: Library/Application Support/Cursor/User/settings.json
    profiles: [work]
    role: overlay

  - id: cursor.keybindings
    kind: file
    owner: cursor
    source: assistants/cursor/keybindings.json
    destination: Library/Application Support/Cursor/User/keybindings.json

  - id: cursor.user-rules
    kind: manual
    owner: cursor
    source: assistants/cursor/user-rules.md
    summary: Copy the rendered cursor-user-rules.md from the bootstrap state directory into Cursor Customize > Rules.

  - id: cursor.extensions.catalog
    kind: catalog
    owner: cursor
    source: assistants/cursor/extensions.yaml
    catalog_kind: extension
    item_ids:
      - adamviola.parquet-explorer
      - anthropic.claude-code
      - anysphere.remote-containers
      - anysphere.remote-ssh
      - bierner.markdown-mermaid
      - bierner.markdown-preview-github-styles
      - charliermarsh.ruff
      - davidanson.vscode-markdownlint
      - esbenp.prettier-vscode
      - humao.rest-client
      - jjk.jjk
      - matangover.mypy
      - mhutchie.git-graph
      - ms-azuretools.vscode-docker
      - ms-python.python
      - ms-toolsai.jupyter
      - ms-vscode.atom-keybindings
      - ms-vscode.makefile-tools
      - openai.chatgpt
      - redhat.vscode-yaml
      - samuelcolvin.jinjahtml
      - shd101wyy.markdown-preview-enhanced
      - tamasfe.even-better-toml
      - tomoki1207.pdf
      - visualjj.visualjj
      - velociraptor115.vscode-jj-graph
```

The Cursor adapter treats `cursor.settings` as a rendered resource: it loads
`settings.base.json` and, for the work profile, merges
`settings.work.json` before emitting one managed-file action. It must not emit
separate actions for the same settings destination.

- [ ] **Step 2: Write extension-resolution tests**

```python
# tests/assistants/test_cursor.py
from hashlib import sha256

from ballen_config.assistants.cursor import (
    ExtensionState,
    plan_cursor_extension_actions,
    read_bundled_extensions,
    resolve_extensions,
)
from ballen_config.install import InstallAction, Installer
from tests.assistants.fakes import StatefulAssistantFake


def test_agent_extensions_follow_agent_selection(repo_root: Path) -> None:
    """Install assistant extensions only when that assistant is enabled."""
    without_agents = resolve_extensions(
        repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=frozenset({"cursor"}),
        installed=frozenset(),
        bundled=frozenset(),
    )
    assert "anthropic.claude-code" not in without_agents.missing
    assert "openai.chatgpt" not in without_agents.missing

    with_agents = resolve_extensions(
        repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=frozenset({"cursor", "claude-code", "codex"}),
        installed=frozenset(),
        bundled=frozenset(),
    )
    assert "anthropic.claude-code" in with_agents.missing
    assert "openai.chatgpt" in with_agents.missing


def test_bundled_extension_satisfies_requirement(repo_root: Path) -> None:
    """Avoid reinstalling a feature bundled with Cursor."""
    state = resolve_extensions(
        repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=frozenset({"cursor"}),
        installed=frozenset(),
        bundled=frozenset({"ms-python.python"}),
    )
    assert "ms-python.python" not in state.missing


def test_transitive_and_replaced_extensions_are_not_declared(
    repo_root: Path,
) -> None:
    """Keep the curated list feature-level and Cursor-native."""
    text = (repo_root / "assistants/cursor/extensions.yaml").read_text()
    forbidden = {
        "gitlab.gitlab-workflow",
        "anysphere.cursorpyright",
        "ms-python.debugpy",
        "ms-toolsai.jupyter-keymap",
        "ms-toolsai.jupyter-renderers",
        "ms-toolsai.vscode-jupyter-cell-tags",
        "ms-toolsai.vscode-jupyter-slideshow",
        "ms-vscode-remote.remote-ssh",
        "ms-vscode.remote-explorer",
    }
    assert forbidden.isdisjoint(text.split())
```

```python
def test_bundled_manifest_ids_are_normalized(tmp_path: Path) -> None:
    """Read publisher.name IDs from Cursor's packaged manifests."""
    manifest = tmp_path / "extensions/python/package.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"publisher":"MS-Python","name":"Python"}')
    assert read_bundled_extensions(tmp_path / "extensions") == frozenset(
        {"ms-python.python"}
    )


def test_gallery_action_uses_extension_id(repo_root: Path) -> None:
    """Install gallery entries without version locking."""
    actions = plan_cursor_extension_actions(
        repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=frozenset({"cursor"}),
        installed=frozenset(),
        bundled=frozenset(),
    )
    markdown = next(
        action
        for action in actions
        if action.component_id
        == "cursor.extension.bierner.markdown-mermaid"
    )
    assert markdown == InstallAction(
        component_id="cursor.extension.bierner.markdown-mermaid",
        argv=(
            "cursor",
            "--install-extension",
            "bierner.markdown-mermaid",
        ),
    )


def test_vsix_uses_core_verified_download_without_network(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Delegate bounded download, verification, and cleanup to core."""
    payload = b"fixture-vsix-bytes"
    url = "https://example.invalid/vscode-jj-graph-0.0.9.vsix"
    fake_runner.add_vsix(
        url=url,
        payload=payload,
        extension_id="velociraptor115.vscode-jj-graph",
    )
    action = InstallAction(
        component_id="cursor.extension.velociraptor115.vscode-jj-graph",
        kind="verified-download",
        argv=("cursor", "--install-extension", "{artifact}"),
        required=False,
        url=url,
        artifact_name="vscode-jj-graph.vsix",
        size_bytes=len(payload),
        sha256=sha256(payload).hexdigest(),
    )
    outcome = Installer(
        fake_runner,
        temporary_home,
        downloader=fake_runner,
        private_temp_root=temporary_home / ".local/state/test-tmp",
    ).run_action(action)
    assert outcome.state == "installed"
    assert (
        "velociraptor115.vscode-jj-graph"
        in fake_runner.cursor_extensions
    )
    assert fake_runner.downloads
    assert not fake_runner.downloads[0][1].exists()


def test_extension_resolution_reports_independent_sets(
    repo_root: Path,
) -> None:
    """Keep skipped, missing, bundled, and unmanaged states distinct."""
    state = resolve_extensions(
        repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=frozenset({"cursor"}),
        installed=frozenset({"unmanaged.extra"}),
        bundled=frozenset({"ms-python.python"}),
    )
    assert "ms-python.python" in state.bundled
    assert "ms-python.python" not in state.missing
    assert "unmanaged.extra" in state.unmanaged_extra
    assert "anthropic.claude-code" in state.skipped_condition
```

- [ ] **Step 3: Commit the curated extension manifest**

Use unversioned feature IDs for gallery extensions. The current version is a
doctor diagnostic, not an install pin:

```yaml
extensions:
  - id: adamviola.parquet-explorer
  - id: anthropic.claude-code
    condition: claude-code
  - id: anysphere.remote-containers
  - id: anysphere.remote-ssh
  - id: bierner.markdown-mermaid
  - id: bierner.markdown-preview-github-styles
  - id: charliermarsh.ruff
  - id: davidanson.vscode-markdownlint
  - id: esbenp.prettier-vscode
  - id: humao.rest-client
  - id: jjk.jjk
  - id: matangover.mypy
  - id: mhutchie.git-graph
  - id: ms-azuretools.vscode-docker
  - id: ms-python.python
  - id: ms-toolsai.jupyter
  - id: ms-vscode.atom-keybindings
  - id: ms-vscode.makefile-tools
  - id: openai.chatgpt
    condition: codex
  - id: redhat.vscode-yaml
  - id: samuelcolvin.jinjahtml
  - id: shd101wyy.markdown-preview-enhanced
  - id: tamasfe.even-better-toml
  - id: tomoki1207.pdf
  - id: visualjj.visualjj
  - id: velociraptor115.vscode-jj-graph
    install_mode: vsix
    required: false
    version: 0.0.9
    size_bytes: 10291769
    url: https://Velociraptor115.gallery.vsassets.io/_apis/public/gallery/publisher/Velociraptor115/extension/vscode-jj-graph/0.0.9/assetbyname/Microsoft.VisualStudio.Services.VSIXPackage
    sha256: a822f2e2afd644aa22c64e1caec5e62dd8fb896ada30028f831ce28068570ace
```

The audited VSIX is 10,291,769 bytes. Treat a size mismatch as an optional
failure in addition to checking SHA-256.

- [ ] **Step 4: Implement the Cursor adapter**

Create the complete adapter:

```python
# src/ballen_config/assistants/cursor.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

import yaml
from pydantic import BaseModel, ConfigDict

from ballen_config.assistants.instructions import (
    render_native_instructions,
)
from ballen_config.assistants.models import (
    ExtensionCatalog,
    ExtensionSpec,
)
from ballen_config.configure import (
    ApplyMethod,
    ConfigurationContribution,
    ManagedFileSpec,
    Renderer,
)
from ballen_config.install import InstallAction
from ballen_config.models import ResolvedSetup
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths


class CursorExtensionPackage(TypedDict):
    """Fields read from a bundled Cursor extension package."""

    name: str
    publisher: str


class ExtensionState(BaseModel):
    """Deterministic extension resolution."""

    model_config = ConfigDict(frozen=True)

    installed: frozenset[str]
    bundled: frozenset[str]
    missing: tuple[str, ...]
    skipped_condition: tuple[str, ...]
    unmanaged_extra: tuple[str, ...]


def _catalog(path: Path) -> ExtensionCatalog:
    """Load the curated extension catalog."""
    return ExtensionCatalog.model_validate(yaml.safe_load(path.read_text()))


def read_bundled_extensions(root: Path) -> frozenset[str]:
    """Read lowercase publisher.name IDs from Cursor's packaged manifests."""
    identifiers: set[str] = set()
    for manifest in sorted(root.glob("*/package.json")):
        document: CursorExtensionPackage = json.loads(manifest.read_text())
        identifiers.add(
            f"{document['publisher']}.{document['name']}".lower()
        )
    return frozenset(identifiers)


def resolve_extensions(
    catalog_path: Path,
    *,
    enabled_agents: frozenset[str],
    installed: frozenset[str],
    bundled: frozenset[str],
) -> ExtensionState:
    """Resolve desired and diagnostic extension sets independently."""
    catalog = _catalog(catalog_path)
    desired = {
        extension.id
        for extension in catalog.extensions
        if extension.condition is None
        or extension.condition in enabled_agents
    }
    skipped = {
        extension.id
        for extension in catalog.extensions
        if extension.condition is not None
        and extension.condition not in enabled_agents
    }
    declared = {extension.id for extension in catalog.extensions}
    return ExtensionState(
        installed=installed,
        bundled=bundled,
        missing=tuple(sorted(desired - installed - bundled)),
        skipped_condition=tuple(sorted(skipped)),
        unmanaged_extra=tuple(sorted(installed - declared)),
    )


def jj_graph_action(extension: ExtensionSpec) -> InstallAction:
    """Build the core-owned verified VSIX installation action."""
    return InstallAction(
        component_id=(
            "cursor.extension.velociraptor115.vscode-jj-graph"
        ),
        kind="verified-download",
        argv=("cursor", "--install-extension", "{artifact}"),
        required=False,
        url=extension.url,
        artifact_name="vscode-jj-graph.vsix",
        size_bytes=extension.size_bytes,
        sha256=extension.sha256,
    )


def plan_cursor_extension_actions(
    catalog_path: Path,
    *,
    enabled_agents: frozenset[str],
    installed: frozenset[str],
    bundled: frozenset[str],
) -> tuple[InstallAction, ...]:
    """Translate missing features into deterministic core install actions."""
    catalog = _catalog(catalog_path)
    by_id = {extension.id: extension for extension in catalog.extensions}
    state = resolve_extensions(
        catalog_path,
        enabled_agents=enabled_agents,
        installed=installed,
        bundled=bundled,
    )
    actions: list[InstallAction] = []
    for identifier in state.missing:
        extension = by_id[identifier]
        if extension.install_mode == "vsix":
            actions.append(jj_graph_action(extension))
        else:
            actions.append(
                InstallAction(
                    component_id=f"cursor.extension.{identifier}",
                    argv=("cursor", "--install-extension", identifier),
                    required=extension.required,
                )
            )
    return tuple(actions)


def deep_merge(base: object, overlay: object) -> object:
    """Recursively merge objects and replace scalar or list values."""
    if not isinstance(base, dict) or not isinstance(overlay, dict):
        return overlay
    merged: dict[str, Any] = dict(base)
    for key, value in overlay.items():
        merged[key] = (
            deep_merge(merged[key], value)
            if key in merged
            else value
        )
    return merged


def render_settings(
    repo_root: Path,
    *,
    profiles: tuple[str, ...],
) -> dict[str, Any]:
    """Load and merge reviewed Cursor settings for selected profiles."""
    base_path = repo_root / "assistants/cursor/settings.base.json"
    document = json.loads(base_path.read_text())
    if "work" in profiles:
        overlay_path = repo_root / "assistants/cursor/settings.work.json"
        document = deep_merge(
            document,
            json.loads(overlay_path.read_text()),
        )
    if not isinstance(document, dict):
        raise ValueError("Cursor settings must be a JSON object")
    return document


def cursor_settings_renderer(
    paths: RuntimePaths,
    *,
    work: bool,
) -> Renderer:
    """Build the profile-aware Cursor settings renderer."""
    work_path = paths.repo_root / "assistants/cursor/settings.work.json"

    def render(source: bytes, current: bytes | None) -> bytes:
        del current
        document: object = json.loads(source)
        if work:
            document = deep_merge(
                document,
                json.loads(work_path.read_bytes()),
            )
        return (
            json.dumps(document, indent=2, sort_keys=True).encode()
            + b"\n"
        )

    return render


def cursor_rules_renderer(paths: RuntimePaths) -> Renderer:
    """Render shared guidance plus the Cursor-specific suffix."""
    engineering = (
        paths.repo_root / "assistants/shared/instructions/engineering.md"
    ).read_text()
    rtk = (
        paths.repo_root / "assistants/shared/instructions/rtk.md"
    ).read_text()

    def render(source: bytes, current: bytes | None) -> bytes:
        del current
        return render_native_instructions(
            engineering=engineering,
            rtk=rtk,
            agent_suffix=source.decode(),
        ).encode()

    return render


def install_actions(
    setup: ResolvedSetup,
    paths: RuntimePaths,
    runner: Runner,
) -> tuple[InstallAction, ...]:
    """Read current Cursor state and return only missing installs."""
    if not setup.is_enabled("cursor"):
        return ()
    listed = runner.run(("cursor", "--list-extensions"))
    installed = (
        frozenset(
            line.strip().lower()
            for line in listed["stdout"].splitlines()
            if line.strip()
        )
        if listed["returncode"] == 0
        else frozenset()
    )
    bundled = read_bundled_extensions(
        Path(
            "/Applications/Cursor.app/Contents/Resources/app/extensions"
        )
    )
    enabled = frozenset(
        agent
        for agent in ("cursor", "claude-code", "codex")
        if setup.is_enabled(agent)
    )
    return plan_cursor_extension_actions(
        paths.repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=enabled,
        installed=installed,
        bundled=bundled,
    )


def configuration(
    setup: ResolvedSetup,
    paths: RuntimePaths,
) -> ConfigurationContribution:
    """Return Cursor-owned settings, keybindings, and manual rules."""
    if not setup.is_enabled("cursor"):
        return ConfigurationContribution(specs=())
    settings = ManagedFileSpec(
        id="cursor.settings",
        source=paths.repo_root / "assistants/cursor/settings.base.json",
        destination=(
            paths.home
            / "Library/Application Support/Cursor/User/settings.json"
        ),
        method=ApplyMethod.RENDER,
        renderer_id="cursor-settings",
        validator_id="json",
        component="cursor",
    )
    keybindings = ManagedFileSpec(
        id="cursor.keybindings",
        source=paths.repo_root / "assistants/cursor/keybindings.json",
        destination=(
            paths.home
            / "Library/Application Support/Cursor/User/keybindings.json"
        ),
        method=ApplyMethod.COPY,
        validator_id="json",
        component="cursor",
    )
    user_rules = ManagedFileSpec(
        id="cursor.user-rules",
        source=paths.repo_root / "assistants/cursor/user-rules.md",
        destination=(
            paths.state_root / "manual/cursor-user-rules.md"
        ),
        method=ApplyMethod.RENDER,
        renderer_id="cursor-user-rules",
        component="cursor",
    )
    return ConfigurationContribution(
        specs=(settings, keybindings, user_rules),
        renderers={
            "cursor-settings": cursor_settings_renderer(
                paths,
                work="work" in setup.profiles,
            ),
            "cursor-user-rules": cursor_rules_renderer(paths),
        },
    )
```

The hook adapter remains the sole owner of `~/.cursor/hooks.json`. The Cursor
adapter never opens a URL or cleans a downloaded file; core `Installer` owns
the verified-download lifecycle. Extensions outside the curated set remain
diagnostic-only and are never uninstalled.

- [ ] **Step 5: Run focused tests and checkpoint**

Run:

```bash
rtk uv run pytest tests/assistants/test_cursor.py -q
rtk uv run python -m json.tool assistants/cursor/settings.base.json
rtk uv run python -m json.tool assistants/cursor/settings.work.json
rtk uv run python -m json.tool assistants/cursor/keybindings.json
rtk uv run python -m json.tool assistants/cursor/hooks.json
```

Expected: tests pass and all JSON sources parse.

Checkpoint:

```bash
rtk jj describe -m "feat: restore Cursor settings and extensions"
rtk jj new
```

### Task 5: Configure Claude Code with reviewed plugins

**Files:**

- Create: `src/ballen_config/assistants/claude.py`
- Move: `claude-code/settings.json` to `assistants/claude/settings.json`
- Create: `assistants/claude/CLAUDE.md`
- Create: `assistants/claude/plugins.yaml`
- Create: `tests/assistants/test_claude.py`
- Modify: `assistants/inventory.yaml`

- [ ] **Step 1: Write stable-settings and plugin-action tests**

```python
# tests/assistants/test_claude.py
import json
from pathlib import Path

from ballen_config.assistants.claude import (
    claude_configuration,
    claude_settings_renderer,
    load_stable_settings,
    plan_claude_plugins,
)
from ballen_config.assistants.hooks import hook_contribution
from ballen_config.install import Installer
from tests.assistants.fakes import StatefulAssistantFake


def test_stable_settings_have_no_runtime_state(repo_root: Path) -> None:
    """Track only authored Claude preferences and the stable RTK hook."""
    settings = load_stable_settings(
        repo_root / "assistants/claude/settings.json"
    )
    serialized = settings.model_dump_json()
    forbidden = (
        "/Users/",
        "projects",
        "session",
        "history",
        "oauth",
        "token",
        "cache-heal",
        "plugins/cache",
        "update-piste-plato",
    )
    assert all(term not in serialized for term in forbidden)


def test_plugin_commands_are_user_scoped(repo_root: Path) -> None:
    """Install reviewed marketplaces and plugins through Claude's CLI."""
    actions = plan_claude_plugins(
        repo_root / "assistants/claude/plugins.yaml",
        profiles=("default",),
        installed=frozenset(),
    )
    commands = [action.argv for action in actions]
    assert (
        "claude",
        "plugin",
        "marketplace",
        "add",
        "--scope",
        "user",
        "anthropics/claude-plugins-official",
    ) in commands
    assert (
        "claude",
        "plugin",
        "install",
        "--scope",
        "user",
        "frontend-design@claude-plugins-official",
    ) in commands


def test_gitlab_and_repo_plugins_are_absent(repo_root: Path) -> None:
    """Use glab and repo add-ons instead of global GitLab/Plato plugins."""
    text = (repo_root / "assistants/claude/plugins.yaml").read_text()
    assert "gitlab@" not in text
    assert "plato@" not in text
    assert "plato-local" not in text


def test_claude_settings_merge_preserves_cli_owned_fields(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Change managed keys without erasing native plugin state."""
    current = b"""{
      "extraKnownMarketplaces": {
        "native-market": {"source": "owner/repo"}
      },
      "enabledPlugins": {"native@native-market": true},
      "effortLevel": "high",
      "hooks": {
        "SessionStart": [{"hooks": [{"type": "command", "command": "native"}]}]
      }
    }"""
    rendered = claude_settings_renderer(temporary_home)(
        (
            repo_root / "assistants/claude/settings.json"
        ).read_bytes(),
        current,
    )
    document = json.loads(rendered)
    assert document["model"] == "opus"
    assert document["extraKnownMarketplaces"] == {
        "native-market": {"source": "owner/repo"}
    }
    assert document["enabledPlugins"] == {
        "native@native-market": True
    }
    assert document["effortLevel"] == "high"
    assert "SessionStart" in document["hooks"]
    assert any(
        hook["hooks"][0]["command"].endswith("rtk-hook claude")
        for hook in document["hooks"]["PreToolUse"]
    )


def test_claude_is_the_only_settings_owner(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Reject duplicate ownership between hook and Claude adapters."""
    hooks = hook_contribution(
        repo_root=repo_root,
        home=temporary_home,
        enabled=frozenset({"cursor", "claude-code"}),
    )
    claude = claude_configuration(
        repo_root=repo_root,
        home=temporary_home,
        profiles=("default",),
        enabled=frozenset({"cursor", "claude-code"}),
    )
    specs = (*hooks.specs, *claude.specs)
    destinations = [spec.destination for spec in specs]
    assert destinations.count(
        temporary_home / ".claude/settings.json"
    ) == 1


def test_install_then_configure_preserves_native_plugin_fields(
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Match core all-stage ordering: install before configure."""
    actions = plan_claude_plugins(
        repo_root / "assistants/claude/plugins.yaml",
        profiles=("default",),
        installed=frozenset(),
    )
    installer = Installer(fake_runner, temporary_home)
    for action in actions:
        installer.run_action(action)
    settings_path = temporary_home / ".claude/settings.json"
    rendered = claude_settings_renderer(temporary_home)(
        (
            repo_root / "assistants/claude/settings.json"
        ).read_bytes(),
        settings_path.read_bytes(),
    )
    document = json.loads(rendered)
    assert document["extraKnownMarketplaces"]
    assert document["enabledPlugins"]
    assert set(document["enabledPlugins"]) == fake_runner.claude_plugins
```

Use this exact ordering assertion:

```python
def test_claude_actions_are_ordered_and_installed_plugins_are_noops(
    repo_root: Path,
) -> None:
    """Place marketplaces first and omit an installed plugin."""
    actions = plan_claude_plugins(
        repo_root / "assistants/claude/plugins.yaml",
        profiles=("default",),
        installed=frozenset(
            {"frontend-design@claude-plugins-official"}
        ),
    )
    ids = [action.component_id for action in actions]
    assert "claude.plugin.frontend-design@claude-plugins-official" not in ids
    marketplace_indexes = [
        index
        for index, item in enumerate(ids)
        if item.startswith("claude.marketplace.")
    ]
    plugin_indexes = [
        index
        for index, item in enumerate(ids)
        if item.startswith("claude.plugin.")
    ]
    assert max(marketplace_indexes) < min(plugin_indexes)
```

- [ ] **Step 2: Run the focused test and confirm the red state**

Run:

```bash
rtk uv run pytest tests/assistants/test_claude.py -q
```

Expected: import fails because `claude.py` does not exist.

- [ ] **Step 3: Reduce settings to stable authored state**

Move the reviewed legacy source once:

```bash
rtk mkdir -p assistants/claude
rtk mv claude-code/settings.json assistants/claude/settings.json
```

Keep the current `model: "opus"` preference if it is still present in the
tracked legacy file, retain only plugin enablement represented by
`plugins.yaml`, and merge the stable RTK hook from Task 3. The committed
`assistants/claude/settings.json` must have this shape:

```json
{
  "model": "opus"
}
```

The Claude CLI, not the bootstrap renderer, owns
`extraKnownMarketplaces` and `enabledPlugins`. Implement a key-level renderer
that changes only the allowlisted stable source keys and the one managed RTK
hook, while preserving every other existing local key:

```python
# src/ballen_config/assistants/claude.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NotRequired, TypedDict

import yaml
from pydantic import BaseModel, ConfigDict

from ballen_config.assistants.hooks import claude_hook_fragment
from ballen_config.assistants.instructions import (
    render_native_instructions,
)
from ballen_config.assistants.models import PluginCatalog
from ballen_config.configure import (
    ApplyMethod,
    ConfigurationContribution,
    ManagedFileSpec,
    Renderer,
)
from ballen_config.install import InstallAction
from ballen_config.models import ResolvedSetup
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths


class ClaudeStableSettings(BaseModel):
    """Repository-owned Claude settings keys."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str


class ClaudePluginEntry(TypedDict):
    """One entry returned by `claude plugin list --json`."""

    id: str


class ClaudeMarketplaceEntry(TypedDict):
    """One known marketplace returned by the Claude CLI."""

    name: str


class ClaudePluginSnapshot(TypedDict):
    """External Claude plugin-list response fields used by the adapter."""

    plugins: list[ClaudePluginEntry]
    marketplaces: NotRequired[list[ClaudeMarketplaceEntry]]


def load_stable_settings(path: Path) -> ClaudeStableSettings:
    """Load the allowlisted repository-owned settings."""
    return ClaudeStableSettings.model_validate_json(path.read_text())


def _is_managed_rtk_hook(value: object) -> bool:
    """Identify only this repository's RTK hook registration."""
    if not isinstance(value, dict):
        return False
    hooks = value.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(
        isinstance(hook, dict)
        and isinstance(hook.get("command"), str)
        and hook["command"].endswith("rtk-hook claude")
        for hook in hooks
    )


def claude_settings_renderer(home: Path) -> Renderer:
    """Build a key-level renderer that preserves native CLI state."""
    managed_hook = claude_hook_fragment(home)["hooks"]["PreToolUse"][0]

    def render(source: bytes, current: bytes | None) -> bytes:
        stable = ClaudeStableSettings.model_validate_json(source)
        existing: dict[str, Any] = (
            json.loads(current) if current is not None else {}
        )
        if not isinstance(existing, dict):
            raise ValueError("Claude settings must be a JSON object")
        result = dict(existing)
        result["model"] = stable.model
        existing_hooks = existing.get("hooks", {})
        if not isinstance(existing_hooks, dict):
            existing_hooks = {}
        hooks = dict(existing_hooks)
        pre_tool_use = hooks.get("PreToolUse", [])
        if not isinstance(pre_tool_use, list):
            pre_tool_use = []
        hooks["PreToolUse"] = [
            item
            for item in pre_tool_use
            if not _is_managed_rtk_hook(item)
        ] + [managed_hook]
        result["hooks"] = hooks
        return (
            json.dumps(result, indent=2, sort_keys=True).encode()
            + b"\n"
        )

    return render


def plan_claude_plugins(
    catalog_path: Path,
    *,
    profiles: tuple[str, ...],
    installed: frozenset[str],
    known_marketplaces: frozenset[str] = frozenset(),
) -> tuple[InstallAction, ...]:
    """Plan missing Claude marketplaces and plugins deterministically."""
    catalog = PluginCatalog.model_validate(
        yaml.safe_load(catalog_path.read_text())
    )
    active = set(profiles)
    selected_plugins = tuple(
        plugin
        for plugin in catalog.plugins
        if active.intersection(plugin.profiles)
    )
    selected_marketplaces = {
        plugin.marketplace for plugin in selected_plugins
    }
    marketplace_by_name = {
        marketplace.name: marketplace
        for marketplace in catalog.marketplaces
    }
    actions: list[InstallAction] = []
    for name in sorted(selected_marketplaces - known_marketplaces):
        marketplace = marketplace_by_name[name]
        required = any(
            plugin.required
            for plugin in selected_plugins
            if plugin.marketplace == name
        )
        actions.append(
            InstallAction(
                component_id=f"claude.marketplace.{name}",
                argv=(
                    "claude",
                    "plugin",
                    "marketplace",
                    "add",
                    "--scope",
                    "user",
                    marketplace.source,
                ),
                required=required,
            )
        )
    for plugin in sorted(selected_plugins, key=lambda item: item.id):
        if plugin.id in installed:
            continue
        actions.append(
            InstallAction(
                component_id=f"claude.plugin.{plugin.id}",
                argv=(
                    "claude",
                    "plugin",
                    "install",
                    "--scope",
                    "user",
                    plugin.id,
                ),
                required=plugin.required,
            )
        )
    return tuple(actions)


def install_actions(
    setup: ResolvedSetup,
    paths: RuntimePaths,
    runner: Runner,
) -> tuple[InstallAction, ...]:
    """Inspect Claude's native inventory and return only missing actions."""
    if not setup.is_enabled("claude-code"):
        return ()
    listed = runner.run(("claude", "plugin", "list", "--json"))
    snapshot: ClaudePluginSnapshot = (
        json.loads(listed["stdout"])
        if listed["returncode"] == 0
        else {"plugins": [], "marketplaces": []}
    )
    return plan_claude_plugins(
        paths.repo_root / "assistants/claude/plugins.yaml",
        profiles=setup.profiles,
        installed=frozenset(
            plugin["id"] for plugin in snapshot["plugins"]
        ),
        known_marketplaces=frozenset(
            marketplace["name"]
            for marketplace in snapshot.get("marketplaces", [])
        ),
    )


def claude_instruction_renderer(paths: RuntimePaths) -> Renderer:
    """Render canonical guidance plus the Claude-specific suffix."""
    engineering = (
        paths.repo_root / "assistants/shared/instructions/engineering.md"
    ).read_text()
    rtk = (
        paths.repo_root / "assistants/shared/instructions/rtk.md"
    ).read_text()

    def render(source: bytes, current: bytes | None) -> bytes:
        del current
        return render_native_instructions(
            engineering=engineering,
            rtk=rtk,
            agent_suffix=source.decode(),
        ).encode()

    return render


def claude_configuration(
    *,
    repo_root: Path,
    home: Path,
    profiles: tuple[str, ...],
    enabled: frozenset[str],
) -> ConfigurationContribution:
    """Return Claude-owned files and pure renderers."""
    del profiles
    if "claude-code" not in enabled:
        return ConfigurationContribution(specs=())
    settings = ManagedFileSpec(
        id="claude.settings",
        source=repo_root / "assistants/claude/settings.json",
        destination=home / ".claude/settings.json",
        method=ApplyMethod.RENDER,
        renderer_id="claude-settings",
        mode=0o600,
        component="claude-code",
    )
    instructions = ManagedFileSpec(
        id="claude.instructions",
        source=repo_root / "assistants/claude/CLAUDE.md",
        destination=home / ".claude/CLAUDE.md",
        method=ApplyMethod.RENDER,
        renderer_id="claude-instructions",
        mode=0o600,
        component="claude-code",
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=home)
    return ConfigurationContribution(
        specs=(settings, instructions),
        renderers={
            "claude-settings": claude_settings_renderer(home),
            "claude-instructions": claude_instruction_renderer(paths),
        },
    )
```

`claude_configuration()` is the sole owner of
`~/.claude/settings.json`. Extend its returned contribution with the
instruction spec and instruction renderer defined in Task 3; do not add this
destination to `hooks.py`. The core configuration engine backs up and
atomically replaces a conflicting destination, but never records its contents.

Write `assistants/claude/CLAUDE.md` as this Claude-specific suffix:

```markdown
# Claude Code additions

Repository instructions take precedence for repository-specific behavior.
Do not copy credentials, sessions, project trust, or generated plugin state
between machines.
```

Append the final Claude file entries to `assistants/inventory.yaml`:

```yaml
  - id: claude.settings
    kind: file
    owner: claude-code
    source: assistants/claude/settings.json
    destination: .claude/settings.json
    role: render-source

  - id: claude.instructions
    kind: file
    owner: claude-code
    source: assistants/claude/CLAUDE.md
    destination: .claude/CLAUDE.md
    role: suffix

  - id: claude.plugins.catalog
    kind: catalog
    owner: claude-code
    source: assistants/claude/plugins.yaml
    catalog_kind: plugin
    item_ids:
      - bigspin@bigspinai
      - context-mode@claude-context-mode
      - frontend-design@claude-plugins-official
      - iterative-development@prime-radiant-marketplace
      - logfire@claude-plugins-official
      - ponytail@ponytail
      - pydantic-ai@claude-plugins-official
      - superpowers@claude-plugins-official
      - superpowers-developing-for-claude-code@superpowers-marketplace
      - ami-qsp-tools@piste
      - fieldkit@piste
```

The Claude adapter owns both rendered destinations. Settings are emitted once
after the native plugin CLI has updated `extraKnownMarketplaces` and
`enabledPlugins`; its key-level renderer preserves those fields and merges the
stable hook. `CLAUDE.md` is emitted once after prepending the canonical
engineering and RTK sources through `render_native_instructions()`.

- [ ] **Step 4: Declare the reviewed plugin set**

```yaml
# assistants/claude/plugins.yaml
marketplaces:
  - name: claude-plugins-official
    source: anthropics/claude-plugins-official
    profiles: [default]
  - name: superpowers-marketplace
    source: obra/superpowers-marketplace
    profiles: [default]
  - name: claude-context-mode
    source: mksglu/claude-context-mode
    profiles: [default]
  - name: bigspinai
    source: bigspinai/toolkit
    profiles: [default]
  - name: prime-radiant-marketplace
    source: prime-radiant-inc/prime-radiant-marketplace
    profiles: [default]
  - name: ponytail
    source: DietrichGebert/ponytail
    profiles: [default]
  - name: piste
    source: git@gitlab.com:flagship-informatics/internal-open-source/piste.git
    profiles: [work]

plugins:
  - id: bigspin@bigspinai
    marketplace: bigspinai
    profiles: [default]
  - id: context-mode@claude-context-mode
    marketplace: claude-context-mode
    profiles: [default]
  - id: frontend-design@claude-plugins-official
    marketplace: claude-plugins-official
    profiles: [default]
  - id: iterative-development@prime-radiant-marketplace
    marketplace: prime-radiant-marketplace
    profiles: [default]
  - id: logfire@claude-plugins-official
    marketplace: claude-plugins-official
    profiles: [default]
  - id: ponytail@ponytail
    marketplace: ponytail
    profiles: [default]
  - id: pydantic-ai@claude-plugins-official
    marketplace: claude-plugins-official
    profiles: [default]
  - id: superpowers@claude-plugins-official
    marketplace: claude-plugins-official
    profiles: [default]
  - id: superpowers-developing-for-claude-code@superpowers-marketplace
    marketplace: superpowers-marketplace
    profiles: [default]
  - id: ami-qsp-tools@piste
    marketplace: piste
    profiles: [work]
    required: false
  - id: fieldkit@piste
    marketplace: piste
    profiles: [work]
    required: false
```

Do not migrate duplicate inline/legacy context-mode registrations, `gitlab`,
either `plato` registration, or local marketplaces. The two work-wide Piste
plugins are optional because the private marketplace is unavailable until SSH
access is established; repository-specific Plato remains a repo add-on.

- [ ] **Step 5: Run focused tests and checkpoint**

Run:

```bash
rtk uv run pytest tests/assistants/test_claude.py -q
rtk uv run python -m json.tool assistants/claude/settings.json
```

Expected: tests pass and settings parse.

Checkpoint:

```bash
rtk jj describe -m "feat: configure Claude Code plugins and settings"
rtk jj new
```

### Task 6: Configure Codex without machine-local state

**Files:**

- Create: `src/ballen_config/assistants/codex.py`
- Create: `assistants/codex/AGENTS.md`
- Create: `assistants/codex/config.overlay.toml`
- Create: `assistants/codex/plugins.yaml`
- Create: `tests/assistants/test_codex.py`
- Modify: `assistants/inventory.yaml`

- [ ] **Step 1: Write overlay and plugin tests**

```python
# tests/assistants/test_codex.py
from pathlib import Path
import tomllib

from ballen_config.assistants.codex import (
    codex_overlay_renderer,
    configuration,
    install_actions,
    load_portable_overlay,
    plan_codex_plugins,
)
from ballen_config.configure import ApplyMethod
from ballen_config.manifests import ManifestRepository
from ballen_config.models import ResolutionRequest
from ballen_config.runtime import RuntimePaths
from tests.assistants.fakes import StatefulAssistantFake


def test_overlay_contains_only_portable_preferences(repo_root: Path) -> None:
    """Exclude generated paths, trust, auth, runtime MCP, and state."""
    overlay = load_portable_overlay(
        repo_root / "assistants/codex/config.overlay.toml"
    )
    assert set(overlay) == {
        "model",
        "model_reasoning_effort",
        "service_tier",
    }
    serialized = repr(overlay)
    forbidden = (
        "/Users/",
        "projects",
        "trusted",
        "auth",
        "mcp_servers",
        "notify",
        "plugins/cache",
        "sqlite",
    )
    assert all(term not in serialized for term in forbidden)


def test_plugin_commands_use_json_mode(repo_root: Path) -> None:
    """Use stable machine-readable Codex plugin commands."""
    actions = plan_codex_plugins(
        repo_root / "assistants/codex/plugins.yaml",
        profiles=("default",),
        installed=frozenset(),
    )
    commands = [action.argv for action in actions]
    assert (
        "codex",
        "plugin",
        "marketplace",
        "add",
        "anthropics/claude-plugins-official",
        "--json",
    ) in commands
    assert (
        "codex",
        "plugin",
        "add",
        "frontend-design@claude-plugins-official",
        "--json",
    ) in commands


def test_repo_and_gitlab_plugins_are_absent(repo_root: Path) -> None:
    """Keep GitLab and Plato behavior out of global Codex state."""
    text = (repo_root / "assistants/codex/plugins.yaml").read_text()
    assert "gitlab" not in text.lower()
    assert "plato" not in text.lower()


def test_codex_actions_filter_order_and_severity(repo_root: Path) -> None:
    """Filter installed/default entries and preserve optional work severity."""
    actions = plan_codex_plugins(
        repo_root / "assistants/codex/plugins.yaml",
        profiles=("default", "work"),
        installed=frozenset(
            {"frontend-design@claude-plugins-official"}
        ),
    )
    ids = [action.component_id for action in actions]
    assert "codex.plugin.frontend-design@claude-plugins-official" not in ids
    marketplaces = [
        index
        for index, identifier in enumerate(ids)
        if identifier.startswith("codex.marketplace.")
    ]
    plugins = [
        index
        for index, identifier in enumerate(ids)
        if identifier.startswith("codex.plugin.")
    ]
    assert max(marketplaces) < min(plugins)
    piste = [
        action
        for action in actions
        if "piste" in action.component_id
        or "ami-qsp-tools" in action.component_id
        or "fieldkit" in action.component_id
    ]
    assert piste
    assert all(not action.required for action in piste)


def test_codex_overlay_preserves_native_tables(repo_root: Path) -> None:
    """Change three keys without rewriting native plugin or trust tables."""
    current = b"""
model = "old"
[plugins]
enabled = ["native"]
[projects."/example"]
trust_level = "trusted"
"""
    rendered = codex_overlay_renderer()(
        (
            repo_root / "assistants/codex/config.overlay.toml"
        ).read_bytes(),
        current,
    )
    before = tomllib.loads(current.decode())
    after = tomllib.loads(rendered.decode())
    assert after["plugins"] == before["plugins"]
    assert after["projects"] == before["projects"]
    assert {
        key: after[key]
        for key in (
            "model",
            "model_reasoning_effort",
            "service_tier",
        )
    } == load_portable_overlay(
        repo_root / "assistants/codex/config.overlay.toml"
    )


def test_codex_skip_has_no_actions_specs_or_hook(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Remove the complete Codex surface before native inspection."""
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile="work", skips=("codex",))
    )
    paths = RuntimePaths.from_roots(
        repo_root=repo_root,
        home=temporary_home,
    )
    runner = StatefulAssistantFake(temporary_home)
    assert install_actions(setup, paths, runner) == ()
    contribution = configuration(setup, paths)
    assert contribution.specs == ()
    assert runner.commands == []


def test_enabled_codex_configuration_has_no_rtk_hook(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Rely on native Codex hooks instead of inventing an RTK adapter."""
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile="default")
    )
    paths = RuntimePaths.from_roots(
        repo_root=repo_root,
        home=temporary_home,
    )
    contribution = configuration(setup, paths)
    assert {spec.id for spec in contribution.specs} == {
        "codex.config",
        "codex.instructions",
        "codex.rtk",
    }
    assert all("hook" not in spec.id for spec in contribution.specs)
    rtk = next(spec for spec in contribution.specs if spec.id == "codex.rtk")
    assert rtk.source == (
        repo_root / "assistants/shared/instructions/rtk.md"
    )
    assert rtk.destination == temporary_home / ".codex/RTK.md"
    assert rtk.method is ApplyMethod.COPY
```

- [ ] **Step 2: Run the focused test and confirm the red state**

Run:

```bash
rtk uv run pytest tests/assistants/test_codex.py -q
```

Expected: import fails because `codex.py` does not exist.

- [ ] **Step 3: Commit the portable Codex sources**

```toml
# assistants/codex/config.overlay.toml
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"
service_tier = "priority"
```

This is an overlay, not a snapshot. The adapter validates an allowlist of
exactly those three keys. Its `ApplyMethod.RENDER` callback parses an existing
destination with `tomlkit`, changes only those keys, and preserves every other
local-only table without inspecting, logging, persisting in bootstrap state, or
copying it into the repository. The core engine backs up and atomically
replaces the destination. On a clean machine, rendering starts from an empty
TOML document. This key-level convergence prevents later or earlier native
plugin installation from being erased.

Write `assistants/codex/AGENTS.md` as the Codex-specific suffix:

```markdown
# Codex additions

Repository instructions take precedence for repository-specific behavior.
Never migrate authentication, trust, sessions, project paths, or generated
plugin state.
```

The adapter renders native `~/.codex/AGENTS.md` by prepending canonical
engineering guidance and an injected absolute include of
`~/.codex/RTK.md`. It manages `~/.codex/RTK.md` directly from
`assistants/shared/instructions/rtk.md`. Tracked sources contain no local
project paths, secrets, authentication material, sessions, or cache paths.

Append the final Codex entries to `assistants/inventory.yaml`:

```yaml
  - id: codex.config
    kind: file
    owner: codex
    source: assistants/codex/config.overlay.toml
    destination: .codex/config.toml
    role: overlay

  - id: codex.instructions
    kind: file
    owner: codex
    source: assistants/codex/AGENTS.md
    destination: .codex/AGENTS.md
    role: suffix

  - id: codex.rtk
    kind: file
    owner: codex
    source: assistants/shared/instructions/rtk.md
    destination: .codex/RTK.md

  - id: codex.plugins.catalog
    kind: catalog
    owner: codex
    source: assistants/codex/plugins.yaml
    catalog_kind: plugin
    item_ids:
      - bigspin@bigspinai
      - context-mode@context-mode
      - frontend-design@claude-plugins-official
      - github@claude-plugins-official
      - logfire@claude-plugins-official
      - superpowers@claude-plugins-official
      - superpowers-developing-for-claude-code@superpowers-marketplace
      - ami-qsp-tools@piste
      - fieldkit@piste
```

The Codex adapter treats `codex.config` as a rendered allowlisted TOML overlay.
It renders `codex.instructions` through `render_native_instructions()` and
uses a direct managed-file action for the canonical RTK source.

- [ ] **Step 4: Declare the conservative Codex plugin set**

Use only reviewed generic marketplaces that have a stable Git source:

```yaml
# assistants/codex/plugins.yaml
marketplaces:
  - name: claude-plugins-official
    source: anthropics/claude-plugins-official
    profiles: [default]
  - name: superpowers-marketplace
    source: obra/superpowers-marketplace
    profiles: [default]
  - name: context-mode
    source: mksglu/claude-context-mode
    profiles: [default]
  - name: bigspinai
    source: bigspinai/toolkit
    profiles: [default]
  - name: piste
    source: git@gitlab.com:flagship-informatics/internal-open-source/piste.git
    profiles: [work]

plugins:
  - id: bigspin@bigspinai
    marketplace: bigspinai
    profiles: [default]
  - id: context-mode@context-mode
    marketplace: context-mode
    profiles: [default]
  - id: frontend-design@claude-plugins-official
    marketplace: claude-plugins-official
    profiles: [default]
  - id: github@claude-plugins-official
    marketplace: claude-plugins-official
    profiles: [default]
  - id: logfire@claude-plugins-official
    marketplace: claude-plugins-official
    profiles: [default]
  - id: superpowers@claude-plugins-official
    marketplace: claude-plugins-official
    profiles: [default]
  - id: superpowers-developing-for-claude-code@superpowers-marketplace
    marketplace: superpowers-marketplace
    profiles: [default]
  - id: ami-qsp-tools@piste
    marketplace: piste
    profiles: [work]
    required: false
  - id: fieldkit@piste
    marketplace: piste
    profiles: [work]
    required: false
```

Do not duplicate Codex-bundled browser, computer-use, Sites, visualize,
documents, PDF, spreadsheet, presentation, or template capabilities as copied
files. Doctor checks availability and documents first-party installation if a
new Codex release does not bundle them. Do not migrate Plato, GitLab, local
marketplaces, or generated OpenAI runtime registrations. `ami-qsp-tools` and
`fieldkit` are optional work-wide plugins; their SSH-hosted marketplace is
attempted only in the work profile after the user has arranged access.

- [ ] **Step 5: Implement Codex actions and managed files**

```python
# src/ballen_config/assistants/codex.py
from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import NotRequired, TypedDict

import tomlkit
import yaml

from ballen_config.assistants.instructions import (
    render_native_instructions,
)
from ballen_config.assistants.models import PluginCatalog
from ballen_config.configure import (
    ApplyMethod,
    ConfigurationContribution,
    ManagedFileSpec,
    Renderer,
)
from ballen_config.install import InstallAction
from ballen_config.models import ResolvedSetup
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths


PORTABLE_KEYS = frozenset(
    {"model", "model_reasoning_effort", "service_tier"}
)


class CodexPluginEntry(TypedDict):
    """One installed Codex plugin."""

    id: str


class CodexMarketplaceEntry(TypedDict):
    """One installed Codex marketplace."""

    name: str


class CodexPluginSnapshot(TypedDict):
    """External Codex plugin-list fields consumed by the adapter."""

    plugins: list[CodexPluginEntry]
    marketplaces: NotRequired[list[CodexMarketplaceEntry]]


def load_portable_overlay(path: Path) -> dict[str, object]:
    """Load and enforce the three-key portable Codex overlay."""
    overlay = tomllib.loads(path.read_text())
    if set(overlay) != PORTABLE_KEYS:
        raise ValueError("Codex overlay contains non-portable keys")
    return overlay


def codex_overlay_renderer() -> Renderer:
    """Change only portable top-level keys in the native TOML document."""
    def render(source: bytes, current: bytes | None) -> bytes:
        overlay = tomllib.loads(source.decode())
        if set(overlay) != PORTABLE_KEYS:
            raise ValueError("Codex overlay contains non-portable keys")
        document = (
            tomlkit.parse(current.decode())
            if current is not None
            else tomlkit.document()
        )
        for key in sorted(PORTABLE_KEYS):
            document[key] = overlay[key]
        return tomlkit.dumps(document).encode()

    return render


def plan_codex_plugins(
    catalog_path: Path,
    *,
    profiles: tuple[str, ...],
    installed: frozenset[str],
    known_marketplaces: frozenset[str] = frozenset(),
) -> tuple[InstallAction, ...]:
    """Plan missing Codex marketplaces and plugins deterministically."""
    catalog = PluginCatalog.model_validate(
        yaml.safe_load(catalog_path.read_text())
    )
    active = set(profiles)
    selected_plugins = tuple(
        plugin
        for plugin in catalog.plugins
        if active.intersection(plugin.profiles)
    )
    selected_marketplaces = {
        plugin.marketplace for plugin in selected_plugins
    }
    marketplace_by_name = {
        marketplace.name: marketplace
        for marketplace in catalog.marketplaces
    }
    actions: list[InstallAction] = []
    for name in sorted(selected_marketplaces - known_marketplaces):
        marketplace = marketplace_by_name[name]
        actions.append(
            InstallAction(
                component_id=f"codex.marketplace.{name}",
                argv=(
                    "codex",
                    "plugin",
                    "marketplace",
                    "add",
                    marketplace.source,
                    "--json",
                ),
                required=any(
                    plugin.required
                    for plugin in selected_plugins
                    if plugin.marketplace == name
                ),
            )
        )
    for plugin in sorted(selected_plugins, key=lambda item: item.id):
        if plugin.id in installed:
            continue
        actions.append(
            InstallAction(
                component_id=f"codex.plugin.{plugin.id}",
                argv=(
                    "codex",
                    "plugin",
                    "add",
                    plugin.id,
                    "--json",
                ),
                required=plugin.required,
            )
        )
    return tuple(actions)


def install_actions(
    setup: ResolvedSetup,
    paths: RuntimePaths,
    runner: Runner,
) -> tuple[InstallAction, ...]:
    """Inspect Codex's native inventory and return only missing actions."""
    if not setup.is_enabled("codex"):
        return ()
    listed = runner.run(("codex", "plugin", "list", "--json"))
    snapshot: CodexPluginSnapshot = (
        json.loads(listed["stdout"])
        if listed["returncode"] == 0
        else {"plugins": [], "marketplaces": []}
    )
    return plan_codex_plugins(
        paths.repo_root / "assistants/codex/plugins.yaml",
        profiles=setup.profiles,
        installed=frozenset(
            plugin["id"] for plugin in snapshot["plugins"]
        ),
        known_marketplaces=frozenset(
            marketplace["name"]
            for marketplace in snapshot.get("marketplaces", [])
        ),
    )


def codex_instruction_renderer(paths: RuntimePaths) -> Renderer:
    """Render engineering guidance plus an absolute RTK include."""
    engineering = (
        paths.repo_root / "assistants/shared/instructions/engineering.md"
    ).read_text()
    rtk = (
        paths.repo_root / "assistants/shared/instructions/rtk.md"
    ).read_text()

    def render(source: bytes, current: bytes | None) -> bytes:
        del current
        return render_native_instructions(
            engineering=engineering,
            rtk=rtk,
            agent_suffix=source.decode(),
            rtk_include=paths.home / ".codex/RTK.md",
        ).encode()

    return render


def configuration(
    setup: ResolvedSetup,
    paths: RuntimePaths,
) -> ConfigurationContribution:
    """Return only portable Codex files; native plugin tables stay local."""
    if not setup.is_enabled("codex"):
        return ConfigurationContribution(specs=())
    specs = (
        ManagedFileSpec(
            id="codex.config",
            source=paths.repo_root / "assistants/codex/config.overlay.toml",
            destination=paths.home / ".codex/config.toml",
            method=ApplyMethod.RENDER,
            renderer_id="codex-overlay",
            validator_id="toml",
            component="codex",
        ),
        ManagedFileSpec(
            id="codex.instructions",
            source=paths.repo_root / "assistants/codex/AGENTS.md",
            destination=paths.home / ".codex/AGENTS.md",
            method=ApplyMethod.RENDER,
            renderer_id="codex-instructions",
            component="codex",
        ),
        ManagedFileSpec(
            id="codex.rtk",
            source=(
                paths.repo_root
                / "assistants/shared/instructions/rtk.md"
            ),
            destination=paths.home / ".codex/RTK.md",
            method=ApplyMethod.COPY,
            component="codex",
        ),
    )
    return ConfigurationContribution(
        specs=specs,
        renderers={
            "codex-overlay": codex_overlay_renderer(),
            "codex-instructions": codex_instruction_renderer(paths),
        },
    )
```

There is no `rtk hook codex` adapter, so this module emits no hook spec.
Core `Installer` preserves required/optional action severity; the renderers
preserve native plugin tables and project trust without logging their values.

- [ ] **Step 6: Run focused tests and checkpoint**

Run:

```bash
rtk uv run pytest tests/assistants/test_codex.py -q
rtk uv run python -c 'import tomllib; tomllib.load(open("assistants/codex/config.overlay.toml", "rb"))'
```

Expected: tests pass and the overlay parses.

Checkpoint:

```bash
rtk jj describe -m "feat: configure portable Codex settings and plugins"
rtk jj new
```

### Task 7: Add agent-aware doctor checks and repository policy

**Files:**

- Create: `src/ballen_config/assistants/checks.py`
- Create: `tests/assistants/test_checks.py`
- Modify: `src/ballen_config/policy.py`
- Modify: `tests/test_policy.py`

- [ ] **Step 1: Write redaction, skip, and legacy-state tests**

```python
# tests/assistants/test_checks.py
from pathlib import Path

import pytest

from ballen_config.assistants.checks import assistant_checks
from ballen_config.assistants.skills import hash_skill_tree
from ballen_config.doctor import (
    CheckSeverity,
    FindingStatus,
    run_doctor,
)
from ballen_config.install import InstallAction
from ballen_config.runtime import RuntimePaths
from ballen_config.state import ManagedRecord, StateStore
from tests.assistants.fakes import StatefulAssistantFake


def test_secret_bearing_native_output_is_discarded(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Report readiness without native stdout or stderr."""
    fake_runner.add(
        ("claude", "auth", "status"),
        returncode=1,
        stdout="token=anthropic-secret-value",
        stderr="account=private-user",
    )
    report = run_doctor(
        assistant_checks(
            enabled=frozenset({"cursor", "claude-code", "codex"}),
            paths=RuntimePaths.from_roots(
                repo_root=temporary_home / "repo",
                home=temporary_home,
            ),
            runner=fake_runner,
        )
    )
    rendered = report.render()
    assert "anthropic-secret-value" not in rendered
    assert "private-user" not in rendered
    assert "Claude Code sign-in requires manual login" in rendered


def test_skipped_agent_is_left_to_core_without_duplicate_id(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Let the core component check report selected or skipped agents."""
    report = run_doctor(
        assistant_checks(
            enabled=frozenset({"cursor", "claude-code"}),
            paths=RuntimePaths.from_roots(
                repo_root=temporary_home / "repo",
                home=temporary_home,
            ),
            runner=fake_runner,
        )
    )
    assert "codex" not in {finding.id for finding in report.findings}
    assert ("codex", "login", "status") not in fake_runner.commands
    assert report.exit_code == 0


def test_legacy_cursor_mcp_is_manual_cleanup(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Identify but never import a local MCP snapshot."""
    path = temporary_home / ".cursor/mcp.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"mcpServers":{"playwright":{}}}')
    report = run_doctor(
        assistant_checks(
            enabled=frozenset({"cursor"}),
            paths=RuntimePaths.from_roots(
                repo_root=temporary_home / "repo",
                home=temporary_home,
            ),
            runner=fake_runner,
        )
    )
    finding = report.finding("cursor.legacy-mcp")
    assert finding.status is FindingStatus.MANUAL
    assert "playwright" not in finding.message.lower()


def test_pending_action_severity_is_normalized(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Make required plugin gaps fail and optional VSIX gaps informational."""
    findings = assistant_checks(
        enabled=frozenset({"cursor", "claude-code"}),
        paths=RuntimePaths.from_roots(
            repo_root=temporary_home / "repo",
            home=temporary_home,
        ),
        runner=fake_runner,
        pending_actions=(
            InstallAction(
                component_id="claude.plugin.required",
                argv=("claude", "plugin", "install", "required"),
            ),
            InstallAction(
                component_id="cursor.extension.optional-vsix",
                kind="verified-download",
                argv=("cursor", "--install-extension", "{artifact}"),
                required=False,
                url="https://example.invalid/optional.vsix",
                artifact_name="optional.vsix",
                size_bytes=1,
                sha256="a" * 64,
            ),
        ),
    )
    by_id = {finding.id: finding for finding in findings}
    assert by_id["claude.plugin.required"].severity is CheckSeverity.ERROR
    assert (
        by_id["cursor.extension.optional-vsix"].severity
        is CheckSeverity.WARNING
    )


def test_skill_collision_reports_names_only(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Detect cross-root collisions without reading unrelated files."""
    for root, description in (
        (".cursor/skills/example", "Cursor version"),
        (".claude/skills/example", "Claude version"),
    ):
        path = temporary_home / root
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(
            f"---\nname: example\ndescription: {description}.\n---\n"
        )
    findings = assistant_checks(
        enabled=frozenset({"cursor", "claude-code"}),
        paths=RuntimePaths.from_roots(
            repo_root=temporary_home / "repo",
            home=temporary_home,
        ),
        runner=fake_runner,
    )
    collision = next(
        finding
        for finding in findings
        if finding.id == "skills.collision.example"
    )
    assert collision.status is FindingStatus.MANUAL
    assert "Cursor version" not in collision.message
    assert "Claude version" not in collision.message


def test_clean_managed_skill_is_not_reported_as_drift(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Resolve state-store destinations relative to the injected home."""
    paths = RuntimePaths.from_roots(
        repo_root=temporary_home / "repo",
        home=temporary_home,
    )
    skill = temporary_home / ".cursor/skills/example"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: example\ndescription: Portable example.\n---\n"
    )
    digest = hash_skill_tree(skill)
    StateStore(paths).record_managed(
        ManagedRecord(
            resource_id="skill:example:cursor",
            source_digest=digest,
            destination_digest=digest,
            destination=".cursor/skills/example",
        )
    )
    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=fake_runner,
    )
    assert not any(
        finding.id.startswith("skills.drift.")
        for finding in findings
    )


def test_cursor_worktree_check_is_count_only_and_non_mutating(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Report stale disposable state without names or deletion."""
    worktree = temporary_home / ".cursor/worktrees/stale-repo/abc"
    worktree.mkdir(parents=True)
    before = tuple(temporary_home.rglob("*"))
    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=RuntimePaths.from_roots(
            repo_root=temporary_home / "repo",
            home=temporary_home,
        ),
        runner=fake_runner,
    )
    finding = next(
        item for item in findings if item.id == "cursor.worktrees"
    )
    assert finding.status is FindingStatus.MANUAL
    assert "1 stale Cursor worktree root" in finding.message
    assert "stale-repo" not in finding.message
    assert tuple(temporary_home.rglob("*")) == before


def test_skipped_cursor_avoids_worktree_lookup(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not inspect excluded Cursor runtime state."""
    worktrees = temporary_home / ".cursor/worktrees"
    monkeypatch.setattr(
        Path,
        "iterdir",
        lambda self: pytest.fail("must not inspect worktrees")
        if self == worktrees
        else iter(()),
    )
    findings = assistant_checks(
        enabled=frozenset({"claude-code"}),
        paths=RuntimePaths.from_roots(
            repo_root=temporary_home / "repo",
            home=temporary_home,
        ),
        runner=fake_runner,
    )
    assert "cursor.worktrees" not in {item.id for item in findings}


def test_agent_manual_and_unmanaged_extension_findings_are_nonfatal(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Keep browser, Notion, sign-in, and unmanaged extras informational."""
    report = run_doctor(
        assistant_checks(
            enabled=frozenset({"cursor"}),
            paths=RuntimePaths.from_roots(
                repo_root=temporary_home / "repo",
                home=temporary_home,
            ),
            runner=fake_runner,
            unmanaged_extension_count=2,
        )
    )
    ids = {finding.id for finding in report.findings}
    assert {
        "cursor.sign-in",
        "cursor.browser",
        "cursor.notion",
        "cursor.extensions.unmanaged",
    }.issubset(ids)
    assert report.exit_code == 0
```

- [ ] **Step 2: Add operational policy tests**

```python
# tests/test_policy.py additions
from pathlib import Path

import pytest

from ballen_config.policy import scan_paths


@pytest.mark.parametrize(
    ("relative", "content", "rule"),
    [
        ("assistants/cursor/mcp.json", "{}", "operational-mcp"),
        (
            "assistants/cursor/settings.json",
            '"mcpServers": {}',
            "operational-mcp",
        ),
        (
            "assistants/tool.yaml",
            "command: " + "@playwright/" + "mcp",
            "forbidden-mcp",
        ),
        (
            "assistants/tool.yaml",
            "command: gitlab-mr-" + "mcp",
            "forbidden-mcp",
        ),
        (
            "assistants/tool.yaml",
            "command: notion-" + "mcp",
            "forbidden-mcp",
        ),
        ("assistants/tool.yaml", "/Users/" + "someone/path", "machine-path"),
        ("assistants/tool.py", "from " + "plato import x", "repo-specific"),
        ("assistants/tool.py", "import " + "plato", "repo-specific"),
        ("assistants/tool.yaml", "Projects/" + "plato", "repo-specific"),
        ("assistants/tool.yaml", "plato" + ":skill", "repo-specific"),
        ("assistants/tool.yaml", "plugins/cache/1.2.3", "generated-state"),
        ("assistants/tool.yaml", "local_marketplace: /tmp/x", "local-state"),
        ("assistants/tool.toml", "trust_level = 'trusted'", "local-state"),
        ("assistants/sessions/a.json", "{}", "generated-state"),
        ("assistants/history/a.json", "{}", "generated-state"),
        ("assistants/cache/a.json", "{}", "generated-state"),
        ("assistants/tool.yaml", "auth_token: value", "credential-field"),
        (
            "docs/bad.md",
            "copy " + "credentials from your old laptop",
            "credential-copy",
        ),
    ],
)
def test_operational_policy_rejects_nonportable_state(
    tmp_path: Path,
    relative: str,
    content: str,
    rule: str,
) -> None:
    """Report path and policy name without echoing matching content."""
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    violations = scan_paths(tmp_path, (Path(relative),))
    assert rule in {violation.rule for violation in violations}
    assert content not in repr(violations)


def test_narrative_docs_may_explain_excluded_integrations(
    tmp_path: Path,
) -> None:
    """Allow rationale while forbidding operational MCP configuration."""
    path = tmp_path / "README.md"
    path.write_text(
        "Playwright, GitLab, and Notion MCP servers are intentionally "
        "excluded in favor of first-party integrations.\n"
    )
    assert scan_paths(tmp_path, (Path("README.md"),)) == ()
```

- [ ] **Step 3: Run the focused tests and confirm the red state**

Run:

```bash
rtk uv run pytest tests/assistants/test_checks.py tests/test_policy.py -q
```

Expected: the new assistant checks and operational policies fail until
implemented.

- [ ] **Step 4: Implement normalized checks**

Append these final manual resources to `assistants/inventory.yaml`:

```yaml
  - id: cursor.browser
    kind: manual
    owner: cursor
    summary: Enable Cursor's first-party browser capability if it is not already enabled.

  - id: claude.browser
    kind: manual
    owner: claude-code
    summary: Use Claude Code's first-party browser tooling; do not add a global Playwright MCP server.

  - id: codex.browser
    kind: manual
    owner: codex
    summary: Enable Codex's first-party browser plugin if it is not already available.

  - id: cursor.notion
    kind: manual
    owner: cursor
    summary: Connect the official Notion integration from Cursor's integration UI when needed.

  - id: claude.notion
    kind: manual
    owner: claude-code
    summary: Connect the official Notion integration from Claude's integration UI when needed.

  - id: codex.notion
    kind: manual
    owner: codex
    summary: Connect the official Notion integration from Codex's integration UI when needed.
```

```python
# src/ballen_config/assistants/checks.py
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
import re

from ballen_config.assistants.skills import hash_skill_tree
from ballen_config.doctor import (
    CheckSeverity,
    DoctorCheck,
    DoctorFinding,
    FindingStatus,
)
from ballen_config.install import InstallAction
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore


_AGENTS = ("cursor", "claude-code", "codex")
_SKILL_ROOTS = {
    "cursor": (Path(".cursor/skills"),),
    "claude-code": (Path(".claude/skills"),),
    "codex": (Path(".agents/skills"), Path(".codex/skills")),
}


def _finding(
    finding_id: str,
    status: FindingStatus,
    severity: CheckSeverity,
    message: str,
) -> DoctorFinding:
    """Build one normalized finding."""
    return DoctorFinding(
        id=finding_id,
        status=status,
        severity=severity,
        message=message,
    )


def _safe_id(value: str) -> str:
    """Convert a local resource name into a stable finding-ID suffix."""
    normalized = re.sub(r"[^a-z0-9.-]+", "-", value.lower()).strip("-")
    return normalized or "unknown"


def _agent_findings(
    enabled: frozenset[str],
    runner: Runner,
) -> list[DoctorFinding]:
    """Report sign-in and integrations; core owns application IDs."""
    findings: list[DoctorFinding] = []
    for agent in _AGENTS:
        if agent not in enabled:
            continue
        prefix = "claude" if agent == "claude-code" else agent
        findings.extend(
            (
                _finding(
                    f"{prefix}.browser",
                    FindingStatus.MANUAL,
                    CheckSeverity.INFO,
                    f"Enable {agent}'s first-party browser capability",
                ),
                _finding(
                    f"{prefix}.notion",
                    FindingStatus.MANUAL,
                    CheckSeverity.INFO,
                    f"Connect {agent}'s official Notion integration",
                ),
            )
        )

    if "cursor" in enabled:
        findings.append(
            _finding(
                "cursor.sign-in",
                FindingStatus.MANUAL,
                CheckSeverity.INFO,
                "Cursor sign-in requires manual confirmation",
            )
        )
    for agent, command, label in (
        ("claude-code", ("claude", "auth", "status"), "Claude Code"),
        ("codex", ("codex", "login", "status"), "Codex"),
    ):
        if agent not in enabled:
            continue
        result = runner.run(command)
        ready = result["returncode"] == 0
        findings.append(
            _finding(
                f"{'claude' if agent == 'claude-code' else agent}.sign-in",
                FindingStatus.READY if ready else FindingStatus.MANUAL,
                CheckSeverity.INFO,
                (
                    f"{label} sign-in is ready"
                    if ready
                    else f"{label} sign-in requires manual login"
                ),
            )
        )
    return findings


def _pending_findings(
    pending_actions: Sequence[InstallAction],
) -> list[DoctorFinding]:
    """Normalize missing install actions without exposing native output."""
    return [
        _finding(
            action.component_id,
            (
                FindingStatus.MISSING
                if action.required
                else FindingStatus.UNAVAILABLE
            ),
            (
                CheckSeverity.ERROR
                if action.required
                else CheckSeverity.WARNING
            ),
            (
                "required install is missing"
                if action.required
                else "optional install is unavailable"
            ),
        )
        for action in pending_actions
    ]


def _skill_findings(
    enabled: frozenset[str],
    paths: RuntimePaths,
) -> list[DoctorFinding]:
    """Report only names for cross-root collisions and managed drift."""
    by_name: dict[str, set[str]] = defaultdict(set)
    for agent in sorted(enabled):
        for relative_root in _SKILL_ROOTS[agent]:
            root = paths.home / relative_root
            if not root.is_dir():
                continue
            for candidate in sorted(root.iterdir()):
                if candidate.is_dir() and (candidate / "SKILL.md").is_file():
                    try:
                        by_name[candidate.name].add(
                            hash_skill_tree(candidate)
                        )
                    except ValueError:
                        by_name[candidate.name].add("invalid")

    findings = [
        _finding(
            f"skills.collision.{_safe_id(name)}",
            FindingStatus.MANUAL,
            CheckSeverity.WARNING,
            f"skill {name} has conflicting definitions",
        )
        for name, digests in sorted(by_name.items())
        if len(digests) > 1
    ]

    for record in StateStore(paths).load().managed.values():
        if (
            not record.resource_id.startswith("skill:")
            or record.resource_id.rsplit(":", maxsplit=1)[-1]
            not in enabled
        ):
            continue
        relative_destination = Path(record.destination)
        try:
            if relative_destination.is_absolute():
                raise ValueError("managed destination must be relative")
            destination = paths.home / relative_destination
            destination.resolve().relative_to(paths.home.resolve())
            digest = hash_skill_tree(destination)
        except (ValueError, FileNotFoundError):
            digest = ""
        if digest != record.destination_digest:
            findings.append(
                _finding(
                    f"skills.drift.{_safe_id(record.resource_id)}",
                    FindingStatus.DRIFT,
                    CheckSeverity.WARNING,
                    "a managed shared skill differs from recorded state",
                )
            )
    return findings


def _cursor_state_findings(
    *,
    enabled: frozenset[str],
    paths: RuntimePaths,
    unmanaged_extension_count: int,
) -> list[DoctorFinding]:
    """Inspect only explicitly approved Cursor state paths."""
    if "cursor" not in enabled:
        return []
    findings: list[DoctorFinding] = []
    if (paths.home / ".cursor/mcp.json").is_file():
        findings.append(
            _finding(
                "cursor.legacy-mcp",
                FindingStatus.MANUAL,
                CheckSeverity.WARNING,
                "legacy Cursor MCP configuration requires manual review",
            )
        )
    worktrees = paths.home / ".cursor/worktrees"
    if worktrees.is_dir():
        count = sum(1 for entry in worktrees.iterdir() if entry.is_dir())
        if count:
            noun = "root" if count == 1 else "roots"
            findings.append(
                _finding(
                    "cursor.worktrees",
                    FindingStatus.MANUAL,
                    CheckSeverity.WARNING,
                    f"{count} stale Cursor worktree {noun} require review",
                )
            )
    if unmanaged_extension_count:
        findings.append(
            _finding(
                "cursor.extensions.unmanaged",
                FindingStatus.MANUAL,
                CheckSeverity.INFO,
                (
                    f"{unmanaged_extension_count} unmanaged Cursor "
                    "extensions remain installed"
                ),
            )
        )
    return findings


def assistant_checks(
    *,
    enabled: frozenset[str],
    paths: RuntimePaths,
    runner: Runner,
    pending_actions: Sequence[InstallAction] = (),
    unmanaged_extension_count: int = 0,
) -> tuple[DoctorCheck, ...]:
    """Return deterministic coding-agent findings with redacted messages."""
    findings = [
        *_agent_findings(enabled, runner),
        *_pending_findings(pending_actions),
        *_skill_findings(enabled, paths),
        *_cursor_state_findings(
            enabled=enabled,
            paths=paths,
            unmanaged_extension_count=unmanaged_extension_count,
        ),
    ]
    ordered = tuple(sorted(findings, key=lambda item: item.id))
    ids = [finding.id for finding in ordered]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate DoctorFinding.id")
    return ordered
```

Native auth commands are invoked through the captured runner, but each message
is chosen only from the return code. The implementation never interpolates
stdout, stderr, usernames, endpoints, repository names, or identifiers.

Extend the core tracked-tree policy with operational portability rules:

```python
# src/ballen_config/policy.py additions and replacements
FORBIDDEN_PARTS = {
    "sessions",
    "history",
    "transcripts",
    "cache",
    "__pycache__",
}
CONTENT_RULES = {
    "private-key": re.compile(
        r"BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY"
    ),
    "credential-copy": re.compile(
        r"\bcopy\s+credentials?\s+from\s+your\s+old\s+laptop\b",
        re.IGNORECASE,
    ),
}
PORTABILITY_RULES = {
    "credential-placeholder": re.compile(
        r"<YOUR_GITLAB_TOKEN>|glpat-[A-Za-z0-9_-]{20,}"
    ),
    "credential-field": re.compile(
        r"(?im)^\s*(?:auth_token|access_token|api_key|password)\s*[:=]"
    ),
    "machine-path": re.compile(r"/Users/[^/\s]+/"),
    "forbidden-mcp": re.compile(
        r"gitlab-mr-mcp|@playwright/mcp|notion-mcp"
    ),
    "operational-mcp": re.compile(r'"?mcpServers"?\s*[:=]'),
    "generated-state": re.compile(r"(?:^|/)plugins/cache(?:/|$)"),
    "repo-specific": re.compile(
        r"(?m)(?:from\s+plato\s+import|import\s+plato\b|"
        r"Projects/plato\b|plato:skill\b)"
    ),
    "local-state": re.compile(
        r"(?im)(?:local_marketplace\s*[:=]\s*/|"
        r"trust_level\s*=\s*['\"]trusted['\"])"
    ),
}


def _is_portable(relative: Path) -> bool:
    """Return whether a path belongs to the portable operational surface."""
    return bool(relative.parts) and (
        relative.parts[0] in PORTABLE_PREFIXES
        or relative.as_posix() in PORTABLE_ROOT_FILES
    )


def scan_paths(
    root: Path,
    relative_paths: Iterable[Path],
) -> tuple[Violation, ...]:
    """Scan explicit repository-relative paths without printing matches."""
    violations: list[Violation] = []
    for relative in sorted(relative_paths):
        path = root / relative
        if not path.is_file():
            continue
        if FORBIDDEN_PARTS.intersection(relative.parts) or path.suffix in {
            ".sqlite",
            ".sqlite3",
            ".age",
        }:
            violations.append(
                Violation(rule="generated-state", path=str(relative))
            )
            continue
        text = path.read_text(errors="ignore")
        for rule, pattern in CONTENT_RULES.items():
            if pattern.search(text):
                violations.append(Violation(rule=rule, path=str(relative)))
        if not _is_portable(relative):
            continue
        if relative.name == "mcp.json":
            violations.append(
                Violation(rule="operational-mcp", path=str(relative))
            )
        for rule, pattern in PORTABILITY_RULES.items():
            if pattern.search(text):
                violations.append(Violation(rule=rule, path=str(relative)))
    return tuple(violations)
```

This package must not run or report `gh auth status`, `glab auth status`, AWS
readiness, SSH transfer, or IT-managed application checks. Those are
cross-cutting core-bootstrap responsibilities. Add this ownership regression:

```python
def test_assistant_checks_do_not_duplicate_core_responsibilities(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Keep cross-cutting auth and machine checks in the core plan."""
    findings = assistant_checks(
        enabled=frozenset({"cursor", "claude-code", "codex"}),
        paths=RuntimePaths.from_roots(
            repo_root=temporary_home / "repo",
            home=temporary_home,
        ),
        runner=fake_runner,
    )
    ids = {finding.id for finding in findings}
    assert ids.isdisjoint(
        {
            "github-auth",
            "gitlab-auth",
            "aws-auth",
            "ssh-transfer",
            "it-managed-applications",
        }
    )
    assert ("gh", "auth", "status") not in fake_runner.commands
    assert ("glab", "auth", "status") not in fake_runner.commands
    assert not any(command[0] == "aws" for command in fake_runner.commands)


def test_assistant_doctor_finding_ids_are_unique(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
) -> None:
    """Keep deterministic IDs safe for merger with core findings."""
    findings = assistant_checks(
        enabled=frozenset({"cursor", "claude-code", "codex"}),
        paths=RuntimePaths.from_roots(
            repo_root=temporary_home / "repo",
            home=temporary_home,
        ),
        runner=fake_runner,
    )
    ids = [finding.id for finding in findings]
    assert len(ids) == len(set(ids))
```

Required missing resources produce exit `1`. Optional omissions, skipped
agents, unmanaged extras, and manual authentication/integration actions
produce exit `0`.

- [ ] **Step 5: Run policy and doctor tests and checkpoint**

Run:

```bash
rtk uv run pytest tests/assistants/test_checks.py tests/test_policy.py -q
rtk uv run python -m ballen_config.policy
```

Expected: tests and tracked-tree scan pass.

Checkpoint:

```bash
rtk jj describe -m "feat: diagnose coding-agent portability"
rtk jj new
```

### Task 8: Complete migration, documentation, and end-to-end proof

**Files:**

- Create: `tests/assistants/test_integration.py`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/manual-steps.md`
- Modify: `tests/test_docs.py`
- Modify: `src/ballen_config/cli.py`
- Delete: empty `cursor/` and `claude-code/` legacy directories

- [ ] **Step 1: Write the work-profile integration fixture**

```python
# tests/assistants/test_integration.py
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path

import pytest

from ballen_config.assistants import (
    AssistantPlanContributor,
    configuration,
    doctor_checks,
    install_actions,
)
from ballen_config.cli import RunResult, run
from ballen_config.manifests import ManifestRepository
from ballen_config.models import Manager, ResolutionRequest
from ballen_config.runtime import RuntimePaths
from tests.assistants.fakes import StatefulAssistantFake


def snapshot_tree(root: Path) -> dict[str, str]:
    """Return path, kind, mode, and content digests for a temporary home."""
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[relative] = f"link:{path.readlink()}"
        elif path.is_dir():
            snapshot[relative] = f"dir:{path.stat().st_mode & 0o777:o}"
        else:
            snapshot[relative] = (
                f"file:{path.stat().st_mode & 0o777:o}:"
                f"{sha256(path.read_bytes()).hexdigest()}"
            )
    return snapshot


def run_with_assistants(
    argv: list[str],
    *,
    repo_root: Path,
    home: Path,
    runner: StatefulAssistantFake,
    output: Callable[[str], None] = lambda _: None,
) -> RunResult:
    """Invoke core with every production assistant callback once."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=home)
    resolved = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile="work")
    )
    for component in resolved.components:
        if component.manager is Manager.GIT:
            assert component.destination is not None
            (home / component.destination / ".git").mkdir(
                parents=True,
                exist_ok=True,
            )
    return run(
        argv,
        repo_root=repo_root,
        home=home,
        runner=runner,
        downloader=runner,
        confirm=lambda _: True,
        output=output,
        timestamp=lambda: "20260725T120000Z",
        install_action_suppliers=(install_actions,),
        configuration_suppliers=(configuration,),
        doctor_check_suppliers=(doctor_checks,),
        plan_contributors=(AssistantPlanContributor(paths),),
    )


def test_work_profile_with_codex_skip_converges(
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Configure enabled agents once and leave skipped Codex untouched."""
    fake_runner.satisfy_core_commands()
    fake_runner.cursor_extensions.add(
        "velociraptor115.vscode-jj-graph"
    )
    existing_settings = (
        temporary_home
        / "Library/Application Support/Cursor/User/settings.json"
    )
    existing_settings.parent.mkdir(parents=True)
    existing_settings.write_text('{"unmanaged": true}\n')

    first = run_with_assistants(
        [
            "all",
            "--profile",
            "work",
            "--skip",
            "codex",
        ],
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )
    assert first.exit_code == 0
    assert existing_settings.is_file()
    assert (temporary_home / ".claude/settings.json").is_file()
    assert not (temporary_home / ".codex").exists()
    backup_root = (
        temporary_home / ".local/state/ballen-config/backups"
    )
    assert backup_root.is_dir()
    assert any(path.is_file() for path in backup_root.rglob("*"))

    first_snapshot = snapshot_tree(temporary_home)
    second = run_with_assistants(
        [
            "all",
            "--profile",
            "work",
            "--skip",
            "codex",
        ],
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )
    assert second.exit_code == 0
    assert snapshot_tree(temporary_home) == first_snapshot
    assert second.report.changed_count == 0


@pytest.mark.parametrize(
    ("skipped", "forbidden_tokens", "forbidden_path"),
    [
        (
            "cursor",
            frozenset({"cursor"}),
            Path("Library/Application Support/Cursor"),
        ),
        (
            "claude-code",
            frozenset({"claude", "claude-code"}),
            Path(".claude"),
        ),
        (
            "codex",
            frozenset({"codex"}),
            Path(".codex"),
        ),
    ],
)
def test_agent_skip_removes_complete_surface(
    skipped: str,
    forbidden_tokens: frozenset[str],
    forbidden_path: Path,
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Remove one agent's install, config, hooks, skills, and manual actions."""
    fake_runner.satisfy_core_commands()
    fake_runner.cursor_extensions.add(
        "velociraptor115.vscode-jj-graph"
    )
    result = run_with_assistants(
        ["all", "--profile", "work", "--skip", skipped],
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )
    assert result.exit_code == 0
    assert not (temporary_home / forbidden_path).exists()
    assert all(
        forbidden_tokens.isdisjoint(command)
        for command in fake_runner.commands
    )
    assert all(
        not outcome.startswith(f"{skipped}.")
        for outcome in result.report.outcomes
    )
```

Add the remaining end-to-end assertions:

```python
def test_plan_is_redacted_unique_and_read_only(
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Render structural actions without values, output, or mutation."""
    fake_runner.satisfy_core_commands()
    rendered: list[str] = []
    result = run_with_assistants(
        ["plan", "--profile", "work"],
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
        output=rendered.append,
    )
    assert result.exit_code == 0
    plan = "\n".join(rendered)
    assert "cursor.extensions.catalog" in plan
    assert "CLAUDE_CODE_USE_BEDROCK" not in plan
    assert "token=" not in plan
    assert "stderr" not in plan


def test_all_agents_skipped_have_no_agent_surface_or_commands(
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Apply complete skips before every assistant callback."""
    fake_runner.satisfy_core_commands()
    result = run_with_assistants(
        [
            "all",
            "--profile",
            "work",
            "--skip",
            "cursor",
            "--skip",
            "claude-code",
            "--skip",
            "codex",
        ],
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )
    assert result.exit_code == 0
    assert all(
        command[0] not in {"cursor", "claude", "codex"}
        for command in fake_runner.commands
    )
    for relative in (".cursor", ".claude", ".codex", ".agents"):
        assert not (temporary_home / relative).exists()


def test_excluded_local_state_is_never_imported_or_changed(
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Leave generated, authentication, and disposable state byte-identical."""
    excluded = (
        "sessions",
        "history",
        "auth",
        "token",
        "cache",
        "database",
        "worktree",
        "project-trust",
    )
    sentinels: list[Path] = []
    for name in excluded:
        sentinel = temporary_home / ".local/excluded" / name / "sentinel"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text(f"{name}-private-state")
        sentinels.append(sentinel)
    before = {path: path.read_bytes() for path in sentinels}
    fake_runner.satisfy_core_commands()
    result = run_with_assistants(
        [
            "all",
            "--profile",
            "work",
            "--skip",
            "cursor",
            "--skip",
            "claude-code",
            "--skip",
            "codex",
        ],
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )
    assert result.exit_code == 0
    assert {path: path.read_bytes() for path in sentinels} == before


def test_legacy_cursor_mcp_is_reported_but_not_imported_or_deleted(
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Keep legacy MCP state outside the managed configuration surface."""
    legacy = temporary_home / ".cursor/mcp.json"
    legacy.parent.mkdir(parents=True)
    payload = b'{"mcpServers":{"legacy":{"command":"private"}}}\n'
    legacy.write_bytes(payload)
    fake_runner.satisfy_core_commands()
    rendered: list[str] = []
    result = run_with_assistants(
        ["doctor", "--profile", "work"],
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
        output=rendered.append,
    )
    assert result.exit_code in {0, 1}
    assert "cursor.legacy-mcp" in "\n".join(rendered)
    assert legacy.read_bytes() == payload
    assert not (repo_root / "cursor/mcp.json").exists()
```

The final suite also includes the Task 3 shared-skill target/collision tests and
the Task 7 count-only worktree test. Together with the convergence test above,
they prove enabled-target copying, unmanaged-collision fail-closed behavior,
one-time backup, and second-run no-op behavior without duplicating fixtures.

- [ ] **Step 2: Run the integration test and confirm the red state**

Run:

```bash
rtk uv run pytest tests/assistants/test_integration.py -q
```

Expected: the CLI does not yet dispatch assistant adapters.

- [ ] **Step 3: Wire adapters into the core stages**

Expose from `src/ballen_config/assistants/__init__.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from ballen_config.assistants import checks as _checks
from ballen_config.assistants import claude, codex, cursor, hooks, skills
from ballen_config.assistants.inventory import (
    load_inventory,
    resolve_inventory,
)
from ballen_config.configure import (
    ConfigurationContribution,
    ManagedSpec,
    Renderer,
    SourceValidator,
)
from ballen_config.doctor import DoctorCheck
from ballen_config.install import InstallAction
from ballen_config.models import ResolvedSetup
from ballen_config.planning import PlanAction
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths


def _unique(label: str, values: list[str]) -> None:
    """Reject ambiguous action, callback, spec, or finding IDs."""
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")


def install_actions(
    setup: ResolvedSetup,
    paths: RuntimePaths,
    runner: Runner,
) -> tuple[InstallAction, ...]:
    """Return only missing extension and plugin actions."""
    actions = (
        *cursor.install_actions(setup, paths, runner),
        *claude.install_actions(setup, paths, runner),
        *codex.install_actions(setup, paths, runner),
    )
    ordered = tuple(sorted(actions, key=lambda item: item.component_id))
    _unique(
        "InstallAction.component_id",
        [item.component_id for item in ordered],
    )
    return ordered


def _merge_configuration(
    contributions: tuple[ConfigurationContribution, ...],
) -> ConfigurationContribution:
    specs: list[ManagedSpec] = []
    renderers: dict[str, Renderer] = {}
    validators: dict[str, SourceValidator] = {}
    for contribution in contributions:
        specs.extend(contribution.specs)
        for name, renderer in contribution.renderers.items():
            if name in renderers:
                raise ValueError(f"duplicate renderer id: {name}")
            renderers[name] = renderer
        for name, validator in contribution.validators.items():
            if name in validators:
                raise ValueError(f"duplicate validator id: {name}")
            validators[name] = validator
    _unique("ManagedSpec.id", [spec.id for spec in specs])
    _unique(
        "managed destination",
        [str(spec.destination) for spec in specs],
    )
    return ConfigurationContribution(
        specs=tuple(sorted(specs, key=lambda item: item.id)),
        renderers=renderers,
        validators=validators,
    )


def configuration(
    setup: ResolvedSetup,
    paths: RuntimePaths,
) -> ConfigurationContribution:
    """Return selected files plus all named pure callbacks."""
    enabled = frozenset(
        agent
        for agent in ("cursor", "claude-code", "codex")
        if setup.is_enabled(agent)
    )
    return _merge_configuration(
        (
            hooks.hook_contribution(
                repo_root=paths.repo_root,
                home=paths.home,
                enabled=enabled,
            ),
            skills.configuration(setup, paths),
            cursor.configuration(setup, paths),
            claude.claude_configuration(
                repo_root=paths.repo_root,
                home=paths.home,
                profiles=setup.profiles,
                enabled=enabled,
            ),
            codex.configuration(setup, paths),
        )
    )


def doctor_checks(
    setup: ResolvedSetup,
    paths: RuntimePaths,
    runner: Runner,
) -> tuple[DoctorCheck, ...]:
    """Return normalized coding-agent diagnostics only."""
    enabled = frozenset(
        agent
        for agent in ("cursor", "claude-code", "codex")
        if setup.is_enabled(agent)
    )
    pending_actions = (
        *cursor.install_actions(setup, paths, runner),
        *claude.install_actions(setup, paths, runner),
        *codex.install_actions(setup, paths, runner),
    )
    findings = _checks.assistant_checks(
        enabled=enabled,
        paths=paths,
        runner=runner,
        pending_actions=pending_actions,
    )
    _unique("DoctorFinding.id", [finding.id for finding in findings])
    return tuple(sorted(findings, key=lambda item: item.id))


@dataclass(frozen=True)
class AssistantPlanContributor:
    """Render manual/catalog actions not represented by managed specs."""

    paths: RuntimePaths

    def actions(
        self,
        setup: ResolvedSetup,
    ) -> tuple[PlanAction, ...]:
        inventory = load_inventory(
            self.paths.repo_root / "assistants/inventory.yaml",
            self.paths.repo_root,
        )
        resolved = resolve_inventory(
            inventory,
            profiles=setup.profiles,
            skipped=frozenset(setup.skipped),
        )
        actions = tuple(
            PlanAction(
                component_id=(
                    f"{resource.id}.manual"
                    if resource.kind == "manual"
                    and resource.source is not None
                    else resource.id
                ),
                category=(
                    "manual"
                    if resource.kind == "manual"
                    else "install"
                ),
                action=(
                    "manual action"
                    if resource.kind == "manual"
                    else "reconcile reviewed native catalog"
                ),
                owner=resource.owner.value,
                path=(
                    str(resource.destination)
                    if hasattr(resource, "destination")
                    else None
                ),
                required=resource.required,
            )
            for resource in resolved.resources
            if resource.kind in {"manual", "catalog"}
        )
        _unique(
            "PlanAction.component_id",
            [action.component_id for action in actions],
        )
        return tuple(
            sorted(actions, key=lambda item: item.component_id)
        )
```

Register the callbacks exactly once in `cli.main()` while retaining the core
manual contributor:

```python
# src/ballen_config/cli.py additions plus complete main replacement
from ballen_config.assistants import (
    AssistantPlanContributor,
    configuration,
    doctor_checks,
    install_actions,
)
from ballen_config.install import HttpsDownloader
from ballen_config.planning import CoreManualContributor
from ballen_config.runner import SubprocessRunner


def main(arguments: Sequence[str] | None = None) -> int:
    """Construct core and assistant dependencies and return exit status."""
    previous_umask = os.umask(0o077)
    try:
        paths = RuntimePaths.from_roots(
            repo_root=Path(__file__).resolve().parents[2],
            home=Path.home(),
        )
        runner = SubprocessRunner()
        result = run(
            tuple(sys.argv[1:] if arguments is None else arguments),
            repo_root=paths.repo_root,
            home=paths.home,
            runner=runner,
            downloader=HttpsDownloader(),
            confirm=lambda prompt: (
                input(f"{prompt} [y/N] ").lower() == "y"
            ),
            output=print,
            timestamp=lambda: datetime.now(UTC).strftime(
                "%Y%m%dT%H%M%SZ"
            ),
            install_action_suppliers=(install_actions,),
            configuration_suppliers=(configuration,),
            doctor_check_suppliers=(doctor_checks,),
            plan_contributors=(
                CoreManualContributor(),
                AssistantPlanContributor(paths),
            ),
        )
        for outcome in result.report.outcomes:
            print(outcome)
        return result.exit_code
    finally:
        os.umask(previous_umask)
```

The core passes the same resolved skip state to every supplier and executes
install before configure in `all`.

- [ ] **Step 4: Verify legacy tracked files were retired once**

Tasks 4 and 5 already moved the reviewed settings/keybindings and removed
`cursor/extensions.txt`; the core plan already removed `cursor/mcp.json`.
Do not repeat those mutations. Verify there is no remaining legacy path:

```bash
rtk rg --files | rtk rg '^(cursor|claude-code)/'
```

Expected: the second `rg` exits `1` with no output. Do not delete anything
under the live home directory.

- [ ] **Step 5: Expand README rationale and manual steps**

The README must include:

- Why the repository uses a tiny Zsh stage-zero and frozen Python 3.12
  implementation.
- Why `default` and `work` profiles are broad, and why repository-specific
  behavior is an add-on rather than another base profile.
- How `--skip cursor`, `--skip claude-code`, and `--skip codex` remove an
  agent's entire surface.
- The shared-source-plus-native-adapter model and its collision rule.
- Why Cursor settings use base plus work overlay.
- Why extensions are curated by feature ID, why Jupyter satellites are
  transitive, and why JJ Graph is a checked optional VSIX.
- Why no global Playwright MCP is installed.
- Why GitLab support is `glab` rather than a plugin or MCP server.
- Why Notion is connected through each application's official integration.
- Why User Rules and some first-party capabilities remain manual UI steps.
- Why sessions, history, memories, auth, trust, worktrees, caches, and
  generated plugin state are excluded.
- How to promote a truly generic skill and where repository-specific skills
  belong.

Use this prose as the README's coding-agent rationale:

```markdown
## Coding-agent portability

Cursor, Claude Code, and Codex are optional whole components. Skipping one
removes its application, native configuration, extensions/plugins, hooks,
skills, sign-in reminders, and required diagnostics. The remaining agents
still receive shared resources targeted to them.

General instructions, RTK guidance, hook programs, and reviewed Agent Skills
have one canonical source. Native adapters render each tool's actual format;
same-name skills with different hashes are never silently chosen or
overwritten. A differing destination previously recorded as managed is an
update or repair, while an unmanaged difference is a manual collision.
Portable skills converge to `~/.cursor/skills`, `~/.claude/skills`, and
`~/.agents/skills` for Cursor, Claude Code, and Codex respectively.

Cursor settings use a portable base and a work overlay so Bedrock/AWS
environment is not leaked into the personal profile. Extension IDs are
feature-level and unversioned; Jupyter satellites and bundled Cursor
components are transitive. JJ Graph is the one optional pinned VSIX because it
is not reliably restored through the gallery.

Browser automation uses each agent's first-party capability, GitLab operations
use `glab`, and Notion uses official integrations. No global Playwright,
GitLab, or Notion MCP server is installed. Cursor User Rules and integration
authorization stay explicit UI steps where no stable supported CLI exists.

Sessions, history, memories, authentication, trust, worktrees, caches,
indexes, downloaded plugin code, and generated runtime state are excluded.
Only skills proven generic enter `assistants/shared/skills`; Plato and other
repository-specific instructions/plugins remain repo add-ons.
```

`docs/manual-steps.md` must give ordered, non-secret commands or UI actions for:

1. Cursor, Claude Code, and Codex login.
2. Cursor User Rules import.
3. First-party browser enablement for each enabled agent.
4. Official Notion connector authorization for each enabled agent.
5. Verification with `./bootstrap doctor --profile default` or
   `./bootstrap doctor --profile work`.

Do not add `gh`, `glab`, AWS, SSH, or IT-managed application actions here;
the core plan owns those sections of the shared manual.

The root `CLAUDE.md` must direct an implementation agent to run:

```text
./bootstrap plan --profile default
./bootstrap plan --profile work
./bootstrap doctor --profile work
```

It must not instruct an agent to copy credentials, sessions, or runtime state.

- [ ] **Step 6: Run documentation and integration tests**

Run:

```bash
rtk uv run pytest tests/test_docs.py tests/assistants/test_integration.py -q
```

Expected: documentation contract and end-to-end convergence pass.

- [ ] **Step 7: Run the complete verification suite**

Run:

```bash
rtk uv sync --frozen --python 3.12
rtk uv run pytest -q
rtk uv run ruff check .
rtk uv run ruff format --check .
rtk uv run mypy src tests
rtk zsh -n assistants/shared/hooks/rtk-hook
rtk uv run python -m ballen_config.policy
rtk uv run pre-commit run --all-files
rtk ./bootstrap plan --profile default
rtk ./bootstrap plan --profile work
rtk ./bootstrap plan --profile work --skip cursor --skip claude-code --skip codex
rtk ./bootstrap doctor --profile work
rtk jj diff --summary
rtk jj status
```

Expected:

- All tests, lint, format, type, hook syntax, policy, and pre-commit checks
  pass.
- Every plan command is non-mutating and free of secrets/settings values.
- Doctor may report manual login/connector steps but exits `0` when required
  local components are present.
- `jj status` contains only the intended coding-agent portability changes.

- [ ] **Step 8: Checkpoint the completed plan**

```bash
rtk jj describe -m "feat: complete coding-agent portability"
rtk jj new
rtk jj status
```

Expected: a new empty working-copy change above the completed implementation
change.
