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
                component_id="example-settings",
                category="configure",
                action="update-fields",
                owner="bootstrap",
                path="~/.config/example/settings.json",
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
    assert "install glab" not in output
    assert "~/.config/example/settings.json" in output
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


def test_core_manual_actions_gate_gitlab_and_aws(
    manifest_repository: ManifestRepository,
) -> None:
    """GitLab login is include-gated; AWS sign-in is fsp-only."""
    contributor = CoreManualContributor()
    default = manifest_repository.resolve(ResolutionRequest(profile="default"))
    wsh = manifest_repository.resolve(ResolutionRequest(profile="wsh"))
    fsp = manifest_repository.resolve(ResolutionRequest(profile="fsp"))
    with_glab = manifest_repository.resolve(
        ResolutionRequest(profile="wsh", includes=("glab",))
    )
    default_ids = [action.component_id for action in contributor.actions(default)]
    assert default_ids == [
        "github-auth",
        "ssh-transfer",
        "it-managed-applications",
    ]
    assert [action.component_id for action in contributor.actions(wsh)] == default_ids
    assert "gitlab-auth" in {
        action.component_id for action in contributor.actions(with_glab)
    }
    assert [action.component_id for action in contributor.actions(fsp)][-1] == "aws-auth"


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
