"""Public typed API for portable coding-agent inventory declarations."""

from __future__ import annotations

from typing import Literal

from ballen_config.assistants.checks import assistant_checks
from ballen_config.assistants.claude import (
    ClaudePluginInspectionError,
    ClaudeSettingsError,
    ClaudeStableSettings,
    claude_configuration,
    claude_instruction_renderer,
    claude_settings_renderer,
    load_stable_settings,
    plan_claude_plugins,
)
from ballen_config.assistants.claude import (
    install_actions as claude_install_actions,
)
from ballen_config.assistants.codex import (
    CodexPluginInspectionError,
    CodexSettingsError,
    CodexStableSettings,
    codex_configuration,
    codex_instruction_renderer,
    codex_settings_renderer,
    plan_codex_plugins,
)
from ballen_config.assistants.codex import (
    install_actions as codex_install_actions,
)
from ballen_config.assistants.codex import (
    load_stable_settings as load_codex_stable_settings,
)
from ballen_config.assistants.cursor import (
    CursorExtensionInspectionError,
    CursorExtensionPackage,
    ExtensionState,
    cursor_rules_renderer,
    cursor_settings_renderer,
    deep_merge,
    jj_graph_action,
    plan_cursor_extension_actions,
    read_bundled_extensions,
    render_settings,
    resolve_extensions,
)
from ballen_config.assistants.cursor import (
    configuration as cursor_configuration,
)
from ballen_config.assistants.cursor import (
    install_actions as cursor_install_actions,
)
from ballen_config.assistants.hooks import (
    ClaudeHookFragment,
    CursorRegistration,
    claude_hook_fragment,
    cursor_hook_renderer,
    cursor_registration,
    hook_contribution,
    validate_hook_source,
)
from ballen_config.assistants.instructions import render_native_instructions
from ballen_config.assistants.inventory import load_inventory, resolve_inventory
from ballen_config.assistants.models import (
    AgentName,
    AssistantInventory,
    CatalogKind,
    CatalogResource,
    ExtensionCatalog,
    ExtensionSpec,
    FileResource,
    HookResource,
    ManualResource,
    Marketplace,
    PluginCatalog,
    PluginSpec,
    PortableResource,
    ResourceBase,
    SkillCatalog,
    SkillSpec,
)
from ballen_config.assistants.skills import (
    SkillCollisionError,
    SkillCopyAction,
    hash_skill_tree,
    managed_tree_spec,
    plan_skill_copies,
)
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


def _enabled_agents(setup: ResolvedSetup) -> frozenset[str]:
    """Return enabled coding-agent component IDs in a stable set."""
    return frozenset(
        agent for agent in ("cursor", "claude-code", "codex") if setup.is_enabled(agent)
    )


def install_actions(
    setup: ResolvedSetup, paths: RuntimePaths, runner: Runner
) -> tuple[InstallAction, ...]:
    """Combine agent-native installation planners without duplicate IDs.

    Each adapter owns its own whole-agent skip and native inspection boundary.
    """
    actions = tuple(
        action
        for supplier in (
            cursor_install_actions,
            claude_install_actions,
            codex_install_actions,
        )
        for action in supplier(setup, paths, runner)
    )
    identifiers = [action.component_id for action in actions]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate assistant install action ID")
    return tuple(sorted(actions, key=lambda action: action.component_id))


def install_action_candidates(
    setup: ResolvedSetup, paths: RuntimePaths
) -> tuple[InstallAction, ...]:
    """Return every selected native action without inspecting live agent state.

    Args:
        setup: Fully resolved component and profile selection.
        paths: Approved checkout and runtime roots.

    Returns:
        Deterministically ordered possible Cursor, Claude, and Codex actions.

    Raises:
        ValueError: If reviewed catalogs produce duplicate action identifiers.
    """
    enabled = _enabled_agents(setup)
    actions: list[InstallAction] = []
    if "cursor" in enabled:
        actions.extend(
            plan_cursor_extension_actions(
                paths.repo_root / "assistants/cursor/extensions.yaml",
                enabled_agents=enabled,
                installed=frozenset(),
                bundled=frozenset(),
            )
        )
    if "claude-code" in enabled:
        actions.extend(
            plan_claude_plugins(
                paths.repo_root / "assistants/claude/plugins.yaml",
                profiles=setup.profiles,
                installed=frozenset(),
                known_marketplaces=frozenset(),
            )
        )
    if "codex" in enabled:
        actions.extend(
            plan_codex_plugins(
                paths.repo_root / "assistants/codex/plugins.yaml",
                profiles=setup.profiles,
                installed=frozenset(),
                known_marketplaces=frozenset(),
            )
        )
    identifiers = [action.component_id for action in actions]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate assistant install action ID")
    return tuple(sorted(actions, key=lambda action: action.component_id))


