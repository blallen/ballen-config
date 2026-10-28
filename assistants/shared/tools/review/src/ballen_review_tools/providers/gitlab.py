"""GitLab merge-request transport, payloads, and discussion normalization."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal, NamedTuple, NotRequired, TypedDict
from urllib.parse import quote

from ballen_review_tools.models import (
    NormalizedReviewThreads,
    NormalizedThread,
    ReviewAction,
    ReviewIdentity,
    ReviewSide,
    truncate_thread_body,
)
from ballen_review_tools.providers.base import CommandRunner, failure_detail
from ballen_review_tools.providers.diff import hunk_lines

GitLabThreadState = Literal["open", "resolved", "outdated"]
DiffLineKey = tuple[str, int, ReviewSide]


class DiffLine(NamedTuple):
    """GitLab position fields for one commentable line of the current MR diff."""

    old_path: str
    new_path: str
    old_line: int | None
    new_line: int | None


@dataclass(frozen=True)
class GitLabDiffRefs:
    """The three GitLab diff references required for text positions."""

    base_sha: str
    start_sha: str
    head_sha: str

    def __post_init__(self) -> None:
        """Reject incomplete diff references before normalization."""
        if not all(
            isinstance(value, str) and value
            for value in (self.base_sha, self.start_sha, self.head_sha)
        ):
            raise GitLabProviderError("GitLab diff refs are incomplete")


@dataclass(frozen=True)
class _GitLabPosition:
    """Provider-native text position retained only during normalization."""

    position_type: str | None
    base_sha: str | None
    start_sha: str | None
    head_sha: str | None
    old_path: str | None
    new_path: str | None
    old_line: int | None
    new_line: int | None


@dataclass(frozen=True)
class _GitLabNote:
    """Minimal provider-native note observation."""

    note_id: str
    body: str
    author: str
    created_at: str | None
    system: bool
    resolved: bool
    position: _GitLabPosition | None
    source_index: int


@dataclass(frozen=True)
class GitLabRemoteDiscussion:
    """Minimal native discussion observation used for preview gates."""

    discussion_id: str
    notes: tuple[_GitLabNote, ...]


@dataclass(frozen=True)
class GitLabRemoteState:
    """Current GitLab diff refs, discussions, overview notes, and diff lines.

    Attributes:
        diff_lines: Every commentable `(path, line, side)` in the current MR
            diff, mapped to the GitLab paths and line numbers that a
            discussion position on that line must send.
    """

    diff_refs: GitLabDiffRefs
    discussions: tuple[GitLabRemoteDiscussion, ...]
    notes: tuple[_GitLabNote, ...]
    diff_lines: Mapping[DiffLineKey, DiffLine]


class GitLabPositionPayload(TypedDict):
    """Exact GitLab text-position fields for a diff discussion."""

    position_type: Literal["text"]
    base_sha: str
    head_sha: str
    start_sha: str
    old_path: str
    new_path: str
    old_line: NotRequired[int]
    new_line: NotRequired[int]


class GitLabDiscussionPayload(TypedDict):
    """Exact GitLab discussion creation payload."""

    body: str
    position: NotRequired[GitLabPositionPayload]


class GitLabProviderError(ValueError):
    """Bounded GitLab provider or response error without a raw response body."""


def _string(value: object) -> str | None:
    """Return one non-empty string field."""
    return value if isinstance(value, str) and value else None


def _positive_int(value: object) -> int | None:
    """Return one positive line number."""
    return value if isinstance(value, int) and value > 0 else None


def _position(value: object) -> _GitLabPosition | None:
    """Normalize a GitLab position without asserting it is current."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise GitLabProviderError("GitLab discussion position was malformed")
    return _GitLabPosition(
        position_type=_string(value.get("position_type")),
        base_sha=_string(value.get("base_sha")),
        start_sha=_string(value.get("start_sha")),
        head_sha=_string(value.get("head_sha")),
        old_path=_string(value.get("old_path")),
        new_path=_string(value.get("new_path")),
        old_line=_positive_int(value.get("old_line")),
        new_line=_positive_int(value.get("new_line")),
    )


