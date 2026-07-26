"""Strict models for portable coding-agent inventory declarations."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


class AgentName(StrEnum):
    """Coding agents supported by the portable bootstrap."""

    CURSOR = "cursor"
    CLAUDE = "claude-code"
    CODEX = "codex"
    SHARED = "shared"


def _validate_concrete_targets(
    targets: tuple[AgentName, ...],
) -> tuple[AgentName, ...]:
    """Require target lists to name only installable coding agents.

    Args:
        targets: Parsed target agent names.

    Returns:
        The validated target tuple.

    Raises:
        ValueError: If the shared pseudo-owner is used as a concrete target.
    """
    if AgentName.SHARED in targets:
        raise ValueError("shared is not a concrete target")
    return targets


ConcreteTargets = Annotated[
    tuple[AgentName, ...],
    AfterValidator(_validate_concrete_targets),
]

_MANAGED_STATE_PATH_WORDS = frozenset(
    {
        "auth",
        "cache",
        "caches",
        "credential",
        "credentials",
        "histories",
        "history",
        "index",
        "indexes",
        "indices",
        "mcp",
        "mcpserver",
        "mcpservers",
        "memories",
        "memory",
        "session",
        "sessions",
        "token",
        "tokens",
        "transcript",
        "transcripts",
        "trust",
        "trusted",
        "worktree",
        "worktrees",
    }
)
_PATH_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def _validate_managed_file_path(path: PurePosixPath) -> PurePosixPath:
    """Reject file-copy paths that represent local agent state.

    Args:
        path: Parsed POSIX source or destination path.

    Returns:
        The validated path.

    Raises:
        ValueError: If a path component identifies excluded local state.
    """
    words = {
        word
        for part in path.parts
        for word in _PATH_WORD_PATTERN.findall(part.casefold())
    }
    if words.intersection(_MANAGED_STATE_PATH_WORDS):
        raise ValueError("file resource path represents managed local state")
    return path


ManagedFilePath = Annotated[
    PurePosixPath,
    AfterValidator(_validate_managed_file_path),
]


class ResourceBase(BaseModel):
    """Fields shared by every portable coding-agent resource."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
    owner: AgentName
    profiles: tuple[str, ...] = ("default",)
    required: bool = True


class CatalogKind(StrEnum):
    """Typed subcatalogs referenced by the central inventory."""

    EXTENSION = "extension"
    PLUGIN = "plugin"
    SKILL = "skill"


class FileResource(ResourceBase):
    """A reviewed source managed through the core configuration engine."""

    kind: Literal["file"]
    source: ManagedFilePath
    destination: ManagedFilePath
    mode: Literal[0o600, 0o700] = 0o600
    targets: ConcreteTargets = ()
    role: Literal["direct", "render-source", "overlay", "suffix"] = "direct"


class HookResource(ResourceBase):
    """An authored hook program with one or more native registrations."""

    kind: Literal["hook"]
    source: PurePosixPath
    event: str = Field(min_length=1)
    targets: ConcreteTargets = Field(min_length=1)


class CatalogResource(ResourceBase):
    """A typed subcatalog whose ordered item IDs are flattened for audit."""

    kind: Literal["catalog"]
    source: PurePosixPath
    catalog_kind: CatalogKind
    targets: ConcreteTargets = ()
    item_ids: tuple[str, ...]


class ManualResource(ResourceBase):
    """An informational setup action with no local mutation."""

    kind: Literal["manual"]
    summary: str = Field(min_length=1)
    source: PurePosixPath | None = None


PortableResource = Annotated[
    FileResource | HookResource | CatalogResource | ManualResource,
    Field(discriminator="kind"),
]


