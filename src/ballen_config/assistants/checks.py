"""Non-mutating diagnostics for portable coding-agent configuration."""

from __future__ import annotations

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


def _skill_entries(paths: RuntimePaths, agent: str) -> dict[str, str]:
    """Collect immediate valid skill directories as name-to-digest mappings.

    Invalid or unavailable native state is deliberately ignored because this is
    an advisory, non-mutating inspection.
    """
    entries: dict[str, str] = {}
    for root in _skill_roots(paths, agent):
        if not root.is_dir():
            continue
        try:
            children = sorted(root.iterdir(), key=lambda child: child.name)
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or not (child / "SKILL.md").is_file():
                continue
            try:
                entries.setdefault(child.name, hash_skill_tree(child))
            except (OSError, ValueError):
                continue
    return entries


def _skill_findings(
    paths: RuntimePaths, enabled: Collection[object]
) -> list[DoctorCheck]:
    """Return collision and recorded-drift findings for enabled agents only."""
    by_name: dict[str, set[str]] = {}
    per_agent: dict[str, dict[str, str]] = {}
    for agent in sorted(_AGENT_ROOTS):
        if not _enabled(enabled, agent):
            continue
        skills = _skill_entries(paths, agent)
        per_agent[agent] = skills
        for name, digest in skills.items():
            by_name.setdefault(name, set()).add(digest)

    findings: list[DoctorCheck] = []
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
        prefix, separator, agent = resource_id.rpartition(":")
        if (
            not separator
            or not prefix.startswith("skill:")
            or not _enabled(enabled, agent)
        ):
            continue
        relative_destination = Path(record.destination)
        if relative_destination.is_absolute() or ".." in relative_destination.parts:
            continue
        try:
            destination = assert_contained(paths.home / record.destination, paths.home)
        except ValueError:
            continue
        if destination.parent not in _skill_roots(paths, agent):
            continue
        if not destination.is_dir() or not (destination / "SKILL.md").is_file():
            continue
        try:
            current_digest = hash_skill_tree(destination)
        except (OSError, ValueError):
            continue
        if current_digest != record.destination_digest:
            name = destination.name
            findings.append(
                _finding(
                    f"skill-drift.{name}",
                    FindingStatus.DRIFT,
                    CheckSeverity.WARNING,
                    f"Managed skill {name} differs from recorded state",
                )
            )
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
