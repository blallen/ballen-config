"""Private, versioned state for bootstrap ownership and outcomes."""

from __future__ import annotations

import errno
import fcntl
import os
import stat
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
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


class StateMutationContentionError(RuntimeError):
    """Raised when a non-blocking mutation lock acquire fails."""


class StateStore:
    """Atomically persist private bootstrap state."""

    def __init__(self, paths: RuntimePaths) -> None:
        self.paths = paths
        self.path = paths.state_root / "state.json"
        self._lock_path = paths.state_root / ".mutation.lock"
        self._lock_fd: int | None = None
        self._lock_depth = 0
        self._lock_owner: int | None = None
        self._thread_guard = threading.Lock()

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

    @contextmanager
    def mutation(self, *, blocking: bool = True) -> Iterator[None]:
        """Acquire the exclusive advisory mutation lock.

        Reentrant for the owning thread. Non-blocking acquire raises
        ``StateMutationContentionError`` instead of waiting.
        """
        self._acquire(blocking=blocking)
        try:
            yield
        finally:
            self._release()

    def _acquire(self, *, blocking: bool) -> None:
        ident = threading.get_ident()
        with self._thread_guard:
            if self._lock_depth > 0:
                if self._lock_owner != ident:
                    raise StateMutationContentionError(
                        "mutation lock held by another thread"
                    )
                self._lock_depth += 1
                return
            self._validate_paths()
            self.paths.state_root.mkdir(parents=True, mode=0o700, exist_ok=True)
            self.paths.state_root.chmod(0o700)
            fd = os.open(
                self._lock_path,
                os.O_CREAT | os.O_RDWR,
                0o600,
            )
            os.fchmod(fd, 0o600)
            flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
            try:
                fcntl.flock(fd, flags)
            except OSError as error:
                os.close(fd)
                if error.errno in {errno.EACCES, errno.EAGAIN}:
                    raise StateMutationContentionError(
                        "mutation lock contention"
                    ) from error
                raise
            self._lock_fd = fd
            self._lock_owner = ident
            self._lock_depth = 1

    def _release(self) -> None:
        with self._thread_guard:
            if self._lock_depth <= 0 or self._lock_fd is None:
                raise RuntimeError("mutation lock release without acquire")
            self._lock_depth -= 1
            if self._lock_depth > 0:
                return
            fd = self._lock_fd
            self._lock_fd = None
            self._lock_owner = None
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

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

    def compare_and_remove(self, expected: ManagedRecord) -> bool:
        """Delete managed record only if stored value exactly equals expected.

        Must be called while ``mutation()`` is held. Returns True if removed.
        Returns False and writes nothing on mismatch.

        Args:
            expected: Exact ownership record that must match the stored value.

        Returns:
            True when the record was removed; False when the store differs.
        """
        if self._lock_depth <= 0:
            raise RuntimeError("compare_and_remove requires mutation lock")
        state = self.load()
        current = state.managed.get(expected.resource_id)
        if current != expected:
            return False
        managed = {
            key: value
            for key, value in state.managed.items()
            if key != expected.resource_id
        }
        self.write(state.model_copy(update={"managed": managed}))
        return True

    def record_install(self, record: InstallRecord) -> None:
        """Record a normalized install result without command output.

        Args:
            record: Result to associate with the resource identifier.
        """
        with self.mutation():
            state = self.load()
            installs = {**state.installs, record.resource_id: record}
            self.write(state.model_copy(update={"installs": installs}))

    def record_managed(self, record: ManagedRecord) -> None:
        """Record managed-destination ownership metadata.

        Args:
            record: Ownership record to associate with the resource identifier.
        """
        with self.mutation():
            state = self.load()
            managed = {**state.managed, record.resource_id: record}
            self.write(state.model_copy(update={"managed": managed}))
