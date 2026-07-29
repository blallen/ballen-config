"""Tests for portable shared-skill validation and convergence."""

import os
import shutil
from hashlib import sha256
from pathlib import Path
from typing import Final, cast

import pytest
import yaml

from ballen_config.assistants.inventory import load_inventory
from ballen_config.assistants.models import AgentName, CatalogResource, SkillCatalog
from ballen_config.assistants.skills import (
    SkillCollisionError,
    SkillCopyAction,
    configuration,
    hash_skill_tree,
    managed_tree_spec,
    plan_skill_copies,
)
from ballen_config.configure import (
    ConfigurationContribution,
    ConfigurationEngine,
    ConfigurationPlanContributor,
    ManagedTreeSpec,
    digest_tree,
)
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.planning import PlanAction
from ballen_config.runtime import RuntimePaths
from ballen_config.state import BootstrapState, ManagedRecord, StateStore


@pytest.fixture
def source_skill(tmp_path: Path) -> Path:
    """Create a small portable skill tree."""
    root = tmp_path / "source" / "example-skill"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Example.\n---\n\n# Example\n"
    )
    (root / "reference.md").write_text("# Reference\n")
    (root / "empty").mkdir()
    return root


@pytest.fixture
def skill_paths(tmp_path: Path, temporary_home: Path) -> RuntimePaths:
    """Create isolated checkout and home roots for catalog integration."""
    repo = tmp_path / "repo"
    (repo / "assistants/shared/skills").mkdir(parents=True)
    return RuntimePaths.from_roots(repo_root=repo, home=temporary_home)


def _write_skill(root: Path, name: str, description: str = "Example.") -> Path:
    """Create one canonical skill source with bounded frontmatter."""
    source = root / "assistants/shared/skills" / name
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n"
    )
    return source


def _catalog_item(
    name: str,
    *,
    targets: tuple[str, ...] = ("cursor",),
    profiles: tuple[str, ...] = ("default",),
    dependencies: tuple[str, ...] = (),
    source: str | None = None,
) -> dict[str, object]:
    """Build one valid shared-skill catalog declaration."""
    return {
        "name": name,
        "source": source or f"assistants/shared/skills/{name}",
        "targets": list(targets),
        "profiles": list(profiles),
        "dependencies": list(dependencies),
        "provenance": "reviewed",
        "portability_status": "reviewed-generic",
    }


def _write_catalog(paths: RuntimePaths, skills: list[dict[str, object]]) -> None:
    """Write a strict shared-skill catalog payload."""
    catalog = paths.repo_root / "assistants/shared/skills/catalog.yaml"
    catalog.write_text(yaml.safe_dump({"skills": skills}, sort_keys=False))


def _catalog(paths: RuntimePaths) -> SkillCatalog:
    """Load a test-owned catalog before calling the no-reread adapter."""
    return SkillCatalog.model_validate(
        yaml.safe_load(
            (paths.repo_root / "assistants/shared/skills/catalog.yaml").read_text()
        )
    )


def _resolved_setup(
    *enabled: str,
    profiles: tuple[str, ...] = ("default",),
) -> ResolvedSetup:
    """Build a resolved setup containing explicit coding-agent components."""
    components = tuple(
        Component(
            id=name,
            manager=Manager.BREW_CASK,
            package=name,
        )
        for name in enabled
    )
    all_agents = {"cursor", "claude-code", "codex"}
    return ResolvedSetup(
        profiles=profiles,
        components=components,
        skipped=tuple(sorted(all_agents.difference(enabled))),
    )


