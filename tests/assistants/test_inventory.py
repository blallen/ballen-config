"""Tests for assistant inventory loading, resolution, and core seams."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import cast

import pytest

from ballen_config.assistants.inventory import load_inventory, resolve_inventory
from ballen_config.assistants.models import (
    AgentName,
    AssistantInventory,
    CatalogResource,
)
from ballen_config.cli import run
from ballen_config.configure import ConfigurationContribution, ConfigurationSupplier
from ballen_config.doctor import DoctorCheck, DoctorCheckSupplier
from ballen_config.install import InstallAction, InstallActionSupplier
from ballen_config.manifests import ManifestRepository
from ballen_config.models import Manager, ResolutionRequest, ResolvedSetup
from ballen_config.planning import PlanAction, PlanContributor
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths
from tests.assistants.fakes import StatefulAssistantFake


@pytest.fixture
def inventory() -> AssistantInventory:
    """Create resources spanning profiles, owners, and shared targets."""
    return AssistantInventory.model_validate(
        {
            "resources": [
                {
                    "id": "cursor.default",
                    "kind": "manual",
                    "owner": "cursor",
                    "summary": "default",
                },
                {
                    "id": "cursor.work",
                    "kind": "manual",
                    "owner": "cursor",
                    "profiles": ["work"],
                    "summary": "work",
                },
                {
                    "id": "claude.default",
                    "kind": "manual",
                    "owner": "claude-code",
                    "summary": "claude",
                },
                {
                    "id": "codex.default",
                    "kind": "manual",
                    "owner": "codex",
                    "summary": "codex",
                },
                {
                    "id": "shared.hook",
                    "kind": "hook",
                    "owner": "shared",
                    "source": "assistants/shared/hooks/rtk-hook",
                    "event": "shell-command",
                    "targets": ["cursor", "claude-code", "codex"],
                },
            ]
        }
    )


def test_active_profiles_select_default_and_work_once(
    inventory: AssistantInventory,
) -> None:
    """Resolve the core-expanded profile tuple without duplicate resources."""
    resolved = resolve_inventory(
        inventory,
        profiles=("default", "work"),
        skipped=frozenset(),
    )
    ids = [resource.id for resource in resolved.resources]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))
    assert "cursor.default" in ids
    assert "cursor.work" in ids


@pytest.mark.parametrize(
    ("component", "owner"),
    [
        ("cursor", AgentName.CURSOR),
        ("claude-code", AgentName.CLAUDE),
        ("codex", AgentName.CODEX),
    ],
)
def test_skip_removes_direct_owner_and_shared_target(
    inventory: AssistantInventory,
    component: str,
    owner: AgentName,
) -> None:
    """Apply each whole-agent skip to owners and shared target references."""
    resolved = resolve_inventory(
        inventory,
        profiles=("default", "work"),
        skipped=frozenset({component}),
    )
    assert all(resource.owner is not owner for resource in resolved.resources)
    shared = next(
        resource for resource in resolved.resources if resource.id == "shared.hook"
    )
    assert owner not in getattr(shared, "targets", ())


def test_shared_resource_disappears_when_all_targets_are_skipped(
    inventory: AssistantInventory,
) -> None:
    """Remove a shared targeted resource when no enabled consumer remains."""
    resolved = resolve_inventory(
        inventory,
        profiles=("default", "work"),
        skipped=frozenset({"cursor", "claude-code", "codex"}),
    )
    assert all(
        resource.owner is not AgentName.SHARED for resource in resolved.resources
    )


@pytest.mark.parametrize("source", ["../outside.json", "/outside.json"])
def test_source_escape_is_rejected_before_existence(
    tmp_path: Path,
    source: str,
) -> None:
    """Reject lexical traversal and absolute sources before existence checks."""
    inventory_path = tmp_path / "inventory.yaml"
    inventory_path.write_text(
        "resources:\n"
        "  - id: cursor.settings\n"
        "    kind: file\n"
        "    owner: cursor\n"
        f"    source: {source}\n"
        "    destination: .cursor/settings.json\n"
    )
    with pytest.raises(ValueError, match="source escapes checkout"):
        load_inventory(inventory_path, tmp_path)


def test_symlink_source_escape_is_rejected(tmp_path: Path) -> None:
    """Reject a source whose symlink redirects outside the checkout."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "settings.json").write_text("{}")
    (repo_root / "linked").symlink_to(outside, target_is_directory=True)
    inventory_path = repo_root / "inventory.yaml"
    inventory_path.write_text(
        """
resources:
  - id: cursor.settings
    kind: file
    owner: cursor
    source: linked/settings.json
    destination: .cursor/settings.json
""".lstrip()
    )
    with pytest.raises(ValueError, match="source escapes checkout"):
        load_inventory(inventory_path, repo_root)


