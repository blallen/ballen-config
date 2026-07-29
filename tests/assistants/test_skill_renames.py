"""Tests for declared skill rename classification."""

from __future__ import annotations

from pathlib import Path

import pytest

from ballen_config.assistants.models import AgentName
from ballen_config.assistants.skills import (
    LegacyRenameState,
    _SKILL_ROOTS,
    classify_rename_target,
    hash_skill_tree,
)
from ballen_config.state import BootstrapState, ManagedRecord


def _write_skill(root: Path, name: str, body: str = "body") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Example.\n---\n\n# {body}\n",
        encoding="utf-8",
    )
    return root


def _record(
    *,
    name: str,
    target: AgentName,
    digest: str,
    destination: str | None = None,
) -> ManagedRecord:
    relative = destination or (_SKILL_ROOTS[target] / name).as_posix()
    return ManagedRecord(
        resource_id=f"shared-skill-{name}-{target.value}",
        source_digest=digest,
        destination_digest=digest,
        destination=relative,
    )


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_clean_when_absent(
    temporary_home: Path, target: AgentName
) -> None:
    result = classify_rename_target(
        from_name="old-skill",
        to_name="new-skill",
        target=target,
        home=temporary_home,
        state=BootstrapState(),
        successor_digest="a" * 64,
        enabled=True,
    )
    assert result.legacy_state == LegacyRenameState.CLEAN
    assert result.legacy_record is None
    assert result.legacy_relative == _SKILL_ROOTS[target] / "old-skill"
    assert result.successor_relative == _SKILL_ROOTS[target] / "new-skill"


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_exact_live(
    temporary_home: Path, target: AgentName
) -> None:
    legacy = temporary_home / _SKILL_ROOTS[target] / "old-skill"
    _write_skill(legacy, "old-skill")
    digest = hash_skill_tree(legacy)
    record = _record(name="old-skill", target=target, digest=digest)
    result = classify_rename_target(
        from_name="old-skill",
        to_name="new-skill",
        target=target,
        home=temporary_home,
        state=BootstrapState(managed={record.resource_id: record}),
        successor_digest="b" * 64,
        enabled=True,
    )
    assert result.legacy_state == LegacyRenameState.EXACT_LIVE
    assert result.legacy_record == record


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_exact_stale(
    temporary_home: Path, target: AgentName
) -> None:
    digest = "c" * 64
    record = _record(name="old-skill", target=target, digest=digest)
    result = classify_rename_target(
        from_name="old-skill",
        to_name="new-skill",
        target=target,
        home=temporary_home,
        state=BootstrapState(managed={record.resource_id: record}),
        successor_digest="d" * 64,
        enabled=True,
    )
    assert result.legacy_state == LegacyRenameState.EXACT_STALE
    assert result.legacy_record == record


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_absent_mismatched_receipt_is_ambiguous(
    temporary_home: Path, target: AgentName
) -> None:
    record = ManagedRecord(
        resource_id=f"shared-skill-old-skill-{target.value}",
        source_digest="e" * 64,
        destination_digest="e" * 64,
        destination="somewhere/else",
    )
    result = classify_rename_target(
        from_name="old-skill",
        to_name="new-skill",
        target=target,
        home=temporary_home,
        state=BootstrapState(managed={record.resource_id: record}),
        successor_digest="f" * 64,
        enabled=True,
    )
    assert result.legacy_state == LegacyRenameState.BLOCKED_AMBIGUOUS_RECEIPT


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_present_without_receipt_is_unmanaged(
    temporary_home: Path, target: AgentName
) -> None:
    legacy = temporary_home / _SKILL_ROOTS[target] / "old-skill"
    _write_skill(legacy, "old-skill")
    result = classify_rename_target(
        from_name="old-skill",
        to_name="new-skill",
        target=target,
        home=temporary_home,
        state=BootstrapState(),
        successor_digest="a" * 64,
        enabled=True,
    )
    assert (
        result.legacy_state == LegacyRenameState.BLOCKED_UNMANAGED_OR_AMBIGUOUS
    )


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_present_exact_receipt_digest_mismatch_is_drift(
    temporary_home: Path, target: AgentName
) -> None:
    legacy = temporary_home / _SKILL_ROOTS[target] / "old-skill"
    _write_skill(legacy, "old-skill", body="live")
    record = _record(name="old-skill", target=target, digest="0" * 64)
    result = classify_rename_target(
        from_name="old-skill",
        to_name="new-skill",
        target=target,
        home=temporary_home,
        state=BootstrapState(managed={record.resource_id: record}),
        successor_digest="1" * 64,
        enabled=True,
    )
    assert result.legacy_state == LegacyRenameState.BLOCKED_DRIFT


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_skipped_never_inspects_filesystem(
    temporary_home: Path, target: AgentName, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_home(_home: Path) -> Path:
        raise AssertionError("skipped targets must not inspect the filesystem")

    monkeypatch.setattr(
        "ballen_config.assistants.skills._validated_home", fail_home
    )
    result = classify_rename_target(
        from_name="old-skill",
        to_name="new-skill",
        target=target,
        home=temporary_home,
        state=BootstrapState(),
        successor_digest="a" * 64,
        enabled=False,
    )
    assert result.legacy_state == LegacyRenameState.SKIPPED


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_unreceipted_successor_at_exact_digest_blocks(
    temporary_home: Path, target: AgentName
) -> None:
    successor = temporary_home / _SKILL_ROOTS[target] / "new-skill"
    _write_skill(successor, "new-skill")
    digest = hash_skill_tree(successor)
    result = classify_rename_target(
        from_name="old-skill",
        to_name="new-skill",
        target=target,
        home=temporary_home,
        state=BootstrapState(),
        successor_digest=digest,
        enabled=True,
    )
    assert result.legacy_state == LegacyRenameState.BLOCKED_UNMANAGED_SUCCESSOR
