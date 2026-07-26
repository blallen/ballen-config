"""Tests for portable Codex settings, instructions, and plugins."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ballen_config.assistants.codex import (
    CodexPluginInspectionError,
    CodexSettingsError,
    codex_configuration,
    codex_instruction_renderer,
    codex_settings_renderer,
    install_actions,
    load_stable_settings,
    plan_codex_plugins,
)
from ballen_config.assistants.inventory import load_inventory
from ballen_config.configure import ApplyMethod
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.runtime import RuntimePaths
from tests.assistants.fakes import StatefulAssistantFake


def _setup(*, profiles: tuple[str, ...] = ("default",)) -> ResolvedSetup:
    """Return a minimal enabled Codex setup."""
    return ResolvedSetup(
        profiles=profiles,
        components=(
            Component(id="codex", manager=Manager.BREW_FORMULA, package="codex"),
        ),
        skipped=(),
    )


def test_overlay_is_an_exact_portable_allowlist(repo_root: Path) -> None:
    """Track exactly the portable Codex model preferences."""
    settings = load_stable_settings(repo_root / "assistants/codex/config.overlay.toml")
    assert settings.model_dump() == {
        "model": "gpt-5.6-sol",
        "model_reasoning_effort": "xhigh",
        "service_tier": "priority",
    }
    source = (repo_root / "assistants/codex/config.overlay.toml").read_text()
    assert all(
        term not in source.casefold()
        for term in (
            "auth",
            "trust",
            "project",
            "mcp",
            "plugin",
            "runtime",
            "history",
            "session",
            "cache",
            "memory",
            "/users/",
        )
    )


def test_renderer_preserves_native_toml_and_changes_only_overlay(
    repo_root: Path,
) -> None:
    """Preserve native tables, comments, and unrelated user preferences."""
    current = b"""# retain this comment\nmodel = "old"\nservice_tier = "standard"\n[projects."/work"]\ntrust_level = "trusted"\n[plugins]\nkeep = true\n[mcp_servers.local]\ncommand = "native"\n"""
    rendered = codex_settings_renderer()(
        (repo_root / "assistants/codex/config.overlay.toml").read_bytes(), current
    ).decode()
    assert "# retain this comment" in rendered
    assert 'model = "gpt-5.6-sol"' in rendered
    assert 'model_reasoning_effort = "xhigh"' in rendered
    assert 'service_tier = "priority"' in rendered
    assert '[projects."/work"]' in rendered
    assert "[plugins]" in rendered
    assert "[mcp_servers.local]" in rendered


@pytest.mark.parametrize("current", [b"[broken", b"[table]\nkey ="])
def test_renderer_fails_closed_for_invalid_native_toml(
    repo_root: Path, current: bytes
) -> None:
    """Never replace a malformed native Codex document."""
    with pytest.raises(CodexSettingsError, match="invalid Codex settings"):
        codex_settings_renderer()(
            (repo_root / "assistants/codex/config.overlay.toml").read_bytes(), current
        )


def test_plugin_actions_are_exact_ordered_and_profile_independent(
    repo_root: Path,
) -> None:
    """Plan the same ordered JSON actions for each supported profile."""
    default_actions = plan_codex_plugins(
        repo_root / "assistants/codex/plugins.yaml",
        profiles=("default",),
        installed=frozenset(),
    )
    assert default_actions[0].argv == (
        "codex",
        "plugin",
        "marketplace",
        "add",
        "anthropics/claude-plugins-official",
        "--json",
    )
    assert all(action.argv[-1] == "--json" for action in default_actions)
    work_actions = plan_codex_plugins(
        repo_root / "assistants/codex/plugins.yaml",
        profiles=("default", "work"),
        installed=frozenset(),
    )
    assert work_actions == default_actions