def test_configuration_skips_catalog_and_state_when_all_agents_disabled(
    skill_paths: RuntimePaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All-agent skips do not inspect shared skill sources or state."""
    setup = _resolved_setup()
    assert (
        configuration(setup, skill_paths, SkillCatalog(skills=()))
        == ConfigurationContribution()
    )


def test_configuration_skips_state_when_catalog_selects_no_skills(
    skill_paths: RuntimePaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty selected catalog avoids local state inspection."""
    _write_catalog(skill_paths, [])
    monkeypatch.setattr(
        "ballen_config.assistants.skills.StateStore.load",
        lambda _store: pytest.fail("state read"),
    )

    assert (
        configuration(_resolved_setup("cursor"), skill_paths, _catalog(skill_paths))
        == ConfigurationContribution()
    )


def test_hash_is_stable_across_creation_order(
    tmp_path: Path,
    source_skill: Path,
) -> None:
    """Hash sorted relative entries independent of creation order."""
    second = tmp_path / "second"
    second.mkdir()
    (second / "empty").mkdir()
    (second / "reference.md").write_text("# Reference\n")
    (second / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Example.\n---\n\n# Example\n"
    )
    assert hash_skill_tree(source_skill) == hash_skill_tree(second)


def test_hash_changes_for_executable_bit(
    tmp_path: Path,
    source_skill: Path,
) -> None:
    """Include the user executable bit in the deterministic digest."""
    second = tmp_path / "second"
    shutil.copytree(source_skill, second)
    before = hash_skill_tree(second)
    os.chmod(second / "reference.md", 0o700)
    assert hash_skill_tree(second) != before


def test_hash_changes_for_empty_directory(
    source_skill: Path,
) -> None:
    """Include empty directory entries in the deterministic digest."""
    before = hash_skill_tree(source_skill)
    (source_skill / "another-empty").mkdir()
    assert hash_skill_tree(source_skill) != before


def test_hash_matches_core_managed_tree_digest(source_skill: Path) -> None:
    """Use the exact digest persisted by the core configuration engine."""
    assert hash_skill_tree(source_skill) == digest_tree(source_skill)


def test_missing_skill_entrypoint_is_rejected(tmp_path: Path) -> None:
    """Require a regular standard skill entrypoint."""
    with pytest.raises(ValueError, match=r"missing SKILL\.md"):
        hash_skill_tree(tmp_path)


def test_root_symlink_is_rejected(
    tmp_path: Path,
    source_skill: Path,
) -> None:
    """Reject a skill root that aliases another tree."""
    root = tmp_path / "root-link"
    root.symlink_to(source_skill, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        hash_skill_tree(root)


def test_dangling_root_symlink_is_rejected(tmp_path: Path) -> None:
    """Reject a dangling skill-root alias without following it."""
    root = tmp_path / "root-link"
    root.symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        hash_skill_tree(root)


def test_special_root_is_rejected(tmp_path: Path) -> None:
    """Reject a non-directory skill root before reading it."""
    root = tmp_path / "fifo"
    os.mkfifo(root)
    with pytest.raises(ValueError, match="directory"):
        hash_skill_tree(root)


@pytest.mark.parametrize(
    "dangling",
    [
        pytest.param(False, id="resolved-target"),
        pytest.param(True, id="dangling-target"),
    ],
)
def test_descendant_symlink_is_rejected(
    tmp_path: Path,
    source_skill: Path,
    dangling: bool,
) -> None:
    """Reject resolved and dangling links anywhere in the skill tree."""
    target = tmp_path / "missing"
    if not dangling:
        target.write_text("outside")
    (source_skill / "escape").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        hash_skill_tree(source_skill)


def test_descendant_special_file_is_rejected(source_skill: Path) -> None:
    """Reject special files without attempting to read their bytes."""
    os.mkfifo(source_skill / "pipe")
    with pytest.raises(ValueError, match="unsupported"):
        hash_skill_tree(source_skill)


def _managed_skill_state(
    *,
    target: AgentName,
    digest: str,
    destination: str | None = None,
    resource_id: str | None = None,
) -> BootstrapState:
    """Build one normalized shared-skill ownership record."""
    normalized_id = resource_id or f"shared-skill-example-skill-{target.value}"
    relative = destination or f".{target.value}/skills/example-skill"
    if target is AgentName.CODEX and destination is None:
        relative = ".agents/skills/example-skill"
    record = ManagedRecord(
        resource_id=normalized_id,
        source_digest=digest,
        destination_digest=digest,
        destination=relative,
    )
    return BootstrapState(managed={normalized_id: record})


def test_all_agent_destinations_and_specs_are_native(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Use native roots, normalized IDs, and home-relative core specs."""
    actions = plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(
            AgentName.CURSOR,
            AgentName.CLAUDE,
            AgentName.CODEX,
        ),
        home=temporary_home,
        state=BootstrapState(),
    )
    assert {action.destination for action in actions} == {
        temporary_home / ".cursor/skills/example-skill",
        temporary_home / ".claude/skills/example-skill",
        temporary_home / ".agents/skills/example-skill",
    }
    specs = tuple(managed_tree_spec(action) for action in actions)
    assert all(isinstance(spec, ManagedTreeSpec) for spec in specs)
    assert {spec.id for spec in specs} == {
        "shared-skill-example-skill-cursor",
        "shared-skill-example-skill-claude-code",
        "shared-skill-example-skill-codex",
    }
    assert {spec.destination for spec in specs} == {
        Path(".cursor/skills/example-skill"),
        Path(".claude/skills/example-skill"),
        Path(".agents/skills/example-skill"),
    }
    assert {spec.component for spec in specs} == {
        "cursor",
        "claude-code",
        "codex",
    }


@pytest.mark.parametrize(
    "relative_root",
    [
        pytest.param(".cursor/skills", id="cursor-skills"),
        pytest.param(".claude/skills", id="claude-skills"),
        pytest.param(".agents/skills", id="agents-skills"),
        pytest.param(".codex/skills", id="codex-skills"),
    ],
)
def test_same_name_different_hash_in_cursor_scanned_root_is_collision(
    source_skill: Path,
    temporary_home: Path,
    relative_root: str,
) -> None:
    """Reject different content in every root Cursor scans."""
    conflict = temporary_home / relative_root / "example-skill"
    conflict.mkdir(parents=True)
    (conflict / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Different.\n---\n"
    )
    with pytest.raises(SkillCollisionError, match="example-skill") as error:
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )
    assert "Different" not in str(error.value)
    assert str(temporary_home) not in str(error.value)


def test_non_cursor_targets_ignore_divergent_cursor_skill(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Plan only requested native roots when Cursor is not a target."""
    conflict = temporary_home / ".cursor/skills/example-skill"
    conflict.mkdir(parents=True)
    (conflict / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Different.\n---\n"
    )

    actions = plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(AgentName.CLAUDE, AgentName.CODEX),
        home=temporary_home,
        state=BootstrapState(),
    )

    assert {action.relative_destination for action in actions} == {
        Path(".claude/skills/example-skill"),
        Path(".agents/skills/example-skill"),
    }


def test_identical_destination_is_a_no_op(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Avoid rewriting a byte-identical native skill."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.parent.mkdir(parents=True)
    shutil.copytree(source_skill, destination)
    assert (
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )
        == ()
    )


def test_clean_managed_destination_is_an_update(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Classify a clean managed copy with a new source as an update."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Old.\n---\n"
    )
    old_digest = hash_skill_tree(destination)
    state = _managed_skill_state(target=AgentName.CURSOR, digest=old_digest)
    actions = plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(AgentName.CURSOR,),
        home=temporary_home,
        state=state,
    )
    assert [action.state for action in actions] == ["update"]


def test_managed_destination_drift_is_a_repair(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Classify local drift from the stored destination digest as repair."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Locally changed.\n---\n"
    )
    state = _managed_skill_state(target=AgentName.CURSOR, digest="b" * 64)
    actions = plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(AgentName.CURSOR,),
        home=temporary_home,
        state=state,
    )
    assert [action.state for action in actions] == ["repair"]


