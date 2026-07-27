"""Tests for portable Claude Code settings and reviewed plugins."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ballen_config.assistants.claude import (
    ClaudePluginInspectionError,
    ClaudeSettingsError,
    claude_configuration,
    claude_instruction_renderer,
    claude_settings_renderer,
    install_actions,
    load_stable_settings,
    plan_claude_plugins,
)
from ballen_config.assistants.hooks import hook_contribution
from ballen_config.assistants.inventory import load_inventory
from ballen_config.assistants.models import FileResource, PluginCatalog
from ballen_config.configure import ApplyMethod
from ballen_config.install import Installer
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.runtime import RuntimePaths
from tests.assistants.fakes import StatefulAssistantFake


def _setup(*, profiles: tuple[str, ...] = ("default",)) -> ResolvedSetup:
    """Return a minimal enabled Claude setup."""
    return ResolvedSetup(
        profiles=profiles,
        components=(
            Component(
                id="claude-code",
                manager=Manager.BREW_CASK,
                package="claude-code",
            ),
        ),
        skipped=(),
    )


def test_stable_settings_omit_local_state(repo_root: Path) -> None:
    """Track only the reviewed portable Claude model preference."""
    serialized = load_stable_settings(
        repo_root / "assistants/claude/settings.json"
    ).model_dump_json()
    forbidden = (
        "/Users/",
        "projects",
        "session",
        "history",
        "oauth",
        "token",
        "cache",
        "plugin-script",
        "gitlab",
        "plato",
        "local",
    )
    assert all(term not in serialized.casefold() for term in forbidden)


def test_plugin_actions_are_scoped_ordered_and_profile_independent(
    repo_root: Path,
) -> None:
    """Plan the same ordered native actions for each supported profile."""
    default_actions = plan_claude_plugins(
        repo_root / "assistants/claude/plugins.yaml",
        profiles=("default",),
        installed=frozenset(),
    )
    default_argv = [action.argv for action in default_actions]
    assert default_argv[0] == (
        "claude",
        "plugin",
        "marketplace",
        "add",
        "--scope",
        "user",
        "anthropics/claude-plugins-official",
    )
    assert all(
        action.argv[0:3] == ("claude", "plugin", "install")
        for action in default_actions[6:]
    )
    assert all(
        action.component_id.startswith("claude.marketplace.")
        for action in default_actions[:6]
    )
    work_actions = plan_claude_plugins(
        repo_root / "assistants/claude/plugins.yaml",
        profiles=("default", "work"),
        installed=frozenset(),
    )
    assert work_actions == default_actions


def test_plugin_planner_filters_optional_work_catalog_entries(tmp_path: Path) -> None:
    """Select optional work entries after required default native actions."""
    catalog_path = tmp_path / "plugins.yaml"
    catalog_path.write_text(
        "marketplaces:\n"
        "  - name: default-marketplace\n"
        "    source: example/default\n"
        "  - name: work-marketplace\n"
        "    source: example/work\n"
        "    profiles: [work]\n"
        "plugins:\n"
        "  - id: default-plugin@default-marketplace\n"
        "    marketplace: default-marketplace\n"
        "  - id: work-plugin@work-marketplace\n"
        "    marketplace: work-marketplace\n"
        "    profiles: [work]\n"
        "    required: false\n"
    )

    default_actions = plan_claude_plugins(
        catalog_path, profiles=("default",), installed=frozenset()
    )
    assert [action.component_id for action in default_actions] == [
        "claude.marketplace.default-marketplace",
        "claude.plugin.default-plugin@default-marketplace",
    ]

    work_actions = plan_claude_plugins(
        catalog_path, profiles=("default", "work"), installed=frozenset()
    )
    assert [action.component_id for action in work_actions] == [
        "claude.marketplace.default-marketplace",
        "claude.marketplace.work-marketplace",
        "claude.plugin.default-plugin@default-marketplace",
        "claude.plugin.work-plugin@work-marketplace",
    ]
    assert all(not action.required for action in work_actions[1::2])


def test_registered_native_entries_are_noops(repo_root: Path) -> None:
    """Avoid installing already registered native marketplaces and plugins."""
    actions = plan_claude_plugins(
        repo_root / "assistants/claude/plugins.yaml",
        profiles=("default",),
        installed=frozenset({"frontend-design@claude-plugins-official"}),
        known_marketplaces=frozenset({"claude-plugins-official"}),
    )
    ids = {action.component_id for action in actions}
    assert "claude.marketplace.claude-plugins-official" not in ids
    assert "claude.plugin.frontend-design@claude-plugins-official" not in ids


def test_renderer_replaces_only_the_exact_owned_managed_hook(
    repo_root: Path, temporary_home: Path
) -> None:
    """Preserve unrelated settings and hooks while replacing the RTK entry."""
    current = b"""{
      "extraKnownMarketplaces": {"native": {"source": "owner/repo"}},
      "enabledPlugins": {"native@native": true},
      "effortLevel": "high",
      "unrelated": {"keep": true},
      "hooks": {
        "SessionStart": [{"hooks": [{"type": "command", "command": "native"}]}],
        "PreToolUse": [
          {"matcher": "Edit", "hooks": [{"type": "command", "command": "native-pre"}]},
          {"matcher": "Bash", "hooks": [{"type": "command", "command": "/old/rtk-hook claude"}]},
          {"matcher": "Bash", "hooks": [{"type": "command", "command": "/old/rtk-hook claude"}, {"type": "command", "command": "compound"}]},
          {"matcher": "Bash", "hooks": [{"type": "command", "command": "/old/rtk-hook claude; suffix"}]}
        ]
      }
    }"""
    rendered = claude_settings_renderer(temporary_home)(
        (repo_root / "assistants/claude/settings.json").read_bytes(), current
    )
    document = json.loads(rendered)
    assert document["model"] == "opus"
    assert document["extraKnownMarketplaces"] == {"native": {"source": "owner/repo"}}
    assert document["enabledPlugins"] == {"native@native": True}
    assert document["effortLevel"] == "high"
    assert document["unrelated"] == {"keep": True}
    assert "SessionStart" in document["hooks"]
    pre_tool_use = document["hooks"]["PreToolUse"]
    assert any(item["matcher"] == "Edit" for item in pre_tool_use)
    assert any(
        item["hooks"][0]["command"] == "/old/rtk-hook claude" for item in pre_tool_use
    )
    assert any(len(item["hooks"]) == 2 for item in pre_tool_use)
    assert any(
        item["hooks"][0]["command"].endswith("; suffix") for item in pre_tool_use
    )
    managed = [
        item
        for item in pre_tool_use
        if item["hooks"][0]["command"]
        == f"{temporary_home}/.local/share/ballen-config/hooks/rtk-hook claude"
    ]
    assert len(managed) == 1
    assert managed[0]["hooks"][0]["command"].startswith(str(temporary_home))


def test_renderer_replaces_an_exact_current_managed_hook(
    repo_root: Path, temporary_home: Path
) -> None:
    """Converge an exact adapter-managed entry to precisely one registration."""
    command = f"{temporary_home}/.local/share/ballen-config/hooks/rtk-hook claude"
    current = json.dumps(
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": command}],
                    }
                ]
            }
        }
    ).encode()
    document = json.loads(
        claude_settings_renderer(temporary_home)(
            (repo_root / "assistants/claude/settings.json").read_bytes(), current
        )
    )
    assert document["hooks"]["PreToolUse"] == [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}
    ]


@pytest.mark.parametrize("current", [b"[1]", b"{", b'{"effortLevel": NaN}'])
def test_renderer_fails_closed_for_invalid_native_settings(
    repo_root: Path, temporary_home: Path, current: bytes
) -> None:
    """Reject malformed local settings without producing a replacement."""
    with pytest.raises(ClaudeSettingsError, match="invalid Claude settings"):
        claude_settings_renderer(temporary_home)(
            (repo_root / "assistants/claude/settings.json").read_bytes(), current
        )


def test_claude_owns_exactly_one_settings_and_instruction_destination(
    repo_root: Path, temporary_home: Path
) -> None:
    """Keep Claude settings ownership out of the shared hook adapter."""
    contribution = claude_configuration(
        repo_root=repo_root,
        home=temporary_home,
        profiles=("default",),
        enabled=frozenset({"claude-code"}),
    )
    hooks = hook_contribution(
        repo_root=repo_root,
        home=temporary_home,
        enabled=frozenset({"claude-code"}),
    )
    destinations = [spec.destination for spec in (*contribution.specs, *hooks.specs)]
    assert destinations.count(Path(".claude/settings.json")) == 1
    assert destinations.count(Path(".claude/CLAUDE.md")) == 1
    assert all(spec.method is ApplyMethod.RENDER for spec in contribution.specs)
    assert all(spec.source.is_absolute() for spec in contribution.specs)


def test_instruction_renderer_uses_canonical_guidance_and_claude_suffix(
    repo_root: Path, temporary_home: Path
) -> None:
    """Render canonical engineering and RTK guidance before Claude additions."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    source = (repo_root / "assistants/claude/CLAUDE.md").read_bytes()
    rendered = claude_instruction_renderer(paths)(source, None).decode()
    assert rendered.startswith("# Engineering defaults\n")
    assert "# RTK\n" in rendered
    assert rendered.endswith(
        "Repository instructions take precedence for repository-specific behavior.\n"
        "Do not copy credentials, sessions, project trust, or generated plugin state\n"
        "between machines.\n"
    )


