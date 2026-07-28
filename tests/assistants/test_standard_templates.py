"""Tests for the generic Python tooling starter bundle."""

import json
import tomllib
from collections.abc import Callable
from configparser import ConfigParser
from pathlib import Path
from typing import NotRequired, TypedDict, cast

import pytest
import yaml


class HookDocument(TypedDict):
    """Expected mapping shape for one pre-commit hook."""

    id: str
    args: NotRequired[list[str]]


class RepositoryDocument(TypedDict):
    """Expected mapping shape for one pre-commit hook repository."""

    repo: str
    rev: str
    hooks: list[HookDocument]


class PreCommitDocument(TypedDict):
    """Expected mapping shape for the starter pre-commit configuration."""

    repos: list[RepositoryDocument]


TEMPLATE_FILES = {
    "README.md",
    "ruff.toml",
    "mypy.ini",
    "pytest.ini",
    ".pre-commit-config.yaml",
    ".markdownlint.json",
}
GENERATED_CACHE_DIRECTORIES = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
PRE_COMMIT_REVISIONS = {
    "https://github.com/pre-commit/pre-commit-hooks": "v6.0.0",
    "https://github.com/astral-sh/ruff-pre-commit": "v0.16.0",
    "https://github.com/DavidAnson/markdownlint-cli2": "v0.23.2",
}
REQUIRED_HOOKS = {
    "trailing-whitespace",
    "end-of-file-fixer",
    "check-yaml",
    "check-toml",
    "check-json",
    "check-added-large-files",
    "ruff-check",
    "ruff-format",
    "markdownlint-cli2",
}
RETAINED_RUFF_IGNORES = {
    "COM",
    "CPY",
    "FIX",
    "TC",
    "D401",
    "N803",
    "N806",
    "TD003",
    "ISC001",
    "RET504",
    "TRY300",
    "PLR0913",
}
REQUIRED_DOCSTRING_RULES = {
    "D100",
    "D101",
    "D102",
    "D103",
    "D104",
    "D105",
    "D106",
    "D107",
}
REMOVED_MIGRATION_IGNORES = {"ASYNC240", "UP042", "PLW0108"}


def template_root(repo_root: Path) -> Path:
    """Locate the copy-once Python bundle within the canonical standards tree."""
    return repo_root / "assistants/shared/standards/templates/python"


def read_ini(path: Path) -> ConfigParser:
    """Parse one INI template without interpolation."""
    parser = ConfigParser(interpolation=None)
    parser.read_string(path.read_text(encoding="utf-8"))
    return parser


