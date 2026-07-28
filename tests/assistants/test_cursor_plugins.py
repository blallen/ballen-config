"""Tests for native, repository-owned Cursor plugin declarations."""

import json
import os
from pathlib import Path

import pytest

from ballen_config.assistants.cursor_plugins import (
    cursor_local_plugin_configuration,
    cursor_marketplace_doctor_checks,
    cursor_marketplace_plan_actions,
    validate_cursor_local_plugin,
    validate_cursor_local_plugins,
)
from ballen_config.assistants.models import (
    CursorLocalPlugin,
    CursorMarketplacePlugin,
)
from ballen_config.configure import (
    ConfigurationEngine,
    ManagedTreeSpec,
    digest_tree,
    run_configure,
)
from ballen_config.doctor import CheckSeverity, FindingStatus
from ballen_config.planning import PlanAction
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore


@pytest.fixture
def cursor_local_plugin_source(tmp_path: Path) -> Path:
    """Create a valid reviewed local Cursor plugin tree."""
    root = tmp_path / "repo/assistants/shared/plugins/local/example-local"
    (root / ".cursor-plugin").mkdir(parents=True)
    (root / ".cursor-plugin/plugin.json").write_text(
        '{"name":"example-local"}\n', encoding="utf-8"
    )
    (root / "skills/example-skill").mkdir(parents=True)
    (root / "skills/example-skill/SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Example.\n---\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def cursor_marketplace_plugin() -> CursorMarketplacePlugin:
    """Return one required Cursor marketplace declaration."""
    return CursorMarketplacePlugin.model_validate(
        {
            "kind": "cursor-marketplace",
            "id": "example-plugin",
            "targets": ["cursor"],
            "profiles": ["default"],
            "required": True,
            "scope": "user",
            "verification": "manual",
        }
    )


@pytest.fixture
def cursor_local_plugin() -> CursorLocalPlugin:
    """Return one canonical reviewed local plugin declaration."""
    return CursorLocalPlugin.model_validate(
        {
            "kind": "cursor-local",
            "id": "example-local",
            "source": "assistants/shared/plugins/local/example-local",
            "targets": ["cursor"],
            "profiles": ["default"],
            "required": True,
        }
    )


def test_cursor_marketplace_is_always_manual_without_runner_state(
    cursor_marketplace_plugin: CursorMarketplacePlugin,
) -> None:
    """Keep Cursor marketplace selection visible without installed-state claims."""
    plan = cursor_marketplace_plan_actions((cursor_marketplace_plugin,))
    checks = cursor_marketplace_doctor_checks((cursor_marketplace_plugin,))

    assert plan == (
        PlanAction(
            component_id="cursor.plugin.example-plugin",
            category="manual",
            action="open-cursor-customize-add-plugin",
            owner="cursor",
            required=True,
        ),
    )
    assert checks[0].id == "cursor.plugin.example-plugin"
    assert checks[0].status is FindingStatus.MANUAL
    assert checks[0].severity is CheckSeverity.INFO
    assert "required" in checks[0].message


def test_optional_cursor_marketplace_wording_is_informational() -> None:
    """Describe optional marketplace declarations without elevating severity."""
    plugin = CursorMarketplacePlugin.model_validate(
        {
            "kind": "cursor-marketplace",
            "id": "optional-plugin",
            "targets": ["cursor"],
            "required": False,
            "scope": "user",
            "verification": "manual",
        }
    )

    check = cursor_marketplace_doctor_checks((plugin,))[0]

    assert check.status is FindingStatus.MANUAL
    assert check.severity is CheckSeverity.INFO
    assert "optional" in check.message


def test_cursor_local_plugin_requires_canonical_contained_source(
    cursor_local_plugin: CursorLocalPlugin,
    cursor_local_plugin_source: Path,
) -> None:
    """Reject a declaration that aliases a reviewed local plugin source."""
    plugin = cursor_local_plugin.model_copy(
        update={"source": "assistants/shared/plugins/local/other"}
    )

    with pytest.raises(ValueError, match="canonical"):
        validate_cursor_local_plugin(
            plugin,
            repo_root=cursor_local_plugin_source.parents[4],
            shared_skill_names=frozenset(),
        )


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        pytest.param('{"name":"different"}', "manifest name", id="name-mismatch"),
        pytest.param(
            '{"name":"example-local", "name":"other"}',
            "plugin manifest",
            id="duplicate-name",
        ),
        pytest.param("{", "plugin manifest", id="invalid-json"),
    ],
)
def test_cursor_local_plugin_requires_strict_matching_manifest(
    cursor_local_plugin: CursorLocalPlugin,
    cursor_local_plugin_source: Path,
    manifest: str,
    message: str,
) -> None:
    """Reject malformed, ambiguous, and mismatched Cursor manifests."""
    (cursor_local_plugin_source / ".cursor-plugin/plugin.json").write_text(
        manifest, encoding="utf-8"
    )

    with pytest.raises(ValueError, match=message):
        validate_cursor_local_plugin(
            cursor_local_plugin,
            repo_root=cursor_local_plugin_source.parents[4],
            shared_skill_names=frozenset(),
        )


