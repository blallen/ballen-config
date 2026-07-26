"""Non-mutating diagnostics for portable coding-agent configuration."""

from __future__ import annotations

import os
import stat
from collections.abc import Collection, Sequence
from pathlib import Path

from ballen_config.assistants.skills import hash_skill_tree
from ballen_config.doctor import (
    CheckSeverity,
    DoctorCheck,
    DoctorFinding,
    FindingStatus,
)
from ballen_config.install import InstallAction
from ballen_config.paths import assert_contained
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore

_AGENT_ROOTS: dict[str, tuple[Path, ...]] = {
    "cursor": (Path(".cursor/skills"),),
    "claude-code": (Path(".claude/skills"),),
    "codex": (Path(".agents/skills"), Path(".codex/skills")),
}
_MAX_SKILL_ROOT_ENTRIES = 512
_MAX_SKILL_TREE_ENTRIES = 2048
_MAX_SKILL_TREE_BYTES = 32 * 1024 * 1024


def _enabled(enabled: Collection[object], name: str) -> bool:
    """Return whether a concrete agent name is enabled.

    Args:
        enabled: Resolved concrete agent names.
        name: Agent name to test.

    Returns:
        Whether the agent is enabled.
    """
    return name in {str(item) for item in enabled}


def _finding(
    finding_id: str,
    status: FindingStatus,
    severity: CheckSeverity,
    message: str,
) -> DoctorFinding:
    """Build one normalized finding with a stable identifier."""
    return DoctorFinding(
        id=finding_id,
        status=status,
        severity=severity,
        message=message,
    )


def _skill_roots(paths: RuntimePaths, agent: str) -> tuple[Path, ...]:
    """Return only enabled agent-native skill roots under the approved home."""
    return tuple(paths.home / relative for relative in _AGENT_ROOTS[agent])


def _safe_skill_tree(root: Path) -> bool:
    """Validate bounded regular skill content before hashing it."""
    entries = 0
    bytes_seen = 0
    pending = [root]
    while pending:
        try:
            with os.scandir(pending.pop()) as scan:
                children = list(scan)
        except OSError:
            return False
        for child in children:
            try:
                metadata = child.stat(follow_symlinks=False)
            except OSError:
                return False
            if stat.S_ISLNK(metadata.st_mode):
                return False
            entries += 1
            if entries > _MAX_SKILL_TREE_ENTRIES:
                return False
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(Path(child.path))
            elif stat.S_ISREG(metadata.st_mode):
                bytes_seen += metadata.st_size
                if bytes_seen > _MAX_SKILL_TREE_BYTES:
                    return False
            else:
                return False
    return True


def _skill_entries(paths: RuntimePaths, agent: str) -> tuple[dict[str, set[str]], bool]:
    """Collect immediate valid skill directories as name-to-digest mappings.

    Invalid or unavailable native state is deliberately ignored because this is
    an advisory, non-mutating inspection.
    """
    entries: dict[str, set[str]] = {}
    unsafe = False
    for root in _skill_roots(paths, agent):
        try:
            root_metadata = os.lstat(root)
        except FileNotFoundError:
            continue
        except OSError:
            unsafe = True
            continue
        if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(
            root_metadata.st_mode
        ):
            unsafe = True
            continue
        try:
            with os.scandir(root) as scan:
                children = sorted(scan, key=lambda child: child.name)
        except OSError:
            unsafe = True
            continue
        if len(children) > _MAX_SKILL_ROOT_ENTRIES:
            unsafe = True
            continue
        for child in children:
            try:
                metadata = child.stat(follow_symlinks=False)
            except OSError:
                unsafe = True
                continue
            if stat.S_ISLNK(metadata.st_mode):
                unsafe = True
                continue
            candidate = Path(child.path)
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or not (candidate / "SKILL.md").is_file()
            ):
                continue
            if not _safe_skill_tree(candidate):
                unsafe = True
                continue
            try:
                entries.setdefault(child.name, set()).add(hash_skill_tree(candidate))
            except (OSError, ValueError):
                unsafe = True
                continue
    return entries, unsafe


def _skill_findings(
    paths: RuntimePaths, enabled: Collection[object]
) -> list[DoctorCheck]:
    """Return collision and recorded-drift findings for enabled agents only."""
    findings: list[DoctorCheck] = []
    enabled_agents = tuple(
        agent for agent in sorted(_AGENT_ROOTS) if _enabled(enabled, agent)
    )
    if not enabled_agents:
        return findings
    by_name: dict[str, set[str]] = {}
    for agent in enabled_agents:
        skills, unsafe = _skill_entries(paths, agent)
        if unsafe:
            findings.append(
                _finding(
                    f"skill-scan.{agent}",
                    FindingStatus.DRIFT,
                    CheckSeverity.WARNING,
                    "Native skill state requires manual review",
                )
            )
        for name, digests in skills.items():
            by_name.setdefault(name, set()).update(digests)
    for name, digests in sorted(by_name.items()):
        if len(digests) > 1:
            findings.append(
                _finding(
                    f"skill-collision.{name}",
                    FindingStatus.DRIFT,
                    CheckSeverity.WARNING,
                    f"Skill {name} differs across enabled agents",
                )
            )

    try:
        state = StateStore(paths).load()
    except (OSError, ValueError):
        return findings
    for resource_id, record in sorted(state.managed.items()):
        if not resource_id.startswith("shared-skill-"):
            continue
        state_agent = next(
            (item for item in _AGENT_ROOTS if resource_id.endswith(f"-{item}")), None
        )
        if state_agent is None or not _enabled(enabled, state_agent):
            continue
        name = (
            resource_id.removeprefix("shared-skill-").removesuffix(f"-{state_agent}")
            or "managed"
        )
        finding_id = f"skill-drift.{name}"
        drift_finding = _finding(
            finding_id,
            FindingStatus.DRIFT,
            CheckSeverity.WARNING,
            f"Managed skill {name} differs from recorded state",
        )

        relative_destination = Path(record.destination)
        if relative_destination.is_absolute() or ".." in relative_destination.parts:
            findings.append(drift_finding)
            continue
        try:
            destination = assert_contained(paths.home / record.destination, paths.home)
        except ValueError:
            findings.append(drift_finding)
            continue
        if destination != paths.home / _AGENT_ROOTS[state_agent][0] / name:
            findings.append(drift_finding)
            continue
        if not destination.is_dir() or not (destination / "SKILL.md").is_file():
            findings.append(drift_finding)
            continue
        try:
            current_digest = hash_skill_tree(destination)
        except (OSError, ValueError):
            findings.append(drift_finding)
            continue
        if current_digest != record.destination_digest:
            findings.append(drift_finding)
    return findings


