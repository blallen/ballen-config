from pathlib import Path

import pytest

from ballen_config.manifests import ManifestRepository
from ballen_config.models import ResolutionRequest, ResolvedSetup
from ballen_config.planning import (
    ComponentState,
    CoreManualContributor,
    PlanAction,
    build_plan,
    build_resolved_plan,
    format_plan,
)


class FakeInspector:
    """Report GitHub CLI as the only present component."""

    def state(self, component_id: str) -> ComponentState:
        """Return a deterministic component state."""
        if component_id == "gh":
            return ComponentState.PRESENT
        return ComponentState.MISSING


class FakeContributor:
    """Contribute deterministic configuration and manual actions."""

    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        """Return redacted structural actions."""
        return (
            PlanAction(
                component_id="wave-settings",
                category="configure",
                action="update-fields",
                owner="bootstrap",
                path="~/.config/waveterm/settings.json",
            ),
            PlanAction(
                component_id="gitlab-auth",
                category="manual",
                action="run glab auth login",
                owner="user",
                required=False,
            ),
        )


class DuplicateContributor:
    """Contribute an action that collides with an install action."""

    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        """Return a duplicate GitHub CLI action."""
        return (
            PlanAction(
                component_id="gh",
                category="diagnostic",
                action="inspect",
                owner="bootstrap",
            ),
        )


def test_plan_preserves_install_order_and_redacts_native_values(
    repo_root: Path,
    manifest_repository: ManifestRepository,
) -> None:
    """Plan preserves install order while withholding native credentials."""
    request = ResolutionRequest(profile="default")

    plan = build_plan(
        repo_root / "manifests",
        request,
        FakeInspector(),
        contributors=(FakeContributor(),),
    )

    expected = [
        component.id for component in manifest_repository.resolve(request).components
    ]
    assert [action.component_id for action in plan.actions[: len(expected)]] == expected
    output = format_plan(plan)
    assert "install gh (owner=bootstrap): present" in output
    assert "install glab (owner=bootstrap): install" in output
    assert "~/.config/waveterm/settings.json" in output
    assert "prompt: confirm package and configuration changes" in output
    assert "glpat-secret-value" not in output


def test_build_plan_delegates_to_resolved_plan(
    repo_root: Path,
    manifest_repository: ManifestRepository,
) -> None:
    """Manifest and resolved entry points produce the same stable plan."""
    request = ResolutionRequest(profile="default")
    resolved = manifest_repository.resolve(request)
    expected = build_resolved_plan(
        resolved,
        profile=request.profile,
        inspector=FakeInspector(),
        contributors=(FakeContributor(),),
    )
    assert (
        build_plan(
            repo_root / "manifests",
            request,
            FakeInspector(),
            contributors=(FakeContributor(),),
        )
        == expected
    )


def test_core_manual_actions_are_stable_and_work_aware(
    manifest_repository: ManifestRepository,
) -> None:
    """Manual actions remain ordered and gain AWS only for work."""
    contributor = CoreManualContributor()
    default = manifest_repository.resolve(ResolutionRequest(profile="default"))
    work = manifest_repository.resolve(ResolutionRequest(profile="work"))

    assert [
        (action.component_id, action.action) for action in contributor.actions(default)
    ] == [
        ("github-auth", "run-gh-auth-login"),
        ("gitlab-auth", "run-glab-auth-login"),
        ("ssh-transfer", "follow-secure-transfer-guide"),
        ("it-managed-applications", "use-company-supported-channel"),
    ]
    assert [
        (action.component_id, action.action) for action in contributor.actions(work)
    ][-1] == ("aws-auth", "complete-organization-sign-in")
    assert all(
        action.category == "manual" and action.owner == "user" and not action.required
        for action in contributor.actions(work)
    )


def test_duplicate_plan_action_component_id_fails_closed(
    repo_root: Path,
) -> None:
    """Plan contributors cannot create ambiguous component action identities."""
    with pytest.raises(ValueError, match=r"duplicate PlanAction\.component_id"):
        build_plan(
            repo_root / "manifests",
            ResolutionRequest(profile="default"),
            FakeInspector(),
            contributors=(DuplicateContributor(),),
        )
