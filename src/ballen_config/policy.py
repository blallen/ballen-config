"""Enforce security and portability policy across the tracked repository tree."""

from __future__ import annotations

import os
import re
import stat
import subprocess
from collections.abc import Sequence
from pathlib import Path, PurePath

from pydantic import BaseModel, ConfigDict

_GENERATED_PARTS = frozenset(
    {
        "__pycache__",
        "cache",
        "history",
        "sessions",
        "transcripts",
    }
)
_GENERATED_SUFFIXES = frozenset({".age", ".sqlite", ".sqlite3"})
_OPERATIONAL_DIRECTORIES = frozenset(
    {
        "assistants",
        ".agents",
        ".claude",
        ".codex",
        ".cursor",
        "claude-code",
        "cursor",
        "dotfiles",
        "manifests",
        "ssh",
        "terminal",
    }
)
_OPERATIONAL_ROOT_FILES = frozenset({"CLAUDE.md", "bootstrap"})
_OPERATIONAL_DOCS = frozenset(
    {
        PurePath("docs/manual-steps.md"),
        PurePath("docs/ssh-transfer.md"),
    }
)

_PRIVATE_KEY_PATTERN = re.compile(
    rb"-----BEGIN (?:(?:OPENSSH|RSA|EC|DSA) )?PRIVATE KEY-----"
    rb"|-----BEGIN PGP "
    rb"PRIVATE KEY BLOCK-----"
)
_CREDENTIAL_COPY_PATTERN = re.compile(
    rb"(?:copy(?:ing)?\s+credentials\s+from\s+(?:an\s+)?old\s+laptop)",
    re.IGNORECASE,
)
_CREDENTIAL_PATTERN = re.compile(
    rb"(?:"
    rb"<YOUR_GITLAB_TOKEN>"
    rb"|"
    rb"<[^>\r\n]*(?:credential|password|secret|token)[^>\r\n]*>"
    rb"|glpat-[A-Za-z0-9_-]{20,}"
    rb"|MR_MCP_GITLAB_TOKEN"
    rb")",
    re.IGNORECASE,
)
_MACHINE_PATH_PATTERN = re.compile(rb"/Users/[^/\\\s\"'`]+/")
_FORBIDDEN_MCP_PATTERN = re.compile(
    rb"(?:"
    rb"gitlab-mr-mcp"
    rb"|@playwright/mcp"
    rb"|notion-mcp"
    rb"|mcpServers"
    rb"|MR_MCP_GITLAB_TOKEN"
    rb")",
    re.IGNORECASE,
)
_CREDENTIAL_FIELD_PATTERN = re.compile(
    rb"(?:auth_token|access_token|api_key|password)\s*[:=]",
    re.IGNORECASE,
)
_REPOSITORY_IMPORT_PATTERN = re.compile(
    rb"(?:\b(?:from|import)\s+plato\b|Projects/plato|plato:skill)",
    re.IGNORECASE,
)
_LOCAL_MARKETPLACE_PATTERN = re.compile(
    rb"(?:trust_level\s*=\s*['\"]trusted['\"]|(?:marketplace|source)\s*[:=][^\r\n]*?/Users/)",
    re.IGNORECASE,
)