def test_plugin_planner_filters_optional_work_catalog_entries(tmp_path: Path) -> None:
    """Select optional work entries after required default JSON actions."""
    catalog_path = tmp_path / "plugins.yaml"
    catalog_path.write_text(
        "marketplaces:\n"
        "  - name: default-marketplace\n"
        "    source: example/default\n"
        "    profiles: [default]\n"
        "  - name: work-marketplace\n"
        "    source: example/work\n"
        "    profiles: [work]\n"
        "plugins:\n"
        "  - id: default-plugin@default-marketplace\n"
        "    marketplace: default-marketplace\n"
        "    profiles: [default]\n"
        "  - id: work-plugin@work-marketplace\n"
        "    marketplace: work-marketplace\n"
        "    profiles: [work]\n"
        "    required: false\n"
    )

    default_actions = plan_codex_plugins(
        catalog_path, profiles=("default",), installed=frozenset()
    )
    assert [action.component_id for action in default_actions] == [
        "codex.marketplace.default-marketplace",
        "codex.plugin.default-plugin@default-marketplace",
    ]

    work_actions = plan_codex_plugins(
        catalog_path, profiles=("default", "work"), installed=frozenset()
    )
    assert [action.component_id for action in work_actions] == [
        "codex.marketplace.default-marketplace",
        "codex.marketplace.work-marketplace",
        "codex.plugin.default-plugin@default-marketplace",
        "codex.plugin.work-plugin@work-marketplace",
    ]
    assert all(not action.required for action in work_actions[1::2])


def test_plugin_catalog_declares_only_retained_default_profile(repo_root: Path) -> None:
    """Keep all retained Codex catalog entries available in both profiles."""
    source = yaml.safe_load(
        (repo_root / "assistants/codex/plugins.yaml").read_text(encoding="utf-8")
    )
    assert all(item["profiles"] == ["default"] for item in source["marketplaces"])
    assert all(item["profiles"] == ["default"] for item in source["plugins"])


def test_native_plugin_inspection_accepts_installed_plugin_records(
    repo_root: Path, temporary_home: Path, fake_runner: StatefulAssistantFake
) -> None:
    """Use the current native plugin-list schema to avoid duplicate actions."""
    fake_runner.add(
        ("codex", "plugin", "list", "--json"),
        returncode=0,
        stdout=(
            '{"installed": [{"pluginId": "frontend-design@claude-plugins-official", '
            '"marketplaceName": "claude-plugins-official", "version": "1.0.0", '
            '"enabled": true, "source": "anthropics/claude-plugins-official"}], '
            '"available": []}'
        ),
    )
    fake_runner.add(
        ("codex", "plugin", "marketplace", "list", "--json"),
        returncode=0,
        stdout=(
            '{"marketplaces": [{"name": "claude-plugins-official", '
            '"root": "/plugins/claude-plugins-official", '
            '"marketplaceSource": "anthropics/claude-plugins-official"}]}'
        ),
    )

    actions = install_actions(
        _setup(),
        RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home),
        fake_runner,
    )

    component_ids = {action.component_id for action in actions}
    assert "codex.marketplace.claude-plugins-official" not in component_ids
    assert "codex.plugin.frontend-design@claude-plugins-official" not in component_ids


