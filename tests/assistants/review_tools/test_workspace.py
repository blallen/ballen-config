"""Tests for safe repository-local review workspaces."""

from dataclasses import dataclass
from pathlib import Path

import pytest
from ballen_review_tools.workspace import validate_workspace


@dataclass
class FakeWorkspaceProbe:
    """Provide deterministic repository-state answers for path tests."""

    ignored: bool = True
    tracked: bool = False
    staged: bool = False
    conflicted: bool = False

    def is_ignored(self, relative: Path) -> bool:
        """Return whether the proposed path is ignored."""
        return self.ignored

    def is_tracked(self, relative: Path) -> bool:
        """Return whether the proposed path is tracked."""
        return self.tracked

    def is_staged(self, relative: Path) -> bool:
        """Return whether the proposed path is staged."""
        return self.staged

    def is_conflicted(self, relative: Path) -> bool:
        """Return whether the proposed path is conflicted."""
        return self.conflicted


def test_ignored_untracked_workspace_is_safe(tmp_path: Path) -> None:
    """Accept one ordinary ignored workspace inside the repository."""
    repo = tmp_path / "repo"
    workspace = repo / ".reviews"
    proposed = workspace / "review-plan.json"
    workspace.mkdir(parents=True)

    result = validate_workspace(
        repo_root=repo,
        destination=workspace,
        proposed_file=proposed,
        probe=FakeWorkspaceProbe(),
    )

    assert result.safe is True


def test_unignored_workspace_is_blocked(tmp_path: Path) -> None:
    """Refuse to create review artifacts when ignore state is unproven."""
    repo = tmp_path / "repo"
    workspace = repo / "review-output"
    workspace.mkdir(parents=True)

    result = validate_workspace(
        repo_root=repo,
        destination=workspace,
        proposed_file=workspace / "review-plan.json",
        probe=FakeWorkspaceProbe(ignored=False),
    )

    assert result.safe is False
    assert "ignored" in result.reason


def test_symlinked_workspace_is_blocked(tmp_path: Path) -> None:
    """Refuse a destination that escapes through a symlink component."""
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    outside.mkdir()
    link = repo / ".reviews"
    repo.mkdir()
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        validate_workspace(
            repo_root=repo,
            destination=link,
            proposed_file=link / "review-plan.json",
            probe=FakeWorkspaceProbe(),
        )


def test_tracked_workspace_is_blocked(tmp_path: Path) -> None:
    """Refuse a tracked review artifact even when the directory is ignored."""
    repo = tmp_path / "repo"
    workspace = repo / ".reviews"
    workspace.mkdir(parents=True)

    result = validate_workspace(
        repo_root=repo,
        destination=workspace,
        proposed_file=workspace / "review-plan.json",
        probe=FakeWorkspaceProbe(tracked=True),
    )

    assert result.safe is False
    assert "tracked" in result.reason
