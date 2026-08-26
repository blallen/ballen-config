import os
import shutil
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

import ballen_config.cli as cli
from ballen_config.assistants.desired_state import (
    AssistantDesiredStateError,
    load_desired_state,
)
from ballen_config.assistants.orchestrator import AssistantOrchestrator
from ballen_config.assistants.skills import configuration as shared_skills_configuration
from ballen_config.assistants.skills import hash_skill_tree
from ballen_config.cli import (
    STAGES,
    RunResult,
    StageReport,
    main,
    parse_args,
    run,
)
from ballen_config.configure import (
    ConfigAction,
    ConfigurationContribution,
    ConfigurationSupplier,
    ConfigureStageReport,
    core_configuration,
)
from ballen_config.doctor import CheckSeverity, DoctorFinding, FindingStatus
from ballen_config.install import InstallAction, InstallStageReport
from ballen_config.manifests import ManifestRepository
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.planning import ComponentState, PlanAction
from ballen_config.runner import CommandResult
from ballen_config.runtime import RuntimePaths
from ballen_config.state import ManagedRecord, StateStore


@pytest.fixture
def repeated_selection_arguments() -> list[str]:
    """Return ordered repeated include and skip arguments."""
    return [
        "plan",
        "--profile",
        "wsh",
        "--include",
        "mactex",
        "--include",
        "signal",
        "--skip",
        "cursor",
        "--skip",
        "codex",
    ]


def test_cli_accepts_stage_profile_and_repeated_selections(
    repeated_selection_arguments: list[str],
) -> None:
    """Repeated selection flags retain caller order in the parsed request."""
    options = parse_args(repeated_selection_arguments)

    assert options.stage == "plan"
    assert options.request.profile == "wsh"
    assert options.request.includes == ("mactex", "signal")
    assert options.request.skips == ("cursor", "codex")


def test_cli_defaults_to_all_and_default_profile() -> None:
    """An empty invocation selects the complete default bootstrap flow."""
    options = parse_args([])

    assert STAGES == (
        "all",
        "prepare",
        "plan",
        "install",
        "configure",
        "doctor",
    )
    assert options.stage == "all"
    assert options.request.profile == "default"
    assert options.request.includes == ()
    assert options.request.skips == ()


def test_help_returns_success_without_an_invalid_configuration_report(
    repo_root: Path,
    fake_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Treat argparse's help exit as a successful read-only request."""
    result = run(
        ("--help",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: False,
        output=lambda _message: None,
        timestamp=lambda: "fixed",
    )

    assert result == RunResult(exit_code=0, report=StageReport())
    assert "usage: bootstrap" in capsys.readouterr().out


class FakeRunner:
    """Return safe defaults while recording every native command."""

    def __init__(self, results: list[CommandResult] | None = None) -> None:
        """Initialize ordered optional command results."""
        self.results = iter(results or [])
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> CommandResult:
        """Record a command and return the next or default success."""
        self.commands.append(tuple(command))
        return next(
            self.results,
            {"returncode": 0, "stdout": "", "stderr": ""},
        )


class FakeDownloader:
    """Fail if a dispatcher test unexpectedly downloads an artifact."""

    def download(
        self,
        *,
        url: str,
        destination: Path,
        maximum_bytes: int,
    ) -> None:
        """Reject an unexpected download."""
        raise AssertionError("no download expected")


def test_state_reports_present_for_a_listed_uv_tool(fake_home: Path) -> None:
    """A uv-managed tool listed by name resolves to present."""
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
    )
    runner = FakeRunner(
        [{"returncode": 0, "stdout": "pre-commit v4.6.0\n- pre-commit\n", "stderr": ""}]
    )
    inspector = cli.ResolvedInspector(runner, (component,), fake_home)

    assert inspector.state("pre-commit") is ComponentState.PRESENT
    assert runner.commands == [("uv", "tool", "list")]


def test_state_reports_missing_for_an_absent_uv_tool(fake_home: Path) -> None:
    """A uv-managed tool absent from the listing resolves to missing."""
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
    )
    runner = FakeRunner([{"returncode": 0, "stdout": "", "stderr": ""}])
    inspector = cli.ResolvedInspector(runner, (component,), fake_home)

    assert inspector.state("pre-commit") is ComponentState.MISSING
    assert runner.commands == [("uv", "tool", "list")]


