"""Project shared assistant declarations into one native target's state."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from ballen_config.assistants.cursor_plugins import (
    ValidatedCursorLocalPlugin,
    validate_cursor_local_plugins,
)
from ballen_config.assistants.inventory import (
    LoadedInventory,
    ResolvedInventory,
    load_inventory,
    resolve_inventory,
)
from ballen_config.assistants.models import (
    AgentName,
    AssistantInventory,
    ConcreteAgentName,
    CursorLocalPlugin,
    CursorMarketplacePlugin,
    ExtensionCatalog,
    Marketplace,
    NativeMarketplacePlugin,
    PluginCatalog,
    SkillCatalog,
)

_CONCRETE_AGENTS: tuple[ConcreteAgentName, ...] = (
    AgentName.CURSOR,
    AgentName.CLAUDE,
    AgentName.CODEX,
)


class AssistantDesiredStateError(ValueError):
    """A secret-free assistant desired-state preflight failure."""


class PluginCatalogProjection(BaseModel):
    """One immutable profile-filtered catalog for one concrete target."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target: ConcreteAgentName
    marketplaces: tuple[Marketplace, ...]
    native_plugins: tuple[NativeMarketplacePlugin, ...]
    cursor_marketplace_plugins: tuple[CursorMarketplacePlugin, ...]
    cursor_local_plugins: tuple[CursorLocalPlugin, ...]


