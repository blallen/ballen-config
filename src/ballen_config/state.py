"""Private, versioned state for bootstrap ownership and outcomes."""

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
    """Atomically persist private bootstrap state.

    Every write path runs under the exclusive advisory lock in ``state_root``,
    which serializes concurrent bootstrap processes. ``mutation()`` acquires it;
    ``compare_and_remove`` requires the calling thread to already own it, and
    ``record_install`` and ``record_managed`` acquire it themselves. ``load`` is
    unlocked, so a read-modify-write sequence must be wrapped in ``mutation()``
    to be race-free.
    """

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
            self._validate_lock_path()
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"symlinked path component: {self.path}")
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"state path is not a regular file: {self.path}")
        self._validate_lock_path()

    def _validate_lock_path(self) -> None:
        """Reject a lock leaf that is not an ordinary regular file."""
        assert_contained(self._lock_path, self.paths.state_root)
        assert_no_symlink_components(
            self._lock_path, stop=self.paths.state_root, include_leaf=False
        )
        try:
            metadata = os.lstat(self._lock_path)
        except FileNotFoundError:
            return
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"mutation lock is not a regular file: {self._lock_path}")

    @contextmanager
    def mutation(self, *, blocking: bool = True) -> Iterator[None]:
        """Acquire the exclusive advisory mutation lock.

        The lock is reentrant only for its owning thread. Other threads and
        processes block until release, or a non-blocking acquire raises
        ``StateMutationContentionError``. The context yields with the lock
        held and releases one reentrant level on exit.

        Args:
            blocking: Whether to wait for another lock holder to release.

        Yields:
            None while the calling thread owns the mutation lock.

        Raises:
            StateMutationContentionError: If a non-blocking acquire contends,
                or another thread owns this store's lock.
            ValueError: If the lock path is unsafe.
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
            self._validate_lock_path()
            nofollow = getattr(os, "O_NOFOLLOW", None)
            if nofollow is None:
                raise ValueError("safe mutation lock opening is unsupported")
            fd: int | None = None
            acquired = False
            flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
            try:
                fd = os.open(
                    self._lock_path,
                    os.O_CREAT | os.O_RDWR | nofollow,
                    0o600,
                )
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise ValueError(
                        f"mutation lock is not a regular file: {self._lock_path}"
                    )
                os.fchmod(fd, 0o600)
                fcntl.flock(fd, flags)
                self._lock_fd = fd
                self._lock_owner = ident
                self._lock_depth = 1
                acquired = True
            except OSError as error:
                if error.errno in {errno.EACCES, errno.EAGAIN}:
                    raise StateMutationContentionError(
                        "mutation lock contention"
                    ) from error
                if error.errno == errno.ELOOP:
                    raise ValueError(
                        f"mutation lock is not a regular file: {self._lock_path}"
                    ) from error
                raise
            finally:
                if fd is not None and not acquired:
                    os.close(fd)

    def _release(self) -> None:
        with self._thread_guard:
            if self._lock_depth <= 0 or self._lock_fd is None:
                raise RuntimeError("mutation lock release without acquire")
            if self._lock_owner != threading.get_ident():
                raise StateMutationContentionError(
                    "mutation lock release attempted by non-owner thread"
                )
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

    def _require_lock_ownership(self, operation: str) -> None:
        """Reject a mutation attempted without this thread owning the lock.

        Args:
            operation: Operation name used in the raised messages.

        Raises:
            RuntimeError: If no mutation lock is held.
            StateMutationContentionError: If another thread owns the lock.
        """
        with self._thread_guard:
            if self._lock_depth <= 0:
                raise RuntimeError(f"{operation} requires mutation lock")
            if self._lock_owner != threading.get_ident():
                raise StateMutationContentionError(
                    f"{operation} attempted by non-owner thread"
                )

    def load(self) -> BootstrapState:
        """Load state, or return empty versioned state when absent."""
        self._validate_paths()
        if not self.path.exists():
            return BootstrapState()
        return BootstrapState.model_validate_json(self.path.read_text(encoding="utf-8"))

    def _write(self, state: BootstrapState) -> None:
        """Write state via a mode-0600 same-directory atomic replacement.

        The calling thread must own ``mutation()``, so that a read-modify-write
        sequence cannot interleave with another process.

        Args:
            state: Fully normalized state to persist.

        Raises:
            RuntimeError: If no mutation lock is held.
            StateMutationContentionError: If another thread owns the lock.
        """
        self._require_lock_ownership("write")
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

        The calling thread must own ``mutation()``. Returns True after removal,
        or False without writing when the stored record differs. Ownership is
        checked before loading and writing so this method does not deadlock on
        the non-reentrant thread guard.

        Args:
            expected: Exact ownership record that must match the stored value.

        Returns:
            True when the record was removed; False when the store differs.

        Raises:
            RuntimeError: If no mutation lock is held.
            StateMutationContentionError: If another thread owns the lock.
        """
        self._require_lock_ownership("compare_and_remove")
        state = self.load()
        current = state.managed.get(expected.resource_id)
        if current != expected:
            return False
        managed = {
            key: value
            for key, value in state.managed.items()
            if key != expected.resource_id
        }
        self._write(state.model_copy(update={"managed": managed}))
        return True

    def record_install(self, record: InstallRecord) -> None:
        """Record a normalized install result without command output.

        Args:
            record: Result to associate with the resource identifier.
        """
        with self.mutation():
            state = self.load()
            installs = {**state.installs, record.resource_id: record}
            self._write(state.model_copy(update={"installs": installs}))

    def record_managed(self, record: ManagedRecord) -> None:
        """Record managed-destination ownership metadata.

        Args:
            record: Ownership record to associate with the resource identifier.
        """
        with self.mutation():
            state = self.load()
            managed = {**state.managed, record.resource_id: record}
            self._write(state.model_copy(update={"managed": managed}))
