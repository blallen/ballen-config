from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from ballen_config.manifests import ManifestRepository
from ballen_config.models import ResolutionRequest, ResolvedSetup


class ComponentState(StrEnum):
    """Observed component state."""

    PRESENT = "present"
    MISSING = "missing"


class Inspector(Protocol):
    """Read-only component state provider."""

    def state(self, component_id: str) -> ComponentState:
        """Return structural state without exposing command output."""


class PlanContributor(Protocol):
    """Extension seam for configuration, manual, and assistant actions."""

    def actions(self, resolved: ResolvedSetup) -> tuple["PlanAction", ...]:
        """Return redacted structural actions for the resolved setup."""


class PlanAction(BaseModel):
    """One redacted plan action."""

    model_config = ConfigDict(frozen=True)

    component_id: str
    category: Literal["install", "configure", "manual", "diagnostic"]
    action: str
    owner: str
    path: str | None = None
    required: bool = True
    large: bool = False


class CoreManualContributor:
    """Cross-cutting manual actions owned by the core bootstrap."""

    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        """Return stable manual actions for a resolved setup.

        Args:
            resolved: The resolved profiles and components.

        Returns:
            Redacted manual actions, including work authentication when needed.
        """
        actions = [
            PlanAction(
                component_id="github-auth",
                category="manual",
                action="run-gh-auth-login",
                owner="user",
                required=False,
            ),
            PlanAction(
                component_id="ssh-transfer",
                category="manual",
                action="follow-secure-transfer-guide",
                owner="user",
                path="docs/ssh-transfer.md",
                required=False,
            ),
            PlanAction(
                component_id="it-managed-applications",
                category="manual",
                action="use-company-supported-channel",
                owner="user",
                required=False,
            ),
        ]
        if resolved.is_enabled("glab"):
            actions.append(
                PlanAction(
                    component_id="gitlab-auth",
                    category="manual",
                    action="run-glab-auth-login",
                    owner="user",
                    required=False,
                )
            )
        if "fsp" in resolved.profiles:
            actions.append(
                PlanAction(
                    component_id="aws-auth",
                    category="manual",
                    action="complete-organization-sign-in",
                    owner="user",
                    required=False,
                )
            )
        return tuple(actions)


class SetupPlan(BaseModel):
    """Deterministic setup plan."""

    model_config = ConfigDict(frozen=True)

    profile: str
    profiles: tuple[str, ...]
    skipped: tuple[str, ...]
    actions: tuple[PlanAction, ...]
    expected_prompts: tuple[str, ...]


def build_resolved_plan(
    resolved: ResolvedSetup,
    *,
    profile: str,
    inspector: Inspector,
    contributors: Sequence[PlanContributor] = (),
) -> SetupPlan:
    """Build a deterministic plan from one already-resolved setup.

    Args:
        resolved: Resolved profiles, components, and skips.
        profile: Requested primary profile name.
        inspector: Read-only component state provider.
        contributors: Additional redacted action providers.

    Returns:
        The ordered, redacted setup plan.

    Raises:
        ValueError: If any action component identifier is duplicated.
    """
    install_actions = tuple(
        PlanAction(
            component_id=component.id,
            category="install",
            action=(
                "present"
                if inspector.state(component.id) is ComponentState.PRESENT
                else "install"
            ),
            owner="bootstrap",
            required=component.required,
            large=component.large,
        )
        for component in resolved.components
    )
    contributed_actions = tuple(
        sorted(
            (
                action
                for contributor in contributors
                for action in contributor.actions(resolved)
            ),
            key=lambda item: (
                item.category,
                item.component_id,
                item.path or "",
            ),
        )
    )
    actions = install_actions + contributed_actions
    action_ids = [action.component_id for action in actions]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("duplicate PlanAction.component_id")
    return SetupPlan(
        profile=profile,
        profiles=resolved.profiles,
        skipped=resolved.skipped,
        actions=actions,
        expected_prompts=("confirm package and configuration changes",),
    )


def build_plan(
    manifest_root: Path,
    request: ResolutionRequest,
    inspector: Inspector,
    contributors: Sequence[PlanContributor] = (),
) -> SetupPlan:
    """Build a deterministic structural plan.

    Args:
        manifest_root: Directory containing package and profile manifests.
        request: Profile and component selection.
        inspector: Read-only component state provider.
        contributors: Additional redacted action providers.

    Returns:
        The ordered, redacted setup plan.

    Raises:
        ValueError: If any action component identifier is duplicated.
    """
    resolved = ManifestRepository.load(manifest_root).resolve(request)
    return build_resolved_plan(
        resolved,
        profile=request.profile,
        inspector=inspector,
        contributors=contributors,
    )


def format_plan(plan: SetupPlan) -> str:
    """Render a setup plan without native command output or values.

    Args:
        plan: Structural setup plan to render.

    Returns:
        A stable, line-oriented representation of the plan.
    """
    lines = [f"profile: {plan.profile}"]
    lines.extend(f"skip: {name} (intentional)" for name in plan.skipped)
    lines.extend(
        f"{action.category} {action.component_id} "
        f"(owner={action.owner}): {action.action}"
        + (f" [{action.path}]" if action.path else "")
        + (" (large download)" if action.large else "")
        for action in plan.actions
    )
    lines.extend(f"prompt: {prompt}" for prompt in plan.expected_prompts)
    return "\n".join(lines)
