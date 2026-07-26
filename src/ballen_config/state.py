"""Private, versioned state for bootstrap ownership and outcomes."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.runtime import RuntimePaths


class ManagedRecord(BaseModel):
    """Checksums proving ownership of one managed destination."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_id: str
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    destination_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    destination: str


class InstallRecord(BaseModel):
    """Normalized install outcome without command output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_id: str
    state: Literal["present", "installed", "optional-failure"]


class BootstrapState(BaseModel):
    """Versioned local ownership and normalized outcome state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1] = 1
    installs: dict[str, InstallRecord] = Field(default_factory=dict)
    managed: dict[str, ManagedRecord] = Field(default_factory=dict)


class StateStore:
    """Atomically persist private bootstrap state."""

    def __init__(self, paths: RuntimePaths) -> None:
        """Initialize a store at the approved state root.

        Args:
            paths: Approved runtime filesystem roots.
        """
        self.paths = paths
        self.path = paths.state_root / "state.json"

    def _validate_paths(self) -> None:
        """Reject state paths outside home or through symlinked components."""
        assert_contained(self.paths.state_root, self.paths.home)
        assert_contained(self.paths.backup_root, self.paths.home)
        assert_no_symlink_components(
            self.paths.state_root, stop=self.paths.home, include_leaf=True
        )
        assert_contained(self.path, self.paths.state_root)
        assert_no_symlink_components(self.path, stop=self.paths.state_root)
        try:
            metadata = os.lstat(self.path)
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"symlinked path component: {self.path}")
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"state path is not a regular file: {self.path}")

    def load(self) -> BootstrapState:
        """Load state, or return empty versioned state when absent."""
        self._validate_paths()
        if not self.path.exists():
            return BootstrapState()
        return BootstrapState.model_validate_json(self.path.read_text(encoding="utf-8"))

    def write(self, state: BootstrapState) -> None:
        """Write state via a mode-0600 same-directory atomic replacement.

        Args:
            state: Fully normalized state to persist.
        """
        self._validate_paths()
        self.paths.state_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        self._validate_paths()
        self.paths.state_root.chmod(0o700)
        payload = state.model_dump_json(indent=2) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.paths.state_root, prefix=".state."
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self._validate_paths()
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def record_install(self, record: InstallRecord) -> None:
        """Record a normalized install result without command output.

        Args:
            record: Result to associate with the resource identifier.
        """
        state = self.load()
        installs = {**state.installs, record.resource_id: record}
        self.write(state.model_copy(update={"installs": installs}))

    def record_managed(self, record: ManagedRecord) -> None:
        """Record managed-destination ownership metadata.

        Args:
            record: Ownership record to associate with the resource identifier.
        """
        state = self.load()
        managed = {**state.managed, record.resource_id: record}
        self.write(state.model_copy(update={"managed": managed}))