def _note(value: object, source_index: int, *, resolved: bool) -> _GitLabNote:
    """Normalize the bounded fields of one GitLab discussion note."""
    if not isinstance(value, Mapping):
        raise GitLabProviderError("GitLab discussion note was malformed")
    note_id = value.get("id")
    body = value.get("body")
    if not isinstance(note_id, (int, str)) or not str(note_id):
        raise GitLabProviderError("GitLab discussion note ID was incomplete")
    if not isinstance(body, str) or not body:
        raise GitLabProviderError("GitLab discussion note body was incomplete")
    author_value = value.get("author")
    author = "unknown"
    if isinstance(author_value, Mapping):
        author = (
            _string(author_value.get("username"))
            or _string(author_value.get("name"))
            or author
        )
    return _GitLabNote(
        note_id=str(note_id),
        body=body,
        author=author,
        created_at=_string(value.get("created_at")),
        system=value.get("system") is True,
        resolved=resolved or value.get("resolved") is True,
        position=_position(value.get("position")),
        source_index=source_index,
    )


def _current_position(
    position: _GitLabPosition | None,
    revisions: GitLabDiffRefs,
) -> tuple[str, int, Literal["LEFT", "RIGHT"]] | None:
    """Project a current GitLab text position onto the shared location shape."""
    if position is None:
        return None
    if position.position_type != "text":
        return None
    if (
        position.base_sha != revisions.base_sha
        or position.start_sha != revisions.start_sha
        or position.head_sha != revisions.head_sha
    ):
        return None
    if position.new_line is not None and position.new_path is not None:
        return position.new_path, position.new_line, "RIGHT"
    if position.old_line is not None and position.old_path is not None:
        return position.old_path, position.old_line, "LEFT"
    return None


def _discussion(value: object) -> GitLabRemoteDiscussion:
    """Normalize one captured GitLab discussion for preview and deduplication."""
    if not isinstance(value, Mapping):
        raise GitLabProviderError("GitLab discussion was malformed")
    discussion_id = value.get("id")
    raw_notes = value.get("notes")
    if not isinstance(discussion_id, (int, str)) or not str(discussion_id):
        raise GitLabProviderError("GitLab discussion ID was incomplete")
    if not isinstance(raw_notes, list) or not raw_notes:
        raise GitLabProviderError("GitLab discussion notes were incomplete")
    resolved = value.get("resolved") is True
    notes = tuple(
        _note(note, note_index, resolved=resolved)
        for note_index, note in enumerate(raw_notes)
    )
    return GitLabRemoteDiscussion(
        discussion_id=str(discussion_id),
        notes=notes,
    )


def _diff_line_map(
    old_path: str,
    new_path: str,
    diff: str,
) -> dict[DiffLineKey, DiffLine]:
    """Map each commentable line of one file diff to its GitLab position.

    Args:
        old_path: File path before the change.
        new_path: File path after the change.
        diff: Unified diff hunks for the file, empty when GitLab omits them.

    Returns:
        A map from `(path, line, side)` to the file's old and new paths and the
        GitLab `old_line` and `new_line`. An added line maps on the right only,
        a removed line on the left only, and an unchanged context line on both
        sides with both numbers. Text before the first hunk and
        `\\ No newline at end of file` markers advance neither line counter.
    """
    lines: dict[DiffLineKey, DiffLine] = {}
    for line in hunk_lines(diff):
        entry = DiffLine(old_path, new_path, line.old_line, line.new_line)
        if line.new_line is not None:
            lines[(new_path, line.new_line, "RIGHT")] = entry
        if line.old_line is not None:
            lines[(old_path, line.old_line, "LEFT")] = entry
    return lines


