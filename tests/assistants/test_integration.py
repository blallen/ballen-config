"""Integration tests for the aggregate coding-agent extension seams."""

import json
import shutil
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, TypedDict

import pytest
import yaml

import ballen_config.cli as cli
from ballen_config.assistants import AssistantOrchestrator
from ballen_config.assistants.claude import ClaudePluginInspectionError
from ballen_config.cli import RunResult, main, run
from ballen_config.install import InstallAction, InstallStageReport
from ballen_config.manifests import ManifestRepository
from ballen_config.models import Manager, ResolutionRequest
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore
from tests.assistants.conftest import (
    CursorLocalPluginFixture,
    CursorLocalPluginRepoFactory,
)
from tests.assistants.fakes import StatefulAssistantFake


class SentinelSnapshot(TypedDict):
    """One immutable observation of an excluded-state sentinel."""

    kind: Literal["directory", "file"]
    mode: int
    data: bytes | None


def snapshot_sentinels(
    home: Path, paths: Sequence[Path]
) -> dict[Path, SentinelSnapshot]:
    """Capture explicit sentinel paths without following or inferring state.

    Args:
        home: Isolated fake home containing the sentinel paths.
        paths: Relative paths whose exact file or directory state is observed.

    Returns:
        Relative-path snapshots including kind, mode, and file bytes.
    """
    snapshots: dict[Path, SentinelSnapshot] = {}
    for relative_path in paths:
        path = home / relative_path
        metadata = path.stat()
        snapshots[relative_path] = {
            "kind": "directory" if path.is_dir() else "file",
            "mode": stat.S_IMODE(metadata.st_mode),
            "data": None if path.is_dir() else path.read_bytes(),
        }
    return snapshots


def run_with_assistants(
    arguments: Sequence[str],
    *,
    repo_root: Path,
    home: Path,
    runner: StatefulAssistantFake,
    output: list[str] | None = None,
) -> RunResult:
    """Run the real aggregate wiring with deterministic external boundaries.

    Args:
        arguments: Bootstrap command and component selection arguments.
        repo_root: Repository containing production manifests and resources.
        home: Isolated fake home directory.
        runner: Stateful native command and downloader fake.
        output: Optional sink for rendered plan and doctor output.

    Returns:
        Result returned by the production core CLI function.
    """
    runner.satisfy_core_commands()
    profile = "default"
    if "--profile" in arguments:
        profile = arguments[arguments.index("--profile") + 1]
    resolved = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile=profile)
    )
    for component in resolved.components:
        if component.manager is Manager.GIT:
            assert component.destination is not None
            assert component.revision is not None
            runner.add_git_checkout(
                home / component.destination,
                origin=component.package,
                revision=component.revision,
            )
        elif component.manager is Manager.UV_TOOL:
            runner.add_uv_tool(component.package)
    runner.cursor_extensions.update(
        {
            "velociraptor115.vscode-jj-graph",
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
        }
    )
    messages = output if output is not None else []
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=home)
    assistants = AssistantOrchestrator(paths)
    return run(
        arguments,
        repo_root=repo_root,
        home=home,
        runner=runner,
        downloader=runner,
        confirm=lambda _prompt: True,
        output=messages.append,
        timestamp=lambda: "20260726T120000Z",
        preflight_suppliers=(assistants.preflight,),
        install_action_candidate_suppliers=(assistants.install_action_candidates,),
        install_action_suppliers=(assistants.install_actions,),
        configuration_suppliers=(assistants.configuration,),
        doctor_check_suppliers=(assistants.doctor_checks,),
        plan_contributors=(assistants,),
    )


def _copy_checkout(repo_root: Path, destination: Path) -> Path:
    """Copy one checkout without runtime and source-control state."""
    shutil.copytree(
        repo_root,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            ".jj",
            ".venv",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
            "__pycache__",
        ),
    )
    return destination


