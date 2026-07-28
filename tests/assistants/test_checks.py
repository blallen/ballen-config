"""Tests for non-mutating coding-agent readiness diagnostics."""

import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from ballen_config.assistants.checks import assistant_checks
from ballen_config.doctor import CheckSeverity, FindingStatus, run_doctor
from ballen_config.install import InstallAction
from ballen_config.runtime import RuntimePaths
from ballen_config.state import BootstrapState, ManagedRecord, StateStore
from tests.assistants.fakes import StatefulAssistantFake


def _guard_scandir(
    original_scandir: Callable[[Path], Any],
    target: Path,
    maximum_requests: int,
) -> Callable[[Path], Any]:
    """Return a scandir replacement that raises after a bounded target scan."""

    @contextmanager
    def guarded(path: Path) -> Iterator[Any]:
        with original_scandir(path) as scan:
            if Path(path) != target:
                yield scan
                return

            def entries() -> Iterator[object]:
                for _ in range(maximum_requests):
                    yield next(scan)
                raise AssertionError("scanner requested an unbounded entry")

            yield entries()

    return guarded


@pytest.fixture
def paths(tmp_path: Path) -> RuntimePaths:
    """Create isolated approved roots for diagnostics."""
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    home.mkdir()
    return RuntimePaths.from_roots(repo_root=repo, home=home)


def test_authentication_uses_exact_commands_and_hides_native_output(
    paths: RuntimePaths,
) -> None:
    """Use return codes only and never render authentication output."""
    runner = StatefulAssistantFake(paths.home)
    runner.add(("claude", "auth", "status"), returncode=0, stdout="user@example")
    runner.add(("codex", "login", "status"), returncode=1, stderr="token=secret")

    findings = assistant_checks(
        enabled=frozenset({"cursor", "claude-code", "codex"}),
        paths=paths,
        runner=runner,
    )

    assert runner.commands == [
        ("claude", "auth", "status"),
        ("codex", "login", "status"),
    ]
    rendered = run_doctor(findings).render()
    assert "user@example" not in rendered
    assert "token=secret" not in rendered
    assert run_doctor(findings).finding("claude.sign-in").status is FindingStatus.READY
    assert (
        run_doctor(findings).finding("codex.sign-in").message
        == "Codex sign-in requires manual login"
    )
    assert run_doctor(findings).finding("cursor.sign-in").status is FindingStatus.MANUAL
    for finding_id in (
        "cursor.browser",
        "cursor.notion",
        "claude.browser",
        "claude.notion",
        "codex.browser",
        "codex.notion",
    ):
        assert run_doctor(findings).finding(finding_id).severity is CheckSeverity.INFO


def test_disabled_agents_do_not_run_or_inspect_their_roots(paths: RuntimePaths) -> None:
    """Skip all native commands and Cursor filesystem lookup when disabled."""
    runner = StatefulAssistantFake(paths.home)
    findings = assistant_checks(enabled=frozenset(), paths=paths, runner=runner)
    assert findings == ()
    assert runner.commands == []


def test_pending_actions_distinguish_required_from_optional(
    paths: RuntimePaths,
) -> None:
    """Escalate required missing actions without failing optional actions."""
    runner = StatefulAssistantFake(paths.home)
    actions = (
        InstallAction(component_id="cursor.required", argv=("cursor", "install")),
        InstallAction(
            component_id="cursor.optional", argv=("cursor", "install"), required=False
        ),
    )
    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=runner,
        pending_actions=actions,
    )
    report = run_doctor(findings)
    assert report.finding("cursor.required").severity is CheckSeverity.ERROR
    assert report.finding("cursor.required").status is FindingStatus.MISSING
    assert report.finding("cursor.optional").severity is CheckSeverity.WARNING
    assert report.exit_code == 1


def test_cursor_inspection_redacts_invalid_mcp_and_counts_immediate_worktrees(
    paths: RuntimePaths,
) -> None:
    """Report invalid MCP state without exposing it or scanning nested roots."""
    cursor = paths.home / ".cursor"
    cursor.mkdir()
    (cursor / "mcp.json").write_text("not json")
    worktrees = cursor / "worktrees"
    (worktrees / "one" / "nested").mkdir(parents=True)
    (worktrees / "two").mkdir()
    (worktrees / "file").write_text("ignored")

    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=StatefulAssistantFake(paths.home),
        profiles=("default", "work"),
        unmanaged_extension_count=2,
    )
    report = run_doctor(findings)
    assert report.finding("cursor.legacy-mcp").status is FindingStatus.MANUAL
    assert (
        report.finding("cursor.worktrees").message
        == "2 stale Cursor worktree root(s) require review"
    )
    assert (
        report.finding("cursor.extensions").message
        == "2 unmanaged Cursor extension(s) require review"
    )


