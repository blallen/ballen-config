"""Tests for declared skill rename classification."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import yaml

from ballen_config.assistants.checks import assistant_checks
from ballen_config.assistants.models import AgentName, SkillCatalog
from ballen_config.assistants.skills import (
    _SKILL_ROOTS,
    LegacyRenameState,
    SkillRenameBlockedError,
    apply_skill_rename_cleanups,
    classify_rename_target,
    configuration,
    hash_skill_tree,
    plan_skill_renames,
)
from ballen_config.configure import (
    ConfigurationEngine,
    ConfigurationPlanContributor,
    run_configure,
)
from ballen_config.doctor import CheckSeverity, FindingStatus, run_doctor
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.planning import PlanAction
from ballen_config.runtime import RuntimePaths
from ballen_config.state import BootstrapState, ManagedRecord, StateStore
from tests.assistants.fakes import StatefulAssistantFake


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
def test_classify_clean_when_absent(temporary_home: Path, target: AgentName) -> None:
    """Classify a genuinely absent legacy path as clean."""
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
    "leaf_kind",
    [
        pytest.param("symlink", id="symlink"),
        pytest.param("file", id="regular-file"),
    ],
)
def test_classify_legacy_leaf_blocks(temporary_home: Path, leaf_kind: str) -> None:
    """Block cleanup when the legacy path holds an unsupported leaf."""
    legacy = temporary_home / _SKILL_ROOTS[AgentName.CURSOR] / "old-skill"
    legacy.parent.mkdir(parents=True)
    if leaf_kind == "symlink":
        legacy.symlink_to(temporary_home)
    else:
        legacy.write_text("unsupported", encoding="utf-8")

    result = classify_rename_target(
        from_name="old-skill",
        to_name="new-skill",
        target=AgentName.CURSOR,
        home=temporary_home,
        state=BootstrapState(),
        successor_digest="a" * 64,
        enabled=True,
    )

    assert result.legacy_state == LegacyRenameState.BLOCKED_UNMANAGED_OR_AMBIGUOUS


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_exact_live(temporary_home: Path, target: AgentName) -> None:
    """Classify a received legacy tree at its recorded digest as exact."""
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
def test_classify_exact_stale(temporary_home: Path, target: AgentName) -> None:
    """Classify an absent legacy tree with an exact receipt as resumable."""
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
    """Block an absent legacy path whose receipt has another destination."""
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
    """Block a live legacy tree without an ownership receipt."""
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
    assert result.legacy_state == LegacyRenameState.BLOCKED_UNMANAGED_OR_AMBIGUOUS


@pytest.mark.parametrize(
    "target",
    [AgentName.CURSOR, AgentName.CLAUDE, AgentName.CODEX],
)
def test_classify_present_exact_receipt_digest_mismatch_is_drift(
    temporary_home: Path, target: AgentName
) -> None:
    """Block a received legacy tree whose bytes have drifted."""
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
    """Leave skipped targets entirely outside filesystem classification."""

    def fail_home(_home: Path) -> Path:
        raise AssertionError("skipped targets must not inspect the filesystem")

    monkeypatch.setattr("ballen_config.assistants.skills._validated_home", fail_home)
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
    """Block cleanup when the successor tree lacks a receipt."""
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


def _resolved_setup(
    *enabled: str,
    profiles: tuple[str, ...] = ("default",),
) -> ResolvedSetup:
    components = tuple(
        Component(id=name, manager=Manager.BREW_CASK, package=name) for name in enabled
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


def test_plan_clean_target_installs_only(temporary_home: Path, tmp_path: Path) -> None:
    """Freeze a clean target without a legacy cleanup receipt."""
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
    """Freeze exact live legacy cleanup after successor installation."""
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
    """Freeze stale legacy receipt cleanup without a live tree."""
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
    """Block all rename work when a legacy tree is unowned."""
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
    """Do not create actions for successor profiles outside this setup."""
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
    """Leave receipts outside declared renames untouched."""
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


def test_apply_removes_exact_live_legacy(temporary_home: Path, tmp_path: Path) -> None:
    """Install the successor then remove a proven legacy tree and receipt."""
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


def test_apply_rejects_changed_successor_source_before_publish(
    temporary_home: Path, tmp_path: Path
) -> None:
    """Reject a changed frozen successor source before publishing its receipt."""
    paths, catalog, _digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    successor = temporary_home / ".cursor/skills/new-skill"
    legacy_record = _record(
        name="old-skill",
        target=AgentName.CURSOR,
        digest=hash_skill_tree(legacy),
    )
    store = StateStore(paths)
    store.write(BootstrapState(managed={legacy_record.resource_id: legacy_record}))
    contribution = configuration(_resolved_setup("cursor"), paths, catalog)
    _write_skill(
        paths.repo_root / "assistants/shared/skills/new-skill",
        "new-skill",
        body="mutated",
    )
    engine = ConfigurationEngine(paths=paths, state_store=store, timestamp="apply")

    with pytest.raises(ValueError, match="managed tree source changed since preflight"):
        run_configure(
            engine, contribution.specs, skill_renames=contribution.skill_renames
        )

    assert hash_skill_tree(legacy) == legacy_record.destination_digest
    assert not successor.exists()
    assert store.load().managed == {legacy_record.resource_id: legacy_record}


@pytest.mark.parametrize(
    "legacy_present",
    [
        pytest.param(True, id="exact-live"),
        pytest.param(False, id="exact-stale"),
    ],
)
def test_plan_contributor_renders_rename_cleanup(
    temporary_home: Path, tmp_path: Path, legacy_present: bool
) -> None:
    """Render exact legacy cleanup as a redacted structural plan action."""
    paths, catalog, _digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=legacy_present
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    legacy_digest = hash_skill_tree(legacy) if legacy_present else "a" * 64
    legacy_record = _record(
        name="old-skill", target=AgentName.CURSOR, digest=legacy_digest
    )
    store = StateStore(paths)
    store.write(BootstrapState(managed={legacy_record.resource_id: legacy_record}))
    contribution = configuration(_resolved_setup("cursor"), paths, catalog)
    engine = ConfigurationEngine(paths=paths, state_store=store, timestamp="plan")
    contributor = ConfigurationPlanContributor(
        engine, lambda _resolved, _paths: contribution
    )

    actions = contributor.actions(_resolved_setup("cursor"))

    assert (
        PlanAction(
            component_id="skill-rename-old-skill-cursor",
            category="configure",
            action="skill-rename-cleanup",
            owner="bootstrap",
            path=".cursor/skills/old-skill",
        )
        in actions
    )
    assert all(str(temporary_home) not in action.path for action in actions)


def test_apply_rejects_stale_successor_receipt(
    temporary_home: Path, tmp_path: Path
) -> None:
    """Preserve legacy state when the successor receipt's digest is stale."""
    paths, catalog, digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    successor = temporary_home / ".cursor/skills/new-skill"
    shutil.copytree(paths.repo_root / "assistants/shared/skills/new-skill", successor)
    legacy_record = _record(
        name="old-skill",
        target=AgentName.CURSOR,
        digest=hash_skill_tree(legacy),
    )
    successor_record = ManagedRecord(
        resource_id="shared-skill-new-skill-cursor",
        source_digest=digest,
        destination_digest="0" * 64,
        destination=".cursor/skills/new-skill",
    )
    store = StateStore(paths)
    store.write(
        BootstrapState(
            managed={
                legacy_record.resource_id: legacy_record,
                successor_record.resource_id: successor_record,
            }
        )
    )
    actions = plan_skill_renames(
        catalog=catalog,
        setup=_resolved_setup("cursor"),
        paths=paths,
        state=store.load(),
    )
    engine = ConfigurationEngine(paths=paths, state_store=store, timestamp="apply")

    with store.mutation(), pytest.raises(SkillRenameBlockedError):
        apply_skill_rename_cleanups(engine, actions)

    assert hash_skill_tree(legacy) == legacy_record.destination_digest
    assert hash_skill_tree(successor) == digest
    assert store.load().managed == {
        legacy_record.resource_id: legacy_record,
        successor_record.resource_id: successor_record,
    }


