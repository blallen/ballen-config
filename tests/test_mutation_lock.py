"""Tests for StateStore coarse mutation locking."""

from __future__ import annotations

import os
import stat
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from multiprocessing import Process, Queue
from multiprocessing.queues import Queue as MultiprocessingQueue
from pathlib import Path
from queue import Queue as ThreadQueue

import pytest

import ballen_config.state as state_module
from ballen_config.runtime import RuntimePaths
from ballen_config.state import (
    BootstrapState,
    ManagedRecord,
    StateMutationContentionError,
    StateStore,
)


def _paths(repo_root: Path, home: Path) -> RuntimePaths:
    return RuntimePaths.from_roots(repo_root=repo_root, home=home)


@contextmanager
def _started_process(
    target: Callable[..., object], args: tuple[object, ...]
) -> Iterator[Process]:
    """Start one child process and always join or terminate it."""
    process = Process(target=target, args=args)
    process.start()
    try:
        yield process
    finally:
        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)


def test_mutation_context_creates_private_lock_file(
    repo_root: Path, fake_home: Path
) -> None:
    """Acquiring a mutation creates a private regular lock file."""
    store = StateStore(_paths(repo_root, fake_home))
    with store.mutation():
        lock = store.paths.state_root / ".mutation.lock"
        assert lock.is_file()
        assert lock.stat().st_mode & 0o777 == 0o600


def _try_nonblocking_lock(
    home: str, repo: str, result: MultiprocessingQueue[str]
) -> None:
    """Report whether an independent process can acquire the mutation lock."""
    store = StateStore(RuntimePaths.from_roots(repo_root=Path(repo), home=Path(home)))
    try:
        with store.mutation(blocking=False):
            result.put("acquired")
    except StateMutationContentionError:
        result.put("contended")


def test_nested_mutation_blocks_competing_process_until_outer_exit(
    repo_root: Path, fake_home: Path
) -> None:
    """Nested mutation retains OS-level exclusion until the outer context exits."""
    store = StateStore(_paths(repo_root, fake_home))
    while_nested: MultiprocessingQueue[str] = Queue()
    after_outer: MultiprocessingQueue[str] = Queue()

    with store.mutation(), store.mutation():
        with _started_process(
            _try_nonblocking_lock,
            (str(fake_home), str(repo_root), while_nested),
        ) as competing:
            assert while_nested.get(timeout=5) == "contended"
        assert competing.exitcode == 0

    with _started_process(
        _try_nonblocking_lock,
        (str(fake_home), str(repo_root), after_outer),
    ) as released:
        assert after_outer.get(timeout=5) == "acquired"
    assert released.exitcode == 0


def _record_managed_after_load(
    home: str,
    repo: str,
    record: ManagedRecord,
    loaded: MultiprocessingQueue[str],
    release: MultiprocessingQueue[str],
) -> None:
    """Pause the first recorder after its load while it owns the lock."""

    class PausingStateStore(StateStore):
        """Expose the load/write boundary without changing lock behavior."""

        def load(self) -> BootstrapState:
            """Load state, then wait before merging and writing."""
            state = super().load()
            loaded.put("loaded")
            release.get(timeout=5)
            return state

    PausingStateStore(
        RuntimePaths.from_roots(repo_root=Path(repo), home=Path(home))
    ).record_managed(record)


def _record_managed_nonblocking(
    home: str,
    repo: str,
    record: ManagedRecord,
    result: MultiprocessingQueue[str],
) -> None:
    """Attempt a real managed-state record with non-blocking acquisition."""

    class NonblockingStateStore(StateStore):
        """Use non-blocking acquisition while preserving StateStore behavior."""

        @contextmanager
        def mutation(self, *, blocking: bool = True) -> Iterator[None]:
            """Acquire the inherited mutation lock without waiting."""
            with super().mutation(blocking=False):
                yield

    try:
        NonblockingStateStore(
            RuntimePaths.from_roots(repo_root=Path(repo), home=Path(home))
        ).record_managed(record)
    except StateMutationContentionError:
        result.put("contended")
    else:
        result.put("acquired")