def test_unmanaged_destination_is_preserved(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Report a collision without mutating unmanaged destination bytes."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.mkdir(parents=True)
    entrypoint = destination / "SKILL.md"
    entrypoint.write_text("---\nname: example-skill\ndescription: Mine.\n---\n")
    before = entrypoint.read_bytes()
    with pytest.raises(SkillCollisionError, match="example-skill"):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )
    assert entrypoint.read_bytes() == before


@pytest.mark.parametrize(
    ("destination", "resource_id"),
    [
        pytest.param(".cursor/skills/other", None, id="destination-mismatch"),
        pytest.param(None, "shared-skill-other-cursor", id="resource-id-mismatch"),
    ],
)
def test_managed_record_must_match_resource_and_destination(
    source_skill: Path,
    temporary_home: Path,
    destination: str | None,
    resource_id: str | None,
) -> None:
    """Reject ownership records whose public identity is inconsistent."""
    state = _managed_skill_state(
        target=AgentName.CURSOR,
        digest="a" * 64,
        destination=destination,
        resource_id=resource_id,
    )
    with pytest.raises(ValueError, match="managed record mismatch"):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=state,
        )


def test_qualified_skill_names_do_not_collide(
    tmp_path: Path,
    temporary_home: Path,
) -> None:
    """Allow distinct, globally qualified skill names."""
    actions: list[SkillCopyAction] = []
    for name, target in (
        ("codex-example", AgentName.CODEX),
        ("claude-example", AgentName.CLAUDE),
    ):
        source = tmp_path / name
        source.mkdir()
        (source / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Qualified.\n---\n"
        )
        actions.extend(
            plan_skill_copies(
                source=source,
                name=name,
                targets=(target,),
                home=temporary_home,
                state=BootstrapState(),
            )
        )
    assert {action.resource_id for action in actions} == {
        "shared-skill-codex-example-codex",
        "shared-skill-claude-example-claude-code",
    }


@pytest.mark.parametrize(
    ("entrypoint", "message"),
    [
        pytest.param(
            "# No frontmatter\n", "initial YAML frontmatter", id="missing-frontmatter"
        ),
        pytest.param("---\nname: example-skill\n", "unterminated", id="unterminated"),
        pytest.param("---\nname: [\n---\n", "invalid", id="invalid-yaml"),
    ],
)
def test_frontmatter_must_be_initial_terminated_and_valid(
    source_skill: Path,
    temporary_home: Path,
    entrypoint: str,
    message: str,
) -> None:
    """Reject malformed metadata without scanning the Markdown body."""
    (source_skill / "SKILL.md").write_text(entrypoint)
    with pytest.raises(ValueError, match=message):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )


def test_frontmatter_parse_is_bounded(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Reject an unbounded opening document before parsing later content."""
    (source_skill / "SKILL.md").write_text(
        "---\nname: example-skill\npadding: " + ("x" * 70_000) + "\n---\n"
    )
    with pytest.raises(ValueError, match="size limit"):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )


@pytest.mark.parametrize(
    ("directory", "frontmatter", "catalog"),
    [
        pytest.param(
            "source-name", "source-name", "catalog-name", id="catalog-name-mismatch"
        ),
        pytest.param(
            "source-name",
            "frontmatter-name",
            "source-name",
            id="frontmatter-name-mismatch",
        ),
    ],
)
def test_directory_frontmatter_and_catalog_names_must_agree(
    tmp_path: Path,
    temporary_home: Path,
    directory: str,
    frontmatter: str,
    catalog: str,
) -> None:
    """Require one globally unique name at every declaration boundary."""
    source = tmp_path / directory
    source.mkdir()
    (source / "SKILL.md").write_text(
        f"---\nname: {frontmatter}\ndescription: Example.\n---\n"
    )
    with pytest.raises(ValueError, match="skill name mismatch"):
        plan_skill_copies(
            source=source,
            name=catalog,
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )


@pytest.mark.parametrize(
    ("targets", "message"),
    [
        pytest.param((AgentName.CURSOR, AgentName.CURSOR), "duplicate", id="duplicate"),
        pytest.param((AgentName.SHARED,), "unsupported", id="shared"),
        pytest.param((), "must not be empty", id="empty"),
        pytest.param(
            cast(tuple[AgentName, ...], ("other",)), "unsupported", id="unknown"
        ),
    ],
)
def test_targets_must_be_unique_supported_concrete_agents(
    source_skill: Path,
    temporary_home: Path,
    targets: tuple[AgentName, ...],
    message: str,
) -> None:
    """Reject invalid target tuples before inspecting destinations."""
    with pytest.raises(ValueError, match=message):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=targets,
            home=temporary_home,
            state=BootstrapState(),
        )


@pytest.mark.parametrize(
    "dangling",
    [
        pytest.param(False, id="resolved-target"),
        pytest.param(True, id="dangling-target"),
    ],
)
def test_destination_leaf_symlink_is_rejected_without_outside_read(
    source_skill: Path,
    temporary_home: Path,
    tmp_path: Path,
    dangling: bool,
) -> None:
    """Reject resolved and dangling destination links before tree hashing."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    if not dangling:
        outside.mkdir()
        (outside / "SKILL.md").write_text("outside secret")
    destination.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )
    if not dangling:
        assert (outside / "SKILL.md").read_text() == "outside secret"


