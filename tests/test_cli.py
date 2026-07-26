from __future__ import annotations

import os
import stat
from collections.abc import Sequence
from pathlib import Path

import pytest

from ballen_config.cli import (
    STAGES,
    RunResult,
    StageReport,
    main,
    parse_args,
    run,
)
from ballen_config.configure import ConfigAction, ConfigureStageReport
from ballen_config.doctor import CheckSeverity, DoctorFinding, FindingStatus
from ballen_config.install import InstallStageReport
from ballen_config.runner import CommandResult


@pytest.fixture
def repeated_selection_arguments() -> list[str]:
    """Return ordered repeated include and skip arguments."""
    return [
        "plan",
        "--profile",
        "work",
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
    options = parse_args(repeated_selection_arguments)

    assert options.stage == "plan"
    assert options.request.profile == "work"
    assert options.request.includes == ("mactex", "signal")
    assert options.request.skips == ("cursor", "codex")


def test_cli_defaults_to_all_and_default_profile() -> None:
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


@pytest.mark.parametrize("stage", ["install", "configure", "all"])
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
        ("unknown-stage",),
        ("plan", "--profile", "unknown"),
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
