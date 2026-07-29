"""Strict models for portable coding-agent inventory declarations."""

import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Final, Literal, Self

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
    """Require target lists to name only installable coding agents."""
    if AgentName.SHARED in targets:
        raise ValueError("shared is not a concrete target")
    if len(targets) != len(set(targets)):
        raise ValueError("duplicate concrete target")
    return targets


ConcreteTargets = Annotated[
    tuple[AgentName, ...],
    AfterValidator(_validate_concrete_targets),
]

ConcreteAgentName = Literal[
    AgentName.CURSOR,
    AgentName.CLAUDE,
    AgentName.CODEX,
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
_CURSOR_ATLASSIAN_MCP_ID: Final = "cursor.atlassian-mcp"
_CURSOR_ATLASSIAN_MCP_SOURCE: Final = PurePosixPath(
    "assistants/cursor/atlassian-workaround.json"
)
_CURSOR_ATLASSIAN_MCP_DESTINATION: Final = PurePosixPath(".cursor/mcp.json")
_APPROVED_MANAGED_STATE_PATHS: Final = frozenset({_CURSOR_ATLASSIAN_MCP_DESTINATION})


def _validate_managed_file_path(path: PurePosixPath) -> PurePosixPath:
    """Reject file-copy paths that represent local agent state."""
    if path in _APPROVED_MANAGED_STATE_PATHS:
        return path
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

    @model_validator(mode="after")
    def validate_managed_state_exception(self) -> Self:
        """Bind the Cursor MCP path exception to one exact work resource."""
        uses_exception = (
            self.source in _APPROVED_MANAGED_STATE_PATHS
            or self.destination in _APPROVED_MANAGED_STATE_PATHS
        )
        if not uses_exception:
            return self
        approved = (
            self.id == _CURSOR_ATLASSIAN_MCP_ID
            and self.owner is AgentName.CURSOR
            and self.source == _CURSOR_ATLASSIAN_MCP_SOURCE
            and self.destination == _CURSOR_ATLASSIAN_MCP_DESTINATION
            and self.profiles == ("work",)
            and self.required
            and self.mode == 0o600
            and not self.targets
            and self.role == "direct"
        )
        if not approved:
            raise ValueError("file resource path represents managed local state")
        return self


class HookResource(ResourceBase):
    """An authored hook program with one or more native registrations."""

    kind: Literal["hook"]
    source: PurePosixPath
    event: str = Field(min_length=1)
    targets: ConcreteTargets = Field(min_length=1)


class CatalogResource(ResourceBase):
    """A typed subcatalog referenced once by the central inventory."""

    kind: Literal["catalog"]
    source: PurePosixPath
    catalog_kind: CatalogKind
    targets: ConcreteTargets = ()


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
        """Require complete immutable metadata only for HTTPS VSIX installs."""
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
        """Reject duplicate extension identifiers."""
        ids = [extension.id for extension in self.extensions]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate extension id")
        return self


class Marketplace(BaseModel):
    """A marketplace available to one or more native agents."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, description="Stable marketplace alias.")
    source: str = Field(min_length=1, description="Marketplace repository source.")
    targets: ConcreteTargets = Field(
        min_length=1,
        description="Native agents that may use this marketplace.",
    )
    profiles: tuple[str, ...] = Field(
        default=("default",),
        min_length=1,
        description="Profiles that enable this marketplace.",
    )


class NativeMarketplacePlugin(BaseModel):
    """A Claude Code or Codex marketplace plugin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["native-marketplace"] = Field(
        description="Native marketplace plugin representation discriminator."
    )
    id: str = Field(min_length=1, description="Stable native plugin identifier.")
    marketplace: str = Field(
        min_length=1,
        description="Marketplace alias that provides this plugin.",
    )
    targets: ConcreteTargets = Field(
        min_length=1,
        description="Native agents that may install this plugin.",
    )
    profiles: tuple[str, ...] = Field(
        default=("default",),
        min_length=1,
        description="Profiles that enable this plugin.",
    )
    required: bool = Field(
        default=True,
        description="Whether the plugin is required for its enabled targets.",
    )


class CursorMarketplacePlugin(BaseModel):
    """A manual user-scoped Cursor marketplace selection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["cursor-marketplace"] = Field(
        description="Cursor marketplace plugin representation discriminator."
    )
    id: str = Field(
        pattern=r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$",
        description="Stable Cursor marketplace plugin identifier.",
    )
    targets: ConcreteTargets = Field(
        min_length=1,
        description="Cursor target selection for this plugin.",
    )
    profiles: tuple[str, ...] = Field(
        default=("default",),
        min_length=1,
        description="Profiles that expose this manual selection.",
    )
    required: bool = Field(
        default=True,
        description="Whether the manual selection is required.",
    )
    scope: Literal["user"] = Field(description="Cursor marketplace installation scope.")
    verification: Literal["manual"] = Field(
        description="Verification mode for the user-managed selection."
    )


class CursorLocalPlugin(BaseModel):
    """A reviewed Cursor plugin tree managed below the native local root."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["cursor-local"] = Field(
        description="Reviewed local Cursor plugin representation discriminator."
    )
    id: str = Field(
        pattern=r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$",
        description="Stable local Cursor plugin identifier.",
    )
    source: PurePosixPath = Field(
        description="Reviewed repository-relative local plugin source path."
    )
    targets: ConcreteTargets = Field(
        min_length=1,
        description="Cursor target selection for this local plugin.",
    )
    profiles: tuple[str, ...] = Field(
        default=("default",),
        min_length=1,
        description="Profiles that enable this local plugin.",
    )
    required: bool = Field(
        default=True,
        description="Whether the local plugin is required.",
    )