def test_catalog_item_ids_must_match_declared_order(tmp_path: Path) -> None:
    """Reject flattened catalog IDs whose order differs from the source."""
    repo_root = tmp_path / "repo"
    catalog = repo_root / "assistants/extensions.yaml"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        """
extensions:
  - id: publisher.first
  - id: publisher.second
""".lstrip()
    )
    inventory_path = repo_root / "inventory.yaml"
    inventory_path.write_text(
        """
resources:
  - id: cursor.extensions
    kind: catalog
    owner: cursor
    source: assistants/extensions.yaml
    catalog_kind: extension
    targets: [cursor]
    item_ids: [publisher.second, publisher.first]
""".lstrip()
    )
    with pytest.raises(ValueError, match="catalog item_ids differ"):
        load_inventory(inventory_path, repo_root)


def test_initial_inventory_is_only_empty_shared_skill_catalog(
    repo_root: Path,
) -> None:
    """Commit only the reviewed empty shared-skill catalog initially."""
    inventory = load_inventory(repo_root / "assistants/inventory.yaml", repo_root)
    assert len(inventory.resources) == 1
    resource = inventory.resources[0]
    assert isinstance(resource, CatalogResource)
    assert resource.id == "shared.skills.catalog"
    assert resource.owner is AgentName.SHARED
    assert resource.item_ids == ()


class RecordingPlanContributor:
    """Record the resolved setup delivered to the plan extension seam."""

    def __init__(self, calls: Counter[str]) -> None:
        """Initialize with a shared call counter."""
        self.calls = calls

    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        """Record one call and assert the whole-agent skip is resolved."""
        self.calls["plan"] += 1
        assert "work" in resolved.profiles
        assert resolved.skipped == ("codex",)
        assert not resolved.is_enabled("codex")
        return ()


def test_core_invokes_each_supplier_once_with_resolved_skip(
    fake_runner: StatefulAssistantFake,
    repo_root: Path,
    isolated_environment: Path,
) -> None:
    """Pass one resolved skip through each prerequisite core extension seam."""
    calls: Counter[str] = Counter()
    home = isolated_environment.resolve()
    fake_runner.satisfy_core_commands()
    resolved = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile="work", skips=("codex",))
    )
    for component in resolved.components:
        if component.manager is Manager.GIT:
            assert component.destination is not None
            (home / component.destination / ".git").mkdir(
                parents=True,
                mode=0o700,
            )

    def assert_setup(setup: ResolvedSetup) -> None:
        assert "work" in setup.profiles
        assert setup.skipped == ("codex",)
        assert not setup.is_enabled("codex")

    def installs(
        setup: ResolvedSetup,
        paths: RuntimePaths,
        runner: Runner,
    ) -> tuple[InstallAction, ...]:
        calls["install"] += 1
        assert_setup(setup)
        assert paths.home == home
        assert runner is fake_runner
        return ()

    def configuration(
        setup: ResolvedSetup,
        paths: RuntimePaths,
    ) -> ConfigurationContribution:
        calls["configure"] += 1
        assert_setup(setup)
        assert paths.home == home
        return ConfigurationContribution()

    def checks(
        setup: ResolvedSetup,
        paths: RuntimePaths,
        runner: Runner,
    ) -> tuple[DoctorCheck, ...]:
        calls["doctor"] += 1
        assert_setup(setup)
        assert paths.home == home
        assert runner is fake_runner
        return ()

    arguments = ("--profile", "work", "--skip", "codex")
    plan_contributor: PlanContributor = RecordingPlanContributor(calls)
    install_supplier: InstallActionSupplier = installs
    configuration_supplier = cast(ConfigurationSupplier, configuration)
    doctor_supplier: DoctorCheckSupplier = checks

    plan_result = run(
        ("plan", *arguments),
        repo_root=repo_root,
        home=home,
        runner=fake_runner,
        downloader=fake_runner,
        confirm=lambda _prompt: pytest.fail("plan must not confirm"),
        output=lambda _message: None,
        timestamp=lambda: "20260725T120000Z",
        plan_contributors=(plan_contributor,),
    )
    install_result = run(
        ("install", *arguments),
        repo_root=repo_root,
        home=home,
        runner=fake_runner,
        downloader=fake_runner,
        confirm=lambda _prompt: True,
        output=lambda _message: None,
        timestamp=lambda: "20260725T120000Z",
        install_action_suppliers=(install_supplier,),
    )
    configure_result = run(
        ("configure", *arguments),
        repo_root=repo_root,
        home=home,
        runner=fake_runner,
        downloader=fake_runner,
        confirm=lambda _prompt: True,
        output=lambda _message: None,
        timestamp=lambda: "20260725T120000Z",
        configuration_suppliers=(configuration_supplier,),
    )
    doctor_result = run(
        ("doctor", *arguments),
        repo_root=repo_root,
        home=home,
        runner=fake_runner,
        downloader=fake_runner,
        confirm=lambda _prompt: pytest.fail("doctor must not confirm"),
        output=lambda _message: None,
        timestamp=lambda: "20260725T120000Z",
        doctor_check_suppliers=(doctor_supplier,),
    )

    assert all(
        result.exit_code == 0
        for result in (
            plan_result,
            install_result,
            configure_result,
            doctor_result,
        )
    )
    assert calls == Counter({"plan": 1, "install": 1, "configure": 1, "doctor": 1})
    assert fake_runner.downloads == []
