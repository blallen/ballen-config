"""Normalized, non-mutating bootstrap readiness checks."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable, Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from ballen_config.configure import ConfigurationEngine, ManagedSpec
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths


class CheckSeverity(StrEnum):
    """Doctor result severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingStatus(StrEnum):
    """Normalized resource state."""

    READY = "ready"
    MISSING = "missing"
    DRIFT = "drift"
    SKIPPED = "skipped"
    MANUAL = "manual"
    UNAVAILABLE = "unavailable"


class DoctorFinding(BaseModel):
    """One normalized diagnostic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    status: FindingStatus
    severity: CheckSeverity
    message: str


type DoctorCheck = DoctorFinding


class DoctorReport(BaseModel):
    """Deterministic doctor findings and exit semantics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    findings: tuple[DoctorFinding, ...]

    @field_validator("findings")
    @classmethod
    def sort_findings(
        cls, findings: tuple[DoctorFinding, ...]
    ) -> tuple[DoctorFinding, ...]:
        """Sort findings by stable identifier.

        Args:
            findings: Normalized findings in arbitrary supplier order.

        Returns:
            Findings in deterministic identifier order.
        """
        return tuple(sorted(findings, key=lambda finding: finding.id))

    @property
    def exit_code(self) -> int:
        """Return one only when a required check failed."""
        return int(
            any(finding.severity is CheckSeverity.ERROR for finding in self.findings)
        )

    def finding(self, finding_id: str) -> DoctorFinding:
        """Return a finding by stable identifier.

        Args:
            finding_id: Identifier to locate.

        Returns:
            The matching normalized finding.

        Raises:
            LookupError: If the identifier is absent.
        """
        for finding in self.findings:
            if finding.id == finding_id:
                return finding
        raise LookupError(f"unknown doctor finding: {finding_id}")

    def render(self) -> str:
        """Render normalized fields without native command output."""
        return "\n".join(
            f"{finding.id}: {finding.status.value} - {finding.message}"
            for finding in self.findings
        )


def run_doctor(checks: Sequence[DoctorCheck]) -> DoctorReport:
    """Package already-normalized, non-mutating checks deterministically.

    Args:
        checks: Normalized findings from core and extension suppliers.

    Returns:
        A deterministic report with normalized exit semantics.
    """
    return DoctorReport(findings=tuple(checks))