def configuration(
    setup: ResolvedSetup, paths: RuntimePaths
) -> ConfigurationContribution:
    """Compose enabled agent configuration, shared skills, and hook resources."""
    enabled = _enabled_agents(setup)
    contribution = merge_configuration_contributions(
        (
            cursor_configuration(setup, paths),
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
                repo_root=paths.repo_root, home=paths.home, enabled=enabled
            ),
            skills_configuration(setup, paths),
        )
    )
    return contribution.model_copy(
        update={"specs": tuple(sorted(contribution.specs, key=lambda spec: spec.id))}
    )


def doctor_checks(
    setup: ResolvedSetup, paths: RuntimePaths, runner: Runner
) -> tuple[DoctorCheck, ...]:
    """Return redacted, unique diagnostics for enabled coding agents."""
    pending_actions: list[InstallAction] = []
    unavailable: list[DoctorCheck] = []
    for agent, supplier, errors, label in (
        ("cursor", cursor_install_actions, (CursorExtensionInspectionError,), "Cursor"),
        (
            "claude-code",
            claude_install_actions,
            (ClaudePluginInspectionError,),
            "Claude",
        ),
        ("codex", codex_install_actions, (CodexPluginInspectionError,), "Codex"),
    ):
        if not setup.is_enabled(agent):
            continue
        try:
            pending_actions.extend(supplier(setup, paths, runner))
        except errors:
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


class AssistantPlanContributor:
    """Expose selected assistant inventory as redacted structural plan actions."""

    def __init__(self, paths: RuntimePaths) -> None:
        """Initialize with the checked-out inventory location.

        Args:
            paths: Approved checkout and home roots.
        """
        self.paths = paths

    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        """Return selected manual and catalog inventory declarations.

        Args:
            resolved: Resolved profile and component selection.

        Returns:
            Deterministically ordered structural actions without source contents.
        """
        inventory = load_inventory(
            self.paths.repo_root / "assistants/inventory.yaml", self.paths.repo_root
        )
        selected = resolve_inventory(
            inventory, profiles=resolved.profiles, skipped=frozenset(resolved.skipped)
        )
        actions: list[PlanAction] = []
        for resource in selected.resources:
            if resource.kind == "manual":
                category: Literal["install", "configure", "manual", "diagnostic"] = (
                    "manual"
                )
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
        identifiers = [action.component_id for action in actions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate assistant plan action ID")
        return tuple(sorted(actions, key=lambda action: action.component_id))


__all__ = [
    "AgentName",
    "AssistantInventory",
    "AssistantPlanContributor",
    "CatalogKind",
    "CatalogResource",
    "ClaudeHookFragment",
    "ClaudePluginInspectionError",
    "ClaudeSettingsError",
    "ClaudeStableSettings",
    "CodexPluginInspectionError",
    "CodexSettingsError",
    "CodexStableSettings",
    "CursorExtensionInspectionError",
    "CursorExtensionPackage",
    "CursorRegistration",
    "ExtensionCatalog",
    "ExtensionSpec",
    "ExtensionState",
    "FileResource",
    "HookResource",
    "ManualResource",
    "Marketplace",
    "PluginCatalog",
    "PluginSpec",
    "PortableResource",
    "ResourceBase",
    "SkillCatalog",
    "SkillCollisionError",
    "SkillCopyAction",
    "SkillSpec",
    "claude_configuration",
    "claude_hook_fragment",
    "claude_install_actions",
    "claude_instruction_renderer",
    "claude_settings_renderer",
    "codex_configuration",
    "codex_install_actions",
    "codex_instruction_renderer",
    "codex_settings_renderer",
    "configuration",
    "cursor_configuration",
    "cursor_hook_renderer",
    "cursor_install_actions",
    "cursor_registration",
    "cursor_rules_renderer",
    "cursor_settings_renderer",
    "deep_merge",
    "doctor_checks",
    "hash_skill_tree",
    "hook_contribution",
    "install_action_candidates",
    "install_actions",
    "jj_graph_action",
    "load_codex_stable_settings",
    "load_stable_settings",
    "managed_tree_spec",
    "plan_claude_plugins",
    "plan_codex_plugins",
    "plan_cursor_extension_actions",
    "plan_skill_copies",
    "read_bundled_extensions",
    "render_native_instructions",
    "render_settings",
    "resolve_extensions",
    "validate_hook_source",
]