@pytest.mark.parametrize(
    "kind",
    [
        pytest.param("symlink", id="symlink"),
        pytest.param("special", id="special"),
    ],
)
def test_cursor_local_plugin_rejects_symlink_and_special_descendants(
    cursor_local_plugin: CursorLocalPlugin,
    cursor_local_plugin_source: Path,
    tmp_path: Path,
    kind: str,
) -> None:
    """Reject non-regular files before plugin content becomes managed."""
    unsafe = cursor_local_plugin_source / "unsafe"
    if kind == "symlink":
        unsafe.symlink_to(tmp_path / "outside")
    else:
        os.mkfifo(unsafe)

    with pytest.raises(ValueError, match=r"(symlink|unsupported)"):
        validate_cursor_local_plugin(
            cursor_local_plugin,
            repo_root=cursor_local_plugin_source.parents[4],
            shared_skill_names=frozenset(),
        )


def test_cursor_local_plugin_rejects_declared_skill_path_escape(
    cursor_local_plugin: CursorLocalPlugin,
    cursor_local_plugin_source: Path,
) -> None:
    """Reject manifest skill paths that could escape the reviewed tree."""
    (cursor_local_plugin_source / ".cursor-plugin/plugin.json").write_text(
        '{"name":"example-local","skills":"../outside"}', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="skill path"):
        validate_cursor_local_plugin(
            cursor_local_plugin,
            repo_root=cursor_local_plugin_source.parents[4],
            shared_skill_names=frozenset(),
        )


@pytest.mark.parametrize(
    ("manifest_skills", "relative_path", "skill_name"),
    [
        pytest.param(
            "explicit-string",
            "explicit-string",
            "string-skill",
            id="string",
        ),
        pytest.param(
            ("explicit-tuple",),
            "explicit-tuple",
            "tuple-skill",
            id="tuple",
        ),
    ],
)
def test_cursor_local_plugin_resolves_and_collision_checks_explicit_skills(
    cursor_local_plugin: CursorLocalPlugin,
    cursor_local_plugin_source: Path,
    manifest_skills: str | tuple[str, ...],
    relative_path: str,
    skill_name: str,
) -> None:
    """Resolve explicit skill entries before checking reserved Cursor names."""
    skill_root = cursor_local_plugin_source / relative_path
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: Example.\n---\n",
        encoding="utf-8",
    )
    (cursor_local_plugin_source / ".cursor-plugin/plugin.json").write_text(
        json.dumps(
            {"name": "example-local", "skills": manifest_skills},
        ),
        encoding="utf-8",
    )

    assert (
        validate_cursor_local_plugin(
            cursor_local_plugin,
            repo_root=cursor_local_plugin_source.parents[4],
            shared_skill_names=frozenset(),
        )
        == cursor_local_plugin_source
    )
    with pytest.raises(
        ValueError, match=f"cursor local plugin skill collision: {skill_name}"
    ):
        validate_cursor_local_plugin(
            cursor_local_plugin,
            repo_root=cursor_local_plugin_source.parents[4],
            shared_skill_names=frozenset({skill_name}),
        )


def test_cursor_local_plugin_rejects_shared_skill_name_collision(
    cursor_local_plugin: CursorLocalPlugin,
    cursor_local_plugin_source: Path,
) -> None:
    """Reject local skills that collide with all Cursor-targeted shared skills."""
    with pytest.raises(
        ValueError, match="cursor local plugin skill collision: example-skill"
    ):
        validate_cursor_local_plugin(
            cursor_local_plugin,
            repo_root=cursor_local_plugin_source.parents[4],
            shared_skill_names=frozenset({"example-skill"}),
        )


