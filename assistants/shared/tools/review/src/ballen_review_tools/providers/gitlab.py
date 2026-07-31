"""Read-only GitLab merge-request discussion normalization."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from ballen_review_tools.models import (
    NormalizedReviewThreads,
    NormalizedThread,
    ReviewIdentity,
)

GitLabThreadState = Literal["open", "resolved", "outdated"]


@dataclass(frozen=True)
class GitLabDiffRefs:
    """The three GitLab diff references required for text positions."""

    base_sha: str
    start_sha: str
    head_sha: str

    def __post_init__(self) -> None:
        """Reject incomplete diff references before normalization."""
        if not all((self.base_sha, self.start_sha, self.head_sha)):
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


class GitLabProviderError(ValueError):
    """Bounded GitLab normalization error without raw provider content."""


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


def normalize_gitlab_threads(
    *,
    raw_discussions: list[object],
    identity: ReviewIdentity,
    revisions: GitLabDiffRefs,
) -> NormalizedReviewThreads:
    """Emit provider-neutral threads from captured GitLab discussions."""
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
    for _discussion_index, raw_discussion in enumerate(raw_discussions):
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
        if len(active_notes) != len(notes):
            continue_system_note_only = not active_notes
            if continue_system_note_only:
                continue
        if not active_notes:
            continue
        active_notes.sort(key=lambda note: (note.created_at or "", note.source_index))
        root = active_notes[0]
        position = root.position
        location = _current_position(position, revisions)
        position_outdated = position is not None and (
            position.position_type != "text"
            or position.base_sha != revisions.base_sha
            or position.start_sha != revisions.start_sha
            or position.head_sha != revisions.head_sha
        )
        if position_outdated:
            state: GitLabThreadState = "outdated"
        elif root.resolved or any(note.resolved for note in active_notes):
            state = "resolved"
        else:
            state = "open"
        thread_limitations: list[str] = []
        if position is not None and location is None and not position_outdated:
            thread_limitations.append("GitLab text position is incomplete")
        if position_outdated:
            thread_limitations.append(
                "GitLab text position does not match current diff refs"
            )
        thread_id = str(discussion_id)
        if thread_id in seen_ids:
            raise GitLabProviderError("GitLab discussion IDs must be unique")
        seen_ids.add(thread_id)
        path = PurePosixPath(location[0]) if location is not None else None
        threads.append(
            NormalizedThread(
                thread_id=thread_id,
                comment_ids=tuple(note.note_id for note in active_notes),
                state=state,
                path=path,
                line=location[1] if location is not None else None,
                side=location[2] if location is not None else None,
                author=root.author,
                body=root.body,
                chronology=tuple(note.note_id for note in active_notes),
                limitations=tuple(thread_limitations),
            )
        )
    return NormalizedReviewThreads(
        contract_version="normalized-review-threads/v1",
        identity=identity,
        observed_head=revisions.head_sha,
        limitations=tuple(limitations),
        threads=tuple(threads),
    )
