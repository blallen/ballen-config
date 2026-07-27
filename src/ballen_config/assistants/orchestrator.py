"""Compose native coding-agent adapters from one desired-state preflight."""

from dataclasses import replace
from typing import Literal

from ballen_config.assistants.checks import assistant_checks
from ballen_config.assistants.claude import (
    ClaudePluginInspectionError,
    claude_configuration,
    plan_claude_plugins,
)
from ballen_config.assistants.claude import (
    install_actions as claude_install_actions,
)
from ballen_config.assistants.codex import (
    CodexPluginInspectionError,
    codex_configuration,
    plan_codex_plugins,
)
from ballen_config.assistants.codex import (
    install_actions as codex_install_actions,
)
from ballen_config.assistants.cursor import (
    CursorExtensionInspectionError,
    plan_cursor_extension_actions,
)
from ballen_config.assistants.cursor import (
    configuration as cursor_configuration,
)
from ballen_config.assistants.cursor import (
    install_actions as cursor_install_actions,
)
from ballen_config.assistants.cursor_plugins import (
    cursor_local_plugin_configuration,
    cursor_marketplace_doctor_checks,
    cursor_marketplace_plan_actions,
)
from ballen_config.assistants.desired_state import (
    AssistantDesiredState,
    AssistantDesiredStateError,
    load_desired_state,
)
from ballen_config.assistants.hooks import hook_contribution
from ballen_config.assistants.models import AgentName
from ballen_config.assistants.skills import configuration as skills_configuration
from ballen_config.configure import (
    ConfigurationContribution,
    merge_configuration_contributions,
)
from ballen_config.doctor import (
    CheckSeverity,
    DoctorCheck,
    DoctorFinding,
    FindingStatus,
)
from ballen_config.install import InstallAction
from ballen_config.models import ResolvedSetup
from ballen_config.planning import PlanAction
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths

type InvocationKey = tuple[RuntimePaths, tuple[str, ...], frozenset[str]]


def _enabled_agents(setup: ResolvedSetup) -> frozenset[str]:
    """Return enabled coding-agent component IDs in a stable set."""
    return frozenset(
        agent for agent in ("cursor", "claude-code", "codex") if setup.is_enabled(agent)
    )