class Violation(BaseModel):
    """A repository policy violation.

    Attributes:
        rule: Stable policy rule identifier.
        path: Repository-relative path that violated the rule.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: str
    path: str


class PolicyError(RuntimeError):
    """A normalized failure while enumerating or reading the tracked tree."""

    def __init__(self) -> None:
        """Initialize an intentionally detail-free policy error."""
        super().__init__("tracked-tree policy failed")


def _run(
    command: Sequence[str], root: Path
) -> subprocess.CompletedProcess[bytes] | None:
    """Run a tracked-file enumeration command without exposing native errors.

    Args:
        command: Command and arguments to execute.
        root: Repository checkout root.

    Returns:
        The completed command, or ``None`` when it could not be executed.
    """
    try:
        return subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
        )
    except OSError:
        return None


def tracked_paths(root: Path) -> tuple[Path, ...]:
    """Enumerate tracked paths, preferring Jujutsu and falling back to Git.

    Args:
        root: Repository checkout root.

    Returns:
        Sorted repository-relative tracked paths.

    Raises:
        PolicyError: If neither source-control command can enumerate the tree.
    """
    jj_result = _run(("jj", "file", "list"), root)
    if jj_result is not None and jj_result.returncode == 0:
        raw_paths = jj_result.stdout.splitlines()
    else:
        git_result = _run(("git", "ls-files", "-z"), root)
        if git_result is None or git_result.returncode != 0:
            raise PolicyError
        raw_paths = [item for item in git_result.stdout.split(b"\0") if item]

    paths = (Path(os.fsdecode(raw_path)) for raw_path in raw_paths if raw_path)
    return tuple(sorted(paths, key=lambda path: path.as_posix()))


def _checkout_root(root: Path) -> Path:
    """Validate and normalize a checkout root without resolving symlinks.

    Args:
        root: Candidate checkout root.

    Returns:
        Absolute lexical checkout root.

    Raises:
        PolicyError: If the root is unavailable, a symlink, or not a directory.
    """
    checkout = Path(os.path.abspath(root))
    try:
        root_mode = checkout.lstat().st_mode
    except OSError:
        raise PolicyError from None
    if stat.S_ISLNK(root_mode) or not stat.S_ISDIR(root_mode):
        raise PolicyError
    return checkout


def _validated_file(checkout: Path, relative_path: Path) -> Path:
    """Validate a tracked path before any file content is read.

    Args:
        checkout: Validated absolute checkout root.
        relative_path: Tracked repository-relative path.

    Returns:
        Validated regular file path.

    Raises:
        PolicyError: If the path is unsafe, escapes the checkout, traverses a
            symlink, or does not name a regular file.
    """
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or ".." in relative_path.parts
    ):
        raise PolicyError

    candidate = Path(os.path.abspath(checkout / relative_path))
    try:
        candidate.relative_to(checkout)
    except ValueError:
        raise PolicyError from None

    current = checkout
    for index, part in enumerate(relative_path.parts):
        current /= part
        try:
            mode = current.lstat().st_mode
        except OSError:
            raise PolicyError from None
        if stat.S_ISLNK(mode):
            raise PolicyError
        is_final = index == len(relative_path.parts) - 1
        if is_final:
            if not stat.S_ISREG(mode):
                raise PolicyError
        elif not stat.S_ISDIR(mode):
            raise PolicyError
    return candidate


def _is_generated(path: Path) -> bool:
    """Return whether a tracked path represents generated or encrypted state."""
    return bool(_GENERATED_PARTS.intersection(path.parts)) or (
        path.suffix.lower() in _GENERATED_SUFFIXES
    )


def _is_operational(path: Path) -> bool:
    """Return whether portability rules apply to the path."""
    pure_path = PurePath(path.as_posix())
    if len(path.parts) == 1 and path.name in _OPERATIONAL_ROOT_FILES:
        return True
    if pure_path in _OPERATIONAL_DOCS:
        return True
    return bool(path.parts and path.parts[0] in _OPERATIONAL_DIRECTORIES)


def _content_rules(path: Path, content: bytes) -> set[str]:
    """Collect content policy rules that a validated file violates.

    Args:
        path: Repository-relative file path.
        content: File bytes.

    Returns:
        Stable rule identifiers violated by the file.
    """
    rules: set[str] = set()
    if _PRIVATE_KEY_PATTERN.search(content):
        rules.add("private-key")
    if _CREDENTIAL_COPY_PATTERN.search(content):
        rules.add("credential-copy-instruction")

    if not _is_operational(path):
        return rules

    if _CREDENTIAL_PATTERN.search(content):
        rules.add("credential-placeholder")
    if _CREDENTIAL_FIELD_PATTERN.search(content):
        rules.add("credential-placeholder")
    if _MACHINE_PATH_PATTERN.search(content):
        rules.add("machine-path")
    if _FORBIDDEN_MCP_PATTERN.search(content):
        rules.add("forbidden-mcp")
    if path.name == "mcp.json":
        rules.add("forbidden-mcp")
    if _REPOSITORY_IMPORT_PATTERN.search(content):
        rules.add("repo-specific-import")
    if _LOCAL_MARKETPLACE_PATTERN.search(content):
        rules.add("local-marketplace")
    return rules


def scan_paths(root: Path, paths: Sequence[Path]) -> tuple[Violation, ...]:
    """Scan specified tracked paths using fail-closed path validation.

    Args:
        root: Repository checkout root.
        paths: Repository-relative tracked paths to scan.

    Returns:
        Deterministically sorted policy violations.

    Raises:
        PolicyError: If any tracked path cannot be validated or read safely.
    """
    checkout = _checkout_root(root)
    violations: list[Violation] = []
    for relative_path in sorted(paths, key=lambda path: path.as_posix()):
        file_path = _validated_file(checkout, relative_path)
        normalized_path = relative_path.as_posix()
        if _is_generated(relative_path):
            violations.append(Violation(rule="generated-state", path=normalized_path))
            continue
        try:
            content = file_path.read_bytes()
        except OSError:
            raise PolicyError from None
        violations.extend(
            Violation(rule=rule, path=normalized_path)
            for rule in sorted(_content_rules(relative_path, content))
        )
    return tuple(
        sorted(violations, key=lambda violation: (violation.path, violation.rule))
    )


def scan_tree(root: Path) -> tuple[Violation, ...]:
    """Scan all files tracked in a repository checkout.

    Args:
        root: Repository checkout root.

    Returns:
        Deterministically sorted policy violations.

    Raises:
        PolicyError: If enumeration or safe path inspection fails.
    """
    return scan_paths(root, tracked_paths(root))


def main(root: Path | None = None) -> int:
    """Run repository policy checks from the current working directory.

    Args:
        root: Checkout root, or the current working directory when omitted.

    Returns:
        ``0`` for a clean tree, ``1`` for policy violations, or ``2`` when the
        tracked tree cannot be inspected safely.
    """
    try:
        violations = scan_tree(Path.cwd() if root is None else root)
    except PolicyError:
        print("policy-error: tracked-tree")
        return 2

    for violation in violations:
        print(f"{violation.rule}: {violation.path}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