def _record_managed_after_attempt(
    home: str,
    repo: str,
    record: ManagedRecord,
    flock_attempted: MultiprocessingQueue[str],
) -> None:
    """Signal immediately before the real exclusive flock, then record state."""
    original_flock = state_module.fcntl.flock

    def signaling_flock(descriptor: int, operation: int) -> None:
        """Notify the parent before forwarding an exclusive flock acquire."""
        if operation == state_module.fcntl.LOCK_EX:
            flock_attempted.put("flock")
        original_flock(descriptor, operation)

    state_module.fcntl.flock = signaling_flock
    try:
        StateStore(
            RuntimePaths.from_roots(repo_root=Path(repo), home=Path(home))
        ).record_managed(record)
    finally:
        state_module.fcntl.flock = original_flock


def _managed_records() -> tuple[ManagedRecord, ManagedRecord]:
    """Build two independent managed-state receipts."""
    return (
        ManagedRecord(
            resource_id="shared-skill-demo-cursor",
            source_digest="a" * 64,
            destination_digest="b" * 64,
            destination=".cursor/skills/demo",
        ),
        ManagedRecord(
            resource_id="shared-skill-demo-codex",
            source_digest="c" * 64,
            destination_digest="d" * 64,
            destination=".codex/skills/demo",
        ),
    )


def test_nonblocking_record_managed_reports_contention_during_load_merge_write(
    repo_root: Path, fake_home: Path
) -> None:
    """A non-blocking record reports contention during another record's merge."""
    records = _managed_records()
    loaded: MultiprocessingQueue[str] = Queue()
    result: MultiprocessingQueue[str] = Queue()
    release: MultiprocessingQueue[str] = Queue()
    with _started_process(
        _record_managed_after_load,
        (str(fake_home), str(repo_root), records[0], loaded, release),
    ) as first:
        try:
            assert loaded.get(timeout=5) == "loaded"
            with _started_process(
                _record_managed_nonblocking,
                (str(fake_home), str(repo_root), records[1], result),
            ) as second:
                assert result.get(timeout=5) == "contended"
            assert second.exitcode == 0
        finally:
            release.put("release")
    assert first.exitcode == 0


def test_blocking_record_managed_waits_then_preserves_both_updates(
    repo_root: Path, fake_home: Path
) -> None:
    """A blocking record waits for another merge and then preserves both receipts."""
    records = _managed_records()
    loaded: MultiprocessingQueue[str] = Queue()
    flock_attempted: MultiprocessingQueue[str] = Queue()
    release: MultiprocessingQueue[str] = Queue()
    released = False
    with _started_process(
        _record_managed_after_load,
        (str(fake_home), str(repo_root), records[0], loaded, release),
    ) as first:
        try:
            assert loaded.get(timeout=5) == "loaded"
            with _started_process(
                _record_managed_after_attempt,
                (str(fake_home), str(repo_root), records[1], flock_attempted),
            ) as second:
                assert flock_attempted.get(timeout=5) == "flock"
                release.put("release")
                released = True
            assert second.exitcode == 0
        finally:
            if not released:
                release.put("release")
    assert first.exitcode == 0
    assert StateStore(_paths(repo_root, fake_home)).load().managed == {
        record.resource_id: record for record in records
    }


def _hold_lock(
    home: str,
    repo: str,
    ready: MultiprocessingQueue[str],
    release: MultiprocessingQueue[str],
) -> None:
    """Hold a lock until the parent signals that the process may exit."""
    store = StateStore(RuntimePaths.from_roots(repo_root=Path(repo), home=Path(home)))
    with store.mutation():
        ready.put("ready")
        release.get()