PluginSpec = Annotated[
    NativeMarketplacePlugin | CursorMarketplacePlugin | CursorLocalPlugin,
    Field(discriminator="kind"),
]


class PluginCatalog(BaseModel):
    """Validated target-aware plugin declarations for every agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    marketplaces: tuple[Marketplace, ...] = Field(
        description="Target-aware native marketplace declarations."
    )
    plugins: tuple[PluginSpec, ...] = Field(
        description="Target-aware native and Cursor plugin declarations."
    )

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
                if plugin.id.rpartition("@")[1:] != ("@", plugin.marketplace):
                    raise ValueError(f"plugin marketplace suffix mismatch: {plugin.id}")
                for target in plugin.targets:
                    matched_marketplace = marketplace_by_target.get(
                        (target, plugin.marketplace)
                    )
                    if matched_marketplace is None:
                        raise ValueError(
                            "plugin target is not covered by marketplace: "
                            f"{target}:{plugin.id}"
                        )
                    if not set(plugin.profiles).issubset(matched_marketplace.profiles):
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


class SkillRenameSpec(BaseModel):
    """Bounded rename from a retired skill name to a catalog successor."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    from_name: str = Field(alias="from", pattern=r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
    to_name: str = Field(alias="to", pattern=r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class SkillCatalog(BaseModel):
    """Validated canonical-skill dependency catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    skills: tuple[SkillSpec, ...]
    renames: tuple[SkillRenameSpec, ...] = ()

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        """Reject duplicate, unknown, and cyclic skill dependencies."""
        by_name = {skill.name: skill for skill in self.skills}
        if len(by_name) != len(self.skills):
            raise ValueError("duplicate skill name")
        for skill in self.skills:
            unknown = set(skill.dependencies).difference(by_name)
            if unknown:
                raise ValueError(
                    f"unknown skill dependencies for {skill.name}: {sorted(unknown)}"
                )
        for skill in self.skills:
            for dependency_name in skill.dependencies:
                dependency = by_name[dependency_name]
                if not set(skill.targets).issubset(dependency.targets):
                    raise ValueError(
                        f"dependency targets do not cover {skill.name}: "
                        f"{dependency_name}"
                    )
                if not set(skill.profiles).issubset(dependency.profiles):
                    raise ValueError(
                        f"dependency profiles do not cover {skill.name}: "
                        f"{dependency_name}"
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

    @model_validator(mode="after")
    def validate_renames(self) -> Self:
        """Reject invalid bounded rename declarations."""
        skill_names = {skill.name for skill in self.skills}
        seen_from: set[str] = set()
        for rename in self.renames:
            if rename.from_name in skill_names:
                raise ValueError("rename from still present in skills")
            if rename.from_name in seen_from:
                raise ValueError("duplicate rename from")
            seen_from.add(rename.from_name)
            if rename.to_name not in skill_names:
                raise ValueError("rename to absent from skills")
        return self


class AssistantInventory(BaseModel):
    """Validated portable-resource inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resources: tuple[PortableResource, ...]

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        """Reject duplicate inventory resource identifiers."""
        ids = [resource.id for resource in self.resources]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate resource id")
        return self
