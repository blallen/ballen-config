"""Tests for GitHub preview and guarded execution."""

import json
from pathlib import Path

import pytest
from ballen_review_tools.canonical import canonical_digest
from ballen_review_tools.github_cli import main as publish_github_review
from ballen_review_tools.models import (
    PublicationPreview,
    PublicationReceipt,
    ReviewAction,
    ReviewCommentPlan,
    ReviewIdentity,
)
from ballen_review_tools.providers.base import CompletedCommand
from ballen_review_tools.providers.github import GitHubProvider, GitHubProviderError
from ballen_review_tools.publication import (
    execute_github_publication,
    plan_digest,
    preview_github_publication,
)

from tests.assistants.review_tools.doubles import RecordingRunner

HEAD_SHA = "b" * 40
NEW_HEAD = "e" * 40


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
        CompletedCommand(0, "[[]]", ""),
        CompletedCommand(0, "[[]]", ""),
        CompletedCommand(0, "[[]]", ""),
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


def _inline_plan() -> ReviewCommentPlan:
    """Return one inline action whose current diff location can be varied."""
    identity = _plan().identity
    action = ReviewAction(
        action_id="R001",
        kind="inline",
        selected=True,
        body="Guard the empty case.",
        path="src/example.py",
        line=20,
        side="RIGHT",
        deduplication_key="f" * 64,
        validation_state="valid",
        intended_action="create-inline",
        outcome="pending",
    )
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=identity,
        source_draft_digest="c" * 64,
        actions=(action,),
    )


def _plan_with(*actions: ReviewAction) -> ReviewCommentPlan:
    """Return one plan for the shared identity holding the given actions."""
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=_plan().identity,
        source_draft_digest="c" * 64,
        actions=actions,
    )


def _reply(thread_id: str) -> ReviewAction:
    """Return the native reply action aimed at one draft-supplied target."""
    return _two_action_plan().actions[1].model_copy(update={"thread_id": thread_id})


def _ranged_inline() -> ReviewAction:
    """Return the inline action widened to a two-line current-diff range."""
    action = _inline_plan().actions[0]
    return action.model_copy(update={"start_line": 19, "start_side": "RIGHT"})


def _diff_reads(review_comments: list[dict[str, object]]) -> list[CompletedCommand]:
    """Return reads with remote review comments and lines 19-20 in the diff."""
    responses = _read_responses()
    responses[1] = CompletedCommand(0, json.dumps([review_comments]), "")
    responses[3] = CompletedCommand(
        0,
        json.dumps(
            [
                [
                    {
                        "filename": "src/example.py",
                        "patch": "@@ -19,2 +19,2 @@\n-old one\n-old two\n+new one\n+new two\n",
                    }
                ]
            ]
        ),
        "",
    )
    return responses


def _plan_file(tmp_path: Path) -> Path:
    """Write the general-comment plan as a CLI input artifact."""
    path = tmp_path / "plan.json"
    path.write_text(_plan().model_dump_json(), encoding="utf-8")
    return path


def _approved_execute(tmp_path: Path) -> list[str]:
    """Return CLI execute arguments that approve the current plan and head."""
    return [
        "execute",
        "--plan",
        str(_plan_file(tmp_path)),
        "--approved-plan-digest",
        plan_digest(_plan()),
        "--expected-head",
        HEAD_SHA,
    ]


def _use_runner(monkeypatch: pytest.MonkeyPatch, runner: RecordingRunner) -> None:
    """Send the CLI's provider requests to one recording runner."""
    monkeypatch.setattr(
        "ballen_review_tools.github_cli.SubprocessRunner", lambda: runner
    )


def test_preview_contains_current_plan_and_remote_digests() -> None:
    """Bind preview output to the current plan and observations."""
    plan = _plan()
    runner = RecordingRunner(_read_responses())
    provider = GitHubProvider(identity=plan.identity, runner=runner)

    preview = preview_github_publication(plan, provider)

    assert preview.status == "ready"
    assert preview.observed_head == HEAD_SHA
    assert preview.plan_digest == plan_digest(plan)
    assert preview.remote_state_digest == canonical_digest(
        {
            "head_sha": HEAD_SHA,
            "review_comments": [],
            "issue_comments": [],
            "valid_locations": [],
        }
    )
    assert preview.items[0].state == "eligible"
    assert preview.items[0].payload == {"body": "Please keep this context."}


def test_preview_blocks_inline_location_missing_from_current_diff() -> None:
    """Do not publish an inline comment at a stale or invalid line."""
    responses = _read_responses()
    responses[3] = CompletedCommand(
        0,
        json.dumps(
            [
                [
                    {
                        "filename": "src/example.py",
                        "patch": "@@ -1,1 +1,1 @@\n-old\n+new\n",
                    }
                ]
            ]
        ),
        "",
    )
    plan = _inline_plan()
    preview = preview_github_publication(
        plan,
        GitHubProvider(identity=plan.identity, runner=RecordingRunner(responses)),
    )

    assert preview.status == "ready"
    assert preview.items[0].state == "blocked"
    assert "current diff" in (preview.items[0].reason or "")


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
        json.dumps([[{"id": 12, "body": "Please keep this context."}]]),
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
        json.dumps([[{"id": 12, "body": "Please keep this context."}]]),
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


