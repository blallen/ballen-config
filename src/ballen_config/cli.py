"""Typed bootstrap command-line parsing and stage dispatch."""

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict, ValidationError
from yaml import YAMLError

from ballen_config.assistants import (
    ClaudePluginInspectionError,
    CodexPluginInspectionError,
    CursorExtensionInspectionError,
    SkillCollisionError,
    SkillRenameBlockedError,
)
from ballen_config.assistants.desired_state import AssistantDesiredStateError
from ballen_config.assistants.orchestrator import AssistantOrchestrator
from ballen_config.configure import (
    ConfigurationContribution,
    ConfigurationEngine,
    ConfigurationPlanContributor,
    ConfigurationSupplier,
    core_configuration,
    core_validators,
    merge_configuration_contributions,
    run_configure,
)
from ballen_config.doctor import (
    DoctorCheckSupplier,
    core_doctor_checks,
    run_doctor,
)
from ballen_config.install import (
    Downloader,
    HttpsDownloader,
    InstallAction,
    InstallActionCandidateSupplier,
    InstallActionSupplier,
    run_install,
)
from ballen_config.manifests import ManifestRepository
from ballen_config.models import (
    Component,
    Manager,
    ResolutionRequest,
    ResolvedSetup,
)
from ballen_config.planning import (
    ComponentState,
    CoreManualContributor,
    Inspector,
    PlanAction,
    PlanContributor,
    build_resolved_plan,
    format_plan,
)
from ballen_config.probes import brew_artifact_present, uv_tool_listed
from ballen_config.runner import CommandResult, Runner, SubprocessRunner
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore

STAGES = ("all", "prepare", "plan", "install", "configure", "doctor")

type PreflightSupplier = Callable[[ResolvedSetup, RuntimePaths], None]


@dataclass(frozen=True)
class CliOptions:
    """Parsed bootstrap options."""

    stage: str
    request: ResolutionRequest


class StageReport(BaseModel):
    """Normalized effects from one CLI invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    changed_count: int = 0
    outcomes: tuple[str, ...] = ()


class RunResult(BaseModel):
    """Exit status plus a secret-free programmatic report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exit_code: int
    report: StageReport