class AssistantDesiredState(BaseModel):
    """All validated assistant desired state for one resolved invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    inventory: AssistantInventory
    resolved_inventory: ResolvedInventory
    extension_catalog: ExtensionCatalog
    skill_catalog: SkillCatalog
    plugin_catalog: PluginCatalog
    plugin_projections: tuple[PluginCatalogProjection, ...]
    validated_cursor_local_plugins: tuple[ValidatedCursorLocalPlugin, ...]

    def plugin_projection(
        self,
        target: ConcreteAgentName,
    ) -> PluginCatalogProjection:
        """Return the one projection for an enabled concrete target.

        Args:
            target: Resolved concrete agent target.

        Returns:
            The target's immutable plugin projection.

        Raises:
            ValueError: If the target was skipped or is otherwise unavailable.
        """
        matches = tuple(
            projection
            for projection in self.plugin_projections
            if projection.target is target
        )
        if len(matches) != 1:
            raise ValueError(f"missing plugin projection: {target.value}")
        return matches[0]

    def cursor_local_plugin_snapshots(self) -> tuple[ValidatedCursorLocalPlugin, ...]:
        """Return active Cursor local-plugin snapshots without revalidation.

        Returns:
            Profile-eligible preflight snapshots in deterministic identifier
            order.

        Raises:
            ValueError: If an active projection lacks its validated snapshot.
        """
        projection = self.plugin_projection(AgentName.CURSOR)
        by_id = {
            snapshot.plugin.id: snapshot
            for snapshot in self.validated_cursor_local_plugins
        }
        try:
            return tuple(by_id[plugin.id] for plugin in projection.cursor_local_plugins)
        except KeyError as error:
            raise ValueError("missing validated Cursor local plugin") from error


def _catalog(
    loaded: LoadedInventory,
    resource_id: str,
    expected_type: type[ExtensionCatalog] | type[SkillCatalog] | type[PluginCatalog],
) -> ExtensionCatalog | SkillCatalog | PluginCatalog:
    """Return one exactly typed catalog from a loaded inventory.

    Args:
        loaded: Already parsed central inventory and catalogs.
        resource_id: Stable inventory resource identifier.
        expected_type: Exact expected Pydantic catalog class.

    Returns:
        The catalog referenced by the stable resource identifier.

    Raises:
        ValueError: If the expected catalog is absent or has the wrong kind.
    """
    matches = tuple(
        catalog.document
        for catalog in loaded.catalogs
        if catalog.resource_id == resource_id
    )
    if len(matches) != 1 or not isinstance(matches[0], expected_type):
        raise ValueError(f"invalid assistant catalog: {resource_id}")
    return matches[0]


def _cursor_shared_skill_names(catalog: SkillCatalog) -> frozenset[str]:
    """Return every shared skill declared for Cursor before profile filtering.

    Args:
        catalog: Fully validated shared skill catalog.

    Returns:
        Names reserved by any Cursor-targeted shared skill.
    """
    return frozenset(
        skill.name for skill in catalog.skills if AgentName.CURSOR in skill.targets
    )


def _validated_cursor_local_plugins(
    catalog: PluginCatalog,
    *,
    repo_root: Path,
    shared_skill_names: frozenset[str],
) -> tuple[ValidatedCursorLocalPlugin, ...]:
    """Validate every declared local plugin before profiles or skips apply.

    Args:
        catalog: Fully validated all-target plugin catalog.
        repo_root: Repository checkout containing reviewed plugin sources.
        shared_skill_names: Every shared skill reserved for Cursor.
    """
    return validate_cursor_local_plugins(
        tuple(
            plugin
            for plugin in catalog.plugins
            if isinstance(plugin, CursorLocalPlugin)
        ),
        repo_root=repo_root,
        shared_skill_names=shared_skill_names,
    )


def load_desired_state(
    repo_root: Path,
    profiles: tuple[str, ...],
    skipped: frozenset[str],
) -> AssistantDesiredState:
    """Load all assistant declarations into one immutable invocation snapshot.

    Args:
        repo_root: Repository root containing the central inventory.
        profiles: Expanded profiles selected by manifest resolution.
        skipped: Whole-agent component identifiers skipped by the invocation.

    Returns:
        Validated inventory, catalogs, and projections for enabled targets.

    Raises:
        AssistantDesiredStateError: If any assistant declaration is unreadable,
            unsafe, or invalid.
    """
    try:
        loaded = load_inventory(repo_root / "assistants/inventory.yaml", repo_root)
        extension_catalog = _catalog(
            loaded,
            "cursor.extensions.catalog",
            ExtensionCatalog,
        )
        skill_catalog = _catalog(loaded, "shared.skills.catalog", SkillCatalog)
        plugin_catalog = _catalog(loaded, "shared.plugins.catalog", PluginCatalog)
        assert isinstance(extension_catalog, ExtensionCatalog)
        assert isinstance(skill_catalog, SkillCatalog)
        assert isinstance(plugin_catalog, PluginCatalog)
        validated_local_plugins = _validated_cursor_local_plugins(
            plugin_catalog,
            repo_root=repo_root,
            shared_skill_names=_cursor_shared_skill_names(skill_catalog),
        )
        resolved_inventory = resolve_inventory(
            loaded.inventory,
            profiles=profiles,
            skipped=skipped,
        )
        enabled_targets = tuple(
            target for target in _CONCRETE_AGENTS if target.value not in skipped
        )
        projections = tuple(
            project_plugin_catalog(
                plugin_catalog,
                target=target,
                profiles=profiles,
            )
            for target in enabled_targets
        )
        return AssistantDesiredState(
            inventory=loaded.inventory,
            resolved_inventory=resolved_inventory,
            extension_catalog=extension_catalog,
            skill_catalog=skill_catalog,
            plugin_catalog=plugin_catalog,
            plugin_projections=projections,
            validated_cursor_local_plugins=validated_local_plugins,
        )
    except (OSError, ValidationError, ValueError, yaml.YAMLError) as error:
        raise AssistantDesiredStateError(
            "assistant desired-state preflight failed"
        ) from error


def project_plugin_catalog(
    catalog: PluginCatalog,
    *,
    target: ConcreteAgentName,
    profiles: tuple[str, ...],
) -> PluginCatalogProjection:
    """Project a validated shared catalog to one target and profile set.

    Args:
        catalog: Validated all-target plugin declarations.
        target: One concrete native agent.
        profiles: Active expanded bootstrap profiles.

    Returns:
        Immutable declarations available to the given target and profiles.
    """
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
