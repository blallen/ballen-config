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
from ballen_config.assistants.desired_state import (
    PluginCatalogProjection,
    project_plugin_catalog,
)
from ballen_config.assistants.hooks import hook_contribution
from ballen_config.assistants.inventory import load_inventory
from ballen_config.assistants.models import AgentName, FileResource, PluginCatalog
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


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(b'{"model":"first","model":"second"}', id="duplicate-key"),
        pytest.param(b'{"model":NaN}', id="non-finite"),
    ],
)
def test_stable_settings_reject_ambiguous_json(tmp_path: Path, source: bytes) -> None:
    """Reject reviewed settings whose JSON has ambiguous value semantics."""
    path = tmp_path / "settings.json"
    path.write_bytes(source)

    with pytest.raises(ClaudeSettingsError, match="invalid Claude settings"):
        load_stable_settings(path)


def test_plugin_actions_are_scoped_ordered_and_profile_independent(
    claude_projection: PluginCatalogProjection,
) -> None:
    """Plan the same ordered native actions for each supported profile."""
    default_actions = plan_claude_plugins(
        claude_projection,
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
        "bigspinai/toolkit",
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
        claude_projection,
        installed=frozenset(),
    )
    assert work_actions == default_actions


def test_plugin_planner_uses_the_preprojected_catalog() -> None:
    """Preserve requiredness after projection selects active native entries."""
    catalog = PluginCatalog.model_validate(
        {
            "marketplaces": [
                {
                    "name": "work-marketplace",
                    "source": "example/work",
                    "targets": ["claude-code"],
                    "profiles": ["work"],
                }
            ],
            "plugins": [
                {
                    "kind": "native-marketplace",
                    "id": "work-plugin@work-marketplace",
                    "marketplace": "work-marketplace",
                    "targets": ["claude-code"],
                    "profiles": ["work"],
                    "required": False,
                }
            ],
        }
    )
    projection = project_plugin_catalog(
        catalog, target=AgentName.CLAUDE, profiles=("default", "work")
    )

    actions = plan_claude_plugins(projection, installed=frozenset())

    assert [action.component_id for action in actions] == [
        "claude.marketplace.work-marketplace",
        "claude.plugin.work-plugin@work-marketplace",
    ]
    assert all(not action.required for action in actions)


def test_registered_native_entries_are_noops(
    claude_projection: PluginCatalogProjection,
) -> None:
    """Avoid installing already registered native marketplaces and plugins."""
    actions = plan_claude_plugins(
        claude_projection,
        installed=frozenset({"frontend-design@claude-plugins-official"}),
        known_marketplaces=frozenset({"claude-plugins-official"}),
    )
    ids = {action.component_id for action in actions}
    assert "claude.marketplace.claude-plugins-official" not in ids
    assert "claude.plugin.frontend-design@claude-plugins-official" not in ids


def test_native_array_inspection_uses_user_scoped_plugins_and_marketplaces(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
    claude_projection: PluginCatalogProjection,
) -> None:
    """Read Claude's separate native plugin and marketplace array responses."""
    fake_runner.add(
        ("claude", "plugin", "list", "--json"),
        returncode=0,
        stdout=json.dumps(
            [
                {
                    "id": "frontend-design@claude-plugins-official",
                    "version": "1.0.0",
                    "scope": "user",
                    "enabled": True,
                    "installPath": "/Users/test/.claude/plugins/frontend-design",
                }
            ]
        ),
    )
    fake_runner.add(
        ("claude", "plugin", "marketplace", "list", "--json"),
        returncode=0,
        stdout=json.dumps(
            [
                {
                    "name": "claude-plugins-official",
                    "source": "anthropics/claude-plugins-official",
                }
            ]
        ),
    )

    actions = install_actions(
        _setup(),
        claude_projection,
        fake_runner,
    )

    ids = {action.component_id for action in actions}
    assert "claude.marketplace.claude-plugins-official" not in ids
    assert "claude.plugin.frontend-design@claude-plugins-official" not in ids
    assert fake_runner.commands == [
        ("claude", "plugin", "list", "--json"),
        ("claude", "plugin", "marketplace", "list", "--json"),
    ]