def assistant_checks(
    *,
    enabled: Collection[object],
    paths: RuntimePaths,
    runner: Runner,
    pending_actions: Sequence[InstallAction] = (),
    unmanaged_extension_count: int = 0,
) -> tuple[DoctorCheck, ...]:
    """Inspect enabled coding-agent readiness without exposing native state.

    Args:
        enabled: Enabled coding-agent names after profile and skip resolution.
        paths: Approved runtime filesystem roots.
        runner: Command runner used only for agent-native sign-in status.
        pending_actions: Unapplied installation actions to report.
        unmanaged_extension_count: Advisory count of Cursor extensions to review.

    Returns:
        Deterministically sorted, unique diagnostics.
    """
    findings: list[DoctorCheck] = []
    existing_ids: set[str] = set()

    def add(finding: DoctorCheck) -> None:
        if finding.id not in existing_ids:
            findings.append(finding)
            existing_ids.add(finding.id)

    for action in sorted(pending_actions, key=lambda item: item.component_id):
        if not any(
            action.component_id.startswith(f"{agent}.") for agent in _AGENT_ROOTS
        ):
            continue
        if not any(
            _enabled(enabled, agent) and action.component_id.startswith(f"{agent}.")
            for agent in _AGENT_ROOTS
        ):
            continue
        add(
            _finding(
                action.component_id,
                FindingStatus.MISSING,
                CheckSeverity.ERROR if action.required else CheckSeverity.WARNING,
                "required installation is missing"
                if action.required
                else "optional installation is missing",
            )
        )

    if _enabled(enabled, "cursor"):
        add(
            _finding(
                "cursor.browser",
                FindingStatus.MANUAL,
                CheckSeverity.INFO,
                "Cursor browser capability requires manual review",
            )
        )
        add(
            _finding(
                "cursor.notion",
                FindingStatus.MANUAL,
                CheckSeverity.INFO,
                "Cursor Notion integration requires manual review",
            )
        )
        add(
            _finding(
                "cursor.sign-in",
                FindingStatus.MANUAL,
                CheckSeverity.INFO,
                "Cursor sign-in requires manual login",
            )
        )
        cursor_root = paths.home / ".cursor"
        if (cursor_root / "mcp.json").exists():
            add(
                _finding(
                    "cursor.mcp",
                    FindingStatus.MANUAL,
                    CheckSeverity.WARNING,
                    "Cursor MCP configuration requires manual review",
                )
            )
        worktrees = cursor_root / "worktrees"
        if worktrees.is_dir():
            try:
                count = sum(child.is_dir() for child in worktrees.iterdir())
            except OSError:
                count = 0
            if count:
                add(
                    _finding(
                        "cursor.worktrees",
                        FindingStatus.MANUAL,
                        CheckSeverity.WARNING,
                        f"{count} stale Cursor worktree root(s) require review",
                    )
                )
        if unmanaged_extension_count > 0:
            add(
                _finding(
                    "cursor.extensions",
                    FindingStatus.MANUAL,
                    CheckSeverity.INFO,
                    f"{unmanaged_extension_count} unmanaged Cursor extension(s) require review",
                )
            )

    for agent, command, label in (
        ("claude-code", ("claude", "auth", "status"), "Claude"),
        ("codex", ("codex", "login", "status"), "Codex"),
    ):
        if not _enabled(enabled, agent):
            continue
        prefix = agent.split("-")[0]
        add(
            _finding(
                f"{prefix}.browser",
                FindingStatus.MANUAL,
                CheckSeverity.INFO,
                f"{label} browser capability requires manual review",
            )
        )
        add(
            _finding(
                f"{prefix}.notion",
                FindingStatus.MANUAL,
                CheckSeverity.INFO,
                f"{label} Notion integration requires manual review",
            )
        )
        ready = runner.run(command)["returncode"] == 0
        add(
            _finding(
                f"{prefix}.sign-in",
                FindingStatus.READY if ready else FindingStatus.MANUAL,
                CheckSeverity.INFO,
                "ready" if ready else f"{label} sign-in requires manual login",
            )
        )

    for finding in _skill_findings(paths, enabled):
        add(finding)
    return tuple(sorted(findings, key=lambda finding: finding.id))
