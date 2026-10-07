"""Tests for manifest component contracts."""

import pytest
from pydantic import ValidationError

from ballen_config.models import Component, Manager

_REVISION = "b37dd49ca5bfe0d99b35607637152cb8cc8b29d7"  # pragma: allowlist secret


@pytest.mark.parametrize(
    "revision",
    [
        pytest.param(
            _REVISION.upper(),
            id="uppercase",
        ),
        pytest.param(
            _REVISION[:-1],
            id="short-hash",
        ),
        pytest.param("main", id="branch-name"),
    ],
)
def test_git_component_requires_a_full_lowercase_commit_revision(
    revision: str,
) -> None:
    """Git components accept only immutable 40-character lowercase revisions."""
    with pytest.raises(ValidationError, match="revision"):
        Component(
            id="oh-my-zsh",
            manager=Manager.GIT,
            package="https://github.com/ohmyzsh/ohmyzsh.git",
            destination=".oh-my-zsh",
            revision=revision,
        )


def test_git_component_requires_a_revision() -> None:
    """Git component declarations cannot leave their source revision mutable."""
    with pytest.raises(ValidationError, match="revision"):
        Component(
            id="oh-my-zsh",
            manager=Manager.GIT,
            package="https://github.com/ohmyzsh/ohmyzsh.git",
            destination=".oh-my-zsh",
        )


def test_git_component_may_track_a_branch_instead_of_a_revision() -> None:
    """Self-updating checkouts declare the upstream branch they follow."""
    component = Component(
        id="oh-my-zsh",
        manager=Manager.GIT,
        package="https://github.com/ohmyzsh/ohmyzsh.git",
        destination=".oh-my-zsh",
        branch="master",
    )
    assert component.branch == "master"


@pytest.mark.parametrize(
    ("revision", "branch"),
    [
        pytest.param(_REVISION, "master", id="both"),
        pytest.param(None, "--upload-pack=touch", id="option-like-branch"),
    ],
)
def test_git_component_rejects_ambiguous_or_unsafe_branch(
    revision: str | None, branch: str
) -> None:
    """A branch replaces the revision and can never be read as a Git option."""
    with pytest.raises(ValidationError, match="branch"):
        Component(
            id="oh-my-zsh",
            manager=Manager.GIT,
            package="https://github.com/ohmyzsh/ohmyzsh.git",
            destination=".oh-my-zsh",
            revision=revision,
            branch=branch,
        )


@pytest.mark.parametrize(
    ("revision", "branch"),
    [
        pytest.param(_REVISION, None, id="revision"),
        pytest.param(None, "master", id="branch"),
    ],
)
def test_non_git_component_rejects_git_source_metadata(
    revision: str | None, branch: str | None
) -> None:
    """Package-manager components cannot declare Git revisions or branches."""
    with pytest.raises(ValidationError, match="only git components"):
        Component(
            id="uv",
            manager=Manager.BREW_FORMULA,
            package="uv",
            revision=revision,
            branch=branch,
        )


def test_uv_tool_manager_is_supported() -> None:
    """Tools installed by uv are expressible as components."""
    assert Manager("uv_tool") is Manager.UV_TOOL
    component = Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
        depends_on=("uv",),
    )
    assert component.manager is Manager.UV_TOOL