@pytest.mark.parametrize(
    "thread_id",
    [
        pytest.param("0012", id="leading-zero"),
        pytest.param("+12", id="sign"),
        pytest.param(" 12", id="leading-space"),
        pytest.param("12 ", id="trailing-space"),
        pytest.param("\u0661\u0662", id="arabic-indic-digits"),
        pytest.param("12/../pulls", id="path-segments"),
    ],
)
def test_reply_target_must_be_a_positive_github_comment_id(thread_id: str) -> None:
    """Block a non-canonical reply target in preview and before any request."""
    plan = _plan_with(_reply(thread_id))
    runner = RecordingRunner(_read_responses())
    provider = GitHubProvider(identity=plan.identity, runner=runner)

    preview = preview_github_publication(plan, provider)

    assert preview.items[0].state == "blocked"
    assert preview.items[0].reason == "reply target is not a GitHub comment ID"
    with pytest.raises(GitHubProviderError, match="positive GitHub comment ID"):
        provider.reply_payload(plan.actions[0])
    with pytest.raises(GitHubProviderError, match="positive GitHub comment ID"):
        provider.post_reply(plan.actions[0])
    assert all("--method" not in call[0] for call in runner.calls)


def test_reply_target_accepts_a_positive_github_comment_id() -> None:
    """Keep a canonical comment ID eligible with its exact reply payload."""
    plan = _plan_with(_reply("12"))
    runner = RecordingRunner(_read_responses())

    preview = preview_github_publication(
        plan, GitHubProvider(identity=plan.identity, runner=runner)
    )

    assert preview.items[0].state == "eligible"
    assert preview.items[0].payload == {"body": "Thanks, I will address this."}


@pytest.mark.parametrize(
    ("approved_digest", "expected_head", "reason"),
    [
        pytest.param(
            "0" * 64,
            HEAD_SHA,
            "approved plan digest does not match current plan",
            id="stale-approved-digest",
        ),
        pytest.param(
            plan_digest(_plan()),
            NEW_HEAD,
            "expected head does not match current plan",
            id="mismatched-expected-head",
        ),
    ],
)
def test_execute_blocks_unapproved_plan_before_any_request(
    approved_digest: str,
    expected_head: str,
    reason: str,
) -> None:
    """Refuse a stale approval or head before reading or posting anything."""
    plan = _plan()
    runner = RecordingRunner(
        [*_read_responses(expected_head), CompletedCommand(0, '{"id": 12}', "")]
    )

    result = execute_github_publication(
        plan=plan,
        approved_plan_digest=approved_digest,
        expected_head=expected_head,
        provider=GitHubProvider(identity=plan.identity, runner=runner),
    )

    assert result.status == "blocked"
    assert result.reason == reason
    assert result.receipt is None
    assert runner.calls == []


@pytest.mark.parametrize(
    ("remote_head", "status", "exit_code"),
    [
        pytest.param(HEAD_SHA, "ready", 0, id="ready"),
        pytest.param(NEW_HEAD, "blocked", 2, id="blocked"),
    ],
)
def test_cli_preview_writes_preview_and_exits_by_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    remote_head: str,
    status: str,
    exit_code: int,
) -> None:
    """Write the preview, print its status, and exit 0 only when ready."""
    _use_runner(monkeypatch, RecordingRunner(_read_responses(remote_head)))
    output = tmp_path / "preview.json"

    code = publish_github_review(
        ["preview", "--plan", str(_plan_file(tmp_path)), "--output", str(output)]
    )

    assert code == exit_code
    assert capsys.readouterr().out == f"{status}\n"
    assert PublicationPreview.model_validate_json(output.read_text()).status == status


def test_cli_execute_requires_receipt_before_any_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Refuse execution without a receipt path and send no request."""
    runner = RecordingRunner()
    _use_runner(monkeypatch, runner)

    code = publish_github_review(_approved_execute(tmp_path))

    assert code == 2
    assert capsys.readouterr().err == "blocked: execute requires --receipt\n"
    assert runner.calls == []


def test_cli_execute_reports_blocked_execution_without_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 2 with the reason and write no receipt when execution is blocked."""
    runner = RecordingRunner(_read_responses(NEW_HEAD))
    _use_runner(monkeypatch, runner)
    receipt_path = tmp_path / "receipt.json"

    code = publish_github_review(
        [*_approved_execute(tmp_path), "--receipt", str(receipt_path)]
    )

    assert code == 2
    assert capsys.readouterr().err == "blocked: remote head changed after approval\n"
    assert not receipt_path.exists()
    assert all("--method" not in call[0] for call in runner.calls)


