"""GitHub REST transport and provider-native payload construction."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict

from ballen_review_tools.models import ReviewAction, ReviewCommentPlan, ReviewIdentity
from ballen_review_tools.providers.base import CommandRunner

API_VERSION = "2026-03-10"
_ACCEPT = "Accept: application/vnd.github+json"
_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _diff_locations(path: str, patch: str) -> set[tuple[str, int, str]]:
    """Extract current diff line locations without persisting the patch."""
    locations: set[tuple[str, int, str]] = set()
    old_line: int | None = None
    new_line: int | None = None
    for line in patch.splitlines():
        hunk = _HUNK.match(line)
        if hunk is not None:
            old_line = int(hunk.group(1))
            new_line = int(hunk.group(2))
            continue
        if old_line is None or new_line is None or line.startswith("\\"):
            continue
        if line.startswith("+"):
            locations.add((path, new_line, "RIGHT"))
            new_line += 1
        elif line.startswith("-"):
            locations.add((path, old_line, "LEFT"))
            old_line += 1
        elif line.startswith(" "):
            locations.add((path, old_line, "LEFT"))
            locations.add((path, new_line, "RIGHT"))
            old_line += 1
            new_line += 1
    return locations


class GitHubReviewCommentPayload(TypedDict):
    """Exact GitHub pull-request review comment payload."""

    path: str
    line: int
    side: Literal["LEFT", "RIGHT"]
    body: str
    start_line: NotRequired[int]
    start_side: NotRequired[Literal["LEFT", "RIGHT"]]


class GitHubReviewPayload(TypedDict):
    """Exact batched GitHub review payload."""

    commit_id: str
    event: str
    comments: list[GitHubReviewCommentPayload]


@dataclass(frozen=True)
class GitHubRemoteComment:
    """Minimal normalized GitHub review-comment observation."""

    comment_id: int
    body: str
    path: str | None = None
    line: int | None = None
    side: str | None = None
    start_line: int | None = None
    start_side: str | None = None
    in_reply_to: int | None = None


@dataclass(frozen=True)
class GitHubRemoteIssueComment:
    """Minimal normalized GitHub conversation-comment observation."""

    comment_id: int
    body: str


@dataclass(frozen=True)
class GitHubRemoteState:
    """Current GitHub state needed for preview and deduplication."""

    head_sha: str
    review_comments: tuple[GitHubRemoteComment, ...]
    issue_comments: tuple[GitHubRemoteIssueComment, ...]
    valid_locations: frozenset[tuple[str, int, str]]


class GitHubProviderError(ValueError):
    """Bounded provider or response error without raw response content."""


@dataclass(frozen=True)
class GitHubProvider:
    """Use `gh api` as an injected, no-shell GitHub transport."""

    identity: ReviewIdentity
    runner: CommandRunner
    owner: str | None = None

    def _repository_path(self) -> str:
        """Return owner/repository for GitHub endpoint paths."""
        parts = self.identity.repository.strip("/").split("/")
        if len(parts) == 2 and all(parts):
            return "/".join(parts)
        if self.owner and parts == [self.identity.repository]:
            return f"{self.owner}/{self.identity.repository}"
        raise GitHubProviderError("GitHub identity must include owner/repository")

    def _read(self, endpoint: str, *, paginate: bool = False) -> object:
        """Issue one bounded read request through `gh api`."""
        arguments = ["gh", "api", endpoint]
        if paginate:
            arguments.append("--paginate")
        arguments.extend(
            ["--header", _ACCEPT, "--header", f"X-GitHub-Api-Version: {API_VERSION}"]
        )
        result = self.runner.run(arguments)
        if result.returncode != 0:
            raise GitHubProviderError("GitHub read request failed")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise GitHubProviderError("GitHub returned invalid JSON") from error

    @staticmethod
    def _int(value: object) -> int | None:
        """Return one positive integer field or None."""
        return value if isinstance(value, int) and value > 0 else None

    @classmethod
    def _review_comment(cls, value: object) -> GitHubRemoteComment:
        """Normalize only the fields needed for safe deduplication."""
        if not isinstance(value, dict):
            raise GitHubProviderError("GitHub review comment was malformed")
        comment_id = cls._int(value.get("id"))
        body = value.get("body")
        if comment_id is None or not isinstance(body, str):
            raise GitHubProviderError("GitHub review comment was incomplete")
        return GitHubRemoteComment(
            comment_id=comment_id,
            body=body,
            path=value.get("path") if isinstance(value.get("path"), str) else None,
            line=cls._int(value.get("line")),
            side=value.get("side") if isinstance(value.get("side"), str) else None,
            start_line=cls._int(value.get("start_line")),
            start_side=(
                value.get("start_side")
                if isinstance(value.get("start_side"), str)
                else None
            ),
            in_reply_to=cls._int(value.get("in_reply_to_id")),
        )

    @classmethod
    def _issue_comment(cls, value: object) -> GitHubRemoteIssueComment:
        """Normalize one issue comment without retaining provider data."""
        if not isinstance(value, dict):
            raise GitHubProviderError("GitHub issue comment was malformed")
        comment_id = cls._int(value.get("id"))
        body = value.get("body")
        if comment_id is None or not isinstance(body, str):
            raise GitHubProviderError("GitHub issue comment was incomplete")
        return GitHubRemoteIssueComment(comment_id=comment_id, body=body)

    def fetch_remote_state(self) -> GitHubRemoteState:
        """Fetch the PR head and current comments using read-only calls."""
        root = self._repository_path()
        pull = self._read(f"repos/{root}/pulls/{self.identity.change_number}")
        review_comments = self._read(
            f"repos/{root}/pulls/{self.identity.change_number}/comments",
            paginate=True,
        )
        issue_comments = self._read(
            f"repos/{root}/issues/{self.identity.change_number}/comments",
            paginate=True,
        )
        files = self._read(
            f"repos/{root}/pulls/{self.identity.change_number}/files",
            paginate=True,
        )
        if not isinstance(pull, dict) or not isinstance(pull.get("head"), dict):
            raise GitHubProviderError("GitHub pull request identity was incomplete")
        head_sha = pull["head"].get("sha")
        number = pull.get("number")
        if not isinstance(head_sha, str) or number != self.identity.change_number:
            raise GitHubProviderError("GitHub pull request identity did not match")
        if (
            not isinstance(review_comments, list)
            or not isinstance(issue_comments, list)
            or not isinstance(files, list)
        ):
            raise GitHubProviderError("GitHub comment response was malformed")
        valid_locations: set[tuple[str, int, str]] = set()
        for file in files:
            if not isinstance(file, dict):
                raise GitHubProviderError("GitHub changed-file response was malformed")
            path = file.get("filename")
            patch = file.get("patch")
            if isinstance(path, str) and isinstance(patch, str):
                valid_locations.update(_diff_locations(path, patch))
        return GitHubRemoteState(
            head_sha=head_sha,
            review_comments=tuple(
                self._review_comment(item) for item in review_comments
            ),
            issue_comments=tuple(self._issue_comment(item) for item in issue_comments),
            valid_locations=frozenset(valid_locations),
        )

    def review_payload(
        self,
        *,
        plan: ReviewCommentPlan,
        observed_head: str,
    ) -> GitHubReviewPayload:
        """Build a commit-pinned batch of selected valid inline comments."""
        comments: list[GitHubReviewCommentPayload] = []
        for action in sorted(plan.actions, key=lambda item: item.action_id):
            if not action.selected or action.kind != "inline":
                continue
            if action.validation_state != "valid":
                continue
            if action.path is None or action.line is None or action.side is None:
                raise GitHubProviderError("selected inline action has no location")
            comment: GitHubReviewCommentPayload = {
                "path": action.path.as_posix(),
                "line": action.line,
                "side": action.side,
                "body": action.body,
            }
            if action.start_line is not None and action.start_side is not None:
                comment["start_line"] = action.start_line
                comment["start_side"] = action.start_side
            comments.append(comment)
        return {
            "commit_id": observed_head,
            "event": "COMMENT",
            "comments": comments,
        }

    def issue_comment_payload(self, action: ReviewAction) -> dict[str, str]:
        """Build a top-level pull-request conversation payload."""
        if action.kind != "general":
            raise GitHubProviderError("issue comment requires general action")
        return {"body": action.body}

    def reply_payload(self, action: ReviewAction) -> dict[str, str]:
        """Build a native review-comment reply payload."""
        if action.kind != "reply" or not action.thread_id:
            raise GitHubProviderError("reply requires a native thread target")
        return {"body": action.body}

    def _post(self, endpoint: str, payload: Mapping[str, object]) -> object:
        """Post one exact JSON request through standard input."""
        arguments = [
            "gh",
            "api",
            "--method",
            "POST",
            endpoint,
            "--input",
            "-",
            "--header",
            _ACCEPT,
            "--header",
            f"X-GitHub-Api-Version: {API_VERSION}",
        ]
        result = self.runner.run(
            arguments, input_text=json.dumps(payload, sort_keys=True)
        )
        if result.returncode != 0:
            raise GitHubProviderError("GitHub mutation request failed")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise GitHubProviderError(
                "GitHub mutation returned invalid JSON"
            ) from error

    def post_review(self, payload: GitHubReviewPayload) -> object:
        """Post one batched inline review payload."""
        return self._post(
            f"repos/{self._repository_path()}/pulls/{self.identity.change_number}/reviews",
            payload,
        )

    def post_issue_comment(self, action: ReviewAction) -> object:
        """Post one top-level conversation comment."""
        return self._post(
            f"repos/{self._repository_path()}/issues/{self.identity.change_number}/comments",
            self.issue_comment_payload(action),
        )

    def post_reply(self, action: ReviewAction) -> object:
        """Post one reply to a top-level review comment."""
        if action.thread_id is None:
            raise GitHubProviderError("reply requires thread_id")
        return self._post(
            f"repos/{self._repository_path()}/pulls/comments/{action.thread_id}/replies",
            self.reply_payload(action),
        )