def test_contention_raises_and_mutates_nothing(
    repo_root: Path, fake_home: Path
) -> None:
    """A non-blocking contender cannot write while another process owns the lock."""
    store = StateStore(_paths(repo_root, fake_home))
    ready: MultiprocessingQueue[str] = Queue()
    release: MultiprocessingQueue[str] = Queue()
    with _started_process(
        _hold_lock,
        (str(fake_home), str(repo_root), ready, release),
    ) as holder:
        try:
            assert ready.get(timeout=5) == "ready"
            with (
                pytest.raises(StateMutationContentionError),
                store.mutation(blocking=False),
            ):
                store.write(BootstrapState())
        finally:
            release.put("done")
    assert holder.exitcode == 0
    assert not (fake_home / ".local/state/ballen-config/state.json").exists()


def test_mutation_rejects_symlinked_lock_leaf_without_touching_target(
    repo_root: Path, fake_home: Path, tmp_path: Path
) -> None:
    """A linked lock leaf is rejected without modifying its outside target."""
    paths = _paths(repo_root, fake_home)
    paths.state_root.mkdir(parents=True)
    target = tmp_path / "outside-lock"
    target.write_bytes(b"outside bytes")
    target.chmod(0o644)
    lock = paths.state_root / ".mutation.lock"
    lock.symlink_to(target)
    expected_bytes = target.read_bytes()
    expected_mode = stat.S_IMODE(target.stat().st_mode)

    try:
        with (
            pytest.raises(ValueError, match=r"mutation lock.*regular file"),
            StateStore(paths).mutation(),
        ):
            pass
        assert target.read_bytes() == expected_bytes
        assert stat.S_IMODE(target.stat().st_mode) == expected_mode
    finally:
        target.chmod(expected_mode)


def test_mutation_closes_descriptor_when_setup_fchmod_fails(
    repo_root: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed lock permission update closes the opened descriptor."""
    descriptor: int | None = None

    def fail_fchmod(fd: int, mode: int) -> None:
        """Capture the descriptor before simulating a permission failure."""
        nonlocal descriptor
        descriptor = fd
        raise OSError("fchmod failed")

    monkeypatch.setattr(os, "fchmod", fail_fchmod)

    with pytest.raises(OSError, match="fchmod failed"):
        StateStore(_paths(repo_root, fake_home))._acquire(blocking=True)

    assert descriptor is not None
    with pytest.raises(OSError):
        os.fstat(descriptor)


def test_compare_and_remove_rejects_non_owner_thread(
    repo_root: Path, fake_home: Path
) -> None:
    """Only the thread that owns a mutation can remove a matching receipt."""
    store = StateStore(_paths(repo_root, fake_home))
    record = ManagedRecord(
        resource_id="receipt",
        source_digest="a" * 64,
        destination_digest="b" * 64,
        destination=".receipt",
    )
    store.write(BootstrapState(managed={record.resource_id: record}))
    errors: ThreadQueue[BaseException] = ThreadQueue()

    def remove_from_non_owner() -> None:
        """Attempt receipt removal from a thread without lock ownership."""
        try:
            store.compare_and_remove(record)
        except BaseException as error:
            errors.put(error)

    with store.mutation():
        thread = threading.Thread(target=remove_from_non_owner)
        thread.start()
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert isinstance(errors.get(timeout=5), StateMutationContentionError)
        assert store.load().managed[record.resource_id] == record


def test_release_rejects_non_owner_thread(repo_root: Path, fake_home: Path) -> None:
    """A non-owner cannot release the outer mutation lock."""
    store = StateStore(_paths(repo_root, fake_home))
    errors: ThreadQueue[BaseException] = ThreadQueue()
    result: MultiprocessingQueue[str] = Queue()

    def release_from_non_owner() -> None:
        """Attempt lock release from a thread without lock ownership."""
        try:
            store._release()
        except BaseException as error:
            errors.put(error)

    store._acquire(blocking=True)
    try:
        thread = threading.Thread(target=release_from_non_owner)
        thread.start()
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert isinstance(errors.get(timeout=5), StateMutationContentionError)

        with _started_process(
            _try_nonblocking_lock,
            (str(fake_home), str(repo_root), result),
        ) as contender:
            assert result.get(timeout=5) == "contended"
        assert contender.exitcode == 0
    finally:
        store._release()