def read_pre_commit(path: Path) -> PreCommitDocument:
    """Parse pre-commit YAML and narrow its repository list for typed assertions."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    assert isinstance(document.get("repos"), list)
    return cast(PreCommitDocument, document)


def test_python_tooling_bundle_has_expected_files(repo_root: Path) -> None:
    """Enforce the reviewed files while ignoring caches and generator state."""
    root = template_root(repo_root)
    assert root.is_dir()
    generated = tuple(
        path for path in root.iterdir() if path.name in GENERATED_CACHE_DIRECTORIES
    )
    entries = tuple(
        path for path in root.iterdir() if path.name not in GENERATED_CACHE_DIRECTORIES
    )
    assert {path.name for path in entries} == TEMPLATE_FILES
    assert all(path.is_file() and not path.is_symlink() for path in entries)
    assert all(path.is_dir() and not path.is_symlink() for path in generated)
    assert all("{{" not in path.read_text(encoding="utf-8") for path in entries)


def _assert_ruff_template(path: Path) -> None:
    """Parse the Ruff template and enforce its reviewed defaults."""
    ruff = tomllib.loads(path.read_text(encoding="utf-8"))
    assert ruff["target-version"] == "py312"
    assert ruff["line-length"] == 100
    assert ruff["indent-width"] == 4
    assert ruff["format"] == {
        "quote-style": "double",
        "indent-style": "space",
        "skip-magic-trailing-comma": False,
        "line-ending": "auto",
        "docstring-code-format": True,
    }
    assert ruff["lint"]["select"] == ["ALL"]
    assert ruff["lint"]["pydocstyle"]["convention"] == "google"
    assert ruff["lint"]["flake8-annotations"]["allow-star-arg-any"] is True
    assert ruff["lint"]["flake8-tidy-imports"]["ban-relative-imports"] == "all"
    assert ruff["lint"]["flake8-pytest-style"] == {
        "fixture-parentheses": True,
        "mark-parentheses": True,
    }
    test_ignores = ruff["lint"]["per-file-ignores"]["tests/**/*.py"]
    assert "SLF001" in test_ignores
    assert "ANN" not in test_ignores
    ignored = set(ruff["lint"]["ignore"])
    per_file_ignored = {
        selector
        for selectors in ruff["lint"]["per-file-ignores"].values()
        for selector in selectors
    }
    docstring_disablers = {
        selector
        for selector in ignored | per_file_ignored
        if any(rule.startswith(selector) for rule in REQUIRED_DOCSTRING_RULES)
    }
    assert ignored >= RETAINED_RUFF_IGNORES
    assert not docstring_disablers, (
        f"missing-docstring rules disabled by {sorted(docstring_disablers)}"
    )
    assert "S" not in ignored
    assert REMOVED_MIGRATION_IGNORES.isdisjoint(ignored)


def _assert_mypy_template(path: Path) -> None:
    """Parse the mypy template and enforce its reviewed defaults."""
    mypy = read_ini(path)
    assert mypy["mypy"]["python_version"] == "3.12"
    for setting in (
        "disallow_untyped_defs",
        "check_untyped_defs",
        "strict_optional",
        "warn_unused_ignores",
        "show_error_codes",
    ):
        assert mypy["mypy"].getboolean(setting)
    assert "ignore_missing_imports" not in mypy["mypy"]
    assert "plugins" not in mypy["mypy"]


def _assert_pytest_template(path: Path) -> None:
    """Parse the pytest template and enforce its reviewed defaults."""
    pytest_document = read_ini(path)
    assert "-ra" in pytest_document["pytest"]["addopts"]
    assert pytest_document["pytest"]["testpaths"] == "tests"
    assert pytest_document["pytest"].getboolean("xfail_strict")
    assert "pythonpath" not in pytest_document["pytest"]
    assert "filterwarnings" not in pytest_document["pytest"]


def _assert_pre_commit_template(path: Path) -> None:
    """Parse the pre-commit template and enforce exact hooks and pins."""
    pre_commit = read_pre_commit(path)
    repositories = {
        repository["repo"]: repository["rev"] for repository in pre_commit["repos"]
    }
    assert repositories == PRE_COMMIT_REVISIONS
    hook_ids = {
        hook["id"] for repository in pre_commit["repos"] for hook in repository["hooks"]
    }
    assert hook_ids == REQUIRED_HOOKS
    hook_args = {
        hook["id"]: hook.get("args", [])
        for repository in pre_commit["repos"]
        for hook in repository["hooks"]
    }
    assert hook_args["ruff-check"] == ["--fix"]
    assert hook_args["markdownlint-cli2"] == [
        "--config",
        ".markdownlint.json",
    ]


def _assert_markdownlint_template(path: Path) -> None:
    """Parse the Markdownlint template and enforce its reviewed defaults."""
    markdownlint = json.loads(path.read_text(encoding="utf-8"))
    assert markdownlint["MD013"] is False
    assert markdownlint["MD007"] == {"indent": 4}
    assert markdownlint["MD024"] == {"siblings_only": True}
    assert markdownlint["MD025"] is False
    assert markdownlint["MD029"] == {"style": "ordered"}


@pytest.mark.parametrize(
    ("template_name", "validator"),
    [
        pytest.param("ruff.toml", _assert_ruff_template, id="ruff"),
        pytest.param("mypy.ini", _assert_mypy_template, id="mypy"),
        pytest.param("pytest.ini", _assert_pytest_template, id="pytest"),
        pytest.param(
            ".pre-commit-config.yaml",
            _assert_pre_commit_template,
            id="pre-commit",
        ),
        pytest.param(
            ".markdownlint.json",
            _assert_markdownlint_template,
            id="markdownlint",
        ),
    ],
)
def test_python_tooling_template_encodes_approved_defaults(
    repo_root: Path,
    template_name: str,
    validator: Callable[[Path], None],
) -> None:
    """Parse one starter configuration and enforce its reviewed defaults."""
    validator(template_root(repo_root) / template_name)
