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


def test_plugin_actions_are_exact_ordered_and_profile_aware(repo_root: Path) -> None:
    """Plan JSON marketplace actions before JSON plugin actions."""
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
    assert all("piste" not in " ".join(action.argv) for action in default_actions)
    work_actions = plan_codex_plugins(
        repo_root / "assistants/codex/plugins.yaml",
        profiles=("default", "work"),
        installed=frozenset(),
    )
    assert [action.component_id for action in work_actions][-2:] == [
        "codex.plugin.ami-qsp-tools@piste",
        "codex.plugin.fieldkit@piste",
    ]
    assert all(
        not action.required for action in work_actions if "piste" in action.component_id
    )


def test_plugin_catalog_explicitly_declares_every_profile(repo_root: Path) -> None:
    """Keep default and work profile selection visible in the reviewed source."""
    source = yaml.safe_load(
        (repo_root / "assistants/codex/plugins.yaml").read_text(encoding="utf-8")
    )
    assert all(item["profiles"] == ["default"] for item in source["marketplaces"][:-1])
    assert source["marketplaces"][-1]["profiles"] == ["work"]
    assert all(item["profiles"] == ["default"] for item in source["plugins"][:-2])
    assert all(item["profiles"] == ["work"] for item in source["plugins"][-2:])


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
        "codex.plugins.catalog",
    ]
    assert all("hook" not in resource.id for resource in codex)
