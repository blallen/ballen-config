"""Tests for normalized, non-mutating bootstrap diagnostics."""

import os
from collections.abc import Sequence
from pathlib import Path

from ballen_config.configure import ConfigurationEngine
from ballen_config.doctor import (
    CheckSeverity,
    Doctor,
    DoctorFinding,
    DoctorReport,
    FindingStatus,
    core_doctor_checks,
    run_doctor,
)
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.runner import CommandResult
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore


class FakeRunner:
    """Return captured results without executing native commands."""

    def __init__(self, results: dict[tuple[str, ...], CommandResult]) -> None:
        """Initialize results keyed by exact command."""
        self.results = results
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> CommandResult:
        """Return a result while retaining only the normalized command."""
        normalized = tuple(command)
        self.commands.append(normalized)
        return self.results.get(
            normalized,
            {"returncode": 127, "stdout": "", "stderr": ""},
        )


def home_snapshot(home: Path) -> tuple[tuple[str, int, bytes], ...]:
    """Return a complete structural snapshot of a test home tree."""
    return tuple(
        (
            str(path.relative_to(home)),
            os.lstat(path).st_mode,
            path.read_bytes() if path.is_file() and not path.is_symlink() else b"",
        )
        for path in sorted(home.rglob("*"))
    )


def test_auth_output_is_never_returned(fake_home: Path) -> None:
    """Authentication identity and token-like output remain captured."""
    secret_stdout = "account@example.com token scopes api"  # pragma: allowlist secret
    secret_stderr = "credential-helper token-like stderr"  # pragma: allowlist secret
    runner = FakeRunner(
        {
            ("glab", "auth", "status"): {
                "returncode": 0,
                "stdout": secret_stdout,
                "stderr": secret_stderr,
            }
        }
    )

    report = run_doctor(
        Doctor(runner, fake_home).authentication_checks(enabled=frozenset({"glab"}))
    )

    assert report.finding("gitlab-auth").message == "ready"
    assert secret_stdout not in report.render()
    assert secret_stderr not in report.render()


def test_gitlab_auth_runs_only_when_glab_is_enabled(fake_home: Path) -> None:
    """GitLab auth is checked only when the glab include is selected."""
    doctor = Doctor(FakeRunner({}), fake_home)
    assert "gitlab-auth" not in {
        finding.id for finding in doctor.authentication_checks(enabled=frozenset())
    }
    report = run_doctor(doctor.authentication_checks(enabled=frozenset({"glab"})))
    finding = report.finding("gitlab-auth")
    assert finding.status is FindingStatus.MANUAL
    assert finding.severity is CheckSeverity.WARNING
    assert finding.message == "not authenticated"
    assert report.exit_code == 0


def test_skip_is_informational_not_missing(fake_home: Path) -> None:
    """An explicit skip is healthy, intentional state."""
    report = run_doctor(Doctor(FakeRunner({}), fake_home).skipped_checks(("cursor",)))
    finding = report.finding("cursor")
    assert finding.status is FindingStatus.SKIPPED
    assert finding.severity is CheckSeverity.INFO
    assert report.exit_code == 0


def test_aws_readiness_runs_only_for_fsp(fake_home: Path) -> None:
    """AWS authentication is relevant only to the fsp profile."""
    default = Doctor(
        FakeRunner({}),
        fake_home,
        profiles=("default",),
    ).authentication_checks(enabled=frozenset())
    fsp = Doctor(
        FakeRunner({}),
        fake_home,
        profiles=("default", "fsp"),
    ).authentication_checks(enabled=frozenset())
    assert "aws-auth" not in {finding.id for finding in default}
    assert "aws-auth" in {finding.id for finding in fsp}


def test_core_manual_checks_are_limited_to_cross_cutting_actions(
    fake_home: Path,
) -> None:
    """Doctor reports only the convergent SSH manual check."""
    checks = Doctor(
        FakeRunner({}),
        fake_home,
        profiles=("default", "wsh"),
    ).manual_checks()
    assert {finding.id for finding in checks} == {"ssh-transfer"}
    rendered = run_doctor(checks).render().lower()
    for app_name in ("notion", "browser", "cursor", "claude", "codex"):
        assert app_name not in rendered


def test_required_component_failure_sets_exit_one(fake_home: Path) -> None:
    """A required missing package fails without leaking native output."""
    component = Component(
        id="gh",
        manager=Manager.BREW_FORMULA,
        package="gh",
    )
    report = run_doctor(
        Doctor(
            FakeRunner(
                {
                    ("brew", "list", "--formula", "gh"): {
                        "returncode": 1,
                        "stdout": "secret",
                        "stderr": "token",
                    }
                }
            ),
            fake_home,
        ).component_checks((component,))
    )
    assert report.finding("gh").status is FindingStatus.MISSING
    assert report.exit_code == 1
    assert "secret" not in report.render()
    assert "token" not in report.render()