def test_destination_ancestor_symlink_is_rejected(
    source_skill: Path,
    temporary_home: Path,
    tmp_path: Path,
) -> None:
    """Reject a native-root ancestor that escapes the approved home."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (temporary_home / ".cursor").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinked path component"):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )
    assert list(outside.iterdir()) == []


def test_destination_special_file_is_rejected(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Reject a special destination without opening it."""
    destination = temporary_home / ".cursor/skills/example-skill"
    destination.parent.mkdir(parents=True)
    os.mkfifo(destination)
    with pytest.raises(ValueError, match="unsupported"):
        plan_skill_copies(
            source=source_skill,
            name="example-skill",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )


def test_skill_name_cannot_escape_home(
    source_skill: Path,
    temporary_home: Path,
) -> None:
    """Reject traversal-like names before constructing native paths."""
    with pytest.raises(ValueError, match="invalid skill name"):
        plan_skill_copies(
            source=source_skill,
            name="../outside",
            targets=(AgentName.CURSOR,),
            home=temporary_home,
            state=BootstrapState(),
        )
    assert not (temporary_home.parent / "outside").exists()


def test_configuration_rejects_noncanonical_and_escaping_sources(
    skill_paths: RuntimePaths,
    tmp_path: Path,
) -> None:
    """Keep catalog sources canonical and inside the checkout."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Outside.\n---\n"
    )
    canonical = skill_paths.repo_root / "assistants/shared/skills/example-skill"
    canonical.symlink_to(outside, target_is_directory=True)
    _write_catalog(skill_paths, [_catalog_item("example-skill")])
    with pytest.raises(ValueError, match="symlinked path component"):
        configuration(_resolved_setup("cursor"), skill_paths, _catalog(skill_paths))

    canonical.unlink()
    _write_catalog(
        skill_paths,
        [
            _catalog_item(
                "example-skill",
                source="../outside/example-skill",
            )
        ],
    )
    with pytest.raises(ValueError, match="canonical"):
        configuration(_resolved_setup("cursor"), skill_paths, _catalog(skill_paths))


def test_selected_dependency_must_also_be_eligible(
    skill_paths: RuntimePaths,
) -> None:
    """Validate dependencies without auto-selecting ineligible skills."""
    _write_skill(skill_paths.repo_root, "base")
    _write_skill(skill_paths.repo_root, "consumer")
    _write_catalog(
        skill_paths,
        [
            _catalog_item("base", profiles=("work",)),
            _catalog_item("consumer", dependencies=("base",)),
        ],
    )
    with pytest.raises(ValueError, match="dependency profiles do not cover"):
        configuration(_resolved_setup("cursor"), skill_paths, _catalog(skill_paths))


def test_selected_dependency_cannot_target_only_a_skipped_agent(
    skill_paths: RuntimePaths,
) -> None:
    """Treat a dependency with no enabled target as ineligible."""
    _write_skill(skill_paths.repo_root, "base")
    _write_skill(skill_paths.repo_root, "consumer")
    _write_catalog(
        skill_paths,
        [
            _catalog_item("base", targets=("codex",)),
            _catalog_item("consumer", dependencies=("base",)),
        ],
    )
    with pytest.raises(ValueError, match="dependency targets do not cover"):
        configuration(_resolved_setup("cursor"), skill_paths, _catalog(skill_paths))


def test_dependency_must_cover_consumer_enabled_targets(
    skill_paths: RuntimePaths,
) -> None:
    """Reject a selected dependency that targets a different enabled agent."""
    _write_skill(skill_paths.repo_root, "base")
    _write_skill(skill_paths.repo_root, "consumer")
    _write_catalog(
        skill_paths,
        [
            _catalog_item("base", targets=("codex",)),
            _catalog_item(
                "consumer",
                targets=("cursor",),
                dependencies=("base",),
            ),
        ],
    )
    with pytest.raises(ValueError, match="dependency targets do not cover"):
        configuration(
            _resolved_setup("cursor", "codex"), skill_paths, _catalog(skill_paths)
        )


@pytest.mark.parametrize(
    ("dependency_targets", "consumer_targets", "expected_spec_count"),
    [
        pytest.param(("cursor",), ("cursor",), 2, id="same-targets"),
        pytest.param(("cursor", "codex"), ("cursor",), 3, id="dependency-superset"),
        pytest.param(("cursor", "codex"), ("cursor", "codex"), 4, id="all-targets"),
    ],
)
def test_dependency_target_coverage_accepts_same_or_superset_targets(
    skill_paths: RuntimePaths,
    dependency_targets: tuple[str, ...],
    consumer_targets: tuple[str, ...],
    expected_spec_count: int,
) -> None:
    """Allow dependencies covering all enabled consumer targets."""
    _write_skill(skill_paths.repo_root, "base")
    _write_skill(skill_paths.repo_root, "consumer")
    _write_catalog(
        skill_paths,
        [
            _catalog_item("base", targets=dependency_targets),
            _catalog_item(
                "consumer",
                targets=consumer_targets,
                dependencies=("base",),
            ),
        ],
    )
    contribution = configuration(
        _resolved_setup("cursor", "codex"),
        skill_paths,
        _catalog(skill_paths),
    )
    assert len(contribution.specs) == expected_spec_count


def test_configuration_selects_all_eligible_skills_deterministically(
    skill_paths: RuntimePaths,
) -> None:
    """Select every eligible catalog skill without dependency expansion."""
    _write_skill(skill_paths.repo_root, "base")
    _write_skill(skill_paths.repo_root, "consumer")
    _write_catalog(
        skill_paths,
        [
            _catalog_item("consumer", dependencies=("base",)),
            _catalog_item("base"),
        ],
    )
    contribution = configuration(
        _resolved_setup("cursor"), skill_paths, _catalog(skill_paths)
    )
    assert [spec.id for spec in contribution.specs] == [
        "shared-skill-base-cursor",
        "shared-skill-consumer-cursor",
    ]
    assert not skill_paths.state_root.exists()
    assert not (skill_paths.home / ".cursor").exists()


def test_using_jujutsu_catalog_inventory_and_configuration_are_synchronized(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Verify using-jujutsu metadata, digests, renames, and read-only plans."""
    inventory = load_inventory(
        repo_root / "assistants/inventory.yaml", repo_root
    ).inventory
    catalog = yaml.safe_load(
        (repo_root / "assistants/shared/skills/catalog.yaml").read_text()
    )
    resource = next(
        item for item in inventory.resources if item.id == "shared.skills.catalog"
    )
    expected_skill = {
        "name": "using-jujutsu",
        "source": "assistants/shared/skills/using-jujutsu",
        "targets": ["cursor", "claude-code", "codex"],
        "profiles": ["default"],
        "dependencies": [],
        "provenance": (
            "Renamed from the promoted jujutsu-workflow skill added in commit "
            "2d057f673971232e2327924c1a5f846ff9ace48e, itself promoted out of "
            "plato/skills/jujutsu-workflow at commit "
            "f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records both."
        ),
        "portability_status": "reviewed-generic",
    }
    entry = next(item for item in catalog["skills"] if item["name"] == "using-jujutsu")
    assert entry == expected_skill
    assert catalog.get("renames") == [
        {"from": "jujutsu-workflow", "to": "using-jujutsu"}
    ]
    assert isinstance(resource, CatalogResource)
    assert resource.owner is AgentName.SHARED
    assert resource.targets == (
        AgentName.CURSOR,
        AgentName.CLAUDE,
        AgentName.CODEX,
    )
    source = repo_root / "assistants/shared/skills/using-jujutsu"
    expected_using_jujutsu_tree_digest = "36852753f77034db3513201dbd75318dee30413d90f8262aa723a7523b374cf0"  # pragma: allowlist secret
    assert hash_skill_tree(source) == expected_using_jujutsu_tree_digest
    assert (
        sha256((source / "SKILL.md").read_bytes()).hexdigest()
        == (
            "bad8b9e4975e5ecf674a3b226e8a3a01f6269353b8fabccc16cb19212187aef7"  # pragma: allowlist secret
        )
    )
    assert (
        sha256((source / "reference.md").read_bytes()).hexdigest()
        == (
            "5bf5d9320b46672700b4d0d2f063ba90ce7d8fd67ec83f096971f522576b2a93"  # pragma: allowlist secret
        )
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    contribution = configuration(
        _resolved_setup("cursor", "claude-code", "codex"),
        paths,
        _catalog(paths),
    )
    assert all(isinstance(spec, ManagedTreeSpec) for spec in contribution.specs)
    jujutsu_specs = [
        (spec.id, spec.destination)
        for spec in contribution.specs
        if spec.id.startswith("shared-skill-using-jujutsu-")
    ]
    assert jujutsu_specs == [
        (
            "shared-skill-using-jujutsu-codex",
            Path(".agents/skills/using-jujutsu"),
        ),
        (
            "shared-skill-using-jujutsu-claude-code",
            Path(".claude/skills/using-jujutsu"),
        ),
        (
            "shared-skill-using-jujutsu-cursor",
            Path(".cursor/skills/using-jujutsu"),
        ),
    ]
    assert contribution.skill_renames
    assert all(
        action.from_name == "jujutsu-workflow" and action.to_name == "using-jujutsu"
        for action in contribution.skill_renames
    )
    assert not paths.state_root.exists()
    assert not (temporary_home / ".cursor/skills/using-jujutsu").exists()
    assert not (temporary_home / ".claude/skills/using-jujutsu").exists()
    assert not (temporary_home / ".agents/skills/using-jujutsu").exists()


def test_jujutsu_workflow_rename_converges_managed_install(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Rename managed jujutsu-workflow installs onto using-jujutsu under lock."""
    import shutil

    from ballen_config.configure import ConfigurationEngine, run_configure

    legacy_fixture = (
        Path(__file__).resolve().parent / "fixtures" / "jujutsu-workflow-legacy"
    )
    legacy_digest = "e7ca3f2e0a0f3f79dff90cc8fd718d74fecf18234d9b57dfeb0245480af1a8ec"  # pragma: allowlist secret
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    store = StateStore(paths)
    managed: dict[str, ManagedRecord] = {}
    for target, relative in (
        (AgentName.CURSOR, Path(".cursor/skills/jujutsu-workflow")),
        (AgentName.CLAUDE, Path(".claude/skills/jujutsu-workflow")),
        (AgentName.CODEX, Path(".agents/skills/jujutsu-workflow")),
    ):
        destination = temporary_home / relative
        destination.mkdir(parents=True)
        shutil.copy(legacy_fixture / "SKILL.md", destination / "SKILL.md")
        shutil.copy(legacy_fixture / "reference.md", destination / "reference.md")
        assert hash_skill_tree(destination) == legacy_digest
        record = ManagedRecord(
            resource_id=f"shared-skill-jujutsu-workflow-{target.value}",
            source_digest=legacy_digest,
            destination_digest=legacy_digest,
            destination=relative.as_posix(),
        )
        managed[record.resource_id] = record
    store.write(BootstrapState(managed=managed))
    catalog = _catalog(paths)
    setup = _resolved_setup("cursor", "claude-code", "codex")
    contribution = configuration(setup, paths, catalog)
    engine = ConfigurationEngine(
        paths=paths, state_store=store, timestamp="20260729T140000Z"
    )
    run_configure(engine, contribution.specs, skill_renames=contribution.skill_renames)
    state = store.load()
    for target, relative in (
        (AgentName.CURSOR, Path(".cursor/skills")),
        (AgentName.CLAUDE, Path(".claude/skills")),
        (AgentName.CODEX, Path(".agents/skills")),
    ):
        assert not (temporary_home / relative / "jujutsu-workflow").exists()
        assert (temporary_home / relative / "using-jujutsu").is_dir()
        successor_id = f"shared-skill-using-jujutsu-{target.value}"
        assert successor_id in state.managed
        assert f"shared-skill-jujutsu-workflow-{target.value}" not in state.managed
    backups = list((paths.backup_root / "20260729T140000Z").rglob("SKILL.md"))
    assert len(backups) == 3
    contribution2 = configuration(setup, paths, catalog)
    engine2 = ConfigurationEngine(
        paths=paths, state_store=store, timestamp="20260729T150000Z"
    )
    report = run_configure(
        engine2, contribution2.specs, skill_renames=contribution2.skill_renames
    )
    assert all(action.outcome == "unchanged" for action in report.actions)
    assert all(
        action.legacy_state.value == "clean" for action in contribution2.skill_renames
    )
    assert not (paths.backup_root / "20260729T150000Z").exists()


@pytest.mark.parametrize(
    ("stored_digest", "expected_action"),
    [
        pytest.param(None, "update", id="missing-digest"),
        pytest.param("0" * 64, "repair", id="stale-digest"),
    ],
)
def test_skill_plan_override_is_read_only_before_confirmation(
    skill_paths: RuntimePaths,
    stored_digest: str | None,
    expected_action: str,
) -> None:
    """Expose update versus repair structurally without mutating home or state."""
    source = _write_skill(skill_paths.repo_root, "example-skill", "New.")
    _write_catalog(skill_paths, [_catalog_item("example-skill")])
    destination = skill_paths.home / ".cursor/skills/example-skill"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Old.\n---\n"
    )
    current_digest = hash_skill_tree(destination)
    recorded_digest = stored_digest or current_digest
    resource_id = "shared-skill-example-skill-cursor"
    store = StateStore(skill_paths)
    store.record_managed(
        ManagedRecord(
            resource_id=resource_id,
            source_digest=recorded_digest,
            destination_digest=recorded_digest,
            destination=".cursor/skills/example-skill",
        )
    )
    before_state = store.load()
    before_bytes = (destination / "SKILL.md").read_bytes()
    contribution = configuration(
        _resolved_setup("cursor"), skill_paths, _catalog(skill_paths)
    )
    engine = ConfigurationEngine(
        paths=skill_paths,
        state_store=store,
        timestamp="plan",
    )
    contributor = ConfigurationPlanContributor(
        engine,
        lambda _resolved, _paths: contribution,
    )

    actions = contributor.actions(_resolved_setup("cursor"))

    assert actions == (
        PlanAction(
            component_id=resource_id,
            category="configure",
            action=expected_action,
            owner="bootstrap",
            path="~/.cursor/skills/example-skill",
        ),
    )
    assert source.is_dir()
    assert (destination / "SKILL.md").read_bytes() == before_bytes
    assert store.load() == before_state
    assert not (skill_paths.backup_root / "plan").exists()


def test_applied_skill_record_uses_public_tree_digest(
    skill_paths: RuntimePaths,
) -> None:
    """Persist destination digests compatible with skill collision checks."""
    source = _write_skill(skill_paths.repo_root, "example-skill")
    action = plan_skill_copies(
        source=source,
        name="example-skill",
        targets=(AgentName.CURSOR,),
        home=skill_paths.home,
        state=BootstrapState(),
    )[0]
    store = StateStore(skill_paths)
    engine = ConfigurationEngine(
        paths=skill_paths,
        state_store=store,
        timestamp="apply",
    )
    engine.apply(managed_tree_spec(action))
    destination = skill_paths.home / ".cursor/skills/example-skill"
    record = store.load().managed[action.resource_id]
    assert record.destination_digest == hash_skill_tree(destination)


def test_managed_skill_publish_failure_rolls_back(
    skill_paths: RuntimePaths,
) -> None:
    """Restore the original managed tree and state after publish failure."""
    source_skill = _write_skill(skill_paths.repo_root, "example-skill")
    destination = skill_paths.home / ".cursor/skills/example-skill"
    destination.mkdir(parents=True)
    original = destination / "SKILL.md"
    original.write_text("---\nname: example-skill\ndescription: Original.\n---\n")
    store = StateStore(skill_paths)
    old_digest = hash_skill_tree(destination)
    resource_id = "shared-skill-example-skill-cursor"
    store.record_managed(
        ManagedRecord(
            resource_id=resource_id,
            source_digest=old_digest,
            destination_digest=old_digest,
            destination=".cursor/skills/example-skill",
        )
    )
    before_state = store.load()
    replacements = 0

    def fail_publish(source: Path, target: Path) -> None:
        """Fail the staged publish, then permit managed backup restoration."""
        nonlocal replacements
        replacements += 1
        if replacements == 1:
            raise OSError("injected publish failure")
        os.replace(source, target)

    subject = ConfigurationEngine(
        paths=skill_paths,
        state_store=store,
        timestamp="publish-failure",
        replace=fail_publish,
    )
    action = plan_skill_copies(
        source=source_skill,
        name="example-skill",
        targets=(AgentName.CURSOR,),
        home=skill_paths.home,
        state=before_state,
    )[0]

    with pytest.raises(OSError, match="injected publish failure"):
        subject.apply(managed_tree_spec(action))

    assert original.read_text().endswith("description: Original.\n---\n")
    assert store.load() == before_state


_REJECT: Final[tuple[str, ...]] = (
    "plato",
    "/users/",
    "/home/",
    "ami-",
    "pydantic 2.8",
    "{{",
    "sk-",
    "ghp_",
    "glpat-",
)


def _assert_skill_tree_excludes_blacklisted_tokens(root: Path) -> None:
    """Reject tokens from a bounded blacklist in shared-skill text files."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for token in _REJECT:
            assert token not in text, f"{token!r} in {path}"


def _assert_shared_skill_synchronized(
    repo_root: Path,
    temporary_home: Path,
    *,
    name: str,
    tree_digest: str,
    provenance: str,
    dependencies: tuple[str, ...] = (),
) -> None:
    """Assert catalog metadata, digest pin, and planned managed-tree ids."""
    catalog = yaml.safe_load(
        (repo_root / "assistants/shared/skills/catalog.yaml").read_text(
            encoding="utf-8"
        )
    )
    entry = next(item for item in catalog["skills"] if item["name"] == name)
    assert entry["source"] == f"assistants/shared/skills/{name}"
    assert entry["targets"] == ["cursor", "claude-code", "codex"]
    assert entry["profiles"] == ["default"]
    assert entry["dependencies"] == list(dependencies)
    assert entry["provenance"] == provenance
    assert entry["portability_status"] == "reviewed-generic"
    source = repo_root / entry["source"]
    assert hash_skill_tree(source) == tree_digest
    _assert_skill_tree_excludes_blacklisted_tokens(source)
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    contribution = configuration(
        _resolved_setup("cursor", "claude-code", "codex"),
        paths,
        SkillCatalog.model_validate(catalog),
    )
    expected_ids = {
        f"shared-skill-{name}-cursor",
        f"shared-skill-{name}-claude-code",
        f"shared-skill-{name}-codex",
    }
    assert expected_ids.issubset({spec.id for spec in contribution.specs})


@pytest.mark.parametrize(
    ("name", "tree_digest", "provenance", "dependencies"),
    [
        pytest.param(
            "discover-project-standards",
            "c748dc5434c64aef74007c63966e5dfb2bc42914af78145bc70804806c06a08d",  # pragma: allowlist secret
            "Genericized from plato/skills/tooling-discover-standards at commit "
            "f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the "
            "promotion.",
            (),
            id="discover-project-standards",
        ),
        pytest.param(
            "review-project-standards",
            "9fe8886151b8db6130b0fb3685174fc10ae43531a2a63253cf2cdc5826c430f0",  # pragma: allowlist secret
            "Genericized from plato/skills/tooling-review-standards at commit "
            "f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the "
            "promotion.",
            ("discover-project-standards",),
            id="review-project-standards",
        ),
        pytest.param(
            "using-uv",
            "b7af2515aea5ca7ccbbfe72f31c498a51a3f1bd1c706bd5942365b050068f2af",  # pragma: allowlist secret
            "Authored for ballen-config against current primary uv documentation.",
            (),
            id="using-uv",
        ),
        pytest.param(
            "writing-executive-communications",
            "3c824845f43a60ad6af5221d9706e26226e707163afef091b0312fd3a8cd9d6b",  # pragma: allowlist secret
            "Genericized from plato/skills/reports-consultant-style at commit "
            "f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the "
            "promotion.",
            (),
            id="writing-executive-communications",
        ),
        pytest.param(
            "using-gitlab",
            "cf2fe8d0c2d4a7e5e36854b6d58226c739dc00b4806266f9c32960ee3ecc311e",  # pragma: allowlist secret
            "Rewritten for portability from plato/skills/using-gitlab at commit "
            "f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the "
            "promotion.",
            (),
            id="using-gitlab",
        ),
        pytest.param(
            "using-github",
            "c836e3bdeb1010d0ecc0f3e98e87de4ae9a82466fe63a32830f7c2e305bd8c6d",  # pragma: allowlist secret
            "Authored for ballen-config as the GitHub counterpart to using-gitlab, "
            "verified against current primary GitHub CLI documentation.",
            (),
            id="using-github",
        ),
    ],
)
def test_shared_skill_catalog_and_configuration_are_synchronized(
    repo_root: Path,
    temporary_home: Path,
    name: str,
    tree_digest: str,
    provenance: str,
    dependencies: tuple[str, ...],
) -> None:
    """Verify each skill's catalog metadata, digest, rejected tokens, and plans."""
    _assert_shared_skill_synchronized(
        repo_root,
        temporary_home,
        name=name,
        tree_digest=tree_digest,
        provenance=provenance,
        dependencies=dependencies,
    )


def test_standards_pair_discovery_contract_is_stable(repo_root: Path) -> None:
    """Discovery reports its reusable inventory without reviewing code."""
    text = (
        repo_root / "assistants/shared/skills/discover-project-standards/SKILL.md"
    ).read_text(encoding="utf-8")
    for field in (
        "Ordered Instruction Sources",
        "Applicable Standards",
        "Repository-Selected Tools",
        "Conflicts",
        "Unavailable Sources",
    ):
        assert field in text
    for instruction in (
        "CLAUDE.md",
        "AGENTS.md",
        "GEMINI.md",
        "COPILOT.md",
        ".github/copilot-instructions.md",
    ):
        assert instruction in text
    assert "applicable precedence" in text
    assert "executable tool configuration" in text
    assert "narrative standards" in text
    assert "Do not review code or diffs." in text


def test_standards_pair_review_uses_neutral_supplied_scope(repo_root: Path) -> None:
    """Review composes discovery without selecting a VCS change scope."""
    text = (
        repo_root / "assistants/shared/skills/review-project-standards/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "Invoke `discover-project-standards`" in text
    assert "tooling-discover-standards" not in text
    assert "supplied diff or changed-file set" in text
    assert "A git diff" not in text
    assert "Git/Jujutsu change-scope resolver" not in text
    for outcome in (
        "No applicable standards",
        "Incomplete discovery",
        "Clean review",
        "Actionable findings",
    ):
        assert outcome in text


def test_using_uv_projection_matches_canonical_standard(repo_root: Path) -> None:
    """Keep the co-packaged dependency-management projection byte-identical."""
    canonical = (
        repo_root / "assistants/shared/standards/dependency-management.md"
    ).read_bytes()
    projection = (
        repo_root
        / "assistants/shared/skills/using-uv/references/dependency-management.md"
    ).read_bytes()
    assert projection == canonical


def test_using_uv_skill_has_distinct_sync_and_policy_handoff_contract(
    repo_root: Path,
) -> None:
    """Keep uv procedure distinct from its single bundled policy handoff."""
    text = (repo_root / "assistants/shared/skills/using-uv/SKILL.md").read_text(
        encoding="utf-8"
    )
    bundled_reference = "references/dependency-management.md"
    assert text.count(bundled_reference) == 1
    assert "assistants/shared/standards/dependency-management.md" not in text
    assert (
        "dependency intent, groups, lockfile policy, or workspace policy"
        in text.lower()
    )
    assert "`uv sync`" in text
    assert "`uv sync --locked`" in text
    assert "`uv sync --frozen`" in text
    assert "checks and updates the lockfile as needed" in text
    assert "errors if the lockfile is not current" in text
    assert "without checking freshness" in text
    assert "`uv lock`" in text
    assert "existing locked versions are preferred" in text
    refresh_row = "| Create or refresh the lockfile |"
    upgrade_row = "| Intentionally upgrade broadly |"
    assert f"{refresh_row} `uv lock`; existing locked versions are preferred" in text
    assert f"{upgrade_row} `uv lock --upgrade`" in text


def test_writing_executive_communications_avoids_placeholder_option_labels(
    repo_root: Path,
) -> None:
    """Keep descriptive options and require evidence-bound quantification."""
    text = (
        repo_root / "assistants/shared/skills/writing-executive-communications/SKILL.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "Incremental refactor" in text
    assert "Complete rewrite" in text
    assert "Option A" not in text
    assert "Option B" not in text
    assert "reports-consultant-style" not in text
    assert "sourced or directly observed values" in normalized
    assert "source, context, timeframe, and denominator" in normalized
    assert "state the gap or explicitly label a grounded estimate" in normalized
    assert "never invent measurements or precision" in normalized


def test_using_gitlab_names_github_counterpart_for_wrong_forge(
    repo_root: Path,
) -> None:
    """GitLab skill must name the GitHub counterpart and glab fallback."""
    text = (repo_root / "assistants/shared/skills/using-gitlab/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "using-github" in text
    assert "glab" in text


def test_using_gitlab_has_shared_forge_protocol_headings(repo_root: Path) -> None:
    """Stable shared forge protocol headings for parity with using-github."""
    text = (repo_root / "assistants/shared/skills/using-gitlab/SKILL.md").read_text(
        encoding="utf-8"
    )
    for heading in (
        "## Repository and remote identity",
        "## Provider discovery",
        "## Read-only inspection",
        "## CLI fallback",
        "## Provider setup vs workflow",
        "## Mutation safety",
        "## Forge guard",
        "## Authentication boundary",
    ):
        assert heading in text


def test_using_github_names_gitlab_counterpart_for_wrong_forge(
    repo_root: Path,
) -> None:
    """GitHub skill must name the GitLab counterpart and gh fallback."""
    text = (repo_root / "assistants/shared/skills/using-github/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "using-gitlab" in text
    assert "gh" in text


def test_forge_skills_share_protocol_headings(repo_root: Path) -> None:
    """Both forge skills share the stable protocol section headings."""
    gitlab = (repo_root / "assistants/shared/skills/using-gitlab/SKILL.md").read_text(
        encoding="utf-8"
    )
    github = (repo_root / "assistants/shared/skills/using-github/SKILL.md").read_text(
        encoding="utf-8"
    )
    headings = (
        "## Repository and remote identity",
        "## Provider discovery",
        "## Read-only inspection",
        "## CLI fallback",
        "## Provider setup vs workflow",
        "## Mutation safety",
        "## Forge guard",
        "## Authentication boundary",
    )
    for heading in headings:
        assert heading in gitlab
        assert heading in github
    assert "using-github" in gitlab
    assert "using-gitlab" in github
    assert "glab" in gitlab
    assert "gh" in github
