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


import shutil
import yaml

from ballen_config.assistants.skills import (
    SkillRenameBlockedError,
    configuration,
    plan_skill_renames,
)
from ballen_config.assistants.models import SkillCatalog
from ballen_config.configure import ConfigurationEngine, run_configure
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore


def _resolved_setup(
    *enabled: str,
    profiles: tuple[str, ...] = ("default",),
) -> ResolvedSetup:
    components = tuple(
        Component(id=name, manager=Manager.BREW_CASK, package=name)
        for name in enabled
    )
    all_agents = {"cursor", "claude-code", "codex"}
    return ResolvedSetup(
        profiles=profiles,
        components=components,
        skipped=tuple(sorted(all_agents.difference(enabled))),
    )


def _skill_item(
    name: str,
    *,
    targets: tuple[str, ...] = ("cursor",),
    profiles: tuple[str, ...] = ("default",),
) -> dict[str, object]:
    return {
        "name": name,
        "source": f"assistants/shared/skills/{name}",
        "targets": list(targets),
        "profiles": list(profiles),
        "dependencies": [],
        "provenance": "reviewed",
        "portability_status": "reviewed-generic",
    }


def _prepare_rename_repo(
    temporary_home: Path, tmp_path: Path, *, legacy_present: bool = False
) -> tuple[RuntimePaths, SkillCatalog, str]:
    repo = tmp_path / "repo"
    source = repo / "assistants/shared/skills/new-skill"
    _write_skill(source, "new-skill", body="successor")
    catalog_payload = {
        "skills": [_skill_item("new-skill")],
        "renames": [{"from": "old-skill", "to": "new-skill"}],
    }
    catalog_path = repo / "assistants/shared/skills/catalog.yaml"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(yaml.safe_dump(catalog_payload, sort_keys=False))
    paths = RuntimePaths.from_roots(repo_root=repo, home=temporary_home)
    digest = hash_skill_tree(source)
    if legacy_present:
        legacy = temporary_home / ".cursor/skills/old-skill"
        _write_skill(legacy, "old-skill", body="legacy")
    catalog = SkillCatalog.model_validate(catalog_payload)
    return paths, catalog, digest


