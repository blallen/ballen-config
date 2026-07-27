"""Project shared assistant declarations into one native target's state."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ballen_config.assistants.models import (
    ConcreteAgentName,
    CursorLocalPlugin,
    CursorMarketplacePlugin,
    Marketplace,
    NativeMarketplacePlugin,
    PluginCatalog,
)


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