def test_cursor_local_plugin_configuration_uses_native_managed_tree(
    cursor_local_plugin: CursorLocalPlugin,
    cursor_local_plugin_source: Path,
) -> None:
    """Provide one native local-plugin tree through the core engine seam."""
    contribution = cursor_local_plugin_configuration(
        validate_cursor_local_plugins(
            (cursor_local_plugin,),
            repo_root=cursor_local_plugin_source.parents[4],
            shared_skill_names=frozenset(),
        ),
    )

    assert contribution.specs == (
        ManagedTreeSpec(
            id="cursor-local-plugin-example-local",
            source=cursor_local_plugin_source,
            destination=Path(".cursor/plugins/local/example-local"),
            component="cursor",
            expected_source_digest=digest_tree(cursor_local_plugin_source),
        ),
    )


def test_cursor_local_plugin_preserves_unmanaged_collision(
    cursor_local_plugin: CursorLocalPlugin,
    cursor_local_plugin_source: Path,
    temporary_home: Path,
) -> None:
    """Refuse to replace a native local plugin that lacks a receipt."""
    paths = RuntimePaths.from_roots(
        repo_root=cursor_local_plugin_source.parents[4], home=temporary_home
    )
    contribution = cursor_local_plugin_configuration(
        validate_cursor_local_plugins(
            (cursor_local_plugin,),
            repo_root=paths.repo_root,
            shared_skill_names=frozenset(),
        ),
    )
    destination = temporary_home / ".cursor/plugins/local/example-local"
    destination.mkdir(parents=True)
    (destination / "unmanaged").write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="unmanaged"):
        run_configure(
            ConfigurationEngine(paths=paths, state_store=StateStore(paths)),
            contribution.specs,
        )
    assert (destination / "unmanaged").read_text(encoding="utf-8") == "keep"


def test_cursor_local_plugin_managed_update_backup_and_rollback(
    cursor_local_plugin: CursorLocalPlugin,
    cursor_local_plugin_source: Path,
    temporary_home: Path,
) -> None:
    """Use core tree backup and rollback semantics for managed plugin updates."""
    paths = RuntimePaths.from_roots(
        repo_root=cursor_local_plugin_source.parents[4], home=temporary_home
    )
    contribution = cursor_local_plugin_configuration(
        validate_cursor_local_plugins(
            (cursor_local_plugin,),
            repo_root=paths.repo_root,
            shared_skill_names=frozenset(),
        ),
    )
    engine = ConfigurationEngine(
        paths=paths,
        state_store=StateStore(paths),
        timestamp="fixed",
    )
    run_configure(engine, contribution.specs)
    (cursor_local_plugin_source / "new-file").write_text("new", encoding="utf-8")
    updated_contribution = cursor_local_plugin_configuration(
        validate_cursor_local_plugins(
            (cursor_local_plugin,),
            repo_root=paths.repo_root,
            shared_skill_names=frozenset(),
        ),
    )
    run_configure(engine, updated_contribution.specs)
    destination = temporary_home / ".cursor/plugins/local/example-local"

    assert (paths.backup_root / "fixed/.cursor/plugins/local/example-local").is_dir()
    assert (destination / "new-file").read_text(encoding="utf-8") == "new"

    before_rollback = digest_tree(destination)
    (cursor_local_plugin_source / "later-file").write_text("later", encoding="utf-8")

    def fail_publish(source: Path, destination_path: Path) -> None:
        """Fail after the core engine has safely backed up the old tree."""
        if source.parent == destination_path.parent:
            raise OSError("simulated publish failure")
        os.replace(source, destination_path)

    rollback_engine = ConfigurationEngine(
        paths=paths,
        state_store=StateStore(paths),
        timestamp="rollback",
        replace=fail_publish,
    )
    with pytest.raises(OSError, match="simulated publish failure"):
        run_configure(
            rollback_engine,
            cursor_local_plugin_configuration(
                validate_cursor_local_plugins(
                    (cursor_local_plugin,),
                    repo_root=paths.repo_root,
                    shared_skill_names=frozenset(),
                ),
            ).specs,
        )

    assert digest_tree(destination) == before_rollback
    assert not (destination / "later-file").exists()