def test_declared_application_path_satisfies_component(fake_home: Path) -> None:
    """A declared app bundle can satisfy a missing Homebrew receipt."""
    component = Component(
        id="wave",
        manager=Manager.BREW_CASK,
        package="wave",
        application_paths=("/Applications/Wave.app",),
    )
    doctor = Doctor(
        FakeRunner({}),
        fake_home,
        path_exists=lambda path: path == Path("/Applications/Wave.app"),
    )
    finding = doctor.component_checks((component,))[0]
    assert finding.status is FindingStatus.READY


def test_declared_application_path_without_matching_receipt_is_missing(
    fake_home: Path,
) -> None:
    """A vendor-provided path is insufficient without the declared receipt.

    BasicTeX provides the same ``latex`` binary as full MacTeX, so the
    receipt prefix is what distinguishes them. Without a matching receipt,
    the application path alone must not report the component as ready.
    """
    component = Component(
        id="mactex",
        manager=Manager.BREW_CASK,
        package="mactex",
        application_paths=("/Library/TeX/texbin/latex",),
        receipt_prefixes=("org.tug.mactex.gui",),
    )
    runner = FakeRunner(
        {
            ("pkgutil", "--pkgs"): {
                "returncode": 0,
                "stdout": "org.tug.texlive2025\n",
                "stderr": "",
            }
        }
    )
    doctor = Doctor(
        runner,
        fake_home,
        path_exists=lambda path: path == Path("/Library/TeX/texbin/latex"),
    )
    finding = doctor.component_checks((component,))[0]
    assert finding.status is FindingStatus.MISSING


def test_declared_application_path_with_matching_receipt_is_ready(
    fake_home: Path,
) -> None:
    """A vendor-provided path with the declared receipt is ready."""
    component = Component(
        id="mactex",
        manager=Manager.BREW_CASK,
        package="mactex",
        application_paths=("/Library/TeX/texbin/latex",),
        receipt_prefixes=("org.tug.mactex.gui",),
    )
    runner = FakeRunner(
        {
            ("pkgutil", "--pkgs"): {
                "returncode": 0,
                "stdout": "org.tug.mactex.gui2025\norg.tug.texlive2025\n",
                "stderr": "",
            }
        }
    )
    doctor = Doctor(
        runner,
        fake_home,
        path_exists=lambda path: path == Path("/Library/TeX/texbin/latex"),
    )
    finding = doctor.component_checks((component,))[0]
    assert finding.status is FindingStatus.READY


def test_no_application_paths_with_failing_brew_list_is_missing(
    fake_home: Path,
) -> None:
    """A component without declared application paths never vacuously passes.

    Regression guard: ``all()`` over an empty ``application_paths`` tuple is
    vacuously ``True``. The presence check must require a non-empty tuple
    before using ``all()``, or every path-less component would report ready
    regardless of ``brew list`` failing.
    """
    component = Component(
        id="gh",
        manager=Manager.BREW_FORMULA,
        package="gh",
    )
    runner = FakeRunner(
        {
            ("brew", "list", "--formula", "gh"): {
                "returncode": 1,
                "stdout": "",
                "stderr": "",
            }
        }
    )
    doctor = Doctor(runner, fake_home)
    finding = doctor.component_checks((component,))[0]
    assert finding.status is FindingStatus.MISSING


def test_git_component_requires_non_symlink_git_checkout(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    """A symlinked Git destination never counts as a managed checkout."""
    outside = tmp_path / "outside"
    (outside / ".git").mkdir(parents=True)
    (fake_home / ".tool").symlink_to(outside, target_is_directory=True)
    component = Component(
        id="tool",
        manager=Manager.GIT,
        package="https://example.test/tool.git",
        destination=".tool",
        revision="a" * 40,
    )
    finding = Doctor(FakeRunner({}), fake_home).component_checks((component,))[0]
    assert finding.status is FindingStatus.MISSING


def test_uv_tool_present_is_ready(fake_home: Path) -> None:
    """A uv-managed tool listed by name counts as ready."""
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
    )
    runner = FakeRunner(
        {
            ("uv", "tool", "list"): {
                "returncode": 0,
                "stdout": "pre-commit v4.6.0\n- pre-commit\n",
                "stderr": "",
            }
        }
    )
    finding = Doctor(runner, fake_home).component_checks((component,))[0]
    assert finding.status is FindingStatus.READY
    assert runner.commands == [("uv", "tool", "list")]