@pytest.fixture
def cursor_marketplace_repo(repo_root: Path, tmp_path: Path) -> Path:
    """Copy the checkout with one explicit manual Cursor marketplace plugin."""
    copied = _copy_checkout(repo_root, tmp_path / "cursor-marketplace")
    catalog_path = copied / "assistants/shared/plugins/catalog.yaml"
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    payload["plugins"].append(
        {
            "kind": "cursor-marketplace",
            "id": "example-plugin",
            "targets": ["cursor"],
            "profiles": ["default"],
            "required": True,
            "scope": "user",
            "verification": "manual",
        }
    )
    catalog_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return copied


@pytest.fixture
def cursor_local_plugin_repo(
    cursor_local_plugin_repo_factory: CursorLocalPluginRepoFactory,
) -> Path:
    """Copy the checkout with one reviewed native Cursor local plugin."""
    return cursor_local_plugin_repo_factory(
        (CursorLocalPluginFixture(id="example-local"),)
    )


@pytest.fixture
def invalid_cursor_local_plugin_repo(
    cursor_local_plugin_repo_factory: CursorLocalPluginRepoFactory,
) -> Path:
    """Copy the checkout with a valid declaration and mismatched local tree."""
    return cursor_local_plugin_repo_factory(
        (
            CursorLocalPluginFixture(
                id="example-local",
                manifest_name="different-name",
            ),
        )
    )


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(("plan",), id="plan"),
        pytest.param(("install",), id="install"),
        pytest.param(("configure",), id="configure"),
        pytest.param(("doctor",), id="doctor"),
        pytest.param(("all",), id="all"),
        pytest.param(
            (
                "all",
                "--skip",
                "cursor",
                "--skip",
                "claude-code",
                "--skip",
                "codex",
            ),
            id="all-agents-skipped",
        ),
    ],
)
def test_invalid_shared_catalog_stops_before_native_or_state_mutation(
    arguments: tuple[str, ...],
    invalid_repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    """Reject malformed shared YAML before every stage's effects or confirmation."""
    paths = RuntimePaths.from_roots(
        repo_root=invalid_repo_root,
        home=temporary_home,
    )
    assistants = AssistantOrchestrator(paths)
    confirmations: list[str] = []

    result = run(
        arguments,
        repo_root=invalid_repo_root,
        home=temporary_home,
        runner=fake_runner,
        downloader=fake_runner,
        confirm=lambda prompt: confirmations.append(prompt) or True,
        output=lambda _message: pytest.fail("output after failed preflight"),
        timestamp=lambda: "20260727T120000Z",
        preflight_suppliers=(assistants.preflight,),
        install_action_candidate_suppliers=(assistants.install_action_candidates,),
        install_action_suppliers=(assistants.install_actions,),
        configuration_suppliers=(assistants.configuration,),
        doctor_check_suppliers=(assistants.doctor_checks,),
        plan_contributors=(assistants,),
    )

    assert result == RunResult(
        exit_code=2,
        report=cli.StageReport(outcomes=("assistant desired-state preflight failed",)),
    )
    assert fake_runner.commands == []
    assert fake_runner.downloads == []
    assert confirmations == []
    assert list(temporary_home.iterdir()) == []
    assert not paths.state_root.exists()
    assert not paths.backup_root.exists()
    assert not StateStore(paths).path.exists()


def test_cursor_marketplace_never_reads_private_state_or_runs_command(
    cursor_marketplace_repo: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep Cursor marketplace declarations manual and private-state-free."""
    private_roots = (
        temporary_home / ".cursor/plugins/cache",
        temporary_home / "Library/Application Support/Cursor/User/globalStorage",
    )
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if any(path == root or path.is_relative_to(root) for root in private_roots):
            pytest.fail(f"private Cursor state read: {path.name}")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    plan_output: list[str] = []
    doctor_output: list[str] = []
    cursor_only = ("--skip", "claude-code", "--skip", "codex")
    planned = run_with_assistants(
        ("plan", *cursor_only),
        repo_root=cursor_marketplace_repo,
        home=temporary_home,
        runner=fake_runner,
        output=plan_output,
    )
    diagnosed = run_with_assistants(
        ("doctor", *cursor_only),
        repo_root=cursor_marketplace_repo,
        home=temporary_home,
        runner=fake_runner,
        output=doctor_output,
    )

    assert planned.exit_code == diagnosed.exit_code == 0
    assert "cursor.plugin.example-plugin" in "\n".join(plan_output)
    assert "cursor.plugin.example-plugin" in "\n".join(doctor_output)
    assert not any(
        command[0].startswith("cursor") and "plugin" in command[1:]
        for command in fake_runner.commands
    )


def test_cursor_local_plugin_converges_and_is_idempotent(
    cursor_local_plugin_repo: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    """Converge one reviewed local plugin through the core tree engine."""
    first = run_with_assistants(
        ("configure",),
        repo_root=cursor_local_plugin_repo,
        home=temporary_home,
        runner=fake_runner,
    )
    destination = temporary_home / ".cursor/plugins/local/example-local"
    first_snapshot = {
        path.relative_to(destination): path.read_bytes()
        for path in sorted(destination.rglob("*"))
        if path.is_file()
    }
    second = run_with_assistants(
        ("configure",),
        repo_root=cursor_local_plugin_repo,
        home=temporary_home,
        runner=fake_runner,
    )
    second_snapshot = {
        path.relative_to(destination): path.read_bytes()
        for path in sorted(destination.rglob("*"))
        if path.is_file()
    }
    paths = RuntimePaths.from_roots(
        repo_root=cursor_local_plugin_repo,
        home=temporary_home,
    )
    state = StateStore(paths).load()

    assert first.exit_code == second.exit_code == 0
    assert first.report.changed_count >= 1
    assert second.report.changed_count == 0
    assert second_snapshot == first_snapshot
    assert "cursor-local-plugin-example-local" in state.managed
    assert not paths.backup_root.exists()


def test_dotted_cursor_local_plugin_ids_keep_distinct_state_and_destinations(
    cursor_local_plugin_repo_factory: CursorLocalPluginRepoFactory,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    """Preserve dotted IDs without colliding with a similarly named plugin."""
    repo_root = cursor_local_plugin_repo_factory(
        (
            CursorLocalPluginFixture(id="example.local", skill_name="dotted-skill"),
            CursorLocalPluginFixture(id="example-local", skill_name="dash-skill"),
        )
    )

    result = run_with_assistants(
        ("configure",),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    state = StateStore(paths).load()

    assert result.exit_code == 0
    assert (temporary_home / ".cursor/plugins/local/example.local").is_dir()
    assert (temporary_home / ".cursor/plugins/local/example-local").is_dir()
    assert {
        "cursor-local-plugin-example.local",
        "cursor-local-plugin-example-local",
    }.issubset(state.managed)


@pytest.mark.parametrize(
    "stage",
    [
        pytest.param("plan", id="plan"),
        pytest.param("install", id="install"),
        pytest.param("configure", id="configure"),
        pytest.param("doctor", id="doctor"),
        pytest.param("all", id="all"),
    ],
)
@pytest.mark.parametrize("skip_all", [False, True], ids=["enabled", "all-skipped"])
def test_invalid_cursor_local_tree_fails_preflight_without_effects(
    invalid_cursor_local_plugin_repo: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    stage: str,
    skip_all: bool,
) -> None:
    """Validate raw local trees before skips, commands, or filesystem effects."""
    arguments: tuple[str, ...] = (stage,)
    if skip_all:
        arguments += (
            "--skip",
            "cursor",
            "--skip",
            "claude-code",
            "--skip",
            "codex",
        )

    result = run_with_assistants(
        arguments,
        repo_root=invalid_cursor_local_plugin_repo,
        home=temporary_home,
        runner=fake_runner,
    )
    paths = RuntimePaths.from_roots(
        repo_root=invalid_cursor_local_plugin_repo,
        home=temporary_home,
    )

    assert result.exit_code == 2
    assert result.report.outcomes == ("assistant desired-state preflight failed",)
    assert fake_runner.commands == []
    assert not paths.state_root.exists()
    assert not paths.backup_root.exists()
    assert not (temporary_home / ".cursor/plugins/local").exists()


def test_aggregate_callbacks_omit_every_cursor_surface_when_skipped(
    repo_root, temporary_home, fake_runner
) -> None:
    """A whole-agent skip prevents Cursor inspection and configuration."""
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(skips=("cursor",))
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)

    assistants = AssistantOrchestrator(paths)
    assistants.preflight(setup, paths)
    actions = assistants.install_actions(setup, paths, fake_runner)
    contribution = assistants.configuration(setup, paths)
    plan = assistants.actions(setup)

    assert not any(action.component_id.startswith("cursor.") for action in actions)
    assert not any(spec.component == "cursor" for spec in contribution.specs)
    assert not any(action.component_id.startswith("cursor.") for action in plan)
    assert ("cursor", "--list-extensions") not in fake_runner.commands


def test_main_registers_exported_callbacks_and_runs_real_aggregate_plan(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Main wires one orchestrator's bound callbacks into the real CLI path."""
    saved_run = cli.run
    monkeypatch.setattr(Path, "home", staticmethod(lambda: temporary_home))

    def wrapped(arguments: Sequence[str], **kwargs: object) -> RunResult:
        assert all(callable(item) for item in kwargs["preflight_suppliers"])
        assert all(callable(item) for item in kwargs["install_action_suppliers"])
        assert all(
            callable(item) for item in kwargs["install_action_candidate_suppliers"]
        )
        assert all(callable(item) for item in kwargs["configuration_suppliers"])
        assert all(callable(item) for item in kwargs["doctor_check_suppliers"])
        contributors = kwargs["plan_contributors"]
        assert isinstance(contributors, tuple)
        assert isinstance(contributors[1], AssistantOrchestrator)
        fake_runner.satisfy_core_commands()
        return saved_run(
            arguments,
            repo_root=repo_root,
            home=temporary_home,
            runner=fake_runner,
            downloader=fake_runner,
            confirm=lambda _prompt: True,
            output=print,
            timestamp=lambda: "20260726T120000Z",
            preflight_suppliers=kwargs["preflight_suppliers"],
            install_action_candidate_suppliers=kwargs[
                "install_action_candidate_suppliers"
            ],
            install_action_suppliers=kwargs["install_action_suppliers"],
            configuration_suppliers=kwargs["configuration_suppliers"],
            doctor_check_suppliers=kwargs["doctor_check_suppliers"],
            plan_contributors=kwargs["plan_contributors"],
        )

    monkeypatch.setattr(cli, "run", wrapped)
    assert (
        main(("plan", "--skip", "cursor", "--skip", "claude-code", "--skip", "codex"))
        == 0
    )
    assert "profile: default" in capsys.readouterr().out


def test_doctor_normalizes_claude_native_inspection_failure(
    repo_root, temporary_home, fake_runner, monkeypatch
) -> None:
    """A failed native inspection becomes one generic warning finding."""
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(skips=("cursor", "codex"))
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    monkeypatch.setattr(
        "ballen_config.assistants.orchestrator.claude_install_actions",
        lambda *_args: (_ for _ in ()).throw(ClaudePluginInspectionError("secret")),
    )

    assistants = AssistantOrchestrator(paths)
    assistants.preflight(setup, paths)
    findings = assistants.doctor_checks(setup, paths, fake_runner)

    unavailable = next(
        finding for finding in findings if finding.id == "claude.unavailable"
    )
    assert unavailable.status.value == "unavailable"
    assert unavailable.message == "Claude native inspection unavailable"


def test_aggregate_install_and_doctor_normalize_bundled_cursor_read_failure(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cursor bundled metadata read failures remain generic at aggregate seams."""
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(skips=("claude-code", "codex"))
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)

    def unreadable_bundles(_root: Path) -> frozenset[str]:
        """Raise a native package-read error without exposing its path."""
        raise OSError("private Cursor package path")

    monkeypatch.setattr(
        "ballen_config.assistants.cursor.read_bundled_extensions", unreadable_bundles
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **_kwargs: InstallStageReport(exit_code=0, outcomes=()),
    )

    installed = run_with_assistants(
        ("install", "--skip", "claude-code", "--skip", "codex"),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )
    assistants = AssistantOrchestrator(paths)
    assistants.preflight(setup, paths)
    findings = assistants.doctor_checks(setup, paths, fake_runner)

    assert installed == RunResult(
        exit_code=1,
        report=cli.StageReport(outcomes=("native assistant inspection failed",)),
    )
    unavailable = next(
        finding for finding in findings if finding.id == "cursor.unavailable"
    )
    assert unavailable.message == "Cursor native inspection unavailable"


def test_wsh_all_converges_native_resources_and_skips_codex(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real all path manages wsh Cursor and Claude resources only once."""
    monkeypatch.setattr(
        "ballen_config.assistants.cursor.read_bundled_extensions",
        lambda _root: frozenset(),
    )
    cursor = temporary_home / "Library/Application Support/Cursor/User"
    cursor.mkdir(parents=True)
    (cursor / "settings.json").write_text('{"native": true}\n')
    (cursor / "keybindings.json").write_text(
        '[{"key":"cmd+k","command":"composerMode.agent"}]\n'
    )
    claude = temporary_home / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text(
        json.dumps(
            {
                "extraKnownMarketplaces": {"native": {"source": "keep"}},
                "enabledPlugins": {"native@local": True},
                "hooks": {"SessionStart": [{"hooks": [{"command": "native"}]}]},
            }
        )
    )

    result = run_with_assistants(
        ("all", "--profile", "wsh", "--skip", "codex"),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )

    assert result.exit_code == 0
    assert not (temporary_home / ".codex").exists()
    settings = json.loads((cursor / "settings.json").read_text())
    assert settings["native"] is True
    keybindings = json.loads((cursor / "keybindings.json").read_text())
    assert {binding["key"] for binding in keybindings} >= {"cmd+k", "cmd+i"}
    claude_settings = json.loads((claude / "settings.json").read_text())
    assert "native" in claude_settings["extraKnownMarketplaces"]
    assert "native@local" in claude_settings["enabledPlugins"]
    assert len(claude_settings["hooks"]["SessionStart"]) == 1
    assert len(claude_settings["hooks"]["PreToolUse"]) == 1
    assert (
        len([command for command in fake_runner.commands if command[0] == "codex"]) == 0
    )


@pytest.mark.parametrize(
    "skipped",
    (
        pytest.param("cursor", id="cursor"),
        pytest.param("claude-code", id="claude-code"),
        pytest.param("codex", id="codex"),
    ),
)
def test_single_agent_skip_removes_its_production_surface(
    skipped: str,
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each whole-agent skip suppresses native commands and managed directories."""
    monkeypatch.setattr(
        "ballen_config.assistants.cursor.read_bundled_extensions",
        lambda _root: frozenset(),
    )
    result = run_with_assistants(
        ("all", "--skip", skipped),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )

    assert result.exit_code == 0
    executable = {"claude-code": "claude"}.get(skipped, skipped)
    assert not any(command[0] == executable for command in fake_runner.commands)
    directory = {"cursor": ".cursor", "claude-code": ".claude", "codex": ".codex"}[
        skipped
    ]
    assert not (temporary_home / directory).exists()


def test_plan_redacts_native_and_secret_values(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    """Plan output reports structural IDs without leaking local native state."""
    output: list[str] = []
    fake_runner.add(
        ("cursor", "--list-extensions"), returncode=1, stdout="token", stderr="secret"
    )

    result = run_with_assistants(
        ("plan", "--profile", "wsh", "--skip", "codex"),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
        output=output,
    )

    rendered = "\n".join(output)
    assert result.exit_code == 0
    assert "cursor.keybindings" in rendered
    assert "claude.plugin" in rendered
    assert str(temporary_home) not in rendered
    assert "token" not in rendered
    assert "secret" not in rendered


def test_wsh_all_is_idempotent_for_agent_managed_state(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second wsh run stabilizes managed resources and native install state."""
    monkeypatch.setattr(
        "ballen_config.assistants.cursor.read_bundled_extensions",
        lambda _root: frozenset(),
    )
    arguments = ("all", "--profile", "wsh", "--skip", "codex")
    first = run_with_assistants(
        arguments, repo_root=repo_root, home=temporary_home, runner=fake_runner
    )
    managed = (
        temporary_home / "Library/Application Support/Cursor/User/keybindings.json",
        temporary_home / ".claude/settings.json",
        temporary_home / ".cursor/hooks.json",
    )
    before = tuple(path.read_bytes() for path in managed)
    command_count = len(fake_runner.commands)

    second = run_with_assistants(
        arguments, repo_root=repo_root, home=temporary_home, runner=fake_runner
    )

    assert first.exit_code == second.exit_code == 0
    assert tuple(path.read_bytes() for path in managed) == before
    assert not any(
        command[1:3] == ("plugin", "install")
        for command in fake_runner.commands[command_count:]
        if len(command) >= 3
    )


def test_aggregate_configure_copies_and_tracks_shared_skill_trees(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    """Copy nested shared skill trees to native roots and converge idempotently."""
    first = run_with_assistants(
        ("configure",),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )
    skill_names = ("using-jujutsu", "resolve-change-scope")
    native_roots = {
        "cursor": temporary_home / ".cursor/skills",
        "claude-code": temporary_home / ".claude/skills",
        "codex": temporary_home / ".agents/skills",
    }

    assert first.exit_code == 0
    records = (
        StateStore(RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home))
        .load()
        .managed
    )
    for skill_name in skill_names:
        source = repo_root / "assistants/shared/skills" / skill_name
        source_files = tuple(
            sorted(path for path in source.rglob("*") if path.is_file())
        )
        for target, native_root in native_roots.items():
            destination = native_root / skill_name
            for source_file in source_files:
                relative = source_file.relative_to(source)
                assert (destination / relative).read_bytes() == source_file.read_bytes()
            resource_id = f"shared-skill-{skill_name}-{target}"
            receipt = records[resource_id]
            assert receipt.resource_id == resource_id
            assert receipt.destination == str(destination.relative_to(temporary_home))
            assert receipt.source_digest == receipt.destination_digest

    second = run_with_assistants(
        ("configure",),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )

    assert second.exit_code == 0
    assert second.report.changed_count == 0
    for skill_name in skill_names:
        source = repo_root / "assistants/shared/skills" / skill_name
        source_files = tuple(
            sorted(path for path in source.rglob("*") if path.is_file())
        )
        for native_root in native_roots.values():
            destination = native_root / skill_name
            for source_file in source_files:
                relative = source_file.relative_to(source)
                assert (destination / relative).read_bytes() == source_file.read_bytes()


def test_aggregate_plan_skips_divergent_cursor_shared_skill_when_cursor_skipped(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    """Allow a Claude and Codex plan to ignore a skipped Cursor skill tree."""
    conflict = temporary_home / ".cursor/skills/using-jujutsu"
    conflict.mkdir(parents=True)
    (conflict / "SKILL.md").write_text(
        "---\nname: using-jujutsu\ndescription: Different.\n---\n"
    )
    output: list[str] = []

    result = run_with_assistants(
        ("plan", "--skip", "cursor"),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
        output=output,
    )

    assert result.exit_code == 0
    rendered = "\n".join(output)
    assert "shared-skill-using-jujutsu-claude-code" in rendered
    assert "shared-skill-using-jujutsu-codex" in rendered
    assert "shared-skill-using-jujutsu-cursor" not in rendered


def test_all_agent_skips_leave_no_assistant_plan_or_native_commands(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    """Skipping all agents leaves the core plan free of assistant resources."""
    output: list[str] = []

    result = run_with_assistants(
        (
            "plan",
            "--skip",
            "cursor",
            "--skip",
            "claude-code",
            "--skip",
            "codex",
        ),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
        output=output,
    )

    assert result.exit_code == 0
    assert not any(
        command[0] in {"cursor", "claude", "codex"} for command in fake_runner.commands
    )
    rendered = "\n".join(output)
    assert "cursor." not in rendered
    assert "claude." not in rendered
    assert "codex." not in rendered


def test_default_and_fsp_profiles_diverge_only_in_cursor_bedrock_resources(
    repo_root: Path, temporary_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the fsp production path adds Cursor Bedrock configuration."""
    monkeypatch.setattr(
        "ballen_config.assistants.cursor.read_bundled_extensions",
        lambda _root: frozenset(),
    )
    default_home = temporary_home / "default"
    fsp_home = temporary_home / "fsp"
    default_home.mkdir()
    fsp_home.mkdir()
    default_runner = StatefulAssistantFake(default_home)
    fsp_runner = StatefulAssistantFake(fsp_home)
    default_output: list[str] = []
    fsp_output: list[str] = []

    default_result = run_with_assistants(
        ("all",),
        repo_root=repo_root,
        home=default_home,
        runner=default_runner,
        output=default_output,
    )
    fsp_result = run_with_assistants(
        ("all", "--profile", "fsp"),
        repo_root=repo_root,
        home=fsp_home,
        runner=fsp_runner,
        output=fsp_output,
    )
    assert default_result.exit_code == fsp_result.exit_code == 0

    default_settings = json.loads(
        (
            default_home / "Library/Application Support/Cursor/User/settings.json"
        ).read_text()
    )
    fsp_settings = json.loads(
        (fsp_home / "Library/Application Support/Cursor/User/settings.json").read_text()
    )
    assert "claudeCode.environmentVariables" not in default_settings
    assert "claudeCode.environmentVariables" in fsp_settings
    default_agent_commands = [
        command
        for command in default_runner.commands
        if command[0] in {"claude", "codex"}
    ]
    fsp_agent_commands = [
        command for command in fsp_runner.commands if command[0] in {"claude", "codex"}
    ]
    assert fsp_agent_commands == default_agent_commands
    default_agent_outcomes = [
        outcome
        for outcome in default_result.report.outcomes
        if outcome.startswith(("claude.", "codex."))
    ]
    fsp_agent_outcomes = [
        outcome
        for outcome in fsp_result.report.outcomes
        if outcome.startswith(("claude.", "codex."))
    ]
    assert fsp_agent_outcomes == default_agent_outcomes
    assert all("BEDROCK" not in outcome for outcome in fsp_result.report.outcomes)


def test_doctor_continues_after_cursor_native_inspection_failure(
    repo_root: Path, temporary_home: Path, fake_runner: StatefulAssistantFake
) -> None:
    """One unavailable native boundary yields a generic finding and continues."""
    output: list[str] = []
    fake_runner.add(
        ("cursor", "--list-extensions"), returncode=1, stdout="token", stderr="secret"
    )

    result = run_with_assistants(
        ("doctor",),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
        output=output,
    )

    rendered = "\n".join(output)
    assert "cursor.unavailable: unavailable" in result.report.outcomes
    assert ("claude", "plugin", "list", "--json") in fake_runner.commands
    assert ("codex", "plugin", "list", "--json") in fake_runner.commands
    assert "token" not in rendered and "secret" not in rendered


def test_wsh_all_preserves_excluded_agent_state_bytes_and_tree_identity(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aggregate wsh setup leaves explicit local-state sentinels untouched."""
    monkeypatch.setattr(
        "ballen_config.assistants.cursor.read_bundled_extensions",
        lambda _root: frozenset(),
    )
    sentinel_paths = (
        Path(".claude/sessions/session-opaque/blob.bin"),
        Path(".claude/history/opaque.log"),
        Path(".claude/auth/state.bin"),
        Path(".codex/sessions/session-opaque/blob.bin"),
        Path(".codex/memories/opaque.bin"),
        Path(".codex/auth/state.bin"),
        Path(".codex/projects/project-opaque/trust.bin"),
        Path("Library/Application Support/Cursor/User/worktrees/tree-opaque/state.bin"),
        Path("Library/Application Support/Cursor/cache/index/opaque.bin"),
        Path("Library/Application Support/Cursor/User/globalStorage/runtime.sqlite3"),
        Path(".cursor/plugins/runtime/generated-state.bin"),
    )
    payload = b"opaque-state-sentinel-v1\x00\xff"
    for index, relative_path in enumerate(sentinel_paths):
        destination = temporary_home / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload + str(index).encode())
        destination.chmod(0o640)
    sentinel_directories = (
        Path(".claude/sessions/session-opaque"),
        Path(".codex/projects/project-opaque"),
        Path("Library/Application Support/Cursor/User/worktrees/tree-opaque"),
        Path(".cursor/plugins/runtime"),
    )
    for relative_path in sentinel_directories:
        (temporary_home / relative_path).chmod(0o750)
    before = snapshot_sentinels(
        temporary_home, (*sentinel_directories, *sentinel_paths)
    )

    result = run_with_assistants(
        ("all", "--profile", "wsh"),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )

    assert result.exit_code == 0
    assert (
        snapshot_sentinels(temporary_home, (*sentinel_directories, *sentinel_paths))
        == before
    )


@pytest.mark.parametrize(
    "stage",
    (
        pytest.param("install", id="install"),
        pytest.param("all", id="all"),
    ),
)
def test_core_install_id_collision_stops_before_mutation(
    stage: str,
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
) -> None:
    """A supplied core-ID collision is rejected before install or state mutation."""
    fake_runner.satisfy_core_commands()
    resolved = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile="wsh")
    )
    core_component_id = resolved.components[0].id
    state_path = (
        RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home).state_root
        / "state.json"
    )
    commands_before = tuple(fake_runner.commands)
    state_before = state_path.read_bytes() if state_path.exists() else None

    def duplicate_core_action(*_args: object) -> tuple[InstallAction, ...]:
        """Supply one conflicting action without requiring a native command."""
        return (
            InstallAction(
                component_id=core_component_id,
                argv=("collision-safe",),
            ),
        )

    result = cli.run(
        (stage, "--profile", "wsh"),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
        downloader=fake_runner,
        confirm=lambda _prompt: True,
        output=lambda _line: None,
        timestamp=lambda: "20260726T120000Z",
        install_action_candidate_suppliers=(duplicate_core_action,),
        install_action_suppliers=(duplicate_core_action,),
    )

    assert result.exit_code == 2
    assert result.report.outcomes == ("duplicate install action IDs",)
    assert tuple(fake_runner.commands) == commands_before
    assert (state_path.read_bytes() if state_path.exists() else None) == state_before


@pytest.mark.parametrize(
    "profile",
    (
        pytest.param("default", id="default"),
        pytest.param("wsh", id="wsh"),
    ),
)
def test_candidate_actions_cover_every_possible_native_action(
    profile: str,
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Static candidates cover all dynamically missing agent-native actions."""
    monkeypatch.setattr(
        "ballen_config.assistants.cursor.read_bundled_extensions",
        lambda _root: frozenset(),
    )
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile=profile)
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)

    assistants = AssistantOrchestrator(paths)
    assistants.preflight(setup, paths)
    candidates = assistants.install_action_candidates(setup, paths)
    dynamic = assistants.install_actions(setup, paths, fake_runner)

    assert {action.component_id for action in dynamic} <= {
        action.component_id for action in candidates
    }