@pytest.mark.parametrize(
    ("profiles", "warns"),
    [
        pytest.param(("default",), True, id="default-profile"),
        pytest.param(("default", "work"), False, id="work-profile"),
    ],
)
def test_approved_cursor_atlassian_mcp_is_work_profile_only(
    paths: RuntimePaths,
    profiles: tuple[str, ...],
    warns: bool,
) -> None:
    """Accept the exact secret-free Atlassian endpoint only for work."""
    cursor = paths.home / ".cursor"
    cursor.mkdir()
    (cursor / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "atlassian": {
                        "type": "http",
                        "url": "https://mcp.atlassian.com/v1/mcp/authv2",
                    }
                }
            }
        )
    )

    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=StatefulAssistantFake(paths.home),
        profiles=profiles,
    )

    assert ("cursor.legacy-mcp" in {finding.id for finding in findings}) is warns


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"not json", id="invalid-json"),
        pytest.param(
            b'{"mcpServers":{"atlassian":{"type":"http",'
            b'"url":"https://mcp.atlassian.com/v1/mcp/authv2",'
            b'"url":"https://example.com"}}}',
            id="duplicate-key",
        ),
        pytest.param(
            b'{"mcpServers":{"atlassian":{"type":"http","url":"https://example.com"}}}',
            id="altered-url",
        ),
        pytest.param(
            b'{"mcpServers":{"atlassian":{"type":"http",'
            b'"url":"https://mcp.atlassian.com/v1/mcp/authv2",'
            b'"headers":{"Authorization":"redacted"}}}}',
            id="extra-atlassian-field",
        ),
        pytest.param(
            b'{"mcpServers":{"atlassian":{"type":"http",'
            b'"url":"https://mcp.atlassian.com/v1/mcp/authv2"},'
            b'"other":{"type":"http","url":"https://example.com"}}}',
            id="extra-server",
        ),
    ],
)
def test_work_profile_warns_on_every_other_cursor_mcp_document(
    paths: RuntimePaths,
    content: bytes,
) -> None:
    """Keep altered, ambiguous, or expanded MCP state outside desired state."""
    cursor = paths.home / ".cursor"
    cursor.mkdir()
    (cursor / "mcp.json").write_bytes(content)

    findings = assistant_checks(
        enabled=frozenset({"cursor"}),
        paths=paths,
        runner=StatefulAssistantFake(paths.home),
        profiles=("default", "work"),
    )

    assert "cursor.legacy-mcp" in {finding.id for finding in findings}


def test_skills_report_names_only_collisions_and_managed_drift(
    paths: RuntimePaths,
) -> None:
    """Compare enabled skill trees by digest without exposing native paths."""
    for root, body in (
        (paths.home / ".claude/skills/shared", "claude"),
        (paths.home / ".agents/skills/shared", "codex"),
    ):
        root.mkdir(parents=True)
        (root / "SKILL.md").write_text(f"---\nname: shared\n---\n{body}\n")
    managed = paths.home / ".claude/skills/managed"
    managed.mkdir(parents=True)
    (managed / "SKILL.md").write_text("---\nname: managed\n---\ncurrent\n")
    StateStore(paths).write(
        BootstrapState(
            managed={
                "shared-skill-managed-claude-code": ManagedRecord(
                    resource_id="shared-skill-managed-claude-code",
                    source_digest="0" * 64,
                    destination_digest="1" * 64,
                    destination=".claude/skills/managed",
                ),
            }
        )
    )

    findings = assistant_checks(
        enabled=frozenset({"claude-code", "codex"}),
        paths=paths,
        runner=StatefulAssistantFake(paths.home),
    )
    report = run_doctor(findings)
    assert (
        report.finding("skill-collision.shared").message
        == "Skill shared differs across enabled agents"
    )
    assert (
        report.finding("skill-drift.managed").message
        == "Managed skill managed differs from recorded state"
    )
    rendered = report.render()
    assert ".claude" not in rendered
    assert "current" not in rendered
    assert ".cursor" not in rendered


