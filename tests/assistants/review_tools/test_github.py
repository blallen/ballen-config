"""Tests for GitHub payloads and fixed transport vectors."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

from ballen_review_tools.models import ReviewAction, ReviewCommentPlan, ReviewIdentity
from ballen_review_tools.providers.base import CompletedCommand
from ballen_review_tools.providers.github import GitHubProvider

HEAD_SHA = "b" * 40


@dataclass
class RecordingRunner:
    """Return bounded command responses and retain argument vectors."""

    responses: list[CompletedCommand] = field(default_factory=list)
    calls: list[tuple[Sequence[str], str | None]] = field(default_factory=list)

    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CompletedCommand:
        """Record one no-shell command invocation."""
        self.calls.append((tuple(argv), input_text))
        return self.responses.pop(0)


def _identity() -> ReviewIdentity:
    """Return one GitHub identity with a fully qualified repository."""
    return ReviewIdentity(
        provider="github",
        host="github.com",
        repository="acme/ballen-config",
        change_number=17,
        base_revision="a" * 40,
        head_revision=HEAD_SHA,
    )


def _inline_plan() -> ReviewCommentPlan:
    """Return one selected multi-line inline action."""
    action = ReviewAction(
        action_id="R001",
        kind="inline",
        selected=True,
        body="Guard the empty case.",
        path="src/example.py",
        line=20,
        side="RIGHT",
        start_line=18,
        start_side="RIGHT",
        deduplication_key="d" * 64,
        validation_state="valid",
        intended_action="create-inline",
        outcome="pending",
    )
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=_identity(),
        source_draft_digest="c" * 64,
        actions=(action,),
    )


def test_github_review_payload_uses_current_line_fields() -> None:
    """Build a commit-pinned multi-line review comment."""
    provider = GitHubProvider(identity=_identity(), runner=RecordingRunner())

    payload = provider.review_payload(
        plan=_inline_plan(),
        observed_head=HEAD_SHA,
    )

    assert payload["comments"] == [
        {
            "path": "src/example.py",
            "line": 20,
            "side": "RIGHT",
            "start_line": 18,
            "start_side": "RIGHT",
            "body": "Guard the empty case.",
        }
    ]
    assert payload["commit_id"] == HEAD_SHA
    assert "position" not in payload["comments"][0]


def test_github_read_vectors_use_gh_api_without_shell() -> None:
    """Use fixed argument arrays and standard output only for reads."""
    runner = RecordingRunner(
        responses=[
            CompletedCommand(
                0,
                json.dumps({"number": 17, "head": {"sha": HEAD_SHA}}),
                "",
            ),
            CompletedCommand(0, "[]", ""),
            CompletedCommand(0, "[]", ""),
        ]
    )
    provider = GitHubProvider(identity=_identity(), runner=runner)

    state = provider.fetch_remote_state()

    assert state.head_sha == HEAD_SHA
    assert [call[0] for call in runner.calls] == [
        (
            "gh",
            "api",
            "repos/acme/ballen-config/pulls/17",
            "--header",
            "Accept: application/vnd.github+json",
            "--header",
            "X-GitHub-Api-Version: 2026-03-10",
        ),
        (
            "gh",
            "api",
            "repos/acme/ballen-config/pulls/17/comments",
            "--paginate",
            "--header",
            "Accept: application/vnd.github+json",
            "--header",
            "X-GitHub-Api-Version: 2026-03-10",
        ),
        (
            "gh",
            "api",
            "repos/acme/ballen-config/issues/17/comments",
            "--paginate",
            "--header",
            "Accept: application/vnd.github+json",
            "--header",
            "X-GitHub-Api-Version: 2026-03-10",
        ),
    ]