@pytest.mark.parametrize(
    "receipt_update",
    [
        pytest.param(
            {
                "destination": ".cursor/skills/unrelated-skill",
            },
            id="wrong-destination",
        ),
        pytest.param(
            {
                "resource_id": "shared-skill-unrelated-skill-cursor",
            },
            id="wrong-embedded-resource-id",
        ),
    ],
)
def test_apply_rejects_successor_receipt_with_mismatched_identity(
    temporary_home: Path, tmp_path: Path, receipt_update: dict[str, str]
) -> None:
    """Preserve legacy state when successor receipt identity is mismatched."""
    paths, catalog, digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    successor = temporary_home / ".cursor/skills/new-skill"
    shutil.copytree(paths.repo_root / "assistants/shared/skills/new-skill", successor)
    legacy_record = _record(
        name="old-skill",
        target=AgentName.CURSOR,
        digest=hash_skill_tree(legacy),
    )
    successor_record = ManagedRecord(
        resource_id="shared-skill-new-skill-cursor",
        source_digest=digest,
        destination_digest=digest,
        destination=".cursor/skills/new-skill",
    )
    store = StateStore(paths)
    store.write(
        BootstrapState(
            managed={
                legacy_record.resource_id: legacy_record,
                successor_record.resource_id: successor_record,
            }
        )
    )
    actions = plan_skill_renames(
        catalog=catalog,
        setup=_resolved_setup("cursor"),
        paths=paths,
        state=store.load(),
    )
    mismatched_successor_record = successor_record.model_copy(update=receipt_update)
    store.write(
        BootstrapState(
            managed={
                legacy_record.resource_id: legacy_record,
                successor_record.resource_id: mismatched_successor_record,
            }
        )
    )
    engine = ConfigurationEngine(paths=paths, state_store=store, timestamp="apply")

    with store.mutation(), pytest.raises(SkillRenameBlockedError):
        apply_skill_rename_cleanups(engine, actions)

    assert hash_skill_tree(legacy) == legacy_record.destination_digest
    assert hash_skill_tree(successor) == digest
    assert store.load().managed == {
        legacy_record.resource_id: legacy_record,
        successor_record.resource_id: mismatched_successor_record,
    }