def test_codex_roots_detect_same_name_conflict_but_not_identical_content(
    paths: RuntimePaths,
) -> None:
    """Compare each enabled Codex native root without first-value suppression."""
    for root, body in (
        (paths.home / ".agents/skills/same", "one"),
        (paths.home / ".codex/skills/same", "two"),
    ):
        root.mkdir(parents=True)
        (root / "SKILL.md").write_text(f"---\nname: same\n---\n{body}\n")
    findings = assistant_checks(
        enabled=frozenset({"codex"}),
        paths=paths,
        runner=StatefulAssistantFake(paths.home),
    )
    assert (
        run_doctor(findings).finding("skill-collision.same").status
        is FindingStatus.DRIFT
    )

    (paths.home / ".codex/skills/same/SKILL.md").write_text(
        "---\nname: same\n---\none\n"
    )
    findings = assistant_checks(
        enabled=frozenset({"codex"}),
        paths=paths,
        runner=StatefulAssistantFake(paths.home),
    )
    assert all(item.id != "skill-collision.same" for item in findings)


def test_four_native_skill_roots_allow_identical_content_and_flag_one_difference(
    paths: RuntimePaths,
) -> None:
    """Compare every Cursor, Claude, and both Codex compatibility roots."""
    roots = (
        paths.home / ".cursor/skills/shared",
        paths.home / ".claude/skills/shared",
        paths.home / ".agents/skills/shared",
        paths.home / ".codex/skills/shared",
    )
    for root in roots:
        root.mkdir(parents=True)
        (root / "SKILL.md").write_text("---\nname: shared\n---\nidentical\n")

    findings = assistant_checks(
        enabled=frozenset({"cursor", "claude-code", "codex"}),
        paths=paths,
        runner=StatefulAssistantFake(paths.home),
    )
    assert all(item.id != "skill-collision.shared" for item in findings)

    (roots[-1] / "SKILL.md").write_text("---\nname: shared\n---\ndifferent\n")
    findings = assistant_checks(
        enabled=frozenset({"cursor", "claude-code", "codex"}),
        paths=paths,
        runner=StatefulAssistantFake(paths.home),
    )

    assert (
        run_doctor(findings).finding("skill-collision.shared").status
        is FindingStatus.DRIFT
    )


