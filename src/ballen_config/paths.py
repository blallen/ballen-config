"""Filesystem containment and symlink-safety helpers."""

import os
import stat
from pathlib import Path


def assert_contained(path: Path, root: Path) -> Path:
    """Return an absolute lexical path only when it is beneath ``root``."""
    normalized_root = root.resolve()
    normalized_path = Path(os.path.abspath(path))
    try:
        normalized_path.relative_to(normalized_root)
    except ValueError as error:
        raise ValueError(f"path escapes approved root: {path}") from error
    return normalized_path


def assert_no_symlink_components(
    path: Path,
    *,
    stop: Path,
    include_leaf: bool = False,
) -> None:
    """Reject existing symlinks and non-directory intermediate components."""
    relative = path.relative_to(stop)
    current = stop
    parts = relative.parts if include_leaf else relative.parts[:-1]
    for part in parts:
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"symlinked path component: {current}")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"non-directory path component: {current}")
