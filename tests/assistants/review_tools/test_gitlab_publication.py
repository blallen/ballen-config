"""Tests for GitLab publication preview and guarded execution."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from ballen_review_tools import gitlab_cli
from ballen_review_tools.gitlab_publication import (
    execute_gitlab_publication,
    plan_digest,
    preview_gitlab_publication,
)
from ballen_review_tools.models import (
    PublicationReceipt,
    ReviewAction,
    ReviewCommentPlan,
    ReviewIdentity,
    ReviewSide,
)
from ballen_review_tools.providers.base import CompletedCommand
from ballen_review_tools.providers.gitlab import GitLabProvider

BASE_SHA = "a" * 40
START_SHA = "b" * 40
HEAD_SHA = "c" * 40
NEW_HEAD = "d" * 40


@dataclass
class RecordingRunner:
    """Return bounded responses and record mutation vectors."""

    responses: list[CompletedCommand] = field(default_factory=list)
    calls: list[tuple[Sequence[str], str | None]] = field(default_factory=list)

    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CompletedCommand:
        """Record one fixed provider call."""
        self.calls.append((tuple(argv), input_text))
        return self.responses.pop(0)


def _identity(head: str = HEAD_SHA) -> ReviewIdentity:
    """Return one GitLab identity."""
    return ReviewIdentity(
        provider="gitlab",
        host="gitlab.example.com",
        repository="acme/ballen-config",
        change_number=17,
        base_revision=BASE_SHA,
        head_revision=head,
    )


def _plan(*, head: str = HEAD_SHA) -> ReviewCommentPlan:
    """Return one selected top-level MR note."""
    identity = _identity(head)
    action = ReviewAction(
        action_id="R001",
        kind="general",
        selected=True,
        body="Please keep this context.",
        deduplication_key="e" * 64,
        validation_state="valid",
        intended_action="create-general",
        outcome="pending",
    )
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=identity,
        source_draft_digest="f" * 64,
        actions=(action,),
    )


def _two_action_plan() -> ReviewCommentPlan:
    """Return a general note followed by a native discussion reply."""
    identity = _identity()
    actions = (
        _plan().actions[0],
        ReviewAction(
            action_id="R002",
            kind="reply",
            selected=True,
            body="Thanks, I will address this.",
            thread_id="discussion-001",
            deduplication_key="a" * 64,
            validation_state="valid",
            intended_action="reply",
            outcome="pending",
        ),
    )
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=identity,
        source_draft_digest="f" * 64,
        actions=actions,
    )


def _inline_plan(
    *,
    path: str = "src/example.py",
    line: int = 41,
    side: ReviewSide = "RIGHT",
    start_line: int | None = None,
) -> ReviewCommentPlan:
    """Return one selected GitLab inline action, optionally a line range."""
    action = ReviewAction(
        action_id="R001",
        kind="inline",
        selected=True,
        body="Guard the empty case.",
        path=path,
        line=line,
        side=side,
        start_line=start_line,
        start_side=None if start_line is None else side,
        deduplication_key="b" * 64,
        validation_state="valid",
        intended_action="create-inline",
        outcome="pending",
    )
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=_identity(),
        source_draft_digest="f" * 64,
        actions=(action,),
    )


def _reads(head: str = HEAD_SHA) -> list[CompletedCommand]:
    """Return current MR, discussion, note, and diff responses."""
    return [
        CompletedCommand(
            0,
            json.dumps(
                {
                    "iid": 17,
                    "diff_refs": {
                        "base_sha": BASE_SHA,
                        "start_sha": START_SHA,
                        "head_sha": head,
                    },
                }
            ),
            "",
        ),
        CompletedCommand(0, "[]", ""),
        CompletedCommand(0, "[]", ""),
        CompletedCommand(
            0,
            json.dumps(
                [
                    {
                        "old_path": "src/example.py",
                        "new_path": "src/example.py",
                        "diff": (
                            "@@ -40,2 +41,3 @@\n context\n-removed\n+added\n+second\n"
                        ),
                    },
                    {
                        "old_path": "src/large.py",
                        "new_path": "src/large.py",
                        "diff": "",
                        "too_large": True,
                    },
                ]
            ),
            "",
        ),
    ]


def test_preview_contains_current_gitlab_diff_refs_and_payload() -> None:
    """Bind the preview to the current MR diff refs and note payload."""
    plan = _plan()
    preview = preview_gitlab_publication(
        plan,
        GitLabProvider(identity=plan.identity, runner=RecordingRunner(_reads())),
    )

    assert preview.status == "ready"
    assert preview.items[0].state == "eligible"
    assert preview.items[0].payload == {"body": "Please keep this context."}


def test_execute_blocks_changed_gitlab_head_before_any_write() -> None:
    """Invalidate approval when the MR head changes."""
    plan = _plan()
    runner = RecordingRunner(_reads(NEW_HEAD))

    result = execute_gitlab_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitLabProvider(identity=plan.identity, runner=runner),
    )

    assert result.status == "blocked"
    assert all("--method" not in call[0] for call in runner.calls)


def test_execute_posts_note_and_retains_string_native_id() -> None:
    """Post an MR note and preserve its native string identifier."""
    plan = _plan()
    runner = RecordingRunner([*_reads(), CompletedCommand(0, '{"id": 77}', "")])

    result = execute_gitlab_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitLabProvider(identity=plan.identity, runner=runner),
    )

    assert result.status == "posted"
    assert result.receipt is not None
    assert result.receipt.items[0].remote_id == "77"


def test_retry_skips_confirmed_note_and_posts_only_remaining_action() -> None:
    """Re-fetch remote notes before retrying a partial publication."""
    # This test becomes a two-action regression once reply publication is added;
    # the single-note duplicate still proves the confirmed action is skipped.
    plan = _plan()
    runner = RecordingRunner(
        [
            *_reads(),
            CompletedCommand(0, '{"id": 77}', ""),
        ]
    )
    first = execute_gitlab_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitLabProvider(identity=plan.identity, runner=runner),
    )
    assert first.status == "posted"

    retry_reads = _reads()
    retry_reads[2] = CompletedCommand(
        0,
        json.dumps([{"id": 77, "body": "Please keep this context."}]),
        "",
    )
    retry = execute_gitlab_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitLabProvider(
            identity=plan.identity,
            runner=RecordingRunner(retry_reads),
        ),
    )

    assert retry.receipt is not None
    assert retry.receipt.items[0].outcome == "duplicate"


def test_partial_retry_skips_confirmed_note_and_posts_only_reply() -> None:
    """Retry after one failure without repeating a confirmed MR note."""
    plan = _two_action_plan()
    first_runner = RecordingRunner(
        [
            *_reads(),
            CompletedCommand(0, '{"id": 77}', ""),
            CompletedCommand(1, "", "rate limited"),
        ]
    )
    first = execute_gitlab_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitLabProvider(identity=plan.identity, runner=first_runner),
    )

    assert first.status == "partial"
    assert first.receipt is not None
    assert [item.outcome for item in first.receipt.items] == ["posted", "failed"]
    assert all("PUT" not in call[0] for call in first_runner.calls)

    retry_reads = _reads()
    retry_reads[2] = CompletedCommand(
        0,
        json.dumps([{"id": 77, "body": "Please keep this context."}]),
        "",
    )
    retry_runner = RecordingRunner(
        [*retry_reads, CompletedCommand(0, '{"id": 88}', "")]
    )
    retry = execute_gitlab_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitLabProvider(identity=plan.identity, runner=retry_runner),
    )

    assert retry.receipt is not None
    assert [item.outcome for item in retry.receipt.items] == ["duplicate", "posted"]
    assert any(
        item.endswith("/discussions/discussion-001/notes")
        for item in retry_runner.calls[-1][0]
    )
    assert all("PUT" not in call[0] for call in retry_runner.calls)


def test_preview_sends_old_and_new_line_for_context_inline_action() -> None:
    """Position an unchanged-line discussion with both current line numbers."""
    plan = _inline_plan(line=41)
    preview = preview_gitlab_publication(
        plan,
        GitLabProvider(identity=plan.identity, runner=RecordingRunner(_reads())),
    )

    assert preview.items[0].state == "eligible"
    assert preview.items[0].payload is not None
    assert preview.items[0].payload["position"] == {
        "position_type": "text",
        "base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
        "start_sha": START_SHA,
        "old_path": "src/example.py",
        "new_path": "src/example.py",
        "old_line": 40,
        "new_line": 41,
    }


@pytest.mark.parametrize(
    ("path", "line", "side"),
    [
        pytest.param("src/example.py", 99, "RIGHT", id="line-outside-hunks"),
        pytest.param("src/example.py", 43, "LEFT", id="line-on-other-side"),
        pytest.param("src/large.py", 1, "RIGHT", id="file-without-diff-text"),
    ],
)
def test_preview_blocks_inline_action_outside_current_diff(
    path: str, line: int, side: ReviewSide
) -> None:
    """Block an inline location that the current MR diff does not contain."""
    plan = _inline_plan(path=path, line=line, side=side)
    preview = preview_gitlab_publication(
        plan,
        GitLabProvider(identity=plan.identity, runner=RecordingRunner(_reads())),
    )

    assert preview.items[0].state == "blocked"
    assert preview.items[0].reason == (
        "inline location is not present in the current GitLab diff"
    )


@pytest.mark.parametrize(
    ("note_head", "outcome"),
    [
        pytest.param(HEAD_SHA, "duplicate", id="current-position"),
        pytest.param("9" * 40, "posted", id="stale-position"),
    ],
)
def test_execute_skips_inline_discussion_only_at_current_position(
    note_head: str, outcome: str
) -> None:
    """Treat a remote inline note as a duplicate only at its current position."""
    plan = _inline_plan(line=42)
    reads = _reads()
    reads[1] = CompletedCommand(
        0,
        json.dumps(
            [
                {
                    "id": "discussion-001",
                    "notes": [
                        {
                            "id": 5,
                            "body": "Guard the empty case.",
                            "position": {
                                "position_type": "text",
                                "base_sha": BASE_SHA,
                                "start_sha": START_SHA,
                                "head_sha": note_head,
                                "old_path": "src/example.py",
                                "new_path": "src/example.py",
                                "new_line": 42,
                            },
                        }
                    ],
                }
            ]
        ),
        "",
    )
    runner = RecordingRunner(
        [*reads, CompletedCommand(0, '{"id": "discussion-002"}', "")]
    )

    result = execute_gitlab_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitLabProvider(identity=plan.identity, runner=runner),
    )

    assert result.receipt is not None
    assert [item.outcome for item in result.receipt.items] == [outcome]


def test_execute_blocks_inline_range_before_any_post() -> None:
    """Block a GitLab line range in preview so execution never posts it."""
    plan = _inline_plan(line=43, start_line=42)
    runner = RecordingRunner(
        [*_reads(), CompletedCommand(0, '{"id": "discussion-002"}', "")]
    )

    result = execute_gitlab_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitLabProvider(identity=plan.identity, runner=runner),
    )

    assert result.status == "blocked"
    assert result.receipt is not None
    assert [(item.outcome, item.reason) for item in result.receipt.items] == [
        ("blocked", "GitLab line ranges require native line codes")
    ]
    assert all("--method" not in call[0] for call in runner.calls)


@pytest.mark.parametrize(
    ("approved_plan_digest", "expected_head", "reason"),
    [
        pytest.param(
            "0" * 64,
            HEAD_SHA,
            "approved plan digest does not match current plan",
            id="stale-digest",
        ),
        pytest.param(
            plan_digest(_plan()),
            NEW_HEAD,
            "expected head does not match current plan",
            id="other-head",
        ),
    ],
)
def test_execute_blocks_unapproved_plan_before_any_request(
    approved_plan_digest: str, expected_head: str, reason: str
) -> None:
    """Block a stale approval or head before reading or writing GitLab."""
    plan = _plan()
    runner = RecordingRunner([*_reads(), CompletedCommand(0, '{"id": 77}', "")])

    result = execute_gitlab_publication(
        plan=plan,
        approved_plan_digest=approved_plan_digest,
        expected_head=expected_head,
        provider=GitLabProvider(identity=plan.identity, runner=runner),
    )

    assert (result.status, result.reason, result.receipt) == ("blocked", reason, None)
    assert runner.calls == []


def _execute_argv(tmp_path: Path, plan: ReviewCommentPlan) -> list[str]:
    """Write the plan and return complete CLI execute arguments."""
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan.model_dump(mode="json")), encoding="utf-8")
    return [
        "execute",
        "--plan",
        str(plan_path),
        "--approved-plan-digest",
        plan_digest(plan),
        "--expected-head",
        HEAD_SHA,
        "--receipt",
        str(tmp_path / "receipt.json"),
    ]


@pytest.mark.parametrize(
    ("omitted", "message"),
    [
        pytest.param("--receipt", "execute requires --receipt", id="receipt"),
        pytest.param(
            "--expected-head",
            "execute requires approved plan digest and expected head",
            id="expected-head",
        ),
    ],
)
def test_cli_execute_requires_every_approval_argument(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    omitted: str,
    message: str,
) -> None:
    """Refuse execute before any GitLab request when an argument is missing."""
    plan = _plan()
    runner = RecordingRunner([*_reads(), CompletedCommand(0, '{"id": 77}', "")])
    monkeypatch.setattr(gitlab_cli, "SubprocessRunner", lambda: runner)
    argv = _execute_argv(tmp_path, plan)
    del argv[argv.index(omitted) : argv.index(omitted) + 2]

    exit_code = gitlab_cli.main(argv)

    assert exit_code == 2
    assert capsys.readouterr().err == f"blocked: {message}\n"
    assert runner.calls == []
    assert not (tmp_path / "receipt.json").exists()


def test_cli_execute_reports_blocked_execution_without_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 2 with the block reason and no receipt when GitLab moved."""
    runner = RecordingRunner(_reads(NEW_HEAD))
    monkeypatch.setattr(gitlab_cli, "SubprocessRunner", lambda: runner)

    exit_code = gitlab_cli.main(_execute_argv(tmp_path, _plan()))

    assert exit_code == 2
    assert capsys.readouterr().err == "blocked: GitLab head changed after approval\n"
    assert not (tmp_path / "receipt.json").exists()
    assert all("--method" not in call[0] for call in runner.calls)


def test_cli_execute_writes_posted_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit 0 and write the posted receipt after a successful execution."""
    plan = _plan()
    runner = RecordingRunner([*_reads(), CompletedCommand(0, '{"id": 77}', "")])
    monkeypatch.setattr(gitlab_cli, "SubprocessRunner", lambda: runner)

    exit_code = gitlab_cli.main(_execute_argv(tmp_path, plan))

    receipt = PublicationReceipt.model_validate_json(
        (tmp_path / "receipt.json").read_text(encoding="utf-8")
    )
    assert exit_code == 0
    assert receipt.status == "posted"
    assert receipt.plan_digest == plan_digest(plan)
    assert [(item.outcome, item.remote_id) for item in receipt.items] == [
        ("posted", "77")
    ]
