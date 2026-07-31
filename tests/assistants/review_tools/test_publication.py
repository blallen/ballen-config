"""Tests for GitHub preview and guarded execution."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

from ballen_review_tools.models import ReviewAction, ReviewCommentPlan, ReviewIdentity
from ballen_review_tools.providers.base import CompletedCommand
from ballen_review_tools.providers.github import GitHubProvider
from ballen_review_tools.publication import (
    execute_github_publication,
    plan_digest,
    preview_github_publication,
)

HEAD_SHA = "b" * 40
NEW_HEAD = "e" * 40


@dataclass
class RecordingRunner:
    """Return bounded command responses and record mutation vectors."""

    responses: list[CompletedCommand] = field(default_factory=list)
    calls: list[tuple[Sequence[str], str | None]] = field(default_factory=list)

    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CompletedCommand:
        """Record one command and return its next response."""
        self.calls.append((tuple(argv), input_text))
        return self.responses.pop(0)


def _plan() -> ReviewCommentPlan:
    """Return one selected general action."""
    identity = ReviewIdentity(
        provider="github",
        host="github.com",
        repository="acme/ballen-config",
        change_number=17,
        base_revision="a" * 40,
        head_revision=HEAD_SHA,
    )
    action = ReviewAction(
        action_id="R001",
        kind="general",
        selected=True,
        body="Please keep this context.",
        deduplication_key="d" * 64,
        validation_state="valid",
        intended_action="create-general",
        outcome="pending",
    )
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=identity,
        source_draft_digest="c" * 64,
        actions=(action,),
    )


def _read_responses(head: str = HEAD_SHA) -> list[CompletedCommand]:
    """Return GitHub read responses for one remote head."""
    return [
        CompletedCommand(0, json.dumps({"number": 17, "head": {"sha": head}}), ""),
        CompletedCommand(0, "[]", ""),
        CompletedCommand(0, "[]", ""),
    ]


def _two_action_plan() -> ReviewCommentPlan:
    """Return one general action followed by one native reply."""
    identity = _plan().identity
    actions = (
        _plan().actions[0],
        ReviewAction(
            action_id="R002",
            kind="reply",
            selected=True,
            body="Thanks, I will address this.",
            thread_id="10",
            deduplication_key="e" * 64,
            validation_state="valid",
            intended_action="reply",
            outcome="pending",
        ),
    )
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=identity,
        source_draft_digest="c" * 64,
        actions=actions,
    )


def test_preview_contains_current_plan_and_remote_digests() -> None:
    """Bind preview output to the current plan and observations."""
    runner = RecordingRunner(_read_responses())
    provider = GitHubProvider(identity=_plan().identity, runner=runner)

    preview = preview_github_publication(_plan(), provider)

    assert preview.status == "ready"
    assert preview.observed_head == HEAD_SHA
    assert preview.items[0].state == "eligible"
    assert preview.items[0].payload is not None


def test_execute_rejects_changed_head_before_any_write() -> None:
    """Invalidate approval when remote head moves after preview."""
    runner = RecordingRunner(_read_responses(NEW_HEAD))
    provider = GitHubProvider(identity=_plan().identity, runner=runner)

    result = execute_github_publication(
        plan=_plan(),
        approved_plan_digest=plan_digest(_plan()),
        expected_head=HEAD_SHA,
        provider=provider,
    )

    assert result.status == "blocked"
    assert all("--method" not in call[0] for call in runner.calls)


def test_execute_marks_exact_remote_general_comment_duplicate() -> None:
    """Avoid reposting a general comment already observed remotely."""
    responses = _read_responses()
    responses[2] = CompletedCommand(
        0,
        json.dumps([{"id": 12, "body": "Please keep this context."}]),
        "",
    )
    runner = RecordingRunner(responses)
    plan = _plan()
    result = execute_github_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitHubProvider(identity=plan.identity, runner=runner),
    )

    assert result.receipt is not None
    assert result.receipt.items[0].outcome == "duplicate"
    assert all("--method" not in call[0] for call in runner.calls)


def test_execute_posts_general_comment_with_exact_json_stdin() -> None:
    """Keep top-level comments separate from review-comment batches."""
    plan = _plan()
    runner = RecordingRunner(
        [*_read_responses(), CompletedCommand(0, '{"id": 12}', "")]
    )

    result = execute_github_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitHubProvider(identity=plan.identity, runner=runner),
    )

    assert result.status == "posted"
    assert runner.calls[-1] == (
        (
            "gh",
            "api",
            "--method",
            "POST",
            "repos/acme/ballen-config/issues/17/comments",
            "--input",
            "-",
            "--header",
            "Accept: application/vnd.github+json",
            "--header",
            "X-GitHub-Api-Version: 2026-03-10",
        ),
        '{"body": "Please keep this context."}',
    )


def test_partial_retry_skips_successful_general_comment() -> None:
    """Retry only the still-eligible reply after a partial publication."""
    plan = _two_action_plan()
    first_runner = RecordingRunner(
        [
            *_read_responses(),
            CompletedCommand(0, '{"id": 12}', ""),
            CompletedCommand(1, "", "secondary rate limit"),
        ]
    )
    first = execute_github_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitHubProvider(identity=plan.identity, runner=first_runner),
    )

    assert first.status == "partial"
    assert first.receipt is not None
    assert [item.outcome for item in first.receipt.items] == ["posted", "failed"]

    retry_responses = _read_responses()
    retry_responses[2] = CompletedCommand(
        0,
        json.dumps([{"id": 12, "body": "Please keep this context."}]),
        "",
    )
    retry_runner = RecordingRunner(
        [*retry_responses, CompletedCommand(0, '{"id": 13}', "")]
    )
    retry = execute_github_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitHubProvider(identity=plan.identity, runner=retry_runner),
    )

    assert retry.receipt is not None
    assert [item.outcome for item in retry.receipt.items] == ["duplicate", "posted"]
    assert retry_runner.calls[-1][0][4].endswith("/pulls/comments/10/replies")