def test_state_uv_tool_entrypoint_line_does_not_produce_false_present(
    fake_home: Path,
) -> None:
    """An entrypoint line's dash prefix never matches a different package."""
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
    )
    runner = FakeRunner(
        [
            {
                "returncode": 0,
                "stdout": "ruff v0.6.0\n- ruff\n- pre-commit\n",
                "stderr": "",
            }
        ]
    )
    inspector = cli.ResolvedInspector(runner, (component,), fake_home)

    assert inspector.state("pre-commit") is ComponentState.MISSING
    assert runner.commands == [("uv", "tool", "list")]


def test_state_resolves_uv_tool_list_once_across_components(fake_home: Path) -> None:
    """One listing answers every uv_tool component this inspector is asked about."""
    components = tuple(
        Component(id=name, manager=Manager.UV_TOOL, package=name)
        for name in ("pre-commit", "ruff")
    )
    runner = FakeRunner(
        [
            {
                "returncode": 0,
                "stdout": "pre-commit v4.6.0\n- pre-commit\nruff v0.15.1\n- ruff\n",
                "stderr": "",
            }
        ]
    )
    inspector = cli.ResolvedInspector(runner, components, fake_home)

    assert inspector.state("pre-commit") is ComponentState.PRESENT
    assert inspector.state("ruff") is ComponentState.PRESENT
    assert runner.commands == [("uv", "tool", "list")]


def test_state_unreadable_uv_tool_list_is_missing(fake_home: Path) -> None:
    """An unreadable listing is missing even when stdout names the tool."""
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
    )
    runner = FakeRunner(
        [
            {
                "returncode": 127,
                "stdout": "pre-commit v4.6.0\n- pre-commit\n",
                "stderr": "",
            }
        ]
    )
    inspector = cli.ResolvedInspector(runner, (component,), fake_home)

    assert inspector.state("pre-commit") is ComponentState.MISSING
    assert runner.commands == [("uv", "tool", "list")]


