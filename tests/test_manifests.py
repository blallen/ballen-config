from pathlib import Path

import pytest
from pydantic import ValidationError

from ballen_config.manifests import ManifestRepository
from ballen_config.models import Component, Profile, ResolutionRequest


@pytest.fixture
def minimal_manifest_root(tmp_path: Path) -> Path:
    """Create a complete minimal manifest directory."""
    root = tmp_path / "manifests"
    profiles = root / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "default.yaml").write_text(
        "name: default\nextends: []\n",
        encoding="utf-8",
    )
    (root / "packages.yaml").write_text("components: []\n", encoding="utf-8")
    (root / "applications.yaml").write_text(
        "components: []\n",
        encoding="utf-8",
    )
    return root


def ids(repository: ManifestRepository, request: ResolutionRequest) -> set[str]:
    """Return the resolved component identifiers."""
    return {component.id for component in repository.resolve(request).components}


def test_work_profile_extends_default(manifest_repository: ManifestRepository) -> None:
    """Work includes its inherited tools without optional personal apps."""
    resolved = ids(manifest_repository, ResolutionRequest(profile="work"))
    assert {
        "uv",
        "gh",
        "glab",
        "jj",
        "pre-commit",
        "wave",
        "libmagic",
        "awscli",
    } <= resolved
    assert {"obsidian", "signal", "mactex"}.isdisjoint(resolved)


def test_shell_parent_precedes_nested_git_components(
    manifest_repository: ManifestRepository,
) -> None:
    """Install Oh My Zsh before repositories nested beneath it."""
    ordered = [
        component.id
        for component in manifest_repository.resolve(
            ResolutionRequest(profile="default")
        ).components
    ]
    parent_index = ordered.index("oh-my-zsh")
    for child in (
        "forgit",
        "powerlevel10k",
        "zsh-autosuggestions",
        "zsh-completions",
        "zsh-syntax-highlighting",
    ):
        assert parent_index < ordered.index(child)


def test_profile_cycle_is_rejected(tmp_path: Path) -> None:
    """Reject cyclic inheritance before resolving components."""
    repository = ManifestRepository(
        tmp_path,
        {
            "a": Profile(name="a", extends=("b",)),
            "b": Profile(name="b", extends=("a",)),
        },
        (),
    )
    with pytest.raises(ValueError, match="profile inheritance cycle"):
        repository.resolve(ResolutionRequest(profile="a"))


@pytest.mark.parametrize(
    "include",
    [
        pytest.param("obsidian", id="obsidian"),
        pytest.param("signal", id="signal"),
        pytest.param("mactex", id="mactex"),
    ],
)
def test_personal_applications_are_opt_in(
    manifest_repository: ManifestRepository,
    include: str,
) -> None:
    """Optional personal applications appear only after explicit selection."""
    resolved = ids(
        manifest_repository,
        ResolutionRequest(profile="default", includes=(include,)),
    )
    assert include in resolved


@pytest.mark.parametrize(
    "skip",
    [
        pytest.param("cursor", id="cursor"),
        pytest.param("claude-code", id="claude-code"),
        pytest.param("codex", id="codex"),
        pytest.param("wave", id="wave"),
    ],
)
def test_skip_removes_complete_component(
    manifest_repository: ManifestRepository,
    skip: str,
) -> None:
    """Skipping a component removes it from resolution and records the choice."""
    result = manifest_repository.resolve(
        ResolutionRequest(profile="work", skips=(skip,)),
    )
    assert skip not in {component.id for component in result.components}
    assert skip in result.skipped


def test_interface_ids_match_manifests(
    manifest_repository: ManifestRepository,
) -> None:
    """Published selection IDs remain synchronized with resolved manifests."""
    expected = (
        "profile default",
        "profile work",
        "include mactex",
        "include obsidian",
        "include signal",
        "skip claude-code",
        "skip codex",
        "skip cursor",
        "skip wave",
    )
    assert manifest_repository.interface_lines() == expected
    interface_path = manifest_repository.root / "component-ids.txt"
    assert tuple(interface_path.read_text().splitlines()) == expected


def test_component_rejects_unknown_safety_field() -> None:
    """Manifest component validation rejects misspelled safety settings."""
    with pytest.raises(ValidationError, match="enabled_by_defualt"):
        Component.model_validate(
            {
                "id": "signal",
                "manager": "brew_cask",
                "package": "signal",
                "enabled_by_defualt": False,
            }
        )


def test_profile_filename_must_match_declared_name(
    minimal_manifest_root: Path,
) -> None:
    """Profile files cannot silently declare a different identity."""
    profile_path = minimal_manifest_root / "profiles/default.yaml"
    profile_path.write_text("name: work\nextends: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="profile name mismatch"):
        ManifestRepository.load(minimal_manifest_root)


def test_component_profiles_must_exist(
    minimal_manifest_root: Path,
) -> None:
    """Components may only target profiles defined by the manifest set."""
    packages_path = minimal_manifest_root / "packages.yaml"
    packages_path.write_text(
        """
components:
  - id: uv
    manager: brew_formula
    package: uv
    profiles: [missing]
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"component uv references unknown profiles: \['missing'\]",
    ):
        ManifestRepository.load(minimal_manifest_root)