def test_install_then_configure_preserves_plugin_native_state(
    fake_runner: StatefulAssistantFake, repo_root: Path, temporary_home: Path
) -> None:
    """Preserve plugin CLI state created by install before configure runs."""
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
        (repo_root / "assistants/claude/settings.json").read_bytes(),
        settings_path.read_bytes(),
    )
    document = json.loads(rendered)
    assert document["extraKnownMarketplaces"]
    assert set(document["enabledPlugins"]) == fake_runner.claude_plugins


def test_skip_prevents_claude_inspection(
    fake_runner: StatefulAssistantFake, repo_root: Path, temporary_home: Path
) -> None:
    """Return before invoking Claude when its whole component is skipped."""
    setup = _setup().model_copy(update={"skipped": ("claude-code",)})
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    assert install_actions(setup, paths, fake_runner) == ()
    assert fake_runner.commands == []


@pytest.mark.parametrize(
    "payload",
    [
        '{"plugins": [], "plugins": []}',
        '{"plugins": [{"id": "one", "id": "two"}], "marketplaces": []}',
        '{"plugins": [], "marketplaces": [], "unrelated": Infinity}',
    ],
    ids=["top-level", "nested", "non-finite"],
)
def test_native_plugin_inspection_rejects_duplicate_json_keys(
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
    payload: str,
) -> None:
    """Fail closed instead of collapsing ambiguous native JSON objects."""
    fake_runner.add(
        ("claude", "plugin", "list", "--json"), returncode=0, stdout=payload
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    with pytest.raises(
        ClaudePluginInspectionError, match="Claude plugin inspection failed"
    ):
        install_actions(_setup(), paths, fake_runner)
    assert fake_runner.commands == [("claude", "plugin", "list", "--json")]


def test_plugin_catalog_rejects_plugin_profile_outside_marketplace_profile() -> None:
    """Reject catalog entries that could register private sources by default."""
    with pytest.raises(ValueError, match="plugin profiles must be a subset"):
        PluginCatalog.model_validate(
            {
                "marketplaces": [
                    {
                        "name": "private",
                        "source": "git@example:private",
                        "profiles": ["work"],
                    }
                ],
                "plugins": [
                    {
                        "id": "plugin@private",
                        "marketplace": "private",
                        "profiles": ["default"],
                    }
                ],
            }
        )


def test_plan_selects_only_active_marketplaces(tmp_path: Path) -> None:
    """Omit inactive marketplace sources even when no plugin is selected."""
    catalog_path = tmp_path / "plugins.yaml"
    catalog_path.write_text(
        "marketplaces:\n"
        "  - name: private\n"
        "    source: git@example:private\n"
        "    profiles: [work]\n"
        "plugins: []\n"
    )
    assert (
        plan_claude_plugins(catalog_path, profiles=("default",), installed=frozenset())
        == ()
    )


def test_inventory_has_one_claude_owner_per_native_resource(repo_root: Path) -> None:
    """Synchronize inventory with the reviewed Claude adapter surface."""
    inventory = load_inventory(repo_root / "assistants/inventory.yaml", repo_root)
    resources = [
        resource
        for resource in inventory.resources
        if isinstance(resource, FileResource)
    ]
    destinations = [resource.destination.as_posix() for resource in resources]
    assert destinations.count(".claude/settings.json") == 1
    assert destinations.count(".claude/CLAUDE.md") == 1
