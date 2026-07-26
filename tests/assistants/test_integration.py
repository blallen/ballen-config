"""Integration tests for the aggregate coding-agent extension seams."""

from __future__ import annotations

from ballen_config.assistants import (
    AssistantPlanContributor,
    configuration,
    doctor_checks,
    install_actions,
)
from ballen_config.assistants.claude import ClaudePluginInspectionError
from ballen_config.cli import RunResult, StageReport, main
from ballen_config.manifests import ManifestRepository
from ballen_config.models import ResolutionRequest
from ballen_config.runtime import RuntimePaths


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