def test_uv_tool_absent_is_missing(fake_home: Path) -> None:
    """A uv-managed tool absent from the listing counts as missing."""
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
    )
    runner = FakeRunner(
        {
            ("uv", "tool", "list"): {
                "returncode": 0,
                "stdout": "",
                "stderr": "",
            }
        }
    )
    finding = Doctor(runner, fake_home).component_checks((component,))[0]
    assert finding.status is FindingStatus.MISSING
    assert runner.commands == [("uv", "tool", "list")]


def test_uv_tool_entrypoint_line_does_not_produce_false_ready(
    fake_home: Path,
) -> None:
    """An entrypoint line's dash prefix never matches a package name."""
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
    )
    runner = FakeRunner(
        {
            ("uv", "tool", "list"): {
                "returncode": 0,
                "stdout": "ruff v0.6.0\n- ruff\n- pre-commit\n",
                "stderr": "",
            }
        }
    )
    finding = Doctor(runner, fake_home).component_checks((component,))[0]
    assert finding.status is FindingStatus.MISSING
    assert runner.commands == [("uv", "tool", "list")]


def test_uv_tool_list_is_resolved_once_for_every_component(fake_home: Path) -> None:
    """One listing answers every uv_tool component in a check pass."""
    components = tuple(
        Component(id=name, manager=Manager.UV_TOOL, package=name)
        for name in ("pre-commit", "ruff")
    )
    runner = FakeRunner(
        {
            ("uv", "tool", "list"): {
                "returncode": 0,
                "stdout": "pre-commit v4.6.0\n- pre-commit\nruff v0.15.1\n- ruff\n",
                "stderr": "",
            }
        }
    )
    findings = Doctor(runner, fake_home).component_checks(components)
    assert [finding.status for finding in findings] == [
        FindingStatus.READY,
        FindingStatus.READY,
    ]
    assert runner.commands == [("uv", "tool", "list")]


def test_unreadable_uv_tool_list_is_missing(fake_home: Path) -> None:
    """An unreadable listing is missing even when stdout names the tool."""
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
    )
    runner = FakeRunner(
        {
            ("uv", "tool", "list"): {
                "returncode": 127,
                "stdout": "pre-commit v4.6.0\n- pre-commit\n",
                "stderr": "",
            }
        }
    )
    finding = Doctor(runner, fake_home).component_checks((component,))[0]
    assert finding.status is FindingStatus.MISSING
    assert runner.commands == [("uv", "tool", "list")]


def test_homebrew_prefix_output_is_redacted(fake_home: Path) -> None:
    """The machine-specific Homebrew path is never rendered."""
    prefix = "/machine/private/homebrew"
    finding = Doctor(
        FakeRunner(
            {
                ("brew", "--prefix"): {
                    "returncode": 0,
                    "stdout": prefix,
                    "stderr": "",
                }
            }
        ),
        fake_home,
    ).homebrew_check()
    report = run_doctor((finding,))
    assert finding.status is FindingStatus.READY
    assert prefix not in report.render()


def test_doctor_report_sorts_findings_deterministically() -> None:
    """Direct report construction normalizes finding order."""
    report = DoctorReport(
        findings=(
            DoctorFinding(
                id="z-last",
                status=FindingStatus.MANUAL,
                severity=CheckSeverity.WARNING,
                message="manual",
            ),
            DoctorFinding(
                id="a-first",
                status=FindingStatus.READY,
                severity=CheckSeverity.INFO,
                message="ready",
            ),
        )
    )
    assert [finding.id for finding in report.findings] == ["a-first", "z-last"]


def test_core_doctor_check_order_is_stable(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    """Core checks retain their declared construction order before reporting."""
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    component = Component(
        id="gh",
        manager=Manager.BREW_FORMULA,
        package="gh",
    )
    resolved = ResolvedSetup(
        profiles=("default",),
        components=(component,),
        skipped=("cursor",),
    )
    checks = core_doctor_checks(
        resolved,
        paths,
        FakeRunner({}),
        engine=ConfigurationEngine(paths=paths, state_store=StateStore(paths)),
        specs=(),
    )
    assert [finding.id for finding in checks] == [
        "homebrew",
        "gh",
        "github-auth",
        "ssh-transfer",
        "cursor",
    ]


def test_doctor_does_not_mutate_home(fake_home: Path) -> None:
    """Authentication and manual checks preserve the complete home snapshot."""
    (fake_home / ".ssh").mkdir(mode=0o700)
    before = home_snapshot(fake_home)
    doctor = Doctor(
        FakeRunner(
            {
                ("gh", "auth", "status"): {
                    "returncode": 1,
                    "stdout": "token-like stdout",
                    "stderr": "token-like stderr",
                }
            }
        ),
        fake_home,
    )

    report = run_doctor(
        (
            *doctor.authentication_checks(enabled=frozenset()),
            *doctor.manual_checks(),
        )
    )

    assert home_snapshot(fake_home) == before
    assert "token-like" not in report.render()
