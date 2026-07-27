"""Tests for target-aware assistant desired-state projections."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import ballen_config.assistants.cursor_plugins as cursor_plugins_module
import ballen_config.assistants.desired_state as desired_state_module
from ballen_config.assistants.cursor_plugins import ValidatedCursorLocalPlugin
from ballen_config.assistants.desired_state import (
    AssistantDesiredStateError,
    load_desired_state,
    project_plugin_catalog,
)
from ballen_config.assistants.models import (
    AgentName,
    CursorLocalPlugin,
    ExtensionCatalog,
    PluginCatalog,
    SkillCatalog,
)
from ballen_config.assistants.orchestrator import AssistantOrchestrator
from ballen_config.manifests import ManifestRepository
from ballen_config.models import ResolutionRequest
from ballen_config.runtime import RuntimePaths
from tests.assistants.conftest import (
    CursorLocalPluginFixture,
    CursorLocalPluginRepoFactory,
)


def _targeted_catalog() -> PluginCatalog:
    """Create deliberately unsorted declarations across targets and profiles."""
    return PluginCatalog.model_validate(
        {
            "marketplaces": [
                {
                    "name": "z-native",
                    "source": "owner/z-native",
                    "targets": ["claude-code", "codex"],
                    "profiles": ["default"],
                },
                {
                    "name": "work-only",
                    "source": "owner/work-only",
                    "targets": ["claude-code"],
                    "profiles": ["work"],
                },
                {
                    "name": "a-native",
                    "source": "owner/a-native",
                    "targets": ["claude-code"],
                    "profiles": ["default"],
                },
            ],
            "plugins": [
                {
                    "kind": "native-marketplace",
                    "id": "zed@z-native",
                    "marketplace": "z-native",
                    "targets": ["claude-code", "codex"],
                    "profiles": ["default"],
                },
                {
                    "kind": "cursor-marketplace",
                    "id": "z-cursor-marketplace",
                    "targets": ["cursor"],
                    "scope": "user",
                    "verification": "manual",
                },
                {
                    "kind": "cursor-local",
                    "id": "z-cursor-local",
                    "source": "assistants/shared/plugins/local/z-cursor-local",
                    "targets": ["cursor"],
                },
                {
                    "kind": "native-marketplace",
                    "id": "excluded@work-only",
                    "marketplace": "work-only",
                    "targets": ["claude-code"],
                    "profiles": ["work"],
                },
                {
                    "kind": "native-marketplace",
                    "id": "alpha@a-native",
                    "marketplace": "a-native",
                    "targets": ["claude-code"],
                    "profiles": ["default"],
                },
                {
                    "kind": "cursor-marketplace",
                    "id": "a-cursor-marketplace",
                    "targets": ["cursor"],
                    "scope": "user",
                    "verification": "manual",
                },
                {
                    "kind": "cursor-local",
                    "id": "a-cursor-local",
                    "source": "assistants/shared/plugins/local/a-cursor-local",
                    "targets": ["cursor"],
                },
                {
                    "kind": "cursor-local",
                    "id": "work-cursor-local",
                    "source": "assistants/shared/plugins/local/work-cursor-local",
                    "targets": ["cursor"],
                    "profiles": ["work"],
                },
            ],
        }
    )


def test_project_plugin_catalog_returns_one_concrete_target() -> None:
    """Narrow, filter, and sort native declarations for one target."""
    projection = project_plugin_catalog(
        _targeted_catalog(),
        target=AgentName.CLAUDE,
        profiles=("default",),
    )
    assert projection.target is AgentName.CLAUDE
    assert tuple(
        (marketplace.name, marketplace.targets)
        for marketplace in projection.marketplaces
    ) == (
        ("a-native", (AgentName.CLAUDE,)),
        ("z-native", (AgentName.CLAUDE,)),
    )
    assert tuple(
        (plugin.id, plugin.targets) for plugin in projection.native_plugins
    ) == (
        ("alpha@a-native", (AgentName.CLAUDE,)),
        ("zed@z-native", (AgentName.CLAUDE,)),
    )
    assert projection.cursor_marketplace_plugins == ()
    assert projection.cursor_local_plugins == ()


def test_project_plugin_catalog_filters_and_sorts_cursor_variants() -> None:
    """Filter inactive Cursor entries and sort each variant independently."""
    projection = project_plugin_catalog(
        _targeted_catalog(),
        target=AgentName.CURSOR,
        profiles=("default",),
    )

    assert projection.target is AgentName.CURSOR
    assert projection.marketplaces == ()
    assert projection.native_plugins == ()
    assert tuple(
        (plugin.id, plugin.targets) for plugin in projection.cursor_marketplace_plugins
    ) == (
        ("a-cursor-marketplace", (AgentName.CURSOR,)),
        ("z-cursor-marketplace", (AgentName.CURSOR,)),
    )
    assert tuple(
        (plugin.id, plugin.targets) for plugin in projection.cursor_local_plugins
    ) == (
        ("a-cursor-local", (AgentName.CURSOR,)),
        ("z-cursor-local", (AgentName.CURSOR,)),
    )


def test_shared_plugin_catalog_parses_against_targeted_models(repo_root: Path) -> None:
    """Keep the production shared YAML aligned with catalog models and projection."""
    catalog_path = repo_root / "assistants/shared/plugins/catalog.yaml"
    catalog = PluginCatalog.model_validate(yaml.safe_load(catalog_path.read_text()))

    projection = project_plugin_catalog(
        catalog,
        target=AgentName.CODEX,
        profiles=("default",),
    )

    assert tuple(marketplace.name for marketplace in projection.marketplaces) == (
        "bigspinai",
        "claude-plugins-official",
        "context-mode",
        "superpowers-marketplace",
    )
    assert tuple(plugin.id for plugin in projection.native_plugins) == (
        "bigspin@bigspinai",
        "context-mode@context-mode",
        "frontend-design@claude-plugins-official",
        "github@claude-plugins-official",
        "logfire@claude-plugins-official",
        "superpowers-developing-for-claude-code@superpowers-marketplace",
        "superpowers@claude-plugins-official",
    )
    assert (
        tuple(marketplace.targets for marketplace in projection.marketplaces)
        == ((AgentName.CODEX,),) * 4
    )
    assert (
        tuple(plugin.targets for plugin in projection.native_plugins)
        == ((AgentName.CODEX,),) * 7
    )
    assert projection.cursor_marketplace_plugins == ()
    assert projection.cursor_local_plugins == ()


def test_load_desired_state_validates_every_catalog_before_resolution(
    repo_root: Path,
) -> None:
    """Load all typed documents even when no concrete agent remains enabled."""
    desired = load_desired_state(
        repo_root,
        ("default",),
        frozenset({"cursor", "claude-code", "codex"}),
    )

    assert isinstance(desired.extension_catalog, ExtensionCatalog)
    assert isinstance(desired.skill_catalog, SkillCatalog)
    assert isinstance(desired.plugin_catalog, PluginCatalog)
    assert desired.plugin_projections == ()


def test_skipped_agent_removes_only_its_projection(repo_root: Path) -> None:
    """Apply skips only after every shared catalog has been validated."""
    desired = load_desired_state(
        repo_root,
        ("default",),
        frozenset({"codex"}),
    )

    assert tuple(projection.target for projection in desired.plugin_projections) == (
        AgentName.CURSOR,
        AgentName.CLAUDE,
    )
    with pytest.raises(ValueError, match="missing plugin projection: codex"):
        desired.plugin_projection(AgentName.CODEX)


def test_load_desired_state_validates_raw_cursor_local_plugins_before_skips(
    cursor_local_plugin_repo_factory: CursorLocalPluginRepoFactory,
) -> None:
    """Reject an invalid inactive local plugin before target projection occurs."""
    copied = cursor_local_plugin_repo_factory(
        (
            CursorLocalPluginFixture(
                id="example-local",
                manifest_name="different-name",
            ),
        )
    )

    with pytest.raises(
        AssistantDesiredStateError,
        match="assistant desired-state preflight failed",
    ):
        load_desired_state(
            copied,
            ("default",),
            frozenset({"cursor", "claude-code", "codex"}),
        )


def test_orchestrator_configuration_reuses_preflight_local_plugin_snapshot(
    cursor_local_plugin_repo_factory: CursorLocalPluginRepoFactory,
    temporary_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate local plugin semantics once before configuration consumes them."""
    repo_root = cursor_local_plugin_repo_factory(
        (CursorLocalPluginFixture(id="example-local"),)
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest()
    )
    calls = 0

    original_validation = desired_state_module.validate_cursor_local_plugins

    def record_validation(
        plugins: tuple[CursorLocalPlugin, ...],
        *,
        repo_root: Path,
        shared_skill_names: frozenset[str],
    ) -> tuple[ValidatedCursorLocalPlugin, ...]:
        """Count whole-catalog preflight validation without changing results."""
        nonlocal calls
        calls += 1
        return original_validation(
            plugins,
            repo_root=repo_root,
            shared_skill_names=shared_skill_names,
        )

    monkeypatch.setattr(
        desired_state_module,
        "validate_cursor_local_plugins",
        record_validation,
    )
    monkeypatch.setattr(
        cursor_plugins_module,
        "validate_cursor_local_plugin",
        lambda *_args, **_kwargs: pytest.fail("configuration revalidated plugin"),
    )
    orchestrator = AssistantOrchestrator(paths)

    orchestrator.preflight(setup, paths)
    contribution = orchestrator.configuration(setup, paths)

    assert calls == 1
    assert [
        spec.id for spec in contribution.specs if spec.id.startswith("cursor-local-")
    ] == ["cursor-local-plugin-example-local"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("repo_root", Path("/tmp/other-repo"), id="repo-root"),
        pytest.param("home", Path("/tmp/other-home"), id="home"),
        pytest.param("state_root", Path("/tmp/other-state"), id="state-root"),
        pytest.param("backup_root", Path("/tmp/other-backups"), id="backup-root"),
    ],
)
def test_orchestrator_rejects_every_runtime_path_difference(
    repo_root: Path,
    temporary_home: Path,
    field: str,
    value: Path,
) -> None:
    """Bind cached desired state to all runtime roots, profiles, and skips."""
    setup = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest()
    )
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    orchestrator = AssistantOrchestrator(paths)

    orchestrator.preflight(setup, paths)
    orchestrator.preflight(setup, paths)
    different_paths = paths.model_copy(update={field: value})

    with pytest.raises(
        AssistantDesiredStateError,
        match="assistant desired-state preflight failed",
    ):
        orchestrator.preflight(setup, different_paths)


@pytest.mark.parametrize(
    "changed_request",
    [
        pytest.param(
            ResolutionRequest(profile="work"),
            id="profiles",
        ),
        pytest.param(
            ResolutionRequest(skips=("codex",)),
            id="skips",
        ),
    ],
)
def test_orchestrator_rejects_profile_or_skip_identity_changes(
    repo_root: Path,
    temporary_home: Path,
    changed_request: ResolutionRequest,
) -> None:
    """Reject every profile or skip key change after desired-state loading."""
    repository = ManifestRepository.load(repo_root / "manifests")
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    orchestrator = AssistantOrchestrator(paths)
    orchestrator.preflight(repository.resolve(ResolutionRequest()), paths)

    with pytest.raises(
        AssistantDesiredStateError,
        match="assistant desired-state preflight failed",
    ):
        orchestrator.preflight(repository.resolve(changed_request), paths)