def _diff_lines(value: object) -> dict[DiffLineKey, DiffLine]:
    """Combine the diff line maps of every file in a GitLab MR diffs response.

    Args:
        value: Decoded `merge_requests/:iid/diffs` response.

    Returns:
        The combined line map. A file whose diff text GitLab omitted, such as a
        too-large or collapsed file, contributes no lines.

    Raises:
        GitLabProviderError: If the response or one of its files is malformed.
    """
    if not isinstance(value, list):
        raise GitLabProviderError("GitLab diff response was malformed")
    lines: dict[DiffLineKey, DiffLine] = {}
    for item in value:
        if not isinstance(item, Mapping):
            raise GitLabProviderError("GitLab diff response was malformed")
        old_path = item.get("old_path")
        new_path = item.get("new_path")
        diff = item.get("diff")
        if not (
            isinstance(old_path, str)
            and isinstance(new_path, str)
            and isinstance(diff, str)
        ):
            raise GitLabProviderError("GitLab diff response was malformed")
        lines.update(_diff_line_map(old_path, new_path, diff))
    return lines


class GitLabProvider:
    """Use `glab api` as an injected, no-shell GitLab transport."""

    def __init__(self, *, identity: ReviewIdentity, runner: CommandRunner) -> None:
        """Store the provider identity and a compatible command runner."""
        if identity.provider != "gitlab":
            raise GitLabProviderError("GitLab provider requires a GitLab identity")
        self.identity = identity
        self._runner = runner

    def _repository_path(self) -> str:
        """Return the URL-encoded namespaced GitLab project path."""
        return quote(self.identity.repository.strip("/"), safe="")

    def _read(self, endpoint: str, *, paginate: bool = False) -> object:
        """Issue one bounded read request through `glab api`."""
        arguments = ["glab", "api", endpoint]
        if paginate:
            arguments.append("--paginate")
        result = self._runner.run(arguments)
        if result.returncode != 0:
            raise GitLabProviderError(
                f"GitLab read request failed: {failure_detail(result)}"
            )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise GitLabProviderError("GitLab returned invalid JSON") from error

    def _post(self, endpoint: str, payload: Mapping[str, object]) -> object:
        """Post one exact JSON request through standard input."""
        arguments = [
            "glab",
            "api",
            "--method",
            "POST",
            endpoint,
            "--header",
            "Content-Type: application/json",
            "--input",
            "-",
        ]
        result = self._runner.run(
            arguments,
            input_text=json.dumps(payload, sort_keys=True),
        )
        if result.returncode != 0:
            raise GitLabProviderError(
                f"GitLab mutation request failed: {failure_detail(result)}"
            )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise GitLabProviderError(
                "GitLab mutation returned invalid JSON"
            ) from error

    def fetch_remote_state(self) -> GitLabRemoteState:
        """Fetch the current MR diff refs, discussions, notes, and diff lines."""
        root = (
            f"projects/{self._repository_path()}"
            f"/merge_requests/{self.identity.change_number}"
        )
        merge_request = self._read(root)
        discussions = self._read(f"{root}/discussions", paginate=True)
        notes = self._read(f"{root}/notes", paginate=True)
        diffs = self._read(f"{root}/diffs", paginate=True)
        if not isinstance(merge_request, Mapping):
            raise GitLabProviderError("GitLab merge request response was malformed")
        if merge_request.get("iid") != self.identity.change_number:
            raise GitLabProviderError("GitLab merge request identity did not match")
        raw_refs = merge_request.get("diff_refs")
        if not isinstance(raw_refs, Mapping):
            raise GitLabProviderError("GitLab diff refs are incomplete")

        def _ref(name: str) -> str:
            value = raw_refs.get(name)
            if not isinstance(value, str) or not value:
                raise GitLabProviderError("GitLab diff refs are incomplete")
            return value

        if not isinstance(discussions, list) or not isinstance(notes, list):
            raise GitLabProviderError("GitLab discussion response was malformed")
        refs = GitLabDiffRefs(
            base_sha=_ref("base_sha"),
            start_sha=_ref("start_sha"),
            head_sha=_ref("head_sha"),
        )
        return GitLabRemoteState(
            diff_refs=refs,
            discussions=tuple(_discussion(item) for item in discussions),
            notes=tuple(
                _note(item, note_index, resolved=False)
                for note_index, item in enumerate(notes)
            ),
            diff_lines=_diff_lines(diffs),
        )

    @staticmethod
    def diff_line(
        action: ReviewAction,
        state: GitLabRemoteState,
    ) -> DiffLine | None:
        """Look up an inline action's line in the current MR diff.

        Args:
            action: Inline review action.
            state: Current GitLab state with its diff line map.

        Returns:
            The GitLab paths and line numbers for the action's path, line, and
            side, or `None` when the current MR diff does not contain it.
        """
        if action.path is None or action.line is None or action.side is None:
            return None
        return state.diff_lines.get((action.path.as_posix(), action.line, action.side))

    def discussion_payload(
        self,
        action: ReviewAction,
        state: GitLabRemoteState,
    ) -> GitLabDiscussionPayload:
        """Build an MR discussion payload with a current text position.

        Args:
            action: Single-line inline review action.
            state: Current GitLab state with diff refs and diff lines.

        Returns:
            The discussion payload. Its position sends `new_line` for an added
            line, `old_line` for a removed line, and both for a context line.

        Raises:
            GitLabProviderError: If the action is not inline, is a line range,
                or targets a line absent from the current MR diff.
        """
        if action.kind != "inline":
            raise GitLabProviderError("discussion payload requires inline action")
        if action.path is None or action.line is None or action.side is None:
            raise GitLabProviderError("inline action has no complete GitLab position")
        if action.start_line is not None:
            raise GitLabProviderError("GitLab line ranges require native line codes")
        line = self.diff_line(action, state)
        if line is None:
            raise GitLabProviderError(
                "inline location is not present in the current GitLab diff"
            )
        position: GitLabPositionPayload = {
            "position_type": "text",
            "base_sha": state.diff_refs.base_sha,
            "head_sha": state.diff_refs.head_sha,
            "start_sha": state.diff_refs.start_sha,
            "old_path": line.old_path,
            "new_path": line.new_path,
        }
        if line.old_line is not None:
            position["old_line"] = line.old_line
        if line.new_line is not None:
            position["new_line"] = line.new_line
        return {"body": action.body, "position": position}

    @staticmethod
    def note_payload(action: ReviewAction) -> dict[str, str]:
        """Build a top-level MR note payload."""
        if action.kind != "general":
            raise GitLabProviderError("note payload requires general action")
        return {"body": action.body}

    @staticmethod
    def reply_payload(action: ReviewAction) -> dict[str, str]:
        """Build a discussion reply payload without a resolution field."""
        if action.kind != "reply" or not action.thread_id:
            raise GitLabProviderError("reply payload requires discussion ID")
        return {"body": action.body}

    def post_discussion(
        self,
        action: ReviewAction,
        state: GitLabRemoteState,
    ) -> object:
        """Create one native MR discussion."""
        root = (
            f"projects/{self._repository_path()}"
            f"/merge_requests/{self.identity.change_number}/discussions"
        )
        return self._post(root, self.discussion_payload(action, state))

    def post_note(self, action: ReviewAction) -> object:
        """Create one top-level MR note."""
        root = (
            f"projects/{self._repository_path()}"
            f"/merge_requests/{self.identity.change_number}/notes"
        )
        return self._post(root, self.note_payload(action))

    def post_reply(self, action: ReviewAction) -> object:
        """Add one note to an existing native discussion."""
        if action.thread_id is None:
            raise GitLabProviderError("reply requires discussion ID")
        discussion_id = quote(action.thread_id, safe="")
        root = (
            f"projects/{self._repository_path()}"
            f"/merge_requests/{self.identity.change_number}"
            f"/discussions/{discussion_id}/notes"
        )
        return self._post(root, self.reply_payload(action))