def test_plan_clean_target_installs_only(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, catalog, digest = _prepare_rename_repo(temporary_home, tmp_path)
    actions = plan_skill_renames(
        catalog=catalog,
        setup=_resolved_setup("cursor"),
        paths=paths,
        state=BootstrapState(),
    )
    assert len(actions) == 1
    assert actions[0].legacy_state == LegacyRenameState.CLEAN
    assert actions[0].legacy_record is None
    assert digest


def test_plan_exact_live_sequences_install_then_cleanup(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, catalog, _digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    digest = hash_skill_tree(legacy)
    record = _record(name="old-skill", target=AgentName.CURSOR, digest=digest)
    actions = plan_skill_renames(
        catalog=catalog,
        setup=_resolved_setup("cursor"),
        paths=paths,
        state=BootstrapState(managed={record.resource_id: record}),
    )
    assert len(actions) == 1
    assert actions[0].legacy_state == LegacyRenameState.EXACT_LIVE
    assert actions[0].legacy_record == record


def test_plan_exact_stale_cleanup_without_backup(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, catalog, _digest = _prepare_rename_repo(temporary_home, tmp_path)
    record = _record(name="old-skill", target=AgentName.CURSOR, digest="a" * 64)
    actions = plan_skill_renames(
        catalog=catalog,
        setup=_resolved_setup("cursor"),
        paths=paths,
        state=BootstrapState(managed={record.resource_id: record}),
    )
    assert len(actions) == 1
    assert actions[0].legacy_state == LegacyRenameState.EXACT_STALE


def test_plan_blocks_when_any_target_infeasible(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, catalog, _digest = _prepare_rename_repo(temporary_home, tmp_path)
    legacy = temporary_home / ".cursor/skills/old-skill"
    _write_skill(legacy, "old-skill")
    with pytest.raises(SkillRenameBlockedError) as excinfo:
        plan_skill_renames(
            catalog=catalog,
            setup=_resolved_setup("cursor"),
            paths=paths,
            state=BootstrapState(),
        )
    assert excinfo.value.state == LegacyRenameState.BLOCKED_UNMANAGED_OR_AMBIGUOUS


def test_candidate_ignores_profile_exclusion(
    temporary_home: Path, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    source = repo / "assistants/shared/skills/new-skill"
    _write_skill(source, "new-skill")
    catalog = SkillCatalog.model_validate(
        {
            "skills": [_skill_item("new-skill", profiles=("work",))],
            "renames": [],
        }
    )
    paths = RuntimePaths.from_roots(repo_root=repo, home=temporary_home)
    legacy = temporary_home / ".cursor/skills/old-skill"
    _write_skill(legacy, "old-skill")
    digest = hash_skill_tree(legacy)
    record = _record(name="old-skill", target=AgentName.CURSOR, digest=digest)
    actions = plan_skill_renames(
        catalog=catalog,
        setup=_resolved_setup("cursor", profiles=("default",)),
        paths=paths,
        state=BootstrapState(managed={record.resource_id: record}),
    )
    assert actions == ()


def test_undeclared_orphan_record_is_not_cleaned(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, catalog, _digest = _prepare_rename_repo(temporary_home, tmp_path)
    catalog = SkillCatalog.model_validate(
        {"skills": [_skill_item("new-skill")], "renames": []}
    )
    record = _record(name="orphan-skill", target=AgentName.CURSOR, digest="b" * 64)
    state = BootstrapState(managed={record.resource_id: record})
    actions = plan_skill_renames(
        catalog=catalog,
        setup=_resolved_setup("cursor"),
        paths=paths,
        state=state,
    )
    assert actions == ()
    assert state.managed[record.resource_id] == record


def test_apply_removes_exact_live_legacy(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, catalog, _digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    digest = hash_skill_tree(legacy)
    record = _record(name="old-skill", target=AgentName.CURSOR, digest=digest)
    store = StateStore(paths)
    store.write(BootstrapState(managed={record.resource_id: record}))
    contribution = configuration(_resolved_setup("cursor"), paths, catalog)
    engine = ConfigurationEngine(
        paths=paths, state_store=store, timestamp="20260729T120000Z"
    )
    run_configure(engine, contribution.specs, skill_renames=contribution.skill_renames)
    assert not legacy.exists()
    state = store.load()
    assert record.resource_id not in state.managed
    assert f"shared-skill-new-skill-{AgentName.CURSOR.value}" in state.managed
    backup = paths.backup_root / "20260729T120000Z" / ".cursor/skills/old-skill"
    assert backup.is_dir()


def test_apply_idempotent_second_run(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, catalog, _digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    digest = hash_skill_tree(legacy)
    record = _record(name="old-skill", target=AgentName.CURSOR, digest=digest)
    store = StateStore(paths)
    store.write(BootstrapState(managed={record.resource_id: record}))
    contribution = configuration(_resolved_setup("cursor"), paths, catalog)
    engine = ConfigurationEngine(
        paths=paths, state_store=store, timestamp="20260729T120000Z"
    )
    run_configure(engine, contribution.specs, skill_renames=contribution.skill_renames)
    before_backups = list((paths.backup_root).rglob("*")) if paths.backup_root.exists() else []
    contribution2 = configuration(_resolved_setup("cursor"), paths, catalog)
    engine2 = ConfigurationEngine(
        paths=paths, state_store=store, timestamp="20260729T130000Z"
    )
    report = run_configure(
        engine2, contribution2.specs, skill_renames=contribution2.skill_renames
    )
    assert contribution2.skill_renames
    assert all(
        action.legacy_state == LegacyRenameState.CLEAN
        for action in contribution2.skill_renames
    )
    assert all(action.outcome == "unchanged" for action in report.actions)
    after = list(paths.backup_root.rglob("*")) if paths.backup_root.exists() else []
    assert len(after) == len(before_backups)


def test_toc_tou_legacy_change_fails_closed(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, catalog, _digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    digest = hash_skill_tree(legacy)
    record = _record(name="old-skill", target=AgentName.CURSOR, digest=digest)
    store = StateStore(paths)
    store.write(BootstrapState(managed={record.resource_id: record}))
    contribution = configuration(_resolved_setup("cursor"), paths, catalog)
    assert contribution.skill_renames
    (legacy / "SKILL.md").write_text(
        "---\nname: old-skill\ndescription: Example.\n---\n\n# mutated\n",
        encoding="utf-8",
    )
    engine = ConfigurationEngine(
        paths=paths, state_store=store, timestamp="20260729T120000Z"
    )
    with pytest.raises(SkillRenameBlockedError):
        run_configure(
            engine, contribution.specs, skill_renames=contribution.skill_renames
        )
    assert legacy.exists()
    assert store.load().managed[record.resource_id] == record


def test_compare_and_remove_mismatch_is_noop(
    temporary_home: Path, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    paths = RuntimePaths.from_roots(repo_root=repo, home=temporary_home)
    store = StateStore(paths)
    expected = _record(name="old-skill", target=AgentName.CURSOR, digest="a" * 64)
    other = expected.model_copy(update={"destination_digest": "b" * 64})
    store.write(BootstrapState(managed={other.resource_id: other}))
    with store.mutation():
        assert store.compare_and_remove(expected) is False
    assert store.load().managed[other.resource_id] == other


def test_crash_between_publish_and_receipt_blocks(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, catalog, digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    legacy_digest = hash_skill_tree(legacy)
    legacy_record = _record(
        name="old-skill", target=AgentName.CURSOR, digest=legacy_digest
    )
    successor = temporary_home / ".cursor/skills/new-skill"
    shutil.copytree(paths.repo_root / "assistants/shared/skills/new-skill", successor)
    assert hash_skill_tree(successor) == digest
    state = BootstrapState(managed={legacy_record.resource_id: legacy_record})
    with pytest.raises(SkillRenameBlockedError) as excinfo:
        plan_skill_renames(
            catalog=catalog,
            setup=_resolved_setup("cursor"),
            paths=paths,
            state=state,
        )
    assert excinfo.value.state == LegacyRenameState.BLOCKED_UNMANAGED_SUCCESSOR
