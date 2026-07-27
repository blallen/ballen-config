"""Tests for portable shared-skill validation and convergence."""

from __future__ import annotations

import os
import shutil
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest
import yaml

from ballen_config.assistants.inventory import load_inventory
from ballen_config.assistants.models import AgentName, CatalogResource
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
    monkeypatch.setattr(
        "ballen_config.assistants.skills.yaml.safe_load",
        lambda _source: pytest.fail("catalog read"),
    )
    monkeypatch.setattr(
        "ballen_config.assistants.skills.StateStore.load",
        lambda _store: pytest.fail("state read"),
    )

    assert configuration(setup, skill_paths) == ConfigurationContribution()


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
        configuration(_resolved_setup("cursor"), skill_paths)
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


@pytest.mark.parametrize("dangling", [False, True])
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
        ".cursor/skills",
        ".claude/skills",
        ".agents/skills",
        ".codex/skills",
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
        (".cursor/skills/other", None),
        (None, "shared-skill-other-cursor"),
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
        ("# No frontmatter\n", "initial YAML frontmatter"),
        ("---\nname: example-skill\n", "unterminated"),
        ("---\nname: [\n---\n", "invalid"),
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
        ("source-name", "source-name", "catalog-name"),
        ("source-name", "frontmatter-name", "source-name"),
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


@pytest.mark.parametrize("dangling", [False, True])
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
        configuration(_resolved_setup("cursor"), skill_paths)

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
        configuration(_resolved_setup("cursor"), skill_paths)


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
        configuration(_resolved_setup("cursor"), skill_paths)


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
        configuration(_resolved_setup("cursor"), skill_paths)


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
        configuration(_resolved_setup("cursor", "codex"), skill_paths)


@pytest.mark.parametrize(
    ("dependency_targets", "consumer_targets", "expected_spec_count"),
    [
        (("cursor",), ("cursor",), 2),
        (("cursor", "codex"), ("cursor",), 3),
        (("cursor", "codex"), ("cursor", "codex"), 4),
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
    contribution = configuration(_resolved_setup("cursor"), skill_paths)
    assert [spec.id for spec in contribution.specs] == [
        "shared-skill-base-cursor",
        "shared-skill-consumer-cursor",
    ]
    assert not skill_paths.state_root.exists()
    assert not (skill_paths.home / ".cursor").exists()


def test_jujutsu_workflow_catalog_inventory_and_configuration_are_synchronized(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Declare and plan the first reviewed shared skill without mutation."""
    inventory = load_inventory(repo_root / "assistants/inventory.yaml", repo_root)
    catalog = yaml.safe_load(
        (repo_root / "assistants/shared/skills/catalog.yaml").read_text()
    )
    resource = next(
        item for item in inventory.resources if item.id == "shared.skills.catalog"
    )
    expected_skill = {
        "name": "jujutsu-workflow",
        "source": "assistants/shared/skills/jujutsu-workflow",
        "targets": ["cursor", "claude-code", "codex"],
        "profiles": ["default"],
        "dependencies": [],
        "provenance": (
            "Byte-for-byte promotion from the reviewed "
            "plato/skills/jujutsu-workflow source; commit history records the origin."
        ),
        "portability_status": "reviewed-generic",
    }
    assert catalog == {"skills": [expected_skill]}
    assert isinstance(resource, CatalogResource)
    assert resource.owner is AgentName.SHARED
    assert resource.targets == (
        AgentName.CURSOR,
        AgentName.CLAUDE,
        AgentName.CODEX,
    )
    assert resource.item_ids == ("jujutsu-workflow",)
    source = repo_root / "assistants/shared/skills/jujutsu-workflow"
    expected_jujutsu_workflow_tree_digest = "e7ca3f2e0a0f3f79dff90cc8fd718d74fecf18234d9b57dfeb0245480af1a8ec"  # pragma: allowlist secret
    assert hash_skill_tree(source) == expected_jujutsu_workflow_tree_digest
    assert (
        sha256((source / "SKILL.md").read_bytes()).hexdigest()
        == (
            "fb76302a9d6d8e7555052d62099cf0086e5d64363966fca345298359b36491e3"  # pragma: allowlist secret
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
    )
    assert all(isinstance(spec, ManagedTreeSpec) for spec in contribution.specs)
    assert [(spec.id, spec.destination) for spec in contribution.specs] == [
        (
            "shared-skill-jujutsu-workflow-codex",
            Path(".agents/skills/jujutsu-workflow"),
        ),
        (
            "shared-skill-jujutsu-workflow-claude-code",
            Path(".claude/skills/jujutsu-workflow"),
        ),
        (
            "shared-skill-jujutsu-workflow-cursor",
            Path(".cursor/skills/jujutsu-workflow"),
        ),
    ]
    assert not paths.state_root.exists()
    assert not (temporary_home / ".cursor/skills/jujutsu-workflow").exists()
    assert not (temporary_home / ".claude/skills/jujutsu-workflow").exists()
    assert not (temporary_home / ".agents/skills/jujutsu-workflow").exists()


@pytest.mark.parametrize(
    ("stored_digest", "expected_action"),
    [
        (None, "update"),
        ("0" * 64, "repair"),
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
    contribution = configuration(_resolved_setup("cursor"), skill_paths)
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
