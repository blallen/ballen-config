"""Safe access to reviewed assistant files in the checkout."""

import os
import stat
from pathlib import Path

from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.runtime import RuntimePaths


def reviewed_regular_file(paths: RuntimePaths, relative: Path) -> Path:
    """Return a contained, symlink-free regular reviewed file."""
    source = assert_contained(paths.repo_root / relative, paths.repo_root)
    assert_no_symlink_components(source, stop=paths.repo_root)
    try:
        metadata = os.lstat(source)
    except OSError as error:
        raise ValueError("reviewed source must be a regular file") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("reviewed source must be a regular file")
    assert_contained(source.resolve(strict=True), paths.repo_root)
    return source
