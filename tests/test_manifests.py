from pathlib import Path

import pytest

from ballen_config.manifests import ManifestRepository
from ballen_config.models import Profile, ResolutionRequest


@pytest.fixture
def repository(repo_root: Path) -> ManifestRepository:
    """Load the repository manifests."""
    return ManifestRepository.load(repo_root / "manifests")


def ids(repository: ManifestRepository, request: ResolutionRequest) -> set[str]:
    """Return the resolved component identifiers."""
    return {component.id for component in repository.resolve(request).components}


def test_work_profile_extends_default(repository: ManifestRepository) -> None:
    resolved = ids(repository, ResolutionRequest(profile="work"))
    assert {"uv", "gh", "glab", "jj", "wave", "libmagic", "awscli"} <= resolved
    assert {"obsidian", "signal", "mactex"}.isdisjoint(resolved)


def test_shell_parent_precedes_nested_git_components(
    repository: ManifestRepository,
) -> None:
    """Install Oh My Zsh before repositories nested beneath it."""
    ordered = [
        component.id
        for component in repository.resolve(
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


@pytest.mark.parametrize("include", ["obsidian", "signal", "mactex"])
def test_personal_applications_are_opt_in(
    repository: ManifestRepository,
    include: str,
) -> None:
    resolved = ids(
        repository,
        ResolutionRequest(profile="default", includes=(include,)),
    )
    assert include in resolved


@pytest.mark.parametrize("skip", ["cursor", "claude-code", "codex", "wave"])
def test_skip_removes_complete_component(
    repository: ManifestRepository,
    skip: str,
) -> None:
    result = repository.resolve(
        ResolutionRequest(profile="work", skips=(skip,)),
    )
    assert skip not in {component.id for component in result.components}
    assert skip in result.skipped


def test_interface_ids_match_manifests(repository: ManifestRepository) -> None:
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
    assert repository.interface_lines() == expected
    interface_path = repository.root / "component-ids.txt"
    assert tuple(interface_path.read_text().splitlines()) == expected
