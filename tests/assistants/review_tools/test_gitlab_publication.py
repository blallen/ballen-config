"""Tests for GitLab publication preview and guarded execution."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

from ballen_review_tools.gitlab_publication import (
    execute_gitlab_publication,
    plan_digest,
    preview_gitlab_publication,
)
from ballen_review_tools.models import ReviewAction, ReviewCommentPlan, ReviewIdentity
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


def _reads(head: str = HEAD_SHA) -> list[CompletedCommand]:
    """Return current MR, discussion, and note responses."""
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