class InstallActionCandidatePlanContributor:
    """Expose preflight install actions as redacted plan rows."""

    def __init__(self, actions: Sequence[InstallAction]) -> None:
        """Initialize with static action declarations.

        Args:
            actions: Candidate actions validated before plan rendering.
        """
        self.actions_to_render = tuple(actions)

    def actions(self, _resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        """Return install plan rows without command or state details."""
        return tuple(
            PlanAction(
                component_id=action.component_id,
                category="install",
                action="install",
                owner="bootstrap",
                required=action.required,
            )
            for action in self.actions_to_render
        )


class ResolvedInspector:
    """Read-only installation inspector for resolved components."""

    def __init__(
        self,
        runner: Runner,
        components: Sequence[Component],
        home: Path,
    ) -> None:
        """Initialize the read-only component inspection boundary.

        Args:
            runner: Captured subprocess boundary.
            components: Resolved components keyed internally by identifier.
            home: Approved user home directory.
        """
        self.runner = runner
        self.components = {component.id: component for component in components}
        self.home = home
        # `uv tool list` returns every installed tool, so one call answers every
        # uv_tool component this inspector is asked about.
        self._uv_listing: CommandResult | None = None

    def state(self, component_id: str) -> ComponentState:
        """Return normalized structural state for a resolved component.

        Args:
            component_id: Resolved component identifier.

        Returns:
            Present when an app path, Homebrew package, uv-managed tool, or
            safe Git checkout exists; otherwise missing.
        """
        component = self.components[component_id]
        if component.manager in {Manager.BREW_FORMULA, Manager.BREW_CASK}:
            if brew_artifact_present(
                component.application_paths,
                component.receipt_prefixes,
                Path.exists,
                lambda: self.runner.run(("pkgutil", "--pkgs")),
            ):
                return ComponentState.PRESENT
            flag = (
                "--formula" if component.manager is Manager.BREW_FORMULA else "--cask"
            )
            result = self.runner.run(("brew", "list", flag, component.package))
            return (
                ComponentState.PRESENT
                if result["returncode"] == 0
                else ComponentState.MISSING
            )
        if component.manager is Manager.UV_TOOL:
            if self._uv_listing is None:
                self._uv_listing = self.runner.run(("uv", "tool", "list"))
            return (
                ComponentState.PRESENT
                if self._uv_listing["returncode"] == 0
                and uv_tool_listed(self._uv_listing["stdout"], component.package)
                else ComponentState.MISSING
            )
        if component.destination is None:
            raise ValueError(f"git component lacks destination: {component.id}")
        destination = self.home / component.destination
        return (
            ComponentState.PRESENT
            if not destination.is_symlink() and (destination / ".git").is_dir()
            else ComponentState.MISSING
        )


def parse_args(arguments: Sequence[str] | None = None) -> CliOptions:
    """Parse bootstrap stage and component selection arguments.

    Args:
        arguments: Arguments to parse, or ``None`` to use process arguments.

    Returns:
        Typed CLI options with ordered include and skip selections.
    """
    parser = argparse.ArgumentParser(prog="bootstrap")
    parser.add_argument("stage", nargs="?", choices=STAGES, default="all")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--skip", action="append", default=[])
    namespace = parser.parse_args(arguments)
    return CliOptions(
        stage=namespace.stage,
        request=ResolutionRequest(
            profile=namespace.profile,
            includes=tuple(namespace.include),
            skips=tuple(namespace.skip),
        ),
    )


def run(
    arguments: Sequence[str],
    *,
    repo_root: Path,
    home: Path,
    runner: Runner,
    downloader: Downloader,
    confirm: Callable[[str], bool],
    output: Callable[[str], None],
    timestamp: Callable[[], str],
    preflight_suppliers: Sequence[PreflightSupplier] = (),
    install_action_candidate_suppliers: Sequence[InstallActionCandidateSupplier] = (),
    install_action_suppliers: Sequence[InstallActionSupplier] = (),
    configuration_suppliers: Sequence[ConfigurationSupplier] = (),
    doctor_configuration_suppliers: Sequence[ConfigurationSupplier] | None = None,
    doctor_check_suppliers: Sequence[DoctorCheckSupplier] = (),
    plan_contributors: Sequence[PlanContributor] = (),
) -> RunResult:
    """Execute one validated stage with all side effects injected.

    Args:
        arguments: Command-line stage and selection arguments.
        repo_root: Repository containing reviewed manifests and sources.
        home: Approved destination home.
        runner: Captured subprocess boundary.
        downloader: Verified-download boundary for install actions.
        confirm: Interactive mutation confirmation boundary.
        output: Normalized output sink.
        timestamp: Private backup timestamp supplier.
        preflight_suppliers: Desired-state validation before every other seam.
        install_action_candidate_suppliers: Static extension installation declarations.
        install_action_suppliers: Post-base native-state installation resolvers.
        configuration_suppliers: Extension configuration declarations.
        doctor_configuration_suppliers: Read-only extension configuration declarations.
        doctor_check_suppliers: Extension diagnostic checks.
        plan_contributors: Additional structural plan contributors.

    Returns:
        Normalized exit status and effects.
    """
    if len(install_action_candidate_suppliers) != len(install_action_suppliers):
        return RunResult(
            exit_code=2,
            report=StageReport(outcomes=("invalid configuration",)),
        )
    try:
        options = parse_args(arguments)
        if options.stage == "prepare":
            return RunResult(exit_code=2, report=StageReport())
        paths = RuntimePaths.from_roots(repo_root=repo_root, home=home)
        repository = ManifestRepository.load(repo_root / "manifests")
        resolved = repository.resolve(options.request)
        for supplier in preflight_suppliers:
            supplier(resolved, paths)
        candidate_actions: tuple[InstallAction, ...] = ()
        if options.stage in {"plan", "install", "all"}:
            candidate_actions = tuple(
                action
                for supplier in install_action_candidate_suppliers
                for action in supplier(resolved, paths)
            )
            identifiers = [component.id for component in resolved.components] + [
                action.component_id for action in candidate_actions
            ]
            if len(identifiers) != len(set(identifiers)):
                return RunResult(
                    exit_code=2,
                    report=StageReport(outcomes=("duplicate install action IDs",)),
                )

        core = replace(
            core_configuration(resolved, paths), validators=core_validators(runner)
        )
        active_configuration_suppliers = (
            doctor_configuration_suppliers
            if options.stage == "doctor" and doctor_configuration_suppliers is not None
            else configuration_suppliers
        )
        supplied = tuple(
            supplier(resolved, paths) for supplier in active_configuration_suppliers
        )
        configuration = merge_configuration_contributions((core, *supplied))
        engine = ConfigurationEngine(
            paths=paths,
            state_store=StateStore(paths),
            timestamp=timestamp(),
            renderers=configuration.renderers,
            validators=configuration.validators,
        )

        def selected_configuration(
            resolved: ResolvedSetup,
            paths: RuntimePaths,
        ) -> ConfigurationContribution:
            del resolved, paths
            return configuration

        configuration_contributor = cast(
            PlanContributor,
            ConfigurationPlanContributor(engine, selected_configuration),
        )
        inspector: Inspector = ResolvedInspector(
            runner,
            resolved.components,
            paths.home,
        )
        plan = build_resolved_plan(
            resolved,
            profile=options.request.profile,
            inspector=inspector,
            contributors=(
                InstallActionCandidatePlanContributor(candidate_actions),
                configuration_contributor,
                *plan_contributors,
            ),
        )
    except SystemExit as error:
        if error.code == 0:
            return RunResult(exit_code=0, report=StageReport())
        return RunResult(
            exit_code=2,
            report=StageReport(outcomes=("invalid configuration",)),
        )
    except AssistantDesiredStateError:
        return RunResult(
            exit_code=2,
            report=StageReport(outcomes=("assistant desired-state preflight failed",)),
        )
    except SkillCollisionError as error:
        return RunResult(
            exit_code=2,
            report=StageReport(outcomes=(error.outcome(),)),
        )
    except SkillRenameBlockedError as error:
        return RunResult(
            exit_code=2,
            report=StageReport(outcomes=(error.outcome(),)),
        )
    except (OSError, ValidationError, ValueError, YAMLError):
        return RunResult(
            exit_code=2,
            report=StageReport(outcomes=("invalid configuration",)),
        )

    output(format_plan(plan))
    if options.stage == "plan":
        return RunResult(exit_code=0, report=StageReport())

    def install_stage() -> RunResult:
        base_report = run_install(
            components=resolved.components,
            actions=(),
            runner=runner,
            paths=paths,
            state_store=StateStore(paths),
            downloader=downloader,
        )
        if base_report.exit_code != 0:
            return RunResult(
                exit_code=base_report.exit_code,
                report=StageReport(outcomes=base_report.outcomes),
            )
        try:
            resolved_actions = tuple(
                action
                for supplier in install_action_suppliers
                for action in supplier(resolved, paths, runner)
            )
        except (
            CursorExtensionInspectionError,
            ClaudePluginInspectionError,
            CodexPluginInspectionError,
        ):
            return RunResult(
                exit_code=1,
                report=StageReport(outcomes=("native assistant inspection failed",)),
            )
        component_ids = {component.id for component in resolved.components}
        candidate_by_id = {action.component_id: action for action in candidate_actions}
        action_ids = [action.component_id for action in resolved_actions]
        if (
            len(action_ids) != len(set(action_ids))
            or component_ids.intersection(action_ids)
            or any(
                candidate_by_id.get(action.component_id) != action
                for action in resolved_actions
            )
        ):
            return RunResult(
                exit_code=2,
                report=StageReport(outcomes=("invalid configuration",)),
            )
        if not resolved_actions:
            return RunResult(
                exit_code=base_report.exit_code,
                report=StageReport(outcomes=base_report.outcomes),
            )
        action_report = run_install(
            components=(),
            actions=resolved_actions,
            runner=runner,
            paths=paths,
            state_store=StateStore(paths),
            downloader=downloader,
        )
        return RunResult(
            exit_code=action_report.exit_code,
            report=StageReport(
                outcomes=(*base_report.outcomes, *action_report.outcomes)
            ),
        )

    def configure_stage() -> RunResult:
        try:
            report = run_configure(
                engine,
                configuration.specs,
                skill_renames=configuration.skill_renames,
            )
        except SkillRenameBlockedError as error:
            return RunResult(
                exit_code=2,
                report=StageReport(outcomes=(error.outcome(),)),
            )
        return RunResult(
            exit_code=0,
            report=StageReport(
                changed_count=report.changed_count,
                outcomes=tuple(
                    f"{action.id}: {action.outcome}" for action in report.actions
                ),
            ),
        )

    def doctor_stage() -> RunResult:
        checks = list(
            core_doctor_checks(
                resolved,
                paths,
                runner,
                engine=engine,
                specs=configuration.specs,
            )
        )
        for supplier in doctor_check_suppliers:
            checks.extend(supplier(resolved, paths, runner))
        finding_ids = [check.id for check in checks]
        if len(finding_ids) != len(set(finding_ids)):
            return RunResult(
                exit_code=2,
                report=StageReport(outcomes=("duplicate doctor finding IDs",)),
            )
        report = run_doctor(checks)
        output(report.render())
        return RunResult(
            exit_code=report.exit_code,
            report=StageReport(
                outcomes=tuple(
                    f"{finding.id}: {finding.status.value}"
                    for finding in report.findings
                )
            ),
        )

    if options.stage == "doctor":
        return doctor_stage()
    if not confirm("Apply the displayed bootstrap changes?"):
        return RunResult(
            exit_code=0,
            report=StageReport(outcomes=("declined",)),
        )
    if options.stage == "install":
        return install_stage()
    if options.stage == "configure":
        return configure_stage()

    installed = install_stage()
    if installed.exit_code != 0:
        return installed
    configured = configure_stage()
    if configured.exit_code != 0:
        return configured
    diagnosed = doctor_stage()
    return RunResult(
        exit_code=diagnosed.exit_code,
        report=StageReport(
            changed_count=configured.report.changed_count,
            outcomes=(
                *installed.report.outcomes,
                *configured.report.outcomes,
                *diagnosed.report.outcomes,
            ),
        ),
    )


def main(arguments: Sequence[str] | None = None) -> int:
    """Construct production dependencies and return the process exit code.

    Args:
        arguments: Explicit arguments, or ``None`` for process arguments.

    Returns:
        Normalized process exit code.
    """
    previous_umask = os.umask(0o077)
    try:
        repo_root = Path(__file__).resolve().parents[2]
        paths = RuntimePaths.from_roots(repo_root=repo_root, home=Path.home())
        assistants = AssistantOrchestrator(paths)
        result = run(
            tuple(sys.argv[1:] if arguments is None else arguments),
            repo_root=repo_root,
            home=Path.home(),
            runner=SubprocessRunner(),
            downloader=HttpsDownloader(),
            confirm=lambda prompt: input(f"{prompt} [y/N] ").lower() == "y",
            output=print,
            timestamp=lambda: datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            preflight_suppliers=(assistants.preflight,),
            install_action_candidate_suppliers=(assistants.install_action_candidates,),
            install_action_suppliers=(assistants.install_actions,),
            configuration_suppliers=(
                cast(ConfigurationSupplier, assistants.configuration),
            ),
            doctor_configuration_suppliers=(
                cast(ConfigurationSupplier, assistants.diagnostic_configuration),
            ),
            doctor_check_suppliers=(assistants.doctor_checks,),
            plan_contributors=(
                CoreManualContributor(),
                assistants,
            ),
        )
        for outcome in result.report.outcomes:
            print(outcome)
        return result.exit_code
    finally:
        os.umask(previous_umask)