class AssistantOrchestrator:
    """Reuse one preflight-loaded desired state across assistant seams."""

    def __init__(self, paths: RuntimePaths) -> None:
        """Initialize the orchestrator for one approved runtime-path identity.

        Args:
            paths: Approved runtime roots for the caller's bootstrap invocation.
        """
        self.paths = paths
        self._desired: AssistantDesiredState | None = None
        self._key: InvocationKey | None = None

    @staticmethod
    def _invocation_key(setup: ResolvedSetup, paths: RuntimePaths) -> InvocationKey:
        """Create the complete reusable identity for one resolved invocation."""
        return (paths, setup.profiles, frozenset(setup.skipped))

    def _require(
        self, setup: ResolvedSetup, paths: RuntimePaths
    ) -> AssistantDesiredState:
        """Return the preflight result only for its original invocation key."""
        key = self._invocation_key(setup, paths)
        if self._desired is None or self._key != key:
            raise AssistantDesiredStateError("assistant desired-state preflight failed")
        return self._desired

    def preflight(self, setup: ResolvedSetup, paths: RuntimePaths) -> None:
        """Load desired state exactly once before any assistant side effect.

        Args:
            setup: Resolved components, profiles, and skips.
            paths: Approved runtime roots.

        Raises:
            AssistantDesiredStateError: If this orchestrator receives a distinct
                path, profile, or skip identity after its initial preflight.
        """
        key = self._invocation_key(setup, paths)
        if self._key is not None:
            if self._key != key:
                raise AssistantDesiredStateError(
                    "assistant desired-state preflight failed"
                )
            return
        if paths != self.paths:
            raise AssistantDesiredStateError("assistant desired-state preflight failed")
        self._desired = load_desired_state(
            paths.repo_root,
            setup.profiles,
            frozenset(setup.skipped),
        )
        self._key = key

    def install_action_candidates(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
    ) -> tuple[InstallAction, ...]:
        """Return candidates from the preloaded projections."""
        desired = self._require(setup, paths)
        actions: list[InstallAction] = []
        enabled = _enabled_agents(setup)
        if "cursor" in enabled:
            actions.extend(
                plan_cursor_extension_actions(
                    desired.extension_catalog,
                    enabled_agents=enabled,
                    installed=frozenset(),
                    bundled=frozenset(),
                )
            )
        if "claude-code" in enabled:
            actions.extend(
                plan_claude_plugins(
                    desired.plugin_projection(AgentName.CLAUDE),
                    installed=frozenset(),
                )
            )
        if "codex" in enabled:
            actions.extend(
                plan_codex_plugins(
                    desired.plugin_projection(AgentName.CODEX),
                    installed=frozenset(),
                )
            )
        self._assert_unique_actions(actions)
        return tuple(sorted(actions, key=lambda action: action.component_id))

    def install_actions(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
        runner: Runner,
    ) -> tuple[InstallAction, ...]:
        """Inspect and plan each enabled native target."""
        desired = self._require(setup, paths)
        actions: list[InstallAction] = []
        if setup.is_enabled("cursor"):
            actions.extend(
                cursor_install_actions(setup, desired.extension_catalog, runner)
            )
        if setup.is_enabled("claude-code"):
            actions.extend(
                claude_install_actions(
                    setup,
                    desired.plugin_projection(AgentName.CLAUDE),
                    runner,
                )
            )
        if setup.is_enabled("codex"):
            actions.extend(
                codex_install_actions(
                    setup,
                    desired.plugin_projection(AgentName.CODEX),
                    runner,
                )
            )
        self._assert_unique_actions(actions)
        return tuple(sorted(actions, key=lambda action: action.component_id))

    def configuration(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
    ) -> ConfigurationContribution:
        """Compose target configuration from preloaded models."""
        desired = self._require(setup, paths)
        enabled = _enabled_agents(setup)
        cursor_local = (
            cursor_local_plugin_configuration(
                desired.cursor_local_plugin_snapshots(),
            )
            if "cursor" in enabled
            else ConfigurationContribution()
        )
        contribution = merge_configuration_contributions(
            (
                cursor_configuration(setup, paths),
                cursor_local,
                claude_configuration(
                    repo_root=paths.repo_root,
                    home=paths.home,
                    profiles=setup.profiles,
                    enabled=enabled,
                ),
                codex_configuration(
                    repo_root=paths.repo_root,
                    home=paths.home,
                    profiles=setup.profiles,
                    enabled=enabled,
                ),
                hook_contribution(
                    repo_root=paths.repo_root,
                    home=paths.home,
                    enabled=enabled,
                ),
                skills_configuration(setup, paths, desired.skill_catalog),
            )
        )
        return replace(
            contribution,
            specs=tuple(sorted(contribution.specs, key=lambda spec: spec.id)),
        )

    def doctor_checks(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
        runner: Runner,
    ) -> tuple[DoctorCheck, ...]:
        """Diagnose enabled targets from preloaded models."""
        desired = self._require(setup, paths)
        pending_actions: list[InstallAction] = []
        unavailable: list[DoctorCheck] = []
        for agent, error, label in (
            ("cursor", CursorExtensionInspectionError, "Cursor"),
            ("claude-code", ClaudePluginInspectionError, "Claude"),
            ("codex", CodexPluginInspectionError, "Codex"),
        ):
            if not setup.is_enabled(agent):
                continue
            try:
                pending_actions.extend(
                    self.install_actions_for_agent(setup, paths, runner, agent)
                )
            except error:
                unavailable.append(
                    DoctorFinding(
                        id=f"{agent.split('-')[0]}.unavailable",
                        status=FindingStatus.UNAVAILABLE,
                        severity=CheckSeverity.WARNING,
                        message=f"{label} native inspection unavailable",
                    )
                )
        checks = (
            *unavailable,
            *(
                cursor_marketplace_doctor_checks(
                    desired.plugin_projection(
                        AgentName.CURSOR
                    ).cursor_marketplace_plugins
                )
                if setup.is_enabled("cursor")
                else ()
            ),
            *assistant_checks(
                enabled=_enabled_agents(setup),
                paths=paths,
                runner=runner,
                pending_actions=tuple(pending_actions),
            ),
        )
        identifiers = [check.id for check in checks]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate assistant doctor finding ID")
        return tuple(sorted(checks, key=lambda check: check.id))

    def install_actions_for_agent(
        self,
        setup: ResolvedSetup,
        paths: RuntimePaths,
        runner: Runner,
        agent: str,
    ) -> tuple[InstallAction, ...]:
        """Inspect one enabled native agent without reopening desired state."""
        desired = self._require(setup, paths)
        if agent == "cursor":
            return cursor_install_actions(setup, desired.extension_catalog, runner)
        if agent == "claude-code":
            return claude_install_actions(
                setup,
                desired.plugin_projection(AgentName.CLAUDE),
                runner,
            )
        if agent == "codex":
            return codex_install_actions(
                setup,
                desired.plugin_projection(AgentName.CODEX),
                runner,
            )
        raise ValueError(f"unsupported assistant: {agent}")

    def actions(self, setup: ResolvedSetup) -> tuple[PlanAction, ...]:
        """Render resolved inventory without reopening catalogs."""
        desired = self._require(setup, self.paths)
        actions: list[PlanAction] = []
        for resource in desired.resolved_inventory.resources:
            category: Literal["install", "configure", "manual", "diagnostic"]
            if resource.kind == "manual":
                category = "manual"
                action = "complete-manual-step"
            elif resource.kind == "catalog":
                category = "install"
                action = "apply-catalog"
            else:
                category = "configure"
                action = "manage-resource"
            actions.append(
                PlanAction(
                    component_id=resource.id,
                    category=category,
                    action=action,
                    owner=resource.owner.value,
                    required=resource.required,
                )
            )
        if setup.is_enabled("cursor"):
            actions.extend(
                cursor_marketplace_plan_actions(
                    desired.plugin_projection(
                        AgentName.CURSOR
                    ).cursor_marketplace_plugins
                )
            )
        identifiers = [action.component_id for action in actions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate assistant plan action ID")
        return tuple(sorted(actions, key=lambda action: action.component_id))

    @staticmethod
    def _assert_unique_actions(actions: list[InstallAction]) -> None:
        """Reject duplicate native action identities before returning them."""
        identifiers = [action.component_id for action in actions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate assistant install action ID")
