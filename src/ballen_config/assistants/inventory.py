"""Load and resolve reviewed coding-agent inventory declarations."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Final

import yaml

from ballen_config.assistants.models import (
    AgentName,
    AssistantInventory,
    CatalogKind,
    CatalogResource,
    ExtensionCatalog,
    FileResource,
    HookResource,
    PluginCatalog,
    PortableResource,
    SkillCatalog,
)

type CatalogDocument = ExtensionCatalog | PluginCatalog | SkillCatalog


@dataclass(frozen=True)
class LoadedCatalog:
    """One inventory catalog parsed from one immutable file read."""

    resource_id: str
    document: ExtensionCatalog | PluginCatalog | SkillCatalog


@dataclass(frozen=True)
class LoadedInventory:
    """Validated inventory plus every parsed catalog document."""

    inventory: AssistantInventory
    catalogs: tuple[LoadedCatalog, ...]


@dataclass(frozen=True)
class ResolvedInventory:
    """Resources selected for one bootstrap invocation."""

    resources: tuple[PortableResource, ...]


_COMPONENT_OWNER: Final[Mapping[str, AgentName]] = MappingProxyType(
    {
        "cursor": AgentName.CURSOR,
        "claude-code": AgentName.CLAUDE,
        "codex": AgentName.CODEX,
    }
)


def _validated_source(source: PurePosixPath, root: Path) -> Path:
    """Resolve one source beneath the checkout before testing existence.

    Args:
        source: Inventory-declared POSIX source path.
        root: Resolved checkout root.

    Returns:
        Resolved source path contained by ``root``.

    Raises:
        ValueError: If the source is absolute, traverses upward, escapes
            through a symlink, or does not exist.
    """
    if source.is_absolute() or ".." in source.parts:
        raise ValueError(f"source escapes checkout: {source}")
    candidate = root.joinpath(*source.parts)
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ValueError(f"source escapes checkout: {source}")
    if not resolved.exists():
        raise ValueError(f"source does not exist: {source}")
    return resolved


def _load_catalog(resource: CatalogResource, source: Path) -> CatalogDocument:
    """Parse one declared subcatalog using its declared document type.

    Args:
        resource: Inventory catalog declaration.
        source: Validated catalog source path.

    Returns:
        Validated immutable catalog document.
    """
    payload = yaml.safe_load(source.read_text())
    if resource.catalog_kind is CatalogKind.EXTENSION:
        return ExtensionCatalog.model_validate(payload)
    if resource.catalog_kind is CatalogKind.PLUGIN:
        return PluginCatalog.model_validate(payload)
    return SkillCatalog.model_validate(payload)


def load_inventory(path: Path, repo_root: Path | None = None) -> LoadedInventory:
    """Load an assistant inventory and validate all local sources.

    Inventory schema validation deliberately precedes filesystem inspection so
    malformed declarations cannot influence path handling.

    Args:
        path: Inventory YAML path.
        repo_root: Optional checkout root used to resolve resource sources. When
            omitted, the parent of the ``assistants`` directory is used.

    Returns:
        Validated assistant inventory and each catalog document.

    Raises:
        ValueError: If a source is absent or unsafe.
    """
    inventory = AssistantInventory.model_validate(yaml.safe_load(path.read_text()))
    root = (repo_root or path.parent.parent).resolve(strict=True)
    catalogs: list[LoadedCatalog] = []
    for resource in inventory.resources:
        source = resource.source
        if source is None:
            continue
        candidate = _validated_source(source, root)
        if isinstance(resource, CatalogResource):
            catalogs.append(
                LoadedCatalog(
                    resource_id=resource.id,
                    document=_load_catalog(resource, candidate),
                )
            )
    return LoadedInventory(inventory=inventory, catalogs=tuple(catalogs))


def resolve_inventory(
    inventory: AssistantInventory,
    *,
    profiles: tuple[str, ...],
    skipped: frozenset[str],
) -> ResolvedInventory:
    """Resolve expanded profiles and whole-agent skips deterministically.

    Args:
        inventory: Validated portable-resource inventory.
        profiles: Profiles already expanded by the core manifest resolver.
        skipped: Whole-component skip keys from the core resolved setup.

    Returns:
        Selected resources sorted by stable resource identifier.
    """
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
        if (
            resource.owner is AgentName.SHARED
            and isinstance(resource, FileResource | HookResource | CatalogResource)
            and resource.targets
        ):
            enabled_targets = tuple(
                target for target in resource.targets if target not in disabled_owners
            )
            if not enabled_targets:
                continue
            resource = resource.model_copy(update={"targets": enabled_targets})
        selected.append(resource)
    return ResolvedInventory(
        resources=tuple(sorted(selected, key=lambda item: item.id))
    )
