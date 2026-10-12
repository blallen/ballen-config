"""Tests for installing the shared review-tool tree."""

from pathlib import Path
from stat import S_IXUSR

from ballen_config.assistants.review_tools import review_tools_contribution
from ballen_config.configure import (
    ConfigurationEngine,
    ManagedTreeSpec,
    digest_tree,
    run_configure,
)
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore


def test_review_tools_are_omitted_when_all_agents_are_disabled(tmp_path: Path) -> None:
    """Do not inspect or install review tools without an enabled agent."""
    contribution = review_tools_contribution(
        repo_root=tmp_path,
        enabled=frozenset(),
    )

    assert contribution.specs == ()


def test_review_tools_use_one_shared_managed_tree(repo_root: Path) -> None:
    """Use one digest-bound tree for every selected native agent."""
    source = repo_root / "assistants/shared/tools/review"
    contribution = review_tools_contribution(
        repo_root=repo_root,
        enabled=frozenset({"cursor", "claude-code", "codex"}),
    )

    assert len(contribution.specs) == 1
    spec = contribution.specs[0]
    assert isinstance(spec, ManagedTreeSpec)
    assert spec.id == "shared-review-tools"
    assert spec.destination == Path(".local/share/ballen-config/review-tools")
    assert spec.exclude == frozenset(
        {
            ".DS_Store",
            "__pycache__",
            ".venv",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
        }
    )
    assert spec.expected_source_digest == digest_tree(source, exclude=spec.exclude)


def test_deselected_review_tools_tree_with_bytecode_is_pruned(
    repo_root: Path, tmp_path: Path
) -> None:
    """Remove the installed tree after the last agent is disabled, despite bytecode."""
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=home)
    run_configure(
        ConfigurationEngine(paths=paths, state_store=StateStore(paths), timestamp="1"),
        review_tools_contribution(
            repo_root=repo_root, enabled=frozenset({"codex"})
        ).specs,
    )
    tree = paths.home / ".local/share/ballen-config/review-tools"
    bytecode = tree / "src/ballen_review_tools/__pycache__"
    bytecode.mkdir()
    (bytecode / "plan_cli.cpython-312.pyc").write_bytes(b"\x00")

    report = run_configure(
        ConfigurationEngine(paths=paths, state_store=StateStore(paths), timestamp="2"),
        review_tools_contribution(repo_root=repo_root, enabled=frozenset()).specs,
    )

    assert [(action.id, action.outcome) for action in report.actions] == [
        ("shared-review-tools", "removed")
    ]
    assert not tree.exists()


def test_review_plan_launcher_is_executable(
    repo_root: Path,
) -> None:
    """Keep the managed launcher executable in a source-controlled tree."""
    launcher = repo_root / "assistants/shared/tools/review/bin/review-plan"

    assert launcher.stat().st_mode & S_IXUSR