class ExtensionSpec(BaseModel):
    """A Cursor extension installed from a gallery or verified VSIX."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(
        pattern=(
            r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
            r"\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"
        )
    )
    condition: Literal["cursor", "claude-code", "codex"] | None = None
    install_mode: Literal["gallery", "vsix"] = "gallery"
    required: bool = True
    version: str | None = Field(default=None, min_length=1)
    size_bytes: int | None = Field(default=None, gt=0)
    url: str | None = Field(default=None, min_length=1)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_variant(self) -> Self:
        """Require complete immutable metadata only for HTTPS VSIX installs.

        Returns:
            The validated extension declaration.

        Raises:
            ValueError: If gallery and VSIX fields are inconsistent.
        """
        metadata = (self.version, self.size_bytes, self.url, self.sha256)
        if self.install_mode == "gallery":
            if any(value is not None for value in metadata):
                raise ValueError("gallery extensions cannot declare VSIX metadata")
            return self
        if any(value is None for value in metadata):
            raise ValueError(
                "VSIX extensions require version, size_bytes, url, and sha256"
            )
        if not self.url or not self.url.startswith("https://"):
            raise ValueError("VSIX extensions require an HTTPS URL")
        if not self.version or not self.version.strip():
            raise ValueError("VSIX extensions require a nonempty version")
        return self


class ExtensionCatalog(BaseModel):
    """Validated Cursor extension catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    extensions: tuple[ExtensionSpec, ...]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> Self:
        """Reject duplicate extension identifiers.

        Returns:
            The validated extension catalog.

        Raises:
            ValueError: If extension identifiers are duplicated.
        """
        ids = [extension.id for extension in self.extensions]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate extension id")
        return self


class Marketplace(BaseModel):
    """A named plugin marketplace source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    profiles: tuple[str, ...] = ("default",)


class PluginSpec(BaseModel):
    """A plugin installed through an agent-native CLI."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    marketplace: str = Field(min_length=1)
    profiles: tuple[str, ...] = ("default",)
    required: bool = True


class PluginCatalog(BaseModel):
    """Validated marketplace and plugin declarations for one agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    marketplaces: tuple[Marketplace, ...]
    plugins: tuple[PluginSpec, ...]

    @model_validator(mode="after")
    def validate_marketplaces(self) -> Self:
        """Reject ambiguous or inconsistent plugin catalog declarations.

        Returns:
            The validated plugin catalog.

        Raises:
            ValueError: If declarations are duplicated, unknown, or mismatched.
        """
        marketplace_names = [marketplace.name for marketplace in self.marketplaces]
        if len(marketplace_names) != len(set(marketplace_names)):
            raise ValueError("duplicate marketplace name")

        plugin_ids = [plugin.id for plugin in self.plugins]
        if len(plugin_ids) != len(set(plugin_ids)):
            raise ValueError("duplicate plugin id")

        names = set(marketplace_names)
        unknown = {
            plugin.marketplace
            for plugin in self.plugins
            if plugin.marketplace not in names
        }
        if unknown:
            raise ValueError(f"unknown marketplaces: {sorted(unknown)}")

        mismatched = [
            plugin.id
            for plugin in self.plugins
            if plugin.id.rpartition("@")[1:] != ("@", plugin.marketplace)
        ]
        if mismatched:
            raise ValueError(
                f"plugin marketplace suffix mismatch: {sorted(mismatched)}"
            )
        return self


class SkillSpec(BaseModel):
    """One canonical skill and its enabled native targets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
    source: PurePosixPath
    targets: ConcreteTargets = Field(min_length=1)
    profiles: tuple[str, ...] = ("default",)
    dependencies: tuple[str, ...] = ()
    provenance: str = Field(min_length=1)
    portability_status: Literal["reviewed-generic", "agent-specific"]


class SkillCatalog(BaseModel):
    """Validated canonical-skill dependency catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    skills: tuple[SkillSpec, ...]

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        """Reject duplicate, unknown, and cyclic skill dependencies.

        Returns:
            The validated skill catalog.

        Raises:
            ValueError: If names are duplicated or dependencies are invalid.
        """
        by_name = {skill.name: skill for skill in self.skills}
        if len(by_name) != len(self.skills):
            raise ValueError("duplicate skill name")
        for skill in self.skills:
            unknown = set(skill.dependencies).difference(by_name)
            if unknown:
                raise ValueError(
                    f"unknown skill dependencies for {skill.name}: {sorted(unknown)}"
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


class AssistantInventory(BaseModel):
    """Validated portable-resource inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resources: tuple[PortableResource, ...]

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        """Reject duplicate inventory resource identifiers.

        Returns:
            The validated inventory.

        Raises:
            ValueError: If resource identifiers are duplicated.
        """
        ids = [resource.id for resource in self.resources]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate resource id")
        return self
