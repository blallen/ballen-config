"""Tests for portable Cursor settings and extension management."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from ballen_config import assistants as assistant_api
from ballen_config.assistants.cursor import (
    ExtensionState,
    configuration,
    deep_merge,
    install_actions,
    plan_cursor_extension_actions,
    read_bundled_extensions,
    render_settings,
    resolve_extensions,
)
from ballen_config.assistants.instructions import render_native_instructions
from ballen_config.assistants.inventory import load_inventory
from ballen_config.assistants.models import (
    CatalogResource,
    ExtensionCatalog,
    ExtensionSpec,
    FileResource,
    ManualResource,
)
from ballen_config.configure import (
    ApplyMethod,
    ConfigurationContribution,
    ManagedFileSpec,
)
from ballen_config.install import InstallAction, Installer
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.runtime import RuntimePaths
from tests.assistants.fakes import StatefulAssistantFake

_EXTENSION_IDS = (
    "adamviola.parquet-explorer",
    "anthropic.claude-code",
    "anysphere.remote-containers",
    "anysphere.remote-ssh",
    "bierner.markdown-mermaid",
    "bierner.markdown-preview-github-styles",
    "charliermarsh.ruff",
    "davidanson.vscode-markdownlint",
    "esbenp.prettier-vscode",
    "humao.rest-client",
    "jjk.jjk",
    "matangover.mypy",
    "mhutchie.git-graph",
    "ms-azuretools.vscode-docker",
    "ms-python.python",
    "ms-toolsai.jupyter",
    "ms-vscode.atom-keybindings",
    "ms-vscode.makefile-tools",
    "openai.chatgpt",
    "redhat.vscode-yaml",
    "samuelcolvin.jinjahtml",
    "shd101wyy.markdown-preview-enhanced",
    "tamasfe.even-better-toml",
    "tomoki1207.pdf",
    "visualjj.visualjj",
    "velociraptor115.vscode-jj-graph",
)
_JJ_GRAPH_URL = (
    "https://Velociraptor115.gallery.vsassets.io/_apis/public/gallery/"
    "publisher/Velociraptor115/extension/vscode-jj-graph/0.0.9/"
    "assetbyname/Microsoft.VisualStudio.Services.VSIXPackage"
)
_JJ_GRAPH_SHA256 = "a822f2e2afd644aa22c64e1caec5e62dd8fb896ada30028f831ce28068570ace"  # pragma: allowlist secret


def _resolved_setup(
    *enabled: str,
    profiles: tuple[str, ...] = ("default",),
    skipped: tuple[str, ...] = (),
) -> ResolvedSetup:
    """Build a minimal selected-agent setup."""
    return ResolvedSetup(
        profiles=profiles,
        components=tuple(
            Component(id=item, manager=Manager.BREW_CASK, package=item)
            for item in enabled
        ),
        skipped=skipped,
    )


@pytest.fixture
def cursor_source_repo(tmp_path: Path) -> Path:
    """Create minimal reviewed Cursor configuration sources."""
    repo = tmp_path / "repo"
    cursor_root = repo / "assistants/cursor"
    shared_root = repo / "assistants/shared/instructions"
    cursor_root.mkdir(parents=True)
    shared_root.mkdir(parents=True)
    (cursor_root / "settings.base.json").write_text("{}\n")
    (cursor_root / "settings.work.json").write_text("{}\n")
    (cursor_root / "keybindings.json").write_text("[]\n")
    (cursor_root / "user-rules.md").write_text("# Cursor additions\n")
    (shared_root / "engineering.md").write_text("# Engineering\n")
    (shared_root / "rtk.md").write_text("# RTK\n")
    return repo


def test_default_settings_exactly_match_reviewed_base(repo_root: Path) -> None:
    """Keep work-only Claude environment out of the default profile."""
    rendered = render_settings(repo_root, profiles=("default",))
    base = json.loads((repo_root / "assistants/cursor/settings.base.json").read_text())
    assert rendered == base
    assert "claudeCode.environmentVariables" not in rendered


def test_work_settings_add_only_reviewed_bedrock_overlay(repo_root: Path) -> None:
    """Overlay exactly the reviewed work-only Claude environment."""
    rendered = render_settings(repo_root, profiles=("default", "work"))
    base = render_settings(repo_root, profiles=("default",))
    assert rendered == {
        **base,
        "claudeCode.environmentVariables": [
            "CLAUDE_CODE_USE_BEDROCK=1",
            "AWS_REGION=us-east-1",
        ],
    }


def test_deep_merge_replaces_lists_and_merges_objects() -> None:
    """Give overlays deterministic JSON merge semantics."""
    assert deep_merge(
        {"editor": {"fontSize": 13, "rulers": [88]}, "theme": "A"},
        {"editor": {"rulers": [100]}},
    ) == {
        "editor": {"fontSize": 13, "rulers": [100]},
        "theme": "A",
    }


def test_keybindings_preserve_the_reviewed_bindings(repo_root: Path) -> None:
    """Keep every reviewed binding while making the source strict JSON."""
    document = json.loads(
        (repo_root / "assistants/cursor/keybindings.json").read_text()
    )
    assert document == [
        {
            "key": "cmd+\\",
            "command": "-workbench.action.toggleSidebarVisibility",
        },
        {
            "key": "cmd+b",
            "command": "-workbench.action.quickOpenNavigateNext",
            "when": "inQuickOpen",
        },
        {
            "key": "cmd+b",
            "command": "-workbench.action.showAllEditors",
        },
        {
            "key": "cmd+i",
            "command": "composerMode.agent",
        },
        {
            "key": "shift+enter",
            "command": "workbench.action.terminal.sendSequence",
            "args": {"text": "\u001b\r"},
            "when": "terminalFocus",
        },
    ]


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("settings.base.json", "[]\n", "settings base must be a JSON object"),
        (
            "settings.work.json",
            "[]\n",
            "settings work overlay must be a JSON object",
        ),
        ("keybindings.json", "{}\n", "keybindings must be a JSON array"),
        ("settings.base.json", "{\n", "invalid Cursor settings base JSON"),
        (
            "settings.work.json",
            "{\n",
            "invalid Cursor settings work overlay JSON",
        ),
        ("keybindings.json", "[\n", "invalid Cursor keybindings JSON"),
    ],
)
def test_configuration_validates_every_json_source_before_specs(
    cursor_source_repo: Path,
    temporary_home: Path,
    filename: str,
    content: str,
    message: str,
) -> None:
    """Reject malformed or incorrectly shaped sources before actions exist."""
    source = cursor_source_repo / "assistants/cursor" / filename
    source.write_text(content)
    paths = RuntimePaths.from_roots(
        repo_root=cursor_source_repo,
        home=temporary_home,
    )

    with pytest.raises(ValueError, match=message):
        configuration(_resolved_setup("cursor"), paths)


@pytest.mark.parametrize(
    ("profiles", "expected_environment"),
    [
        (("default",), None),
        (
            ("default", "work"),
            [
                "CLAUDE_CODE_USE_BEDROCK=1",
                "AWS_REGION=us-east-1",
            ],
        ),
    ],
)
def test_configuration_emits_one_profile_aware_settings_spec(
    repo_root: Path,
    temporary_home: Path,
    profiles: tuple[str, ...],
    expected_environment: list[str] | None,
) -> None:
    """Render one settings destination for default and expanded work setups."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    contribution = configuration(
        _resolved_setup("cursor", profiles=profiles),
        paths,
    )
    settings_specs = [
        spec
        for spec in contribution.specs
        if isinstance(spec, ManagedFileSpec)
        and spec.destination
        == Path("Library/Application Support/Cursor/User/settings.json")
    ]
    assert len(settings_specs) == 1
    settings = settings_specs[0]
    assert settings.id == "cursor-settings"
    assert settings.method is ApplyMethod.RENDER
    assert settings.renderer_id == "cursor-settings"
    rendered = json.loads(
        contribution.renderers["cursor-settings"](settings.source.read_bytes(), None)
    )
    if expected_environment is None:
        assert "claudeCode.environmentVariables" not in rendered
    else:
        assert rendered["claudeCode.environmentVariables"] == expected_environment