def normalize_gitlab_threads(
    *,
    raw_discussions: list[object],
    identity: ReviewIdentity,
    revisions: GitLabDiffRefs,
) -> NormalizedReviewThreads:
    """Normalize captured GitLab discussions into provider-neutral threads.

    System notes are excluded, so a discussion with only system notes yields no
    thread. The earliest remaining note is the root. A position made against
    other diff refs makes the thread `outdated`, which outranks `resolved`;
    otherwise any resolved note makes it `resolved`, and it is `open` if none
    is. An image or file position on the current diff refs keeps that state
    without a line. A root body over the thread limit is truncated.

    Args:
        raw_discussions: Every captured GitLab discussion, all pages combined.
        identity: GitLab review identity the discussions belong to.
        revisions: Current merge-request diff refs.

    Returns:
        Provider-neutral threads keyed by discussion ID.

    Raises:
        GitLabProviderError: If the identity is not a GitLab identity, its base
            or head differs from the diff refs, a discussion or note is
            malformed, or two discussions share an ID.
    """
    if identity.provider != "gitlab":
        raise GitLabProviderError("GitLab normalization requires a GitLab identity")
    if (
        identity.base_revision != revisions.base_sha
        or identity.head_revision != revisions.head_sha
    ):
        raise GitLabProviderError("GitLab diff refs do not match review identity")

    limitations = [
        "GitLab pagination must be assembled by the caller before normalization",
        "System notes are excluded from normalized discussions",
        "The shared location keeps one current old-side or new-side text position",
    ]
    threads: list[NormalizedThread] = []
    seen_ids: set[str] = set()
    for raw_discussion in raw_discussions:
        if not isinstance(raw_discussion, Mapping):
            raise GitLabProviderError("GitLab discussion was malformed")
        discussion_id = raw_discussion.get("id")
        raw_notes = raw_discussion.get("notes")
        if not isinstance(discussion_id, (int, str)) or not str(discussion_id):
            raise GitLabProviderError("GitLab discussion ID was incomplete")
        if not isinstance(raw_notes, list) or not raw_notes:
            raise GitLabProviderError("GitLab discussion notes were incomplete")
        discussion_resolved = raw_discussion.get("resolved") is True
        notes = [
            _note(note, note_index, resolved=discussion_resolved)
            for note_index, note in enumerate(raw_notes)
        ]
        active_notes = [note for note in notes if not note.system]
        if not active_notes:
            continue
        active_notes.sort(key=lambda note: (note.created_at or "", note.source_index))
        root = active_notes[0]
        position = root.position
        location = _current_position(position, revisions)
        position_outdated = position is not None and (
            position.base_sha != revisions.base_sha
            or position.start_sha != revisions.start_sha
            or position.head_sha != revisions.head_sha
        )
        if position_outdated:
            state: GitLabThreadState = "outdated"
        elif any(note.resolved for note in active_notes):
            state = "resolved"
        else:
            state = "open"
        thread_limitations: list[str] = []
        if position_outdated:
            thread_limitations.append(
                "GitLab position does not match current diff refs"
            )
        elif position is not None and position.position_type in ("image", "file"):
            thread_limitations.append(
                "GitLab image or file discussion has no line position"
            )
        elif position is not None and location is None:
            thread_limitations.append("GitLab text position is incomplete")
        thread_id = str(discussion_id)
        if thread_id in seen_ids:
            raise GitLabProviderError("GitLab discussion IDs must be unique")
        seen_ids.add(thread_id)
        path = PurePosixPath(location[0]) if location is not None else None
        body, body_limitations = truncate_thread_body(root.body)
        threads.append(
            NormalizedThread(
                thread_id=thread_id,
                comment_ids=tuple(note.note_id for note in active_notes),
                state=state,
                path=path,
                line=location[1] if location is not None else None,
                side=location[2] if location is not None else None,
                author=root.author,
                body=body,
                chronology=tuple(note.note_id for note in active_notes),
                limitations=(*thread_limitations, *body_limitations),
            )
        )
    return NormalizedReviewThreads(
        contract_version="normalized-review-threads/v1",
        identity=identity,
        observed_head=revisions.head_sha,
        limitations=tuple(limitations),
        threads=tuple(threads),
    )