def test_project_scoped_native_plugin_does_not_satisfy_user_install(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
    claude_projection: PluginCatalogProjection,
) -> None:
    """Plan a user install when the native plugin only has project scope."""
    fake_runner.add(
        ("claude", "plugin", "list", "--json"),
        returncode=0,
        stdout=json.dumps(
            [
                {
                    "id": "frontend-design@claude-plugins-official",
                    "version": "1.0.0",
                    "scope": "project",
                    "enabled": True,
                    "installPath": "/repo/.claude/plugins/frontend-design",
                }
            ]
        ),
    )
    fake_runner.add(
        ("claude", "plugin", "marketplace", "list", "--json"),
        returncode=0,
        stdout='[{"name": "claude-plugins-official"}]',
    )

    actions = install_actions(
        _setup(),
        claude_projection,
        fake_runner,
    )

    assert "claude.plugin.frontend-design@claude-plugins-official" in {
        action.component_id for action in actions
    }


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [
        pytest.param(1, "", id="command-failure"),
        pytest.param(0, '[{"source": "missing-name"}]', id="malformed-payload"),
    ],
)
def test_native_marketplace_inspection_fails_closed(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
    claude_projection: PluginCatalogProjection,
    returncode: int,
    stdout: str,
) -> None:
    """Normalize unavailable or malformed marketplace responses."""
    fake_runner.add(
        ("claude", "plugin", "list", "--json"),
        returncode=0,
        stdout='[{"id": "frontend-design@claude-plugins-official", "scope": "user"}]',
    )
    fake_runner.add(
        ("claude", "plugin", "marketplace", "list", "--json"),
        returncode=returncode,
        stdout=stdout,
    )

    with pytest.raises(
        ClaudePluginInspectionError, match="Claude plugin inspection failed"
    ):
        install_actions(
            _setup(),
            claude_projection,
            fake_runner,
        )


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


@pytest.mark.parametrize(
    "current",
    [
        pytest.param(b"[1]", id="array"),
        pytest.param(b"{", id="truncated-object"),
        pytest.param(b'{"effortLevel": NaN}', id="non-finite"),
    ],
)
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
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    temporary_home: Path,
    claude_projection: PluginCatalogProjection,
) -> None:
    """Preserve plugin CLI state created by install before configure runs."""
    actions = plan_claude_plugins(
        claude_projection,
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
    fake_runner: StatefulAssistantFake,
    claude_projection: PluginCatalogProjection,
) -> None:
    """Return before invoking Claude when its whole component is skipped."""
    setup = _setup().model_copy(update={"skipped": ("claude-code",)})
    assert install_actions(setup, claude_projection, fake_runner) == ()
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
    temporary_home: Path,
    claude_projection: PluginCatalogProjection,
    payload: str,
) -> None:
    """Fail closed instead of collapsing ambiguous native JSON objects."""
    fake_runner.add(
        ("claude", "plugin", "list", "--json"), returncode=0, stdout=payload
    )
    with pytest.raises(
        ClaudePluginInspectionError, match="Claude plugin inspection failed"
    ):
        install_actions(_setup(), claude_projection, fake_runner)
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
                        "targets": ["claude-code"],
                    }
                ],
                "plugins": [
                    {
                        "kind": "native-marketplace",
                        "id": "plugin@private",
                        "marketplace": "private",
                        "profiles": ["default"],
                        "targets": ["claude-code"],
                    }
                ],
            }
        )


def test_planner_rejects_a_projection_for_another_agent() -> None:
    """Keep native command ownership aligned with the concrete target."""
    projection = PluginCatalogProjection(
        target=AgentName.CODEX,
        marketplaces=(),
        native_plugins=(),
        cursor_marketplace_plugins=(),
        cursor_local_plugins=(),
    )
    with pytest.raises(ValueError, match="target claude-code"):
        plan_claude_plugins(projection, installed=frozenset())


def test_inventory_has_one_claude_owner_per_native_resource(repo_root: Path) -> None:
    """Synchronize inventory with the reviewed Claude adapter surface."""
    inventory = load_inventory(
        repo_root / "assistants/inventory.yaml", repo_root
    ).inventory
    resources = [
        resource
        for resource in inventory.resources
        if isinstance(resource, FileResource)
    ]
    destinations = [resource.destination.as_posix() for resource in resources]
    assert destinations.count(".claude/settings.json") == 1
    assert destinations.count(".claude/CLAUDE.md") == 1