def test_cli_execute_writes_posted_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 0 and persist the receipt once every request posts."""
    _use_runner(
        monkeypatch,
        RecordingRunner([*_read_responses(), CompletedCommand(0, '{"id": 12}', "")]),
    )
    receipt_path = tmp_path / "receipt.json"

    code = publish_github_review(
        [*_approved_execute(tmp_path), "--receipt", str(receipt_path)]
    )

    assert code == 0
    assert capsys.readouterr().err == ""
    receipt = PublicationReceipt.model_validate_json(receipt_path.read_text())
    assert receipt.status == "posted"
    assert [(item.outcome, item.remote_id) for item in receipt.items] == [
        ("posted", 12)
    ]


@pytest.mark.parametrize(
    ("command", "flag"),
    [
        pytest.param("preview", "--output", id="preview"),
        pytest.param("execute", "--receipt", id="execute"),
    ],
)
def test_cli_blocks_missing_output_directory_before_any_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    flag: str,
) -> None:
    """Block before reading or posting when the output cannot be written."""
    runner = RecordingRunner(
        [*_read_responses(), CompletedCommand(0, '{"id": 12}', "")]
    )
    _use_runner(monkeypatch, runner)
    missing = tmp_path / "missing"
    arguments = (
        _approved_execute(tmp_path)
        if command == "execute"
        else ["preview", "--plan", str(_plan_file(tmp_path))]
    )

    code = publish_github_review([*arguments, flag, str(missing / "out.json")])

    assert code == 2
    assert all("--method" not in call[0] for call in runner.calls)
    assert runner.calls == []
    assert capsys.readouterr().err == (
        f"blocked: {flag} directory must exist and be writable: {missing}\n"
    )


@pytest.mark.parametrize(
    ("review_comments", "states"),
    [
        pytest.param(
            [
                {
                    "id": 21,
                    "body": "Guard the empty case.",
                    "path": "src/example.py",
                    "line": 20,
                    "side": "RIGHT",
                },
                {
                    "id": 22,
                    "body": "Thanks, I will address this.",
                    "in_reply_to_id": 10,
                },
            ],
            ["duplicate", "duplicate"],
            id="exact-remote-comments",
        ),
        pytest.param(
            [
                {
                    "id": 21,
                    "body": "Guard the empty case.",
                    "path": "src/example.py",
                    "line": 20,
                    "side": "LEFT",
                },
                {
                    "id": 22,
                    "body": "Thanks, I will address this.",
                    "in_reply_to_id": 11,
                },
            ],
            ["eligible", "eligible"],
            id="near-miss-remote-comments",
        ),
    ],
)
def test_preview_matches_remote_inline_and_reply_comments(
    review_comments: list[dict[str, object]],
    states: list[str],
) -> None:
    """Treat only exact remote inline comments and replies as duplicates."""
    plan = _plan_with(_inline_plan().actions[0], _reply("10"))
    runner = RecordingRunner(_diff_reads(review_comments))

    preview = preview_github_publication(
        plan, GitHubProvider(identity=plan.identity, runner=runner)
    )

    assert [item.state for item in preview.items] == states


def test_execute_posts_eligible_inline_batch_as_one_review() -> None:
    """Post eligible inline comments as one review pinned to the head."""
    plan = _plan_with(_ranged_inline())
    runner = RecordingRunner([*_diff_reads([]), CompletedCommand(0, '{"id": 31}', "")])

    result = execute_github_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitHubProvider(identity=plan.identity, runner=runner),
    )

    assert result.status == "posted"
    assert result.receipt is not None
    assert [(item.outcome, item.remote_id) for item in result.receipt.items] == [
        ("posted", 31)
    ]
    posts = [call for call in runner.calls if "--method" in call[0]]
    assert len(posts) == 1
    argv, stdin = posts[0]
    assert argv[4] == "repos/acme/ballen-config/pulls/17/reviews"
    assert json.loads(stdin or "") == {
        "commit_id": HEAD_SHA,
        "event": "COMMENT",
        "comments": [
            {
                "path": "src/example.py",
                "line": 20,
                "side": "RIGHT",
                "start_line": 19,
                "start_side": "RIGHT",
                "body": "Guard the empty case.",
            }
        ],
    }


def test_failed_inline_batch_halts_later_items_as_not_attempted() -> None:
    """Stop after a failed review batch and leave later items unattempted."""
    plan = _plan_with(_ranged_inline(), _reply("10"))
    runner = RecordingRunner(
        [
            *_diff_reads([]),
            CompletedCommand(1, "", "validation failed"),
            CompletedCommand(0, '{"id": 13}', ""),
        ]
    )

    result = execute_github_publication(
        plan=plan,
        approved_plan_digest=plan_digest(plan),
        expected_head=HEAD_SHA,
        provider=GitHubProvider(identity=plan.identity, runner=runner),
    )

    assert result.status == "failed"
    assert result.receipt is not None
    assert [(item.action_id, item.outcome) for item in result.receipt.items] == [
        ("R001", "failed"),
        ("R002", "not-attempted"),
    ]
    assert [call[0][4] for call in runner.calls if "--method" in call[0]] == [
        "repos/acme/ballen-config/pulls/17/reviews"
    ]
