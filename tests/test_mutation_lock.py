"""Tests for StateStore coarse mutation locking."""

from __future__ import annotations

import os
from multiprocessing import Process, Queue
from pathlib import Path

import pytest

from ballen_config.runtime import RuntimePaths
from ballen_config.state import (
    BootstrapState,
    ManagedRecord,
    StateMutationContentionError,
    StateStore,
)


def _paths(repo_root: Path, home: Path) -> RuntimePaths:
    return RuntimePaths.from_roots(repo_root=repo_root, home=home)


def test_mutation_context_creates_private_lock_file(
    repo_root: Path, fake_home: Path
) -> None:
    store = StateStore(_paths(repo_root, fake_home))
    with store.mutation():
        lock = store.paths.state_root / ".mutation.lock"
        assert lock.is_file()
        assert lock.stat().st_mode & 0o777 == 0o600


def test_mutation_is_reentrant_on_same_store(
    repo_root: Path, fake_home: Path
) -> None:
    store = StateStore(_paths(repo_root, fake_home))
    with store.mutation():
        with store.mutation():
            store.write(BootstrapState())
    assert store.load() == BootstrapState()


def test_record_managed_holds_lock_for_load_merge_write(
    repo_root: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = StateStore(_paths(repo_root, fake_home))
    held: list[bool] = []

    original_write = store.write

    def wrapped_write(state: BootstrapState) -> None:
        held.append(store._lock_depth > 0)
        original_write(state)

    monkeypatch.setattr(store, "write", wrapped_write)
    store.record_managed(
        ManagedRecord(
            resource_id="shared-skill-demo-cursor",
            source_digest="a" * 64,
            destination_digest="b" * 64,
            destination=".cursor/skills/demo",
        )
    )
    assert held == [True]


def _hold_lock(home: str, repo: str, ready: Queue, release: Queue) -> None:
    store = StateStore(RuntimePaths.from_roots(repo_root=Path(repo), home=Path(home)))
    with store.mutation():
        ready.put("ready")
        release.get()


def test_contention_raises_and_mutates_nothing(
    repo_root: Path, fake_home: Path
) -> None:
    store = StateStore(_paths(repo_root, fake_home))
    ready: Queue = Queue()
    release: Queue = Queue()
    holder = Process(
        target=_hold_lock,
        args=(str(fake_home), str(repo_root), ready, release),
    )
    holder.start()
    assert ready.get(timeout=5) == "ready"
    with pytest.raises(StateMutationContentionError):
        with store.mutation(blocking=False):
            store.write(BootstrapState())
    release.put("done")
    holder.join(timeout=5)
    assert not (fake_home / ".local/state/ballen-config/state.json").exists()