def test_no_enabled_agent_avoids_state_and_native_skill_lookups(
    paths: RuntimePaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Avoid all skill state inspection when every supported agent is disabled."""
    monkeypatch.setattr(
        StateStore,
        "load",
        lambda _self: (_ for _ in ()).throw(AssertionError("state read")),
    )
    monkeypatch.setattr(
        Path,
        "iterdir",
        lambda _self: (_ for _ in ()).throw(AssertionError("root lookup")),
    )
    assert (
        assistant_checks(
            enabled=frozenset(), paths=paths, runner=StatefulAssistantFake(paths.home)
        )
        == ()
    )


def test_symlinked_skill_root_is_not_traversed(
    paths: RuntimePaths, tmp_path: Path
) -> None:
    """Report unsafe native skill roots without reading their target trees."""
    outside = tmp_path / "outside"
    (outside / "secret").mkdir(parents=True)
    (outside / "secret/SKILL.md").write_text("---\nname: secret\n---\nsecret\n")
    (paths.home / ".agents").mkdir()
    (paths.home / ".agents/skills").symlink_to(outside)
    findings = assistant_checks(
        enabled=frozenset({"codex"}),
        paths=paths,
        runner=StatefulAssistantFake(paths.home),
    )
    assert (
        run_doctor(findings).finding("skill-scan.codex").severity
        is CheckSeverity.WARNING
    )


@pytest.mark.parametrize(
    "kind",
    [
        pytest.param("root", id="root"),
        pytest.param("tree", id="tree"),
        pytest.param("worktrees", id="worktrees"),
    ],
)
def test_diagnostic_scans_cap_every_entry(
    paths: RuntimePaths, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Fail closed when noncandidate entries exhaust a scan budget."""
    import ballen_config.assistants.checks as checks

    monkeypatch.setattr(checks, "_MAX_SKILL_ROOT_ENTRIES", 2)
    monkeypatch.setattr(checks, "_MAX_SKILL_TREE_ENTRIES", 2)
    monkeypatch.setattr(checks, "_MAX_CURSOR_WORKTREES", 2)
    if kind == "root":
        root = paths.home / ".agents/skills"
        root.mkdir(parents=True)
        for index in range(3):
            (root / f"file-{index}").write_text("x")
        findings = assistant_checks(
            enabled=frozenset({"codex"}),
            paths=paths,
            runner=StatefulAssistantFake(paths.home),
        )
        assert (
            run_doctor(findings).finding("skill-scan.codex").message
            == "Native skill state requires manual review"
        )
    elif kind == "tree":
        root = paths.home / ".agents/skills/capped"
        root.mkdir(parents=True)
        (root / "SKILL.md").write_text("---\nname: capped\n---\nx\n")
        for index in range(2):
            (root / f"file-{index}").write_text("x")
        findings = assistant_checks(
            enabled=frozenset({"codex"}),
            paths=paths,
            runner=StatefulAssistantFake(paths.home),
        )
        assert (
            run_doctor(findings).finding("skill-scan.codex").message
            == "Native skill state requires manual review"
        )
    else:
        root = paths.home / ".cursor/worktrees"
        root.mkdir(parents=True)
        for index in range(3):
            (root / f"file-{index}").write_text("x")
        findings = assistant_checks(
            enabled=frozenset({"cursor"}),
            paths=paths,
            runner=StatefulAssistantFake(paths.home),
        )
        assert (
            run_doctor(findings).finding("cursor.worktrees").message
            == "Cursor worktree state requires manual review"
        )


@pytest.mark.parametrize(
    "kind",
    [
        pytest.param("root", id="root"),
        pytest.param("tree", id="tree"),
        pytest.param("worktrees", id="worktrees"),
    ],
)
def test_scan_caps_do_not_request_a_fourth_entry(
    paths: RuntimePaths, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Consume cap plus one entries, but never request an unbounded fourth."""
    import ballen_config.assistants.checks as checks

    original_scandir = os.scandir
    monkeypatch.setattr(checks, "_MAX_SKILL_ROOT_ENTRIES", 2)
    monkeypatch.setattr(checks, "_MAX_SKILL_TREE_ENTRIES", 2)
    monkeypatch.setattr(checks, "_MAX_CURSOR_WORKTREES", 2)
    if kind == "root":
        target = paths.home / ".agents/skills"
        target.mkdir(parents=True)
        enabled = frozenset({"codex"})
        finding_id = "skill-scan.codex"
    elif kind == "tree":
        target = paths.home / ".agents/skills/capped"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("---\nname: capped\n---\nx\n")
        enabled = frozenset({"codex"})
        finding_id = "skill-scan.codex"
    else:
        target = paths.home / ".cursor/worktrees"
        target.mkdir(parents=True)
        enabled = frozenset({"cursor"})
        finding_id = "cursor.worktrees"
    for index in range(4):
        (target / f"entry-{index}").write_text("x")

    monkeypatch.setattr(
        os,
        "scandir",
        _guard_scandir(original_scandir, target, maximum_requests=3),
    )
    findings = assistant_checks(
        enabled=enabled, paths=paths, runner=StatefulAssistantFake(paths.home)
    )
    assert run_doctor(findings).finding(finding_id).severity is CheckSeverity.WARNING


def test_inventory_manual_resources_are_exact_and_unique(repo_root: Path) -> None:
    """Declare portable first-party browser and Notion setup guidance."""
    from ballen_config.assistants.inventory import load_inventory

    inventory = load_inventory(
        repo_root / "assistants/inventory.yaml", repo_root
    ).inventory
    manual = {item.id: item for item in inventory.resources if item.kind == "manual"}
    expected = {
        "cursor.browser": "Enable Cursor's first-party browser capability if it is not already enabled.",
        "claude.browser": "Use Claude Code's first-party browser tooling; do not add a global Playwright MCP server.",
        "codex.browser": "Enable Codex's first-party browser plugin if it is not already available.",
        "cursor.notion": "Connect the official Notion integration from Cursor's integration UI when needed.",
        "claude.notion": "Connect the official Notion integration from Claude's integration UI when needed.",
        "codex.notion": "Connect the official Notion integration from Codex's integration UI when needed.",
    }
    assert {key: manual[key].summary for key in expected} == expected
    assert len(inventory.resources) == len({item.id for item in inventory.resources})
