"""Repository-local safety checks for review artifacts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class WorkspaceProbe(Protocol):
    """Provide authoritative VCS state for one repository-relative path."""

    def is_ignored(self, relative: Path) -> bool:
        """Return whether a path is ignored."""

    def is_tracked(self, relative: Path) -> bool:
        """Return whether a path is tracked."""

    def is_staged(self, relative: Path) -> bool:
        """Return whether a path is staged."""

    def is_conflicted(self, relative: Path) -> bool:
        """Return whether a path is conflicted."""


@dataclass(frozen=True)
class WorkspaceCheck:
    """Safe-workspace decision with a bounded diagnostic."""

    safe: bool
    reason: str = ""


def _relative_path(repo_root: Path, candidate: Path) -> Path:
    """Return a path relative to the repository without following links."""
    root = repo_root.absolute()
    absolute = candidate.absolute()
    try:
        relative = absolute.relative_to(root)
    except ValueError as error:
        raise ValueError("workspace path is outside repository") from error
    current = root
    for component in relative.parts:
        current /= component
        if current.is_symlink():
            raise ValueError("workspace path contains a symlink component")
    return relative


def validate_workspace(
    *,
    repo_root: Path,
    destination: Path,
    proposed_file: Path,
    probe: WorkspaceProbe,
) -> WorkspaceCheck:
    """Prove that a proposed artifact is safe to write.

    Args:
        repo_root: Repository root that must contain both paths.
        destination: Existing or proposed ignored workspace directory.
        proposed_file: Repository-local artifact path to write.
        probe: VCS state provider for repository-relative paths.

    Returns:
        A safe decision or a bounded blocking reason.

    Raises:
        ValueError: If a path is outside the repository or crosses a symlink.
    """
    destination_relative = _relative_path(repo_root, destination)
    proposed_relative = _relative_path(repo_root, proposed_file)
    if destination_relative == Path("."):
        return WorkspaceCheck(
            False, "workspace destination must not be repository root"
        )
    destination_absolute = destination.absolute()
    proposed_absolute = proposed_file.absolute()
    if proposed_absolute == destination_absolute:
        return WorkspaceCheck(
            False, "proposed file must be below workspace destination"
        )
    try:
        proposed_absolute.relative_to(destination_absolute)
    except ValueError:
        return WorkspaceCheck(False, "proposed file is outside workspace destination")
    if not destination.exists():
        return WorkspaceCheck(False, "workspace destination does not exist")
    if not destination.is_dir():
        return WorkspaceCheck(False, "workspace destination is not a directory")
    for relative in (destination_relative, proposed_relative):
        if not probe.is_ignored(relative):
            return WorkspaceCheck(False, "workspace path is not ignored")
        if probe.is_tracked(relative):
            return WorkspaceCheck(False, "workspace path is tracked")
        if probe.is_staged(relative):
            return WorkspaceCheck(False, "workspace path is staged")
        if probe.is_conflicted(relative):
            return WorkspaceCheck(False, "workspace path is conflicted")
    return WorkspaceCheck(True)