@pytest.mark.parametrize(
    ("plugin_list", "marketplace_list", "expected_commands"),
    [
        pytest.param(
            '{"installed": [{"pluginId": 1}], "available": []}',
            '{"marketplaces": []}',
            (("codex", "plugin", "list", "--json"),),
            id="invalid-plugin-id",
        ),
        pytest.param(
            '{"installed": [], "available": []}',
            '{"marketplaces": [{}]}',
            (
                ("codex", "plugin", "list", "--json"),
                ("codex", "plugin", "marketplace", "list", "--json"),
            ),
            id="invalid-marketplace-name",
        ),
    ],
)
def test_native_plugin_inspection_fails_closed_for_malformed_native_records(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    plugin_list: str,
    marketplace_list: str,
    expected_commands: tuple[tuple[str, ...], ...],
) -> None:
    """Normalize malformed native records from either inspection command."""
    fake_runner.add(
        ("codex", "plugin", "list", "--json"), returncode=0, stdout=plugin_list
    )
    fake_runner.add(
        ("codex", "plugin", "marketplace", "list", "--json"),
        returncode=0,
        stdout=marketplace_list,
    )

    with pytest.raises(
        CodexPluginInspectionError, match="Codex plugin inspection failed"
    ):
        install_actions(
            _setup(),
            RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home),
            fake_runner,
        )
    assert fake_runner.commands == list(expected_commands)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            ("codex", "plugin", "list", "--json"),
            id="plugin-list-command",
        ),
        pytest.param(
            ("codex", "plugin", "marketplace", "list", "--json"),
            id="marketplace-list-command",
        ),
    ],
)
def test_native_plugin_inspection_normalizes_command_failures(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    command: tuple[str, ...],
) -> None:
    """Normalize either native inspection command failure."""
    fake_runner.add(command, returncode=1)

    with pytest.raises(
        CodexPluginInspectionError, match="Codex plugin inspection failed"
    ):
        install_actions(
            _setup(),
            RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home),
            fake_runner,
        )


def test_enabled_inspection_fails_closed_and_skip_does_nothing(
    repo_root: Path, temporary_home: Path, fake_runner: StatefulAssistantFake
) -> None:
    """Reject ambiguous inspection while skipped Codex never touches boundaries."""
    skipped = ResolvedSetup(profiles=("default",), components=(), skipped=("codex",))
    assert (
        install_actions(
            skipped,
            RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home),
            fake_runner,
        )
        == ()
    )
    assert fake_runner.commands == []
    fake_runner.add(
        ("codex", "plugin", "list", "--json"),
        returncode=0,
        stdout='{"plugins": [], "plugins": []}',
    )
    with pytest.raises(
        CodexPluginInspectionError, match="Codex plugin inspection failed"
    ):
        install_actions(
            _setup(),
            RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home),
            fake_runner,
        )


def test_instruction_and_configuration_own_only_codex_resources(
    repo_root: Path, temporary_home: Path
) -> None:
    """Render canonical guidance plus an absolute managed RTK include."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    rendered = codex_instruction_renderer(paths)(
        (repo_root / "assistants/codex/AGENTS.md").read_bytes(), None
    ).decode()
    assert rendered.startswith("# Engineering defaults\n")
    assert f"@{temporary_home}/.codex/RTK.md" in rendered
    assert rendered.endswith(
        "Repository instructions take precedence for repository-specific behavior.\n"
        "Never migrate authentication, trust, sessions, project paths, or generated plugin state.\n"
    )
    suffix = (repo_root / "assistants/codex/AGENTS.md").read_text(encoding="utf-8")
    assert all(
        concept in suffix
        for concept in (
            "authentication",
            "trust",
            "sessions",
            "project paths",
            "plugin state",
        )
    )
    assert "/Users/" not in suffix
    contribution = codex_configuration(
        repo_root=repo_root,
        home=temporary_home,
        profiles=("default",),
        enabled=frozenset({"codex"}),
    )
    assert {spec.destination for spec in contribution.specs} == {
        Path(".codex/config.toml"),
        Path(".codex/AGENTS.md"),
        Path(".codex/RTK.md"),
    }
    assert {spec.method for spec in contribution.specs} == {
        ApplyMethod.RENDER,
        ApplyMethod.COPY,
    }


def test_inventory_is_synchronized_and_excludes_local_state(repo_root: Path) -> None:
    """Declare only Codex portable resources in the central inventory."""
    inventory = load_inventory(repo_root / "assistants/inventory.yaml")
    codex = [
        resource for resource in inventory.resources if resource.owner.value == "codex"
    ]
    assert [resource.id for resource in codex] == [
        "codex.config",
        "codex.instructions",
        "codex.rtk",
        "codex.browser",
        "codex.notion",
        "codex.plugins.catalog",
    ]
    assert all("hook" not in resource.id for resource in codex)