def test_compare_and_remove_rollback_restores_legacy_tree(
    temporary_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Restore backed-up legacy content when receipt removal rejects it."""
    paths, catalog, digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    successor = temporary_home / ".cursor/skills/new-skill"
    shutil.copytree(paths.repo_root / "assistants/shared/skills/new-skill", successor)
    legacy_record = _record(
        name="old-skill",
        target=AgentName.CURSOR,
        digest=hash_skill_tree(legacy),
    )
    successor_record = _record(name="new-skill", target=AgentName.CURSOR, digest=digest)
    store = StateStore(paths)
    store.write(
        BootstrapState(
            managed={
                legacy_record.resource_id: legacy_record,
                successor_record.resource_id: successor_record,
            }
        )
    )
    actions = plan_skill_renames(
        catalog=catalog,
        setup=_resolved_setup("cursor"),
        paths=paths,
        state=store.load(),
    )
    engine = ConfigurationEngine(paths=paths, state_store=store, timestamp="apply")
    monkeypatch.setattr(store, "compare_and_remove", lambda _record: False)

    with store.mutation(), pytest.raises(SkillRenameBlockedError):
        apply_skill_rename_cleanups(engine, actions)

    assert hash_skill_tree(legacy) == legacy_record.destination_digest
    assert hash_skill_tree(successor) == successor_record.destination_digest
    assert store.load().managed == {
        legacy_record.resource_id: legacy_record,
        successor_record.resource_id: successor_record,
    }


def test_apply_idempotent_second_run(temporary_home: Path, tmp_path: Path) -> None:
    """Leave a completed rename unchanged on a second configuration run."""
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
    before_backups = (
        list((paths.backup_root).rglob("*")) if paths.backup_root.exists() else []
    )
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
    """Preserve all state when a frozen legacy tree changes before apply."""
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
    assert hash_skill_tree(legacy) != record.destination_digest
    assert not (temporary_home / ".cursor/skills/new-skill").exists()
    assert store.load().managed == {record.resource_id: record}
    assert not paths.backup_root.exists()


def test_apply_preflights_all_targets_before_any_successor_mutation(
    temporary_home: Path, tmp_path: Path
) -> None:
    """Block every successor publish when any frozen legacy target changes."""
    repo = tmp_path / "repo"
    catalog_payload = {
        "skills": [_skill_item("new-first"), _skill_item("new-second")],
        "renames": [
            {"from": "old-first", "to": "new-first"},
            {"from": "old-second", "to": "new-second"},
        ],
    }
    for name in ("new-first", "new-second"):
        _write_skill(repo / "assistants/shared/skills" / name, name, body=name)
    paths = RuntimePaths.from_roots(repo_root=repo, home=temporary_home)
    catalog = SkillCatalog.model_validate(catalog_payload)
    records: dict[str, ManagedRecord] = {}
    legacy_paths: dict[str, Path] = {}
    for name in ("old-first", "old-second"):
        legacy = temporary_home / ".cursor/skills" / name
        _write_skill(legacy, name, body=name)
        record = _record(
            name=name,
            target=AgentName.CURSOR,
            digest=hash_skill_tree(legacy),
        )
        records[record.resource_id] = record
        legacy_paths[name] = legacy
    store = StateStore(paths)
    store.write(BootstrapState(managed=records))
    contribution = configuration(_resolved_setup("cursor"), paths, catalog)
    (legacy_paths["old-second"] / "SKILL.md").write_text(
        "---\nname: old-second\ndescription: Example.\n---\n\n# changed\n",
        encoding="utf-8",
    )

    with pytest.raises(SkillRenameBlockedError):
        run_configure(
            ConfigurationEngine(paths=paths, state_store=store, timestamp="apply"),
            contribution.specs,
            skill_renames=contribution.skill_renames,
        )

    assert all(path.is_dir() for path in legacy_paths.values())
    assert (
        hash_skill_tree(legacy_paths["old-first"])
        == records["shared-skill-old-first-cursor"].destination_digest
    )
    assert (
        hash_skill_tree(legacy_paths["old-second"])
        != records["shared-skill-old-second-cursor"].destination_digest
    )
    assert not (temporary_home / ".cursor/skills/new-first").exists()
    assert not (temporary_home / ".cursor/skills/new-second").exists()
    assert store.load().managed == records
    assert not paths.backup_root.exists()


def test_apply_preflights_existing_successor_proof_before_mutation(
    temporary_home: Path, tmp_path: Path
) -> None:
    """Block all publishes when an exact existing successor receipt is invalid."""
    repo = tmp_path / "repo"
    catalog_payload = {
        "skills": [_skill_item("new-first"), _skill_item("new-second")],
        "renames": [
            {"from": "old-first", "to": "new-first"},
            {"from": "old-second", "to": "new-second"},
        ],
    }
    for name in ("new-first", "new-second"):
        _write_skill(repo / "assistants/shared/skills" / name, name, body=name)
    paths = RuntimePaths.from_roots(repo_root=repo, home=temporary_home)
    catalog = SkillCatalog.model_validate(catalog_payload)
    records: dict[str, ManagedRecord] = {}
    for name in ("old-first", "old-second"):
        legacy = temporary_home / ".cursor/skills" / name
        _write_skill(legacy, name, body=name)
        record = _record(
            name=name,
            target=AgentName.CURSOR,
            digest=hash_skill_tree(legacy),
        )
        records[record.resource_id] = record
    successor = temporary_home / ".cursor/skills/new-second"
    shutil.copytree(repo / "assistants/shared/skills/new-second", successor)
    successor_digest = hash_skill_tree(successor)
    records["shared-skill-new-second-cursor"] = ManagedRecord(
        resource_id="shared-skill-new-second-cursor",
        source_digest=successor_digest,
        destination_digest="0" * 64,
        destination=".cursor/skills/new-second",
    )
    store = StateStore(paths)
    store.write(BootstrapState(managed=records))
    contribution = configuration(_resolved_setup("cursor"), paths, catalog)

    with pytest.raises(SkillRenameBlockedError):
        run_configure(
            ConfigurationEngine(paths=paths, state_store=store, timestamp="apply"),
            contribution.specs,
            skill_renames=contribution.skill_renames,
        )

    assert not (temporary_home / ".cursor/skills/new-first").exists()
    assert successor.is_dir()
    assert store.load().managed == records
    assert not paths.backup_root.exists()


def test_apply_verifies_all_successors_before_any_legacy_cleanup(
    temporary_home: Path, tmp_path: Path
) -> None:
    """Preserve every legacy target when one installed successor lacks proof."""
    repo = tmp_path / "repo"
    catalog_payload = {
        "skills": [_skill_item("new-first"), _skill_item("new-second")],
        "renames": [
            {"from": "old-first", "to": "new-first"},
            {"from": "old-second", "to": "new-second"},
        ],
    }
    for name in ("new-first", "new-second"):
        _write_skill(repo / "assistants/shared/skills" / name, name, body=name)
    paths = RuntimePaths.from_roots(repo_root=repo, home=temporary_home)
    catalog = SkillCatalog.model_validate(catalog_payload)
    records: dict[str, ManagedRecord] = {}
    for name in ("old-first", "old-second"):
        legacy = temporary_home / ".cursor/skills" / name
        _write_skill(legacy, name, body=name)
        record = _record(
            name=name,
            target=AgentName.CURSOR,
            digest=hash_skill_tree(legacy),
        )
        records[record.resource_id] = record
    store = StateStore(paths)
    store.write(BootstrapState(managed=records))
    contribution = configuration(_resolved_setup("cursor"), paths, catalog)
    second_successor = temporary_home / ".cursor/skills/new-second"

    def corrupt_second_successor(source: Path, destination: Path) -> None:
        """Corrupt one published successor before its receipt is recorded."""
        os.replace(source, destination)
        if destination == second_successor:
            (destination / "SKILL.md").write_text(
                "---\nname: new-second\ndescription: Example.\n---\n\n# changed\n",
                encoding="utf-8",
            )

    with pytest.raises(SkillRenameBlockedError):
        run_configure(
            ConfigurationEngine(
                paths=paths,
                state_store=store,
                timestamp="apply",
                replace=corrupt_second_successor,
            ),
            contribution.specs,
            skill_renames=contribution.skill_renames,
        )

    assert (temporary_home / ".cursor/skills/old-first").is_dir()
    assert (temporary_home / ".cursor/skills/old-second").is_dir()
    assert (
        store.load().managed["shared-skill-old-first-cursor"]
        == records["shared-skill-old-first-cursor"]
    )
    assert (
        store.load().managed["shared-skill-old-second-cursor"]
        == records["shared-skill-old-second-cursor"]
    )
    assert (temporary_home / ".cursor/skills/new-first").is_dir()
    assert second_successor.is_dir()
    assert not paths.backup_root.exists()


def test_apply_removes_exact_stale_receipt_without_backup(
    temporary_home: Path, tmp_path: Path
) -> None:
    """Remove only an exact stale legacy receipt after successor proof."""
    paths, catalog, _digest = _prepare_rename_repo(temporary_home, tmp_path)
    legacy_record = _record(
        name="old-skill",
        target=AgentName.CURSOR,
        digest="a" * 64,
    )
    store = StateStore(paths)
    store.write(BootstrapState(managed={legacy_record.resource_id: legacy_record}))
    contribution = configuration(_resolved_setup("cursor"), paths, catalog)

    run_configure(
        ConfigurationEngine(paths=paths, state_store=store, timestamp="apply"),
        contribution.specs,
        skill_renames=contribution.skill_renames,
    )

    assert not (temporary_home / ".cursor/skills/old-skill").exists()
    assert (temporary_home / ".cursor/skills/new-skill").is_dir()
    assert legacy_record.resource_id not in store.load().managed
    assert "shared-skill-new-skill-cursor" in store.load().managed
    assert not paths.backup_root.exists()


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


def test_doctor_reports_blocked_unmanaged_legacy(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, _catalog, _digest = _prepare_rename_repo(temporary_home, tmp_path)
    legacy = temporary_home / ".cursor/skills/old-skill"
    _write_skill(legacy, "old-skill")
    catalog_path = paths.repo_root / "assistants/shared/skills/catalog.yaml"
    catalog_path.write_text(
        yaml.safe_dump(
            {
                "skills": [_skill_item("new-skill")],
                "renames": [{"from": "old-skill", "to": "new-skill"}],
            },
            sort_keys=False,
        )
    )
    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=StatefulAssistantFake(temporary_home),
    )
    report = run_doctor(findings)
    finding = report.finding("skill-rename.old-skill.cursor")
    assert finding.status is FindingStatus.MANUAL
    assert finding.severity is CheckSeverity.WARNING


def test_doctor_reports_unreceipted_successor(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, _catalog, digest = _prepare_rename_repo(temporary_home, tmp_path)
    successor = temporary_home / ".cursor/skills/new-skill"
    shutil.copytree(paths.repo_root / "assistants/shared/skills/new-skill", successor)
    assert hash_skill_tree(successor) == digest
    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=StatefulAssistantFake(temporary_home),
    )
    finding = run_doctor(findings).finding("skill-rename.old-skill.cursor")
    assert finding.status is FindingStatus.MANUAL
    assert finding.severity is CheckSeverity.WARNING


def test_doctor_reports_legacy_drift(temporary_home: Path, tmp_path: Path) -> None:
    paths, _catalog, _digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    record = _record(name="old-skill", target=AgentName.CURSOR, digest="0" * 64)
    StateStore(paths).write(BootstrapState(managed={record.resource_id: record}))
    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=StatefulAssistantFake(temporary_home),
    )
    finding = run_doctor(findings).finding("skill-rename.old-skill.cursor")
    assert finding.status is FindingStatus.DRIFT
    assert finding.severity is CheckSeverity.ERROR
    assert legacy.exists()


def test_doctor_reports_incomplete_cleanup_when_successor_present(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, _catalog, digest = _prepare_rename_repo(
        temporary_home, tmp_path, legacy_present=True
    )
    legacy = temporary_home / ".cursor/skills/old-skill"
    legacy_digest = hash_skill_tree(legacy)
    legacy_record = _record(
        name="old-skill", target=AgentName.CURSOR, digest=legacy_digest
    )
    successor = temporary_home / ".cursor/skills/new-skill"
    shutil.copytree(paths.repo_root / "assistants/shared/skills/new-skill", successor)
    successor_record = ManagedRecord(
        resource_id=f"shared-skill-new-skill-{AgentName.CURSOR.value}",
        source_digest=digest,
        destination_digest=digest,
        destination=".cursor/skills/new-skill",
    )
    StateStore(paths).write(
        BootstrapState(
            managed={
                legacy_record.resource_id: legacy_record,
                successor_record.resource_id: successor_record,
            }
        )
    )
    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=StatefulAssistantFake(temporary_home),
    )
    finding = run_doctor(findings).finding("skill-rename.old-skill.cursor")
    assert finding.status is FindingStatus.DRIFT
    assert finding.severity is CheckSeverity.ERROR


def test_doctor_reports_skipped_rename_target(
    temporary_home: Path, tmp_path: Path
) -> None:
    paths, _catalog, _digest = _prepare_rename_repo(temporary_home, tmp_path)
    findings = assistant_checks(
        enabled=frozenset(),
        paths=paths,
        runner=StatefulAssistantFake(temporary_home),
    )
    finding = run_doctor(findings).finding("skill-rename.old-skill.cursor")
    assert finding.status is FindingStatus.SKIPPED
    assert finding.severity is CheckSeverity.INFO


def test_end_to_end_fixture_rename_plan_configure_doctor_idempotent(
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
    setup = _resolved_setup("cursor")
    contribution = configuration(setup, paths, catalog)
    engine = ConfigurationEngine(
        paths=paths, state_store=store, timestamp="20260729T120000Z"
    )
    run_configure(engine, contribution.specs, skill_renames=contribution.skill_renames)
    assert not legacy.exists()
    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=StatefulAssistantFake(temporary_home),
    )
    assert all(not item.id.startswith("skill-rename.") for item in findings)
    contribution2 = configuration(setup, paths, catalog)
    engine2 = ConfigurationEngine(
        paths=paths, state_store=store, timestamp="20260729T130000Z"
    )
    report = run_configure(
        engine2, contribution2.specs, skill_renames=contribution2.skill_renames
    )
    assert all(action.outcome == "unchanged" for action in report.actions)
    assert all(
        action.legacy_state == LegacyRenameState.CLEAN
        for action in contribution2.skill_renames
    )
