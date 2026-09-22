"""Tests for GitLab payloads and fixed transport vectors."""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

from ballen_review_tools.models import ReviewAction, ReviewCommentPlan, ReviewIdentity
from ballen_review_tools.providers.base import CompletedCommand
from ballen_review_tools.providers.gitlab import GitLabDiffRefs, GitLabProvider

BASE_SHA = "a" * 40
START_SHA = "b" * 40
HEAD_SHA = "c" * 40


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
    """Return one GitLab identity with a namespaced repository."""
    return ReviewIdentity(
        provider="gitlab",
        host="gitlab.example.com",
        repository="acme/ballen-config",
        change_number=17,
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
    )


def _refs() -> GitLabDiffRefs:
    """Return one complete GitLab diff-ref tuple."""
    return GitLabDiffRefs(
        base_sha=BASE_SHA,
        start_sha=START_SHA,
        head_sha=HEAD_SHA,
    )


def _inline_plan(
    *, side: str = "RIGHT", path: str = "src/example.py"
) -> ReviewCommentPlan:
    """Return one selected single-line GitLab action."""
    action = ReviewAction(
        action_id="R001",
        kind="inline",
        selected=True,
        body="Guard the empty case.",
        path=path,
        line=42,
        side=side,  # type: ignore[arg-type]
        deduplication_key="d" * 64,
        validation_state="valid",
        intended_action="create-inline",
        outcome="pending",
    )
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=_identity(),
        source_draft_digest="e" * 64,
        actions=(action,),
    )


def test_gitlab_discussion_payload_uses_current_text_position() -> None:
    """Build the exact new-line position with all three current SHAs."""
    provider = GitLabProvider(identity=_identity(), runner=RecordingRunner())

    payload = provider.discussion_payload(
        action=_inline_plan().actions[0],
        revisions=_refs(),
    )

    assert payload == {
        "body": "Guard the empty case.",
        "position": {
            "position_type": "text",
            "base_sha": BASE_SHA,
            "head_sha": HEAD_SHA,
            "start_sha": START_SHA,
            "old_path": "src/example.py",
            "new_path": "src/example.py",
            "new_line": 42,
        },
    }


def test_gitlab_discussion_payload_maps_removed_line_to_old_side() -> None:
    """Use old_line for a removed line and retain both paths."""
    provider = GitLabProvider(identity=_identity(), runner=RecordingRunner())

    payload = provider.discussion_payload(
        action=_inline_plan(side="LEFT", path="src/old_example.py").actions[0],
        revisions=_refs(),
    )

    assert payload["position"]["old_path"] == "src/old_example.py"
    assert payload["position"]["new_path"] == "src/old_example.py"
    assert payload["position"]["old_line"] == 42
    assert "new_line" not in payload["position"]


def test_gitlab_read_vectors_encode_namespace_and_use_pagination() -> None:
    """Use exact no-shell glab vectors for MR, discussions, and notes."""
    runner = RecordingRunner(
        responses=[
            CompletedCommand(
                0,
                json.dumps(
                    {
                        "iid": 17,
                        "diff_refs": {
                            "base_sha": BASE_SHA,
                            "start_sha": START_SHA,
                            "head_sha": HEAD_SHA,
                        },
                    }
                ),
                "",
            ),
            CompletedCommand(0, "[]", ""),
            CompletedCommand(0, "[]", ""),
        ]
    )
    provider = GitLabProvider(identity=_identity(), runner=runner)

    state = provider.fetch_remote_state()

    assert state.diff_refs.head_sha == HEAD_SHA
    assert [call[0] for call in runner.calls] == [
        ("glab", "api", "projects/acme%2Fballen-config/merge_requests/17"),
        (
            "glab",
            "api",
            "projects/acme%2Fballen-config/merge_requests/17/discussions",
            "--paginate",
        ),
        (
            "glab",
            "api",
            "projects/acme%2Fballen-config/merge_requests/17/notes",
            "--paginate",
        ),
    ]


def test_gitlab_post_vectors_use_json_stdin() -> None:
    """Post exact JSON through glab without shell interpolation."""
    runner = RecordingRunner([CompletedCommand(0, '{"id": "D001"}', "")])
    provider = GitLabProvider(identity=_identity(), runner=runner)

    provider.post_discussion(
        _inline_plan().actions[0],
        _refs(),
    )

    assert runner.calls == [
        (
            (
                "glab",
                "api",
                "--method",
                "POST",
                "projects/acme%2Fballen-config/merge_requests/17/discussions",
                "--header",
                "Content-Type: application/json",
                "--input",
                "-",
            ),
            json.dumps(
                {
                    "body": "Guard the empty case.",
                    "position": {
                        "position_type": "text",
                        "base_sha": BASE_SHA,
                        "head_sha": HEAD_SHA,
                        "start_sha": START_SHA,
                        "old_path": "src/example.py",
                        "new_path": "src/example.py",
                        "new_line": 42,
                    },
                },
                sort_keys=True,
            ),
        )
    ]
