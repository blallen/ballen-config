"""Tests for target-aware assistant desired-state projections."""

from __future__ import annotations

from pathlib import Path

import yaml

from ballen_config.assistants.desired_state import project_plugin_catalog
from ballen_config.assistants.models import AgentName, PluginCatalog


def _targeted_catalog() -> PluginCatalog:
    """Create deliberately unsorted declarations across targets and profiles."""
    return PluginCatalog.model_validate(
        {
            "marketplaces": [
                {
                    "name": "z-native",
                    "source": "owner/z-native",
                    "targets": ["claude-code", "codex"],
                    "profiles": ["default"],
                },
                {
                    "name": "work-only",
                    "source": "owner/work-only",
                    "targets": ["claude-code"],
                    "profiles": ["work"],
                },
                {
                    "name": "a-native",
                    "source": "owner/a-native",
                    "targets": ["claude-code"],
                    "profiles": ["default"],
                },
            ],
            "plugins": [
                {
                    "kind": "native-marketplace",
                    "id": "zed@z-native",
                    "marketplace": "z-native",
                    "targets": ["claude-code", "codex"],
                    "profiles": ["default"],
                },
                {
                    "kind": "cursor-marketplace",
                    "id": "z-cursor-marketplace",
                    "targets": ["cursor"],
                    "scope": "user",
                    "verification": "manual",
                },
                {
                    "kind": "cursor-local",
                    "id": "z-cursor-local",
                    "source": "assistants/shared/plugins/local/z-cursor-local",
                    "targets": ["cursor"],
                },
                {
                    "kind": "native-marketplace",
                    "id": "excluded@work-only",
                    "marketplace": "work-only",
                    "targets": ["claude-code"],
                    "profiles": ["work"],
                },
                {
                    "kind": "native-marketplace",
                    "id": "alpha@a-native",
                    "marketplace": "a-native",
                    "targets": ["claude-code"],
                    "profiles": ["default"],
                },
                {
                    "kind": "cursor-marketplace",
                    "id": "a-cursor-marketplace",
                    "targets": ["cursor"],
                    "scope": "user",
                    "verification": "manual",
                },
                {
                    "kind": "cursor-local",
                    "id": "a-cursor-local",
                    "source": "assistants/shared/plugins/local/a-cursor-local",
                    "targets": ["cursor"],
                },
                {
                    "kind": "cursor-local",
                    "id": "work-cursor-local",
                    "source": "assistants/shared/plugins/local/work-cursor-local",
                    "targets": ["cursor"],
                    "profiles": ["work"],
                },
            ],
        }
    )


def test_project_plugin_catalog_returns_one_concrete_target() -> None:
    """Narrow, filter, and sort native declarations for one target."""
    projection = project_plugin_catalog(
        _targeted_catalog(),
        target=AgentName.CLAUDE,
        profiles=("default",),
    )
    assert projection.target is AgentName.CLAUDE
    assert tuple(
        (marketplace.name, marketplace.targets)
        for marketplace in projection.marketplaces
    ) == (
        ("a-native", (AgentName.CLAUDE,)),
        ("z-native", (AgentName.CLAUDE,)),
    )
    assert tuple(
        (plugin.id, plugin.targets) for plugin in projection.native_plugins
    ) == (
        ("alpha@a-native", (AgentName.CLAUDE,)),
        ("zed@z-native", (AgentName.CLAUDE,)),
    )
    assert projection.cursor_marketplace_plugins == ()
    assert projection.cursor_local_plugins == ()


def test_project_plugin_catalog_filters_and_sorts_cursor_variants() -> None:
    """Filter inactive Cursor entries and sort each variant independently."""
    projection = project_plugin_catalog(
        _targeted_catalog(),
        target=AgentName.CURSOR,
        profiles=("default",),
    )

    assert projection.target is AgentName.CURSOR
    assert projection.marketplaces == ()
    assert projection.native_plugins == ()
    assert tuple(
        (plugin.id, plugin.targets) for plugin in projection.cursor_marketplace_plugins
    ) == (
        ("a-cursor-marketplace", (AgentName.CURSOR,)),
        ("z-cursor-marketplace", (AgentName.CURSOR,)),
    )
    assert tuple(
        (plugin.id, plugin.targets) for plugin in projection.cursor_local_plugins
    ) == (
        ("a-cursor-local", (AgentName.CURSOR,)),
        ("z-cursor-local", (AgentName.CURSOR,)),
    )


def test_shared_plugin_catalog_parses_against_targeted_models(repo_root: Path) -> None:
    """Keep the production shared YAML aligned with catalog models and projection."""
    catalog_path = repo_root / "assistants/shared/plugins/catalog.yaml"
    catalog = PluginCatalog.model_validate(yaml.safe_load(catalog_path.read_text()))

    projection = project_plugin_catalog(
        catalog,
        target=AgentName.CODEX,
        profiles=("default",),
    )

    assert tuple(marketplace.name for marketplace in projection.marketplaces) == (
        "bigspinai",
        "claude-plugins-official",
        "context-mode",
        "superpowers-marketplace",
    )
    assert tuple(plugin.id for plugin in projection.native_plugins) == (
        "bigspin@bigspinai",
        "context-mode@context-mode",
        "frontend-design@claude-plugins-official",
        "github@claude-plugins-official",
        "logfire@claude-plugins-official",
        "superpowers-developing-for-claude-code@superpowers-marketplace",
        "superpowers@claude-plugins-official",
    )
    assert (
        tuple(marketplace.targets for marketplace in projection.marketplaces)
        == ((AgentName.CODEX,),) * 4
    )
    assert (
        tuple(plugin.targets for plugin in projection.native_plugins)
        == ((AgentName.CODEX,),) * 7
    )
    assert projection.cursor_marketplace_plugins == ()
    assert projection.cursor_local_plugins == ()