class Doctor:
    """Run non-mutating checks without returning captured command output."""

    def __init__(
        self,
        runner: Runner,
        home: Path,
        profiles: tuple[str, ...] = ("default",),
        path_exists: Callable[[Path], bool] = Path.exists,
    ) -> None:
        """Initialize read-only diagnostic dependencies.

        Args:
            runner: Captured subprocess boundary.
            home: Approved user home directory.
            profiles: Resolved profile names.
            path_exists: Injectable application-path predicate.
        """
        self.runner = runner
        self.home = home
        self.profiles = profiles
        self.path_exists = path_exists

    def component_checks(
        self,
        components: Sequence[Component],
    ) -> tuple[DoctorCheck, ...]:
        """Check resolved packages without exposing native output.

        Args:
            components: Resolved installable components.

        Returns:
            One normalized check per component in input order.
        """
        checks: list[DoctorFinding] = []
        for component in components:
            if component.manager in {
                Manager.BREW_FORMULA,
                Manager.BREW_CASK,
            }:
                type_flag = (
                    "--formula"
                    if component.manager is Manager.BREW_FORMULA
                    else "--cask"
                )
                result = self.runner.run(("brew", "list", type_flag, component.package))
                present = result["returncode"] == 0 or any(
                    self.path_exists(Path(path)) for path in component.application_paths
                )
            else:
                assert component.destination is not None
                destination = self.home / component.destination
                present = (
                    not destination.is_symlink() and (destination / ".git").is_dir()
                )
            checks.append(
                DoctorFinding(
                    id=component.id,
                    status=(FindingStatus.READY if present else FindingStatus.MISSING),
                    severity=(
                        CheckSeverity.INFO
                        if present
                        else (
                            CheckSeverity.ERROR
                            if component.required
                            else CheckSeverity.WARNING
                        )
                    ),
                    message="ready" if present else "not installed",
                )
            )
        return tuple(checks)

    def homebrew_check(self) -> DoctorCheck:
        """Check Homebrew without returning its machine-specific prefix."""
        result = self.runner.run(("brew", "--prefix"))
        ready = result["returncode"] == 0
        return DoctorFinding(
            id="homebrew",
            status=FindingStatus.READY if ready else FindingStatus.MISSING,
            severity=CheckSeverity.INFO if ready else CheckSeverity.ERROR,
            message="ready" if ready else "not installed",
        )

    def managed_checks(
        self,
        engine: ConfigurationEngine,
        specs: Sequence[ManagedSpec],
    ) -> tuple[DoctorCheck, ...]:
        """Convert read-only configuration actions into drift findings.

        Args:
            engine: Hardened configuration engine used only for planning.
            specs: Managed configuration declarations.

        Returns:
            Normalized configuration readiness findings.
        """
        return tuple(
            DoctorFinding(
                id=f"managed-{action.id}",
                status=(
                    FindingStatus.READY
                    if action.outcome == "unchanged"
                    else FindingStatus.DRIFT
                ),
                severity=(
                    CheckSeverity.INFO
                    if action.outcome == "unchanged"
                    else CheckSeverity.WARNING
                ),
                message=(
                    "ready"
                    if action.outcome == "unchanged"
                    else "configuration differs"
                ),
            )
            for action in engine.plan(specs)
        )

    def authentication_checks(self) -> tuple[DoctorCheck, ...]:
        """Check relevant authentication without exposing identity output."""
        checks: list[DoctorFinding] = []
        commands: list[tuple[str, tuple[str, ...]]] = [
            ("github-auth", ("gh", "auth", "status")),
            ("gitlab-auth", ("glab", "auth", "status")),
        ]
        if "work" in self.profiles:
            commands.append(("aws-auth", ("aws", "sts", "get-caller-identity")))
        for finding_id, command in commands:
            result = self.runner.run(command)
            ready = result["returncode"] == 0
            checks.append(
                DoctorFinding(
                    id=finding_id,
                    status=(FindingStatus.READY if ready else FindingStatus.MANUAL),
                    severity=(CheckSeverity.INFO if ready else CheckSeverity.WARNING),
                    message="ready" if ready else "not authenticated",
                )
            )
        return tuple(checks)

    def skipped_checks(self, skipped: tuple[str, ...]) -> tuple[DoctorCheck, ...]:
        """Report explicit skips as intentional informational state.

        Args:
            skipped: Stable skip identifiers from resolution.

        Returns:
            Informational skipped findings.
        """
        return tuple(
            DoctorFinding(
                id=name,
                status=FindingStatus.SKIPPED,
                severity=CheckSeverity.INFO,
                message="intentionally skipped",
            )
            for name in skipped
        )

    def manual_checks(self) -> tuple[DoctorCheck, ...]:
        """Return only core-owned SSH and IT-managed manual actions."""
        try:
            ssh_mode = stat.S_IMODE(os.lstat(self.home / ".ssh").st_mode)
        except FileNotFoundError:
            ssh_ready = False
        else:
            ssh_ready = ssh_mode == 0o700
        return (
            DoctorFinding(
                id="ssh-transfer",
                status=(FindingStatus.READY if ssh_ready else FindingStatus.MANUAL),
                severity=(CheckSeverity.INFO if ssh_ready else CheckSeverity.WARNING),
                message=(
                    "directory permissions ready"
                    if ssh_ready
                    else "follow secure SSH transfer guide"
                ),
            ),
            DoctorFinding(
                id="it-managed-applications",
                status=FindingStatus.MANUAL,
                severity=CheckSeverity.INFO,
                message="complete the IT-managed application checklist",
            ),
        )


type DoctorCheckSupplier = Callable[
    [ResolvedSetup, RuntimePaths, Runner],
    Sequence[DoctorCheck],
]


def core_doctor_checks(
    resolved: ResolvedSetup,
    paths: RuntimePaths,
    runner: Runner,
    *,
    engine: ConfigurationEngine,
    specs: Sequence[ManagedSpec],
) -> tuple[DoctorCheck, ...]:
    """Build every production core check without mutation.

    Args:
        resolved: Resolved profiles, components, and skips.
        paths: Approved runtime filesystem roots.
        runner: Captured subprocess boundary.
        engine: Hardened configuration engine used only for planning.
        specs: Managed configuration declarations.

    Returns:
        Core checks ordered as Homebrew, components, managed configuration,
        authentication, manual actions, and explicit skips.
    """
    doctor = Doctor(runner, paths.home, profiles=resolved.profiles)
    return (
        doctor.homebrew_check(),
        *doctor.component_checks(resolved.components),
        *doctor.managed_checks(engine, specs),
        *doctor.authentication_checks(),
        *doctor.manual_checks(),
        *doctor.skipped_checks(resolved.skipped),
    )
