"""Tests for the generic Python tooling starter bundle."""

from __future__ import annotations

import json
import re
import tomllib
from configparser import ConfigParser
from pathlib import Path
from typing import NotRequired, TypedDict, cast

import yaml


class HookDocument(TypedDict):
    """Describe one pre-commit hook."""

    id: str
    args: NotRequired[list[str]]


class RepositoryDocument(TypedDict):
    """Describe one pre-commit hook repository."""

    repo: str
    rev: str
    hooks: list[HookDocument]


class PreCommitDocument(TypedDict):
    """Describe the starter pre-commit configuration."""

    repos: list[RepositoryDocument]


TEMPLATE_FILES = {
    "README.md",
    "ruff.toml",
    "mypy.ini",
    "pytest.ini",
    ".pre-commit-config.yaml",
    ".markdownlint.json",
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
REMOVED_MIGRATION_IGNORES = {"ASYNC240", "UP042", "PLW0108"}
FORBIDDEN_CASEFOLDED = (
    "plato",
    "/users/",
    "autopilot",
    "ami-",
    "pydantic 2.8",
    "--project src",
    "{{",
)
PLACEHOLDER_PATTERN = re.compile(r"\b(?:TODO|TBD|FIXME)\b", re.IGNORECASE)
SECRET_SAMPLE_PATTERN = re.compile(
    r"\b(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*"
    r"['\"]?[A-Za-z0-9_./+=-]{8,}",
    re.IGNORECASE,
)


def template_root(repo_root: Path) -> Path:
    """Return the generic Python tooling template root."""
    return repo_root / "assistants/shared/standards/templates/python"


def read_ini(path: Path) -> ConfigParser:
    """Parse one INI template without interpolation."""
    parser = ConfigParser(interpolation=None)
    parser.read_string(path.read_text(encoding="utf-8"))
    return parser


def read_pre_commit(path: Path) -> PreCommitDocument:
    """Parse and narrow the pre-commit template."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    assert isinstance(document.get("repos"), list)
    return cast(PreCommitDocument, document)


def test_python_tooling_bundle_has_expected_files(repo_root: Path) -> None:
    """Keep the starter bundle explicit and free of generated files."""
    root = template_root(repo_root)
    assert root.is_dir()
    entries = tuple(root.iterdir())
    assert {path.name for path in entries} == TEMPLATE_FILES
    assert all(path.is_file() and not path.is_symlink() for path in entries)


def test_python_tooling_templates_parse(repo_root: Path) -> None:
    """Require every starter configuration to parse with its native format."""
    root = template_root(repo_root)
    ruff = tomllib.loads((root / "ruff.toml").read_text(encoding="utf-8"))
    mypy = read_ini(root / "mypy.ini")
    pytest = read_ini(root / "pytest.ini")
    pre_commit = read_pre_commit(root / ".pre-commit-config.yaml")
    markdownlint = json.loads((root / ".markdownlint.json").read_text(encoding="utf-8"))

    assert isinstance(ruff, dict)
    assert mypy.has_section("mypy")
    assert pytest.has_section("pytest")
    assert pre_commit["repos"]
    assert isinstance(markdownlint, dict)


def test_python_tooling_templates_encode_approved_defaults(
    repo_root: Path,
) -> None:
    """Preserve the reviewed portable defaults and exact upstream pins."""
    root = template_root(repo_root)
    ruff = tomllib.loads((root / "ruff.toml").read_text(encoding="utf-8"))
    mypy = read_ini(root / "mypy.ini")
    pytest = read_ini(root / "pytest.ini")
    pre_commit = read_pre_commit(root / ".pre-commit-config.yaml")
    markdownlint = json.loads((root / ".markdownlint.json").read_text(encoding="utf-8"))

    assert ruff["target-version"] == "py312"
    assert ruff["line-length"] == 100
    assert ruff["lint"]["pydocstyle"]["convention"] == "google"
    assert "tests/**/*.py" in ruff["lint"]["per-file-ignores"]
    ignored = set(ruff["lint"]["ignore"])
    assert ignored >= RETAINED_RUFF_IGNORES
    assert "S" not in ignored
    assert REMOVED_MIGRATION_IGNORES.isdisjoint(ignored)

    assert mypy["mypy"]["python_version"] == "3.12"
    for setting in (
        "disallow_untyped_defs",
        "strict_optional",
        "check_untyped_defs",
        "show_error_codes",
        "warn_unused_ignores",
    ):
        assert mypy["mypy"].getboolean(setting)
    assert "ignore_missing_imports" not in mypy["mypy"]
    assert "plugins" not in mypy["mypy"]

    assert "-ra" in pytest["pytest"]["addopts"]
    assert pytest["pytest"]["testpaths"] == "tests"
    assert pytest["pytest"].getboolean("xfail_strict")
    assert "pythonpath" not in pytest["pytest"]
    assert "filterwarnings" not in pytest["pytest"]

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

    assert markdownlint["MD013"] is False
    assert markdownlint["MD007"] == {"indent": 4}
    assert markdownlint["MD024"] == {"siblings_only": True}
    assert markdownlint["MD025"] is False
    assert markdownlint["MD029"] == {"style": "ordered"}


def test_python_tooling_bundle_is_portable_and_copy_once(
    repo_root: Path,
) -> None:
    """Reject repository coupling, local state, and unfinished guidance."""
    root = template_root(repo_root)
    readme = (root / "README.md").read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.casefold().split())
    for phrase in (
        "repository-owned snapshot",
        "merge",
        "adapt",
        "pydantic",
        "uv-lock",
        "conventional commits",
        "periodic",
        "copy `.pre-commit-config.yaml` with `ruff.toml` and `.markdownlint.json`",
    ):
        assert phrase in normalized_readme

    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        normalized = text.casefold()
        for forbidden in FORBIDDEN_CASEFOLDED:
            assert forbidden not in normalized, path
        assert PLACEHOLDER_PATTERN.search(text) is None, path
        assert SECRET_SAMPLE_PATTERN.search(text) is None, path
