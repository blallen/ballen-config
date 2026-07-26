"""Integration tests for the aggregate coding-agent extension seams."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from ballen_config.assistants import (
    AssistantPlanContributor,
    configuration,
    doctor_checks,
    install_actions,
)
from ballen_config.assistants.claude import ClaudePluginInspectionError
from ballen_config.cli import RunResult, StageReport, main, run
from ballen_config.manifests import ManifestRepository
from ballen_config.models import Manager, ResolutionRequest
from ballen_config.runtime import RuntimePaths
from tests.assistants.fakes import StatefulAssistantFake


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
    resolved = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(
            profile="work"
            if "--profile" in arguments and "work" in arguments
            else "default"
        )
    )
    for component in resolved.components:
        if component.manager is Manager.GIT and component.destination is not None:
            (home / component.destination / ".git").mkdir(parents=True, exist_ok=True)
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
    return run(
        arguments,
        repo_root=repo_root,
        home=home,
        runner=runner,
        downloader=runner,
        confirm=lambda _prompt: True,
        output=messages.append,
        timestamp=lambda: "20260726T120000Z",
        install_action_suppliers=(install_actions,),
        configuration_suppliers=(configuration,),
        doctor_check_suppliers=(doctor_checks,),
        plan_contributors=(
            AssistantPlanContributor(
                RuntimePaths.from_roots(repo_root=repo_root, home=home)
            ),
        ),
    )


def test_aggregate_callbacks_omit_every_cursor_surface_when_skipped(
    repo_root, temporary_home, fake_runner
) -> None:
    """A whole-agent skip prevents Cursor inspection and configuration."""
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(skips=("cursor",))
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)

    actions = install_actions(setup, paths, fake_runner)
    contribution = configuration(setup, paths)
    plan = AssistantPlanContributor(paths).actions(setup)

    assert not any(action.component_id.startswith("cursor.") for action in actions)
    assert not any(spec.component == "cursor" for spec in contribution.specs)
    assert not any(action.component_id.startswith("cursor.") for action in plan)
    assert ("cursor", "--list-extensions") not in fake_runner.commands


def test_cli_registers_each_aggregate_callback_once(monkeypatch) -> None:
    """Production CLI supplies each aggregate seam exactly once."""
    captured: dict[str, object] = {}

    def fake_run(*_args, **kwargs):
        captured.update(kwargs)
        return RunResult(exit_code=0, report=StageReport())

    monkeypatch.setattr("ballen_config.cli.run", fake_run)

    assert main(("plan",)) == 0
    assert len(captured["install_action_suppliers"]) == 1
    assert len(captured["configuration_suppliers"]) == 1
    assert len(captured["doctor_check_suppliers"]) == 1
    assert len(captured["plan_contributors"]) == 2


def test_doctor_normalizes_claude_native_inspection_failure(
    repo_root, temporary_home, fake_runner, monkeypatch
) -> None:
    """A failed native inspection becomes one generic warning finding."""
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(skips=("cursor", "codex"))
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    monkeypatch.setattr(
        "ballen_config.assistants.claude_install_actions",
        lambda *_args: (_ for _ in ()).throw(ClaudePluginInspectionError("secret")),
    )

    findings = doctor_checks(setup, paths, fake_runner)

    unavailable = next(
        finding for finding in findings if finding.id == "claude.unavailable"
    )
    assert unavailable.status.value == "unavailable"
    assert unavailable.message == "Claude native inspection unavailable"


def test_work_all_converges_native_resources_and_skips_codex(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real all path manages work Cursor and Claude resources only once."""
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
        ("all", "--profile", "work", "--skip", "codex"),
        repo_root=repo_root,
        home=temporary_home,
        runner=fake_runner,
    )

    assert result.exit_code == 0
    assert not (temporary_home / ".codex").exists()
    settings = json.loads((cursor / "settings.json").read_text())
    assert settings["native"] is True
    assert "claudeCode.environmentVariables" in settings
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


@pytest.mark.parametrize("skipped", ("cursor", "claude-code", "codex"))
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
        ("plan", "--profile", "work", "--skip", "codex"),
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


def test_work_all_is_idempotent_for_agent_managed_state(
    repo_root: Path,
    temporary_home: Path,
    fake_runner: StatefulAssistantFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second work run stabilizes managed resources and native install state."""
    monkeypatch.setattr(
        "ballen_config.assistants.cursor.read_bundled_extensions",
        lambda _root: frozenset(),
    )
    arguments = ("all", "--profile", "work", "--skip", "codex")
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