def test_renderers_preserve_unrelated_cursor_native_state(
    repo_root: Path, temporary_home: Path
) -> None:
    """Rendered settings and keybindings retain unrelated local preferences."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    contribution = configuration(_resolved_setup("cursor"), paths)
    specs = {spec.id: spec for spec in contribution.specs}
    settings = json.loads(
        contribution.renderers["cursor-settings"](
            specs["cursor-settings"].source.read_bytes(),
            b'{"native":{"keep":true}}',
        )
    )
    bindings = json.loads(
        contribution.renderers["cursor-keybindings"](
            specs["cursor-keybindings"].source.read_bytes(),
            b'[{"key":"cmd+x","command":"native.keep"}]',
        )
    )

    assert settings["native"] == {"keep": True}
    assert {item["command"] for item in bindings} >= {
        "native.keep",
        "composerMode.agent",
    }


def test_keybindings_renderer_preserves_same_command_on_other_shortcut(
    repo_root: Path, temporary_home: Path
) -> None:
    """Replace reviewed bindings only when their shortcut and context match."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    contribution = configuration(_resolved_setup("cursor"), paths)
    source = {spec.id: spec for spec in contribution.specs}["cursor-keybindings"].source
    renderer = contribution.renderers["cursor-keybindings"]
    native = b"""[
      {"key": "cmd+k", "command": "composerMode.agent"},
      {"key": "cmd+i", "command": "native.replaced"}
    ]"""

    rendered = json.loads(renderer(source.read_bytes(), native))

    assert [item for item in rendered if item["key"] == "cmd+k"] == [
        {"key": "cmd+k", "command": "composerMode.agent"}
    ]
    assert [item for item in rendered if item["key"] == "cmd+i"] == [
        {"key": "cmd+i", "command": "composerMode.agent"}
    ]