def test_state_declared_application_path_without_matching_receipt_is_missing(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    """A vendor-provided path is insufficient without the declared receipt.

    BasicTeX provides the same ``latex`` binary as full MacTeX, so the
    receipt prefix is what distinguishes them. Without a matching receipt,
    the application path alone must not resolve to present.
    """
    latex_path = tmp_path / "latex"
    latex_path.write_text("")
    component = Component(
        id="mactex",
        manager=Manager.BREW_CASK,
        package="mactex",
        application_paths=(str(latex_path),),
        receipt_prefixes=("org.tug.mactex.gui",),
    )
    runner = FakeRunner(
        [
            {"returncode": 0, "stdout": "org.tug.texlive2025\n", "stderr": ""},
            {"returncode": 1, "stdout": "", "stderr": ""},
        ]
    )
    inspector = cli.ResolvedInspector(runner, (component,), fake_home)

    assert inspector.state("mactex") is ComponentState.MISSING
    assert runner.commands == [
        ("pkgutil", "--pkgs"),
        ("brew", "list", "--cask", "mactex"),
    ]


def test_state_declared_application_path_with_matching_receipt_is_present(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    """A vendor-provided path with the declared receipt resolves to present."""
    latex_path = tmp_path / "latex"
    latex_path.write_text("")
    component = Component(
        id="mactex",
        manager=Manager.BREW_CASK,
        package="mactex",
        application_paths=(str(latex_path),),
        receipt_prefixes=("org.tug.mactex.gui",),
    )
    runner = FakeRunner(
        [
            {
                "returncode": 0,
                "stdout": "org.tug.mactex.gui2025\norg.tug.texlive2025\n",
                "stderr": "",
            }
        ]
    )
    inspector = cli.ResolvedInspector(runner, (component,), fake_home)

    assert inspector.state("mactex") is ComponentState.PRESENT
    assert runner.commands == [("pkgutil", "--pkgs")]


def test_state_no_application_paths_with_failing_brew_list_is_missing(
    fake_home: Path,
) -> None:
    """A component without declared application paths never vacuously passes.

    Regression guard: ``all()`` over an empty ``application_paths`` tuple is
    vacuously ``True``. The presence check must require a non-empty tuple
    before using ``all()``, or every path-less component would resolve to
    present regardless of ``brew list`` failing.
    """
    component = Component(
        id="gh",
        manager=Manager.BREW_FORMULA,
        package="gh",
    )
    runner = FakeRunner([{"returncode": 1, "stdout": "", "stderr": ""}])
    inspector = cli.ResolvedInspector(runner, (component,), fake_home)

    assert inspector.state("gh") is ComponentState.MISSING
    assert runner.commands == [("brew", "list", "--formula", "gh")]


def test_state_uv_tool_application_path_never_short_circuits_the_uv_check(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    """A declared application path on a non-brew component is never consulted.

    Nothing in the manifests declares application_paths on a uv_tool or git
    component today, but the dispatch must still check the manager-specific
    state rather than an incidental application path.
    """
    stray_path = tmp_path / "stray"
    stray_path.write_text("")
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
        application_paths=(str(stray_path),),
    )
    runner = FakeRunner([{"returncode": 0, "stdout": "", "stderr": ""}])
    inspector = cli.ResolvedInspector(runner, (component,), fake_home)

    assert inspector.state("pre-commit") is ComponentState.MISSING
    assert runner.commands == [("uv", "tool", "list")]


def _prepare_legacy_skill_rename(
    repo_root: Path,
    fake_home: Path,
) -> tuple[RuntimePaths, Path, ManagedRecord]:
    """Create a received legacy skill ready for a rename cleanup."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    legacy = fake_home / ".cursor/skills/jujutsu-workflow"
    legacy.mkdir(parents=True)
    (legacy / "SKILL.md").write_text(
        "---\nname: jujutsu-workflow\ndescription: Example.\n---\n",
        encoding="utf-8",
    )
    digest = hash_skill_tree(legacy)
    record = ManagedRecord(
        resource_id="shared-skill-jujutsu-workflow-cursor",
        source_digest=digest,
        destination_digest=digest,
        destination=".cursor/skills/jujutsu-workflow",
    )
    StateStore(paths).record_managed(record)
    return paths, legacy, record


def _shared_skill_configuration(
    repo_root: Path,
) -> ConfigurationSupplier:
    """Return the production shared-skill configuration supplier."""

    def supplier(
        setup: ResolvedSetup,
        paths: RuntimePaths,
    ) -> ConfigurationContribution:
        """Load the checked-in skill catalog through production code."""
        desired = load_desired_state(
            repo_root,
            setup.profiles,
            frozenset(setup.skipped),
        )
        return shared_skills_configuration(setup, paths, desired.skill_catalog)

    return supplier


def test_preflight_runs_before_all_supplier_and_state_boundaries(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Reject invalid desired state before any supplied or native boundary."""
    events: list[str] = []

    def preflight(_setup: object, _paths: object) -> None:
        events.append("preflight")
        raise AssistantDesiredStateError("assistant desired-state preflight failed")

    def candidate(_setup: object, _paths: object) -> tuple[InstallAction, ...]:
        events.append("candidate")
        return ()

    def configuration(_setup: object, _paths: object) -> ConfigurationContribution:
        events.append("configuration")
        return ConfigurationContribution()

    result = run(
        ("all",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("confirmation after failed preflight"),
        output=lambda _message: pytest.fail("plan output after failed preflight"),
        timestamp=lambda: "fixed",
        preflight_suppliers=(preflight,),
        install_action_candidate_suppliers=(candidate,),
        install_action_suppliers=(
            lambda _setup, _paths, _runner: pytest.fail("native inspection"),
        ),
        configuration_suppliers=(configuration,),
    )

    assert result == RunResult(
        exit_code=2,
        report=StageReport(outcomes=("assistant desired-state preflight failed",)),
    )
    assert events == ["preflight"]


def test_shared_skill_collision_reports_a_redacted_actionable_outcome(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Map a real managed-skill collision to its stable relative-path report."""
    collision = fake_home / ".cursor/skills/using-jujutsu"
    collision.mkdir(parents=True)
    (collision / "SKILL.md").write_text(
        "---\nname: using-jujutsu\ndescription: Different.\n---\n"
    )

    def shared_skill_configuration(
        setup: ResolvedSetup,
        paths: RuntimePaths,
    ) -> ConfigurationContribution:
        """Run the production shared-skill planner against the collision."""
        desired = load_desired_state(
            repo_root,
            setup.profiles,
            frozenset(setup.skipped),
        )
        return shared_skills_configuration(setup, paths, desired.skill_catalog)

    result = run(
        ("plan",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("collision must not confirm"),
        output=lambda _message: pytest.fail("collision must not render a plan"),
        timestamp=lambda: "fixed",
        configuration_suppliers=(
            cast(ConfigurationSupplier, shared_skill_configuration),
        ),
    )

    assert result == RunResult(
        exit_code=2,
        report=StageReport(
            outcomes=(
                "shared skill collision: using-jujutsu at .cursor/skills/using-jujutsu",
            )
        ),
    )


_RENAME_BLOCKED_RESULT = RunResult(
    exit_code=2,
    report=StageReport(
        outcomes=(
            "shared skill rename blocked: jujutsu-workflow -> using-jujutsu on cursor",
        )
    ),
)
"""Normalized redacted result for a rename blocked at the apply boundary."""


def _drift_legacy_during_apply(
    legacy: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drift the received legacy skill tree during the first spec application.

    Args:
        legacy: Received legacy skill tree that gains an extra file.
        monkeypatch: Fixture used to wrap the configuration apply boundary.
    """
    original_apply = cli.ConfigurationEngine.apply
    injected = False

    def apply_with_legacy_drift(
        engine: cli.ConfigurationEngine,
        spec: object,
    ) -> ConfigAction:
        """Change the received legacy tree after configuration begins."""
        nonlocal injected
        result = original_apply(engine, spec)  # type: ignore[arg-type]
        if not injected:
            injected = True
            (legacy / "blocked-at-apply-boundary").write_text(
                "changed", encoding="utf-8"
            )
        return result

    monkeypatch.setattr(cli.ConfigurationEngine, "apply", apply_with_legacy_drift)


def test_configure_normalizes_apply_time_skill_rename_block(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configure returns a redacted exit-2 result for an apply-time block."""
    paths, legacy, record = _prepare_legacy_skill_rename(repo_root, fake_home)
    _drift_legacy_during_apply(legacy, monkeypatch)
    output: list[str] = []

    result = run(
        ("configure", "--skip", "claude-code", "--skip", "codex"),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: True,
        output=output.append,
        timestamp=lambda: "fixed",
        configuration_suppliers=(_shared_skill_configuration(repo_root),),
    )

    assert result == _RENAME_BLOCKED_RESULT
    assert legacy.exists()
    assert "blocked-at-apply-boundary" in {path.name for path in legacy.iterdir()}
    assert record.resource_id in StateStore(paths).load().managed
    assert str(fake_home) not in "\n".join((*output, *result.report.outcomes))


def test_all_stops_before_doctor_on_apply_time_skill_rename_block(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All stops after a blocked configure stage without running doctor."""
    _paths, legacy, _record = _prepare_legacy_skill_rename(repo_root, fake_home)
    doctor_calls: list[str] = []
    rendered: list[str] = []
    _drift_legacy_during_apply(legacy, monkeypatch)
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **_kwargs: InstallStageReport(exit_code=0, outcomes=()),
    )
    monkeypatch.setattr(
        "ballen_config.cli.core_doctor_checks",
        lambda *_args, **_kwargs: doctor_calls.append("doctor") or (),
    )

    result = run(
        ("all", "--skip", "claude-code", "--skip", "codex"),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: True,
        output=rendered.append,
        timestamp=lambda: "fixed",
        configuration_suppliers=(_shared_skill_configuration(repo_root),),
    )

    assert result == _RENAME_BLOCKED_RESULT
    assert doctor_calls == []
    assert len(rendered) == 1


def _doctor_rename_finding(
    paths: RuntimePaths,
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[DoctorFinding, RunResult]:
    """Run the doctor CLI for cursor only and return the rename finding.

    Args:
        paths: Approved checkout and home roots for the scenario.
        repo_root: Repository checkout passed to the CLI.
        fake_home: Isolated home root passed to the CLI.
        monkeypatch: Fixture used to observe the structured doctor input.

    Returns:
        The declared cursor rename finding and the full CLI result.
    """
    orchestrator = AssistantOrchestrator(paths)
    observed: list[DoctorFinding] = []
    original_run_doctor = cli.run_doctor

    def capture_doctor(checks: Sequence[DoctorFinding]) -> object:
        """Capture the structured checks passed to the real doctor runner."""
        observed.extend(checks)
        return original_run_doctor(checks)

    monkeypatch.setattr("ballen_config.cli.run_doctor", capture_doctor)
    rendered: list[str] = []
    result = run(
        ("doctor", "--skip", "claude-code", "--skip", "codex"),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("doctor must not confirm"),
        output=rendered.append,
        timestamp=lambda: "fixed",
        preflight_suppliers=(orchestrator.preflight,),
        configuration_suppliers=(orchestrator.configuration,),
        doctor_configuration_suppliers=(orchestrator.diagnostic_configuration,),
        doctor_check_suppliers=(orchestrator.doctor_checks,),
    )
    assert rendered, "doctor must render its report"
    finding = next(
        item for item in observed if item.id == "skill-rename.jujutsu-workflow.cursor"
    )
    return finding, result


@pytest.mark.parametrize(
    ("drift_legacy", "install_successor", "status", "severity", "outcome"),
    [
        pytest.param(
            True,
            False,
            FindingStatus.DRIFT,
            CheckSeverity.ERROR,
            "drift",
            id="managed-legacy-drift",
        ),
        pytest.param(
            False,
            True,
            FindingStatus.MANUAL,
            CheckSeverity.WARNING,
            "manual",
            id="unreceipted-successor",
        ),
    ],
)
def test_doctor_cli_reports_declared_rename_state(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift_legacy: bool,
    install_successor: bool,
    status: FindingStatus,
    severity: CheckSeverity,
    outcome: str,
) -> None:
    """Doctor renders structured rename findings even when configure blocks."""
    paths, legacy, _record = _prepare_legacy_skill_rename(repo_root, fake_home)
    if drift_legacy:
        (legacy / "drift").write_text("changed", encoding="utf-8")
    if install_successor:
        shutil.copytree(
            repo_root / "assistants/shared/skills/using-jujutsu",
            fake_home / ".cursor/skills/using-jujutsu",
        )

    finding, result = _doctor_rename_finding(paths, repo_root, fake_home, monkeypatch)

    assert finding.status is status
    assert finding.severity is severity
    assert (
        result.report.outcomes.count(f"skill-rename.jujutsu-workflow.cursor: {outcome}")
        == 1
    )


def test_successful_all_orders_every_cli_seam(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Order manifest, planning, mutation, and diagnostic seams on success."""
    events: list[str] = []
    original_manifest_load = ManifestRepository.load
    original_engine_factory = cli.ConfigurationEngine
    original_inspector = cli.ResolvedInspector
    original_doctor = cli.run_doctor

    def load_manifest(root: Path) -> ManifestRepository:
        events.append("manifest")
        return original_manifest_load(root)

    def preflight(_setup: object, _paths: object) -> None:
        events.append("preflight")

    def candidates(_setup: object, _paths: object) -> tuple[InstallAction, ...]:
        events.append("candidates")
        return (InstallAction(component_id="agent.plugin", argv=("agent", "add")),)

    def native_actions(*_args: object) -> tuple[InstallAction, ...]:
        events.append("native-inspection")
        return (InstallAction(component_id="agent.plugin", argv=("agent", "add")),)

    def configuration(_setup: object, _paths: object) -> ConfigurationContribution:
        events.append("configuration")
        return ConfigurationContribution()

    class Contributor:
        """Record the custom plan-contributor seam."""

        def actions(self, _setup: object) -> tuple[PlanAction, ...]:
            """Record plan contribution without adding a duplicate action."""
            events.append("contributor")
            return ()

    def engine_factory(**kwargs: object) -> object:
        events.append("engine")
        return original_engine_factory(**kwargs)

    def inspector_factory(*args: object) -> object:
        events.append("inspector")
        return original_inspector(*args)

    def install(**kwargs: object) -> InstallStageReport:
        events.append("base-install" if kwargs["components"] else "assistant-install")
        return InstallStageReport(exit_code=0, outcomes=())

    def configured_core(*args: object) -> ConfigurationContribution:
        events.append("core-configuration")
        return core_configuration(*args)

    monkeypatch.setattr(ManifestRepository, "load", staticmethod(load_manifest))
    monkeypatch.setattr("ballen_config.cli.core_configuration", configured_core)
    monkeypatch.setattr("ballen_config.cli.ConfigurationEngine", engine_factory)
    monkeypatch.setattr("ballen_config.cli.ResolvedInspector", inspector_factory)
    monkeypatch.setattr("ballen_config.cli.run_install", install)
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda *_args, **_kwargs: (
            events.append("configure")
            or ConfigureStageReport(actions=(), changed_count=0)
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.core_doctor_checks",
        lambda *_args, **_kwargs: events.append("core-doctor") or (),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_doctor",
        lambda checks: events.append("doctor") or original_doctor(checks),
    )

    result = run(
        ("all",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: events.append("confirmation") or True,
        output=lambda _message: None,
        timestamp=lambda: "fixed",
        preflight_suppliers=(preflight,),
        install_action_candidate_suppliers=(candidates,),
        install_action_suppliers=(native_actions,),
        configuration_suppliers=(configuration,),
        doctor_check_suppliers=(lambda *_args: events.append("doctor-supplier") or (),),
        plan_contributors=(Contributor(),),
    )

    assert result.exit_code == 0
    assert events == [
        "manifest",
        "preflight",
        "candidates",
        "core-configuration",
        "configuration",
        "engine",
        "inspector",
        "contributor",
        "confirmation",
        "base-install",
        "native-inspection",
        "assistant-install",
        "configure",
        "core-doctor",
        "doctor-supplier",
        "doctor",
    ]


@pytest.mark.parametrize(
    "stage",
    [
        pytest.param("install", id="install"),
        pytest.param("configure", id="configure"),
        pytest.param("all", id="all"),
    ],
)
def test_declined_mutating_stage_calls_no_executor(
    stage: str,
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Declining after validation invokes no mutating stage executor."""
    calls: list[str] = []
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **_kwargs: calls.append("install"),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda *_args, **_kwargs: calls.append("configure"),
    )

    result = run(
        (stage,),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: False,
        output=lambda _message: None,
        timestamp=lambda: "fixed",
    )

    assert result == RunResult(
        exit_code=0,
        report=StageReport(outcomes=("declined",)),
    )
    assert calls == []


def test_all_short_circuits_after_required_install_failure(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A required install failure prevents configure and doctor."""
    calls: list[str] = []
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **_kwargs: (
            calls.append("install")
            or InstallStageReport(
                exit_code=1,
                outcomes=("gh: required-failure",),
            )
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda *_args, **_kwargs: calls.append("configure"),
    )
    monkeypatch.setattr(
        "ballen_config.cli.core_doctor_checks",
        lambda *_args, **_kwargs: calls.append("doctor") or (),
    )

    result = run(
        ("all",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: True,
        output=lambda _message: None,
        timestamp=lambda: "fixed",
    )

    assert result.exit_code == 1
    assert result.report.outcomes == ("gh: required-failure",)
    assert calls == ["install"]


def test_all_runs_install_configure_doctor_in_order(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful all stage preserves the required stage order."""
    calls: list[str] = []
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **_kwargs: (
            calls.append("install")
            or InstallStageReport(exit_code=0, outcomes=("gh: present",))
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda *_args, **_kwargs: (
            calls.append("configure")
            or ConfigureStageReport(
                actions=(
                    ConfigAction(
                        id="zshrc",
                        destination=".zshrc",
                        outcome="unchanged",
                    ),
                ),
                changed_count=0,
            )
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.core_doctor_checks",
        lambda *_args, **_kwargs: (
            calls.append("doctor")
            or (
                DoctorFinding(
                    id="ready-check",
                    status=FindingStatus.READY,
                    severity=CheckSeverity.INFO,
                    message="ready",
                ),
            )
        ),
    )

    result = run(
        ("all",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: True,
        output=lambda _message: None,
        timestamp=lambda: "fixed",
    )

    assert result.exit_code == 0
    assert result.report.changed_count == 0
    assert result.report.outcomes == (
        "gh: present",
        "zshrc: unchanged",
        "ready-check: ready",
    )
    assert calls == ["install", "configure", "doctor"]


def test_doctor_is_independent_and_never_confirms(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctor returns diagnostic status without mutating stages."""
    calls: list[str] = []
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **_kwargs: calls.append("install"),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda *_args, **_kwargs: calls.append("configure"),
    )
    monkeypatch.setattr(
        "ballen_config.cli.core_doctor_checks",
        lambda *_args, **_kwargs: (
            DoctorFinding(
                id="required-tool",
                status=FindingStatus.MISSING,
                severity=CheckSeverity.ERROR,
                message="missing",
            ),
        ),
    )

    result = run(
        ("doctor",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("doctor must not confirm"),
        output=lambda _message: None,
        timestamp=lambda: "fixed",
    )

    assert result.exit_code == 1
    assert result.report.outcomes == ("required-tool: missing",)
    assert calls == []


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(("unknown-stage",), id="unknown-stage"),
        pytest.param(("plan", "--profile", "unknown"), id="unknown-profile"),
    ],
)
def test_invalid_arguments_or_profile_have_no_commands_or_files(
    arguments: tuple[str, ...],
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Invalid input returns two before commands, files, or confirmation."""
    runner = FakeRunner()
    before = tuple(fake_home.rglob("*"))

    result = run(
        arguments,
        repo_root=repo_root,
        home=fake_home,
        runner=runner,
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("invalid input must not confirm"),
        output=lambda _message: None,
        timestamp=lambda: "fixed",
    )

    assert result == RunResult(
        exit_code=2,
        report=StageReport(outcomes=("invalid configuration",)),
    )
    assert runner.commands == []
    assert tuple(fake_home.rglob("*")) == before


def test_duplicate_doctor_ids_fail_closed(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Reject ambiguous IDs after core and extension checks are merged."""

    def duplicates(
        *_args: object,
    ) -> tuple[DoctorFinding, ...]:
        finding = DoctorFinding(
            id="duplicate",
            status=FindingStatus.READY,
            severity=CheckSeverity.INFO,
            message="ready",
        )
        return (finding, finding)

    result = run(
        ("doctor",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("doctor must not confirm"),
        output=lambda _message: None,
        timestamp=lambda: "fixed",
        doctor_check_suppliers=(duplicates,),
    )

    assert result.exit_code == 2
    assert result.report.outcomes == ("duplicate doctor finding IDs",)


def test_plan_is_read_only_and_never_confirms(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Plan renders structural actions without confirmation or home writes."""
    output: list[str] = []
    before = tuple(fake_home.rglob("*"))

    result = run(
        ("plan",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("plan must not confirm"),
        output=output.append,
        timestamp=lambda: "fixed",
    )

    assert result == RunResult(exit_code=0, report=StageReport())
    assert output and output[0].startswith("profile: default")
    assert tuple(fake_home.rglob("*")) == before


def test_plan_uses_static_candidates_without_dynamic_native_inspection(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Plan renders static candidate IDs without invoking dynamic suppliers."""
    output: list[str] = []

    def candidates(*_args: object) -> tuple[InstallAction, ...]:
        """Return one redacted install candidate."""
        return (InstallAction(component_id="agent.plugin", argv=("agent", "add")),)

    def dynamic(*_args: object) -> tuple[InstallAction, ...]:
        """Fail if plan reaches the native inspection boundary."""
        pytest.fail("plan must not inspect native agent state")

    result = run(
        ("plan",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("plan must not confirm"),
        output=output.append,
        timestamp=lambda: "fixed",
        install_action_candidate_suppliers=(candidates,),
        install_action_suppliers=(dynamic,),
    )

    assert result.exit_code == 0
    assert "install agent.plugin (owner=bootstrap): install" in output[0]


def test_all_orders_static_base_native_actions_and_configuration(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All resolves native actions only after its base component phase succeeds."""
    events: list[str] = []

    def candidates(*_args: object) -> tuple[InstallAction, ...]:
        """Record static preflight candidate resolution."""
        events.append("candidate")
        return (InstallAction(component_id="agent.plugin", argv=("agent", "add")),)

    def dynamic(*_args: object) -> tuple[InstallAction, ...]:
        """Record post-base native inspection and resolve one missing action."""
        events.append("native-inspection")
        return (InstallAction(component_id="agent.plugin", argv=("agent", "add")),)

    def recorded_install(**kwargs: object) -> InstallStageReport:
        """Record the base and action install phases independently."""
        events.append("base" if kwargs["components"] else "assistant-actions")
        return InstallStageReport(exit_code=0, outcomes=())

    monkeypatch.setattr("ballen_config.cli.run_install", recorded_install)
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda *_args, **_kwargs: (
            events.append("configure")
            or ConfigureStageReport(actions=(), changed_count=0)
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.core_doctor_checks", lambda *_args, **_kwargs: ()
    )

    result = run(
        ("all",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: True,
        output=lambda _message: None,
        timestamp=lambda: "fixed",
        install_action_candidate_suppliers=(candidates,),
        install_action_suppliers=(dynamic,),
    )

    assert result.exit_code == 0
    assert tuple(events) == (
        "candidate",
        "base",
        "native-inspection",
        "assistant-actions",
        "configure",
    )


def test_base_install_failure_prevents_native_inspection_and_configuration(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed base phase stops before native resolution and configure."""
    events: list[str] = []

    def candidates(*_args: object) -> tuple[InstallAction, ...]:
        """Return one static action candidate."""
        return (InstallAction(component_id="agent.plugin", argv=("agent", "add")),)

    def dynamic(*_args: object) -> tuple[InstallAction, ...]:
        """Record an invalid post-failure native inspection."""
        events.append("native-inspection")
        return ()

    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **_kwargs: InstallStageReport(
            exit_code=1, outcomes=("core: required-failure",)
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda *_args, **_kwargs: events.append("configure"),
    )

    result = run(
        ("all",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: True,
        output=lambda _message: None,
        timestamp=lambda: "fixed",
        install_action_candidate_suppliers=(candidates,),
        install_action_suppliers=(dynamic,),
    )

    assert result.exit_code == 1
    assert events == []


@pytest.mark.parametrize(
    "candidate,dynamic",
    [
        pytest.param(
            InstallAction(component_id="agent.plugin", argv=("agent", "add")),
            InstallAction(component_id="agent.plugin", argv=("agent", "other")),
            id="argv-drift",
        ),
        pytest.param(
            InstallAction(component_id="agent.plugin", argv=("agent", "add")),
            InstallAction(
                component_id="agent.plugin", argv=("agent", "add"), required=False
            ),
            id="required-flag-drift",
        ),
        pytest.param(
            InstallAction(
                component_id="agent.plugin",
                kind="verified-download",
                argv=("agent", "add", "{artifact}"),
                url="https://example.test/one",
                artifact_name="one.vsix",
                size_bytes=1,
                sha256="0" * 64,
            ),
            InstallAction(
                component_id="agent.plugin",
                kind="verified-download",
                argv=("agent", "add", "{artifact}"),
                url="https://example.test/two",
                artifact_name="two.vsix",
                size_bytes=2,
                sha256="1" * 64,
            ),
            id="verified-download-metadata-drift",
        ),
    ],
)
def test_dynamic_action_must_exactly_match_static_candidate(
    candidate: InstallAction,
    dynamic: InstallAction,
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-ID dynamic action drift is rejected before the action phase runs."""
    install_calls: list[tuple[InstallAction, ...]] = []

    def candidates(*_args: object) -> tuple[InstallAction, ...]:
        """Return the reviewed static authorization action."""
        return (candidate,)

    def dynamic_actions(*_args: object) -> tuple[InstallAction, ...]:
        """Return one post-base action that differs from the authorization."""
        return (dynamic,)

    def recorded_install(**kwargs: object) -> InstallStageReport:
        """Record each install invocation without executing a command."""
        install_calls.append(tuple(kwargs["actions"]))
        return InstallStageReport(exit_code=0, outcomes=())

    monkeypatch.setattr("ballen_config.cli.run_install", recorded_install)

    result = run(
        ("install",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: True,
        output=lambda _message: None,
        timestamp=lambda: "fixed",
        install_action_candidate_suppliers=(candidates,),
        install_action_suppliers=(dynamic_actions,),
    )

    assert result == RunResult(
        exit_code=2, report=StageReport(outcomes=("invalid configuration",))
    )
    assert install_calls == [()]


@pytest.mark.parametrize(
    "stage",
    (
        pytest.param("plan", id="plan"),
        pytest.param("configure", id="configure"),
        pytest.param("doctor", id="doctor"),
    ),
)
@pytest.mark.parametrize(
    "candidate_suppliers,dynamic_suppliers",
    [
        pytest.param((), (lambda *_args: (),), id="missing-candidates"),
        pytest.param((lambda *_args: (),), (), id="missing-dynamic-suppliers"),
    ],
)
def test_unpaired_install_suppliers_fail_closed_for_every_stage(
    stage: str,
    candidate_suppliers: tuple[object, ...],
    dynamic_suppliers: tuple[object, ...],
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Candidate and dynamic supplier declarations always have equal arity."""
    runner = FakeRunner()

    result = run(
        (stage,),
        repo_root=repo_root,
        home=fake_home,
        runner=runner,
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("invalid wiring must not confirm"),
        output=lambda _message: None,
        timestamp=lambda: "fixed",
        install_action_candidate_suppliers=candidate_suppliers,  # type: ignore[arg-type]
        install_action_suppliers=dynamic_suppliers,  # type: ignore[arg-type]
    )

    assert result == RunResult(
        exit_code=2, report=StageReport(outcomes=("invalid configuration",))
    )
    assert runner.commands == []


def test_prepare_returns_two_without_confirmation(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Python dispatcher leaves prepare to the reviewed shell bootstrap."""
    result = run(
        ("prepare",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: pytest.fail("prepare must not confirm"),
        output=lambda _message: None,
        timestamp=lambda: "fixed",
    )
    assert result == RunResult(exit_code=2, report=StageReport())


def test_configure_reports_normalized_action_effects(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configure derives secret-free outcomes from current Task 6 actions."""
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda *_args, **_kwargs: ConfigureStageReport(
            actions=(
                ConfigAction(
                    id="zshrc",
                    destination=".zshrc",
                    outcome="created",
                ),
            ),
            changed_count=1,
        ),
    )

    result = run(
        ("configure",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner(),
        downloader=FakeDownloader(),
        confirm=lambda _prompt: True,
        output=lambda _message: None,
        timestamp=lambda: "fixed",
    )

    assert result == RunResult(
        exit_code=0,
        report=StageReport(
            changed_count=1,
            outcomes=("zshrc: created",),
        ),
    )


def test_main_applies_private_umask(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production main narrows requested file creation to mode 0600."""
    created = tmp_path / "created"

    def fake_run(*_args: object, **_kwargs: object) -> RunResult:
        descriptor = os.open(created, os.O_CREAT | os.O_WRONLY, 0o666)
        os.close(descriptor)
        return RunResult(exit_code=0, report=StageReport())

    monkeypatch.setattr("ballen_config.cli.run", fake_run)
    assert main(()) == 0
    assert stat.S_IMODE(created.stat().st_mode) == 0o600