def test_configuration_uses_relative_private_core_safe_specs(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Own settings, keybindings, and manual rules through core primitives."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    contribution = configuration(_resolved_setup("cursor"), paths)
    by_id = {
        spec.id: spec
        for spec in contribution.specs
        if isinstance(spec, ManagedFileSpec)
    }

    assert len(by_id) == len(contribution.specs)
    assert set(by_id) == {
        "cursor-settings",
        "cursor-keybindings",
        "cursor-user-rules",
    }
    assert {item.id: item.destination for item in contribution.specs} == {
        "cursor-settings": Path(
            "Library/Application Support/Cursor/User/settings.json"
        ),
        "cursor-keybindings": Path(
            "Library/Application Support/Cursor/User/keybindings.json"
        ),
        "cursor-user-rules": Path(
            ".local/state/ballen-config/manual/cursor-user-rules.md"
        ),
    }
    assert all(not spec.destination.is_absolute() for spec in contribution.specs)
    assert all(spec.source.is_absolute() for spec in contribution.specs)
    assert all(
        spec.source.is_relative_to(repo_root.resolve()) for spec in contribution.specs
    )
    assert all(spec.component == "cursor" for spec in contribution.specs)
    assert all(spec.mode == 0o600 for spec in by_id.values())
    assert by_id["cursor-keybindings"].method is ApplyMethod.RENDER
    assert by_id["cursor-user-rules"].method is ApplyMethod.RENDER
    assert all(
        spec.destination != Path(".cursor/hooks.json") for spec in by_id.values()
    )


def test_rendered_user_rules_are_canonical_and_manual_only(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Render canonical guidance and reviewed Cursor-specific safety rules."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    contribution = configuration(_resolved_setup("cursor"), paths)
    spec = next(item for item in contribution.specs if item.id == "cursor-user-rules")
    suffix = spec.source.read_text()
    engineering = (
        repo_root / "assistants/shared/instructions/engineering.md"
    ).read_text()
    rtk = (repo_root / "assistants/shared/instructions/rtk.md").read_text()
    rendered = contribution.renderers["cursor-user-rules"](
        spec.source.read_bytes(),
        None,
    ).decode()

    assert rendered == render_native_instructions(
        engineering=engineering,
        rtk=rtk,
        agent_suffix=suffix,
    )
    normalized = " ".join(rendered.split())
    assert "Repository instructions take precedence" in normalized
    assert "first-party browser capability" in normalized
    assert "global Playwright MCP server" in normalized
    assert "`glab` for GitLab" in normalized
    assert "official Notion integration" in normalized
    assert (
        "authentication, history, worktrees, indexes, caches, or generated plugin state"
        in normalized
    )
    assert "plugins/cache/" not in rendered
    assert "{{" not in rendered
    assert spec.destination == Path(
        ".local/state/ballen-config/manual/cursor-user-rules.md"
    )


def test_skipped_cursor_returns_before_configuration_inspection(
    tmp_path: Path,
    temporary_home: Path,
) -> None:
    """Avoid reading absent Cursor configuration when the agent is skipped."""
    paths = RuntimePaths.from_roots(
        repo_root=tmp_path / "absent-repo",
        home=temporary_home,
    )
    assert (
        configuration(
            _resolved_setup("codex", skipped=("cursor",)),
            paths,
        )
        == ConfigurationContribution()
    )


def test_extension_catalog_is_exact_ordered_and_gallery_entries_are_unpinned(
    repo_root: Path,
) -> None:
    """Keep the curated feature catalog ordered and gallery installs floating."""
    path = repo_root / "assistants/cursor/extensions.yaml"
    catalog = ExtensionCatalog.model_validate(yaml.safe_load(path.read_text()))

    assert tuple(item.id for item in catalog.extensions) == _EXTENSION_IDS
    gallery = tuple(
        item for item in catalog.extensions if item.install_mode == "gallery"
    )
    assert all(item.version is None for item in gallery)
    assert all(item.size_bytes is None for item in gallery)
    assert all(item.url is None for item in gallery)
    assert all(item.sha256 is None for item in gallery)
    jj_graph = catalog.extensions[-1]
    assert jj_graph.id == "velociraptor115.vscode-jj-graph"
    assert jj_graph.install_mode == "vsix"
    assert jj_graph.required is False
    assert jj_graph.version == "0.0.9"
    assert jj_graph.size_bytes == 10_291_769
    assert jj_graph.url == _JJ_GRAPH_URL
    assert jj_graph.sha256 == _JJ_GRAPH_SHA256


def test_agent_extensions_follow_enabled_claude_and_codex(
    repo_root: Path,
) -> None:
    """Install assistant extensions only when that assistant is enabled."""
    path = repo_root / "assistants/cursor/extensions.yaml"
    without_agents = resolve_extensions(
        path,
        enabled_agents=frozenset({"cursor"}),
        installed=frozenset(),
        bundled=frozenset(),
    )
    assert "anthropic.claude-code" not in without_agents.missing
    assert "openai.chatgpt" not in without_agents.missing
    assert without_agents.skipped_condition == (
        "anthropic.claude-code",
        "openai.chatgpt",
    )

    with_agents = resolve_extensions(
        path,
        enabled_agents=frozenset({"cursor", "claude-code", "codex"}),
        installed=frozenset(),
        bundled=frozenset(),
    )
    assert "anthropic.claude-code" in with_agents.missing
    assert "openai.chatgpt" in with_agents.missing
    assert with_agents.skipped_condition == ()


def test_bundled_extension_satisfies_desired_feature(repo_root: Path) -> None:
    """Avoid reinstalling a feature already bundled with Cursor."""
    state = resolve_extensions(
        repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=frozenset({"cursor"}),
        installed=frozenset(),
        bundled=frozenset({"ms-python.python"}),
    )
    assert state.bundled == frozenset({"ms-python.python"})
    assert "ms-python.python" not in state.missing


def test_bundled_manifest_ids_are_normalized(tmp_path: Path) -> None:
    """Read lowercase publisher.name IDs from Cursor package manifests."""
    manifest = tmp_path / "extensions/python/package.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"publisher":"MS-Python","name":"Python"}')
    assert read_bundled_extensions(tmp_path / "extensions") == frozenset(
        {"ms-python.python"}
    )


def test_obsolete_and_transitive_extensions_are_excluded(repo_root: Path) -> None:
    """Keep the curated list feature-level and Cursor-native."""
    catalog = ExtensionCatalog.model_validate(
        yaml.safe_load((repo_root / "assistants/cursor/extensions.yaml").read_text())
    )
    declared = {item.id for item in catalog.extensions}
    forbidden = {
        "gitlab.gitlab-workflow",
        "anysphere.cursorpyright",
        "ms-azuretools.vscode-containers",
        "ms-python.debugpy",
        "ms-toolsai.jupyter-keymap",
        "ms-toolsai.jupyter-renderers",
        "ms-toolsai.vscode-jupyter-cell-tags",
        "ms-toolsai.vscode-jupyter-slideshow",
        "ms-vscode-remote.remote-ssh",
        "ms-vscode.remote-explorer",
    }
    assert declared.isdisjoint(forbidden)


def test_gallery_action_uses_exact_extension_id(repo_root: Path) -> None:
    """Install gallery entries without version locking."""
    actions = plan_cursor_extension_actions(
        repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=frozenset({"cursor"}),
        installed=frozenset(),
        bundled=frozenset(),
    )
    markdown = next(
        action
        for action in actions
        if action.component_id == "cursor.extension.bierner.markdown-mermaid"
    )
    assert markdown == InstallAction(
        component_id="cursor.extension.bierner.markdown-mermaid",
        argv=(
            "cursor",
            "--install-extension",
            "bierner.markdown-mermaid",
        ),
    )


def test_jj_graph_action_uses_exact_optional_verified_download(
    repo_root: Path,
) -> None:
    """Delegate the audited optional VSIX entirely to the core installer."""
    action = next(
        item
        for item in plan_cursor_extension_actions(
            repo_root / "assistants/cursor/extensions.yaml",
            enabled_agents=frozenset({"cursor"}),
            installed=frozenset(),
            bundled=frozenset(),
        )
        if item.component_id == "cursor.extension.velociraptor115.vscode-jj-graph"
    )
    assert action == InstallAction(
        component_id="cursor.extension.velociraptor115.vscode-jj-graph",
        kind="verified-download",
        argv=("cursor", "--install-extension", "{artifact}"),
        required=False,
        url=_JJ_GRAPH_URL,
        artifact_name="vscode-jj-graph.vsix",
        size_bytes=10_291_769,
        sha256=_JJ_GRAPH_SHA256,
    )


def test_vsix_fake_download_installs_and_core_cleans_up(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
    tmp_path: Path,
) -> None:
    """Exercise verified download, install, and cleanup without network access."""
    payload = b"fixture-vsix-bytes"
    url = "https://example.invalid/vscode-jj-graph-0.0.9.vsix"
    catalog_path = tmp_path / "extensions.yaml"
    catalog_path.write_text(
        "extensions:\n"
        "  - id: velociraptor115.vscode-jj-graph\n"
        "    install_mode: vsix\n"
        "    required: false\n"
        "    version: 0.0.9\n"
        f"    size_bytes: {len(payload)}\n"
        f"    url: {url}\n"
        f"    sha256: {sha256(payload).hexdigest()}\n"
    )
    fake_runner.add_vsix(
        url=url,
        payload=payload,
        extension_id="velociraptor115.vscode-jj-graph",
    )
    action = plan_cursor_extension_actions(
        catalog_path,
        enabled_agents=frozenset({"cursor"}),
        installed=frozenset(),
        bundled=frozenset(),
    )[0]

    outcome = Installer(
        fake_runner,
        temporary_home,
        downloader=fake_runner,
        private_temp_root=temporary_home / ".local/state/test-tmp",
    ).run_action(action)

    assert outcome.state == "installed"
    assert "velociraptor115.vscode-jj-graph" in fake_runner.cursor_extensions
    assert fake_runner.downloads
    assert not fake_runner.downloads[0][1].exists()


def test_extension_resolution_reports_independent_deterministic_sets(
    repo_root: Path,
) -> None:
    """Keep installed, bundled, skipped, missing, and extra states distinct."""
    installed = frozenset(
        {
            "bierner.markdown-mermaid",
            "unmanaged.extra",
        }
    )
    bundled = frozenset({"ms-python.python"})
    state = resolve_extensions(
        repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=frozenset({"cursor"}),
        installed=installed,
        bundled=bundled,
    )

    assert state == ExtensionState(
        installed=installed,
        bundled=bundled,
        missing=tuple(
            sorted(
                set(_EXTENSION_IDS)
                - installed
                - bundled
                - {
                    "anthropic.claude-code",
                    "openai.chatgpt",
                }
            )
        ),
        skipped_condition=(
            "anthropic.claude-code",
            "openai.chatgpt",
        ),
        unmanaged_extra=("unmanaged.extra",),
    )


def test_unmanaged_extensions_are_diagnostic_only(repo_root: Path) -> None:
    """Never produce removal actions for extensions outside the catalog."""
    actions = plan_cursor_extension_actions(
        repo_root / "assistants/cursor/extensions.yaml",
        enabled_agents=frozenset({"cursor"}),
        installed=frozenset({"unmanaged.extra"}),
        bundled=frozenset(),
    )
    assert all("unmanaged.extra" not in action.argv for action in actions)
    assert all("--uninstall-extension" not in action.argv for action in actions)


def test_skipped_cursor_returns_before_native_or_bundled_inspection(
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
    tmp_path: Path,
) -> None:
    """Avoid CLI, packaged-extension, and catalog reads when Cursor is skipped."""
    paths = RuntimePaths.from_roots(
        repo_root=tmp_path / "absent-repo",
        home=temporary_home,
    )
    actions = install_actions(
        _resolved_setup("codex", skipped=("cursor",)),
        paths,
        fake_runner,
        bundled_root=tmp_path / "must-not-be-read",
    )
    assert actions == ()
    assert fake_runner.commands == []


def test_failed_cursor_extension_inspection_never_plans_installs(
    repo_root: Path,
    fake_runner: StatefulAssistantFake,
    temporary_home: Path,
    tmp_path: Path,
) -> None:
    """Fail closed without exposing native output or producing install actions."""
    command = ("cursor", "--list-extensions")
    fake_runner.add(
        command,
        returncode=1,
        stdout="sensitive stdout",
        stderr="sensitive stderr",
    )
    paths = RuntimePaths.from_roots(
        repo_root=repo_root,
        home=temporary_home,
    )

    with pytest.raises(
        RuntimeError,
        match=r"^Cursor extension inspection failed$",
    ) as error:
        install_actions(
            _resolved_setup("cursor"),
            paths,
            fake_runner,
            bundled_root=tmp_path / "must-not-be-read",
        )

    assert str(error.value) == "Cursor extension inspection failed"
    assert "sensitive" not in str(error.value)
    assert fake_runner.commands == [command]
    assert fake_runner.downloads == []


@pytest.mark.parametrize(
    "identifier",
    [
        "missing-dot",
        "Publisher.extension",
        "publisher.Extension",
        ".extension",
        "publisher.",
        "publisher.extension.extra",
        "publisher/extension",
        "publisher_name.extension",
    ],
)
def test_extension_spec_rejects_non_normalized_identifiers(
    identifier: str,
) -> None:
    """Require lowercase publisher.name extension identifiers."""
    with pytest.raises(ValueError):
        ExtensionSpec(id=identifier)


def test_extension_spec_rejects_unknown_agent_condition() -> None:
    """Limit extension conditions to supported coding-agent identifiers."""
    with pytest.raises(ValueError):
        ExtensionSpec.model_validate(
            {
                "id": "publisher.extension",
                "condition": "unknown-agent",
            }
        )


def test_inventory_is_synchronized_with_cursor_sources_and_catalog(
    repo_root: Path,
) -> None:
    """Keep portable resource declarations aligned with reviewed sources."""
    inventory = load_inventory(
        repo_root / "assistants/inventory.yaml",
        repo_root,
    )
    by_id = {resource.id: resource for resource in inventory.resources}

    settings = by_id["cursor.settings"]
    work = by_id["cursor.settings.work"]
    keybindings = by_id["cursor.keybindings"]
    rules = by_id["cursor.user-rules"]
    extensions = by_id["cursor.extensions.catalog"]
    assert isinstance(settings, FileResource)
    assert settings.role == "render-source"
    assert isinstance(work, FileResource)
    assert work.role == "overlay"
    assert work.profiles == ("work",)
    assert work.destination == settings.destination
    assert isinstance(keybindings, FileResource)
    assert isinstance(rules, ManualResource)
    assert rules.source is not None
    assert isinstance(extensions, CatalogResource)
    assert extensions.item_ids == _EXTENSION_IDS


def test_cursor_adapter_is_publicly_exported() -> None:
    """Expose typed Cursor suppliers and resolution helpers."""
    assert assistant_api.ExtensionState is ExtensionState
    assert assistant_api.cursor_configuration is configuration
    assert assistant_api.cursor_install_actions is install_actions
