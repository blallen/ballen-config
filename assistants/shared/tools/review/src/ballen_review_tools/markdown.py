"""Deterministic parser for human-editable review Markdown."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, get_args

from pydantic import ValidationError

from ballen_review_tools.canonical import deduplication_key
from ballen_review_tools.models import (
    INTENDED_ACTION_BY_KIND,
    NormalizedReviewThreads,
    ResponseAction,
    ResponseClassification,
    ReviewAction,
    ReviewDiagnostic,
    ReviewIdentity,
    ReviewResponseItem,
)

_HEADING: Final[re.Pattern[str]] = re.compile(
    r"^###\s+([A-Za-z0-9][A-Za-z0-9._-]*):\s+(.+?)\s*$"
)
_FIELD: Final[re.Pattern[str]] = re.compile(r"^\*\*([^*]+):\*\*\s*(.*?)\s*$")
_KNOWN_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "Type",
        "File",
        "Line",
        "Side",
        "Start line",
        "Start side",
        "Discussion",
        "Thread",
        "POST",
        "Classification",
        "Selected action",
        "Evaluation",
        "Evidence",
        "Proposed changes",
        "Proposed response",
        "Verification",
    }
)
_FENCE: Final[re.Pattern[str]] = re.compile(r"^ {0,3}(`{3,}|~{3,})")


@dataclass(frozen=True)
class ParsedReview:
    """Valid actions and bounded diagnostics from one Markdown draft."""

    actions: tuple[ReviewAction, ...]
    diagnostics: tuple[ReviewDiagnostic, ...]


def _sections(lines: list[str]) -> Iterable[tuple[str, list[str], str | None]]:
    """Yield action IDs and bodies from level-three headings outside fences.

    A heading without a stable ID is yielded as ``line N``, with a heading
    error. The space keeps that label outside the heading ID grammar, so it
    never collides with a real action ID.
    """
    current_id: str | None = None
    current_lines: list[str] = []
    heading_error: str | None = None
    fence_character: str | None = None
    fence_length = 0
    for line_number, line in enumerate(lines, start=1):
        fence = _FENCE.match(line)
        if fence is not None:
            marker = fence.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = None
                fence_length = 0
            if current_id is not None:
                current_lines.append(line)
            continue
        if fence_character is None:
            match = _HEADING.match(line)
            if match is not None:
                if current_id is not None:
                    yield current_id, current_lines, heading_error
                current_id = match.group(1)
                current_lines = []
                heading_error = None
                continue
            if line.startswith("### "):
                if current_id is not None:
                    yield current_id, current_lines, heading_error
                current_id = f"line {line_number}"
                current_lines = []
                heading_error = "action heading must contain a stable ID"
                continue
        if current_id is not None:
            current_lines.append(line)
    if fence_character is not None:
        unclosed_fence = "unclosed fenced block"
        if current_id is None:
            yield "document", [], unclosed_fence
            return
        heading_error = (
            unclosed_fence
            if heading_error is None
            else f"{heading_error}; {unclosed_fence}"
        )
    if current_id is not None:
        yield current_id, current_lines, heading_error


def _metadata_and_body(lines: list[str]) -> tuple[dict[str, str], str]:
    """Split the leading block of bold metadata fields from the Markdown body.

    The field block ends at the first blank or non-field line after a field, so
    body text that starts with bold text stays in the body. A body that starts
    with a known field is rejected, because that field was meant as metadata.
    """
    metadata: dict[str, str] = {}
    body_lines: list[str] = []
    metadata_mode = True
    for line in lines:
        match = _FIELD.match(line) if metadata_mode else None
        if match is not None:
            key, value = match.groups()
            if key not in _KNOWN_FIELDS:
                raise ValueError(f"unknown metadata field: {key}")
            if key in metadata:
                raise ValueError(f"duplicate metadata field: {key}")
            metadata[key] = value.strip().strip("`").strip()
            continue
        if metadata_mode and not metadata and not line.strip():
            continue
        metadata_mode = False
        body_lines.append(line)
    late_field = _FIELD.match(next((line for line in body_lines if line.strip()), ""))
    if late_field is not None and late_field.group(1) in _KNOWN_FIELDS:
        raise ValueError(
            "metadata field must come before the first blank line: "
            f"{late_field.group(1)}"
        )
    return metadata, "\n".join(body_lines).strip()


def _required(metadata: dict[str, str], key: str) -> str:
    """Return required metadata or raise a bounded parse error."""
    value = metadata.get(key)
    if value is None or not value:
        raise ValueError(f"missing metadata field: {key}")
    return value


def _line(metadata: dict[str, str], key: str) -> int | None:
    """Parse one optional positive source line."""
    value = metadata.get(key)
    if value is None:
        return None
    try:
        line = int(value)
    except ValueError as error:
        raise ValueError(f"{key} must be an integer") from error
    if line <= 0:
        raise ValueError(f"{key} must be positive")
    return line


def _validation_reason(error: ValidationError) -> str:
    """Describe a model validation failure without echoing its input."""
    return "; ".join(
        f"{'.'.join(str(part) for part in detail['loc'])}: {detail['msg']}"
        if detail["loc"]
        else detail["msg"]
        for detail in error.errors(include_url=False, include_input=False)
    )


def parse_review_markdown(
    text: str,
    *,
    identity: ReviewIdentity,
) -> ParsedReview:
    """Parse all review actions, retaining selected and skipped items.

    Args:
        text: Human-editable review Markdown.
        identity: Provider and change identity used for deduplication keys.

    Returns:
        Parsed logical actions in document order.

    Malformed sections are retained as bounded diagnostics so one bad section
    does not hide later review coverage.
    """
    actions: list[ReviewAction] = []
    diagnostics: list[ReviewDiagnostic] = []
    seen_ids: set[str] = set()
    for action_id, lines, heading_error in _sections(text.splitlines()):
        if action_id in seen_ids:
            diagnostics.append(
                ReviewDiagnostic(
                    action_id=action_id,
                    reason=f"duplicate action ID: {action_id}",
                )
            )
            continue
        seen_ids.add(action_id)
        if heading_error is not None:
            diagnostics.append(
                ReviewDiagnostic(action_id=action_id, reason=heading_error)
            )
            continue
        try:
            metadata, body = _metadata_and_body(lines)
            if not body:
                raise ValueError("empty body")
            kind = _required(metadata, "Type").strip().lower()
            intended = INTENDED_ACTION_BY_KIND.get(kind)
            if intended is None:
                raise ValueError(f"unsupported action type: {kind}")
            selected_value = _required(metadata, "POST").strip().lower()
            if selected_value not in {"yes", "no"}:
                raise ValueError("POST must be YES or NO")
            path = metadata.get("File")
            line = _line(metadata, "Line")
            start_line = _line(metadata, "Start line")
            side = metadata.get("Side")
            start_side = metadata.get("Start side")
            discussion = metadata.get("Discussion")
            thread = metadata.get("Thread")
            if discussion is not None and thread is not None:
                raise ValueError("Discussion and Thread are ambiguous")
            thread_id = discussion or thread
            if thread_id is not None and thread_id.lower() in {"none", "null", "-"}:
                thread_id = None
            action = ReviewAction.model_validate(
                {
                    "action_id": action_id,
                    "kind": kind,
                    "selected": selected_value == "yes",
                    "body": body,
                    "path": path,
                    "line": line,
                    "side": side,
                    "start_line": start_line,
                    "start_side": start_side,
                    "thread_id": thread_id,
                    "deduplication_key": deduplication_key(
                        provider=identity.provider,
                        host=identity.host,
                        repository=identity.repository,
                        change_number=identity.change_number,
                        kind=kind,
                        body=body,
                        path=path,
                        line=line,
                        side=side,
                        start_line=start_line,
                        start_side=start_side,
                        thread_id=thread_id,
                    ),
                    "validation_state": "valid",
                    "intended_action": intended,
                    "outcome": "pending",
                }
            )
        except ValidationError as error:
            diagnostics.append(
                ReviewDiagnostic(action_id=action_id, reason=_validation_reason(error))
            )
            continue
        except (TypeError, ValueError) as error:
            diagnostics.append(ReviewDiagnostic(action_id=action_id, reason=str(error)))
            continue
        actions.append(action)
    if not actions and not diagnostics:
        diagnostics.append(
            ReviewDiagnostic(
                action_id="document", reason="review contains no action headings"
            )
        )
    return ParsedReview(actions=tuple(actions), diagnostics=tuple(diagnostics))


def _optional_text(metadata: dict[str, str], key: str) -> str | None:
    """Return one optional response field, treating `none` as absent."""
    value = metadata.get(key)
    if value is None or value.lower() in {"", "none", "null", "-"}:
        return None
    return value


def _list_field(metadata: dict[str, str], key: str) -> tuple[str, ...]:
    """Return one bounded single-line list field."""
    value = _optional_text(metadata, key)
    return () if value is None else (value,)


def parse_response_markdown(
    text: str,
    *,
    threads: NormalizedReviewThreads,
) -> tuple[ReviewResponseItem, ...]:
    """Parse a response draft into one item per normalized thread.

    Args:
        text: Human-editable response Markdown with one `### <thread-id>:`
            section per answered thread.
        threads: Validated normalized threads that the draft answers.

    Returns:
        One response item per normalized thread, in thread order. A resolved
        thread without a section becomes a `skip` item classified `resolved`.

    Raises:
        ValueError: If a heading has no thread ID, a section names an unknown
            or repeated thread, a field is unknown, repeated, or missing, a
            classification or action is unsupported, a section gives the
            proposed response both as a field and as text, an item fails model
            validation, or a thread that is not resolved has no section.
    """
    thread_by_id = {thread.thread_id: thread for thread in threads.threads}
    items: dict[str, ReviewResponseItem] = {}
    for thread_id, lines, heading_error in _sections(text.splitlines()):
        if heading_error is not None:
            raise ValueError(f"{thread_id}: {heading_error}")
        if thread_id not in thread_by_id:
            raise ValueError(f"response references unknown thread: {thread_id}")
        metadata, body = _metadata_and_body(lines)
        if body and "Proposed response" in metadata:
            raise ValueError(
                f"{thread_id}: Proposed response field and section text are ambiguous"
            )
        classification = _required(metadata, "Classification").strip().lower()
        if classification not in get_args(ResponseClassification):
            raise ValueError(f"unsupported response classification: {classification}")
        selected_action = _required(metadata, "Selected action").strip().lower()
        if selected_action not in get_args(ResponseAction):
            raise ValueError(f"unsupported response action: {selected_action}")
        if thread_id in items:
            raise ValueError(f"duplicate response thread: {thread_id}")
        items[thread_id] = ReviewResponseItem.model_validate(
            {
                "thread_id": thread_id,
                "classification": classification,
                "evaluation": _required(metadata, "Evaluation"),
                "evidence": _required(metadata, "Evidence"),
                "proposed_changes": _list_field(metadata, "Proposed changes"),
                "proposed_response": (
                    body or _optional_text(metadata, "Proposed response")
                ),
                "verification": _list_field(metadata, "Verification"),
                "selected_action": selected_action,
            }
        )
    missing = [
        thread.thread_id
        for thread in threads.threads
        if thread.thread_id not in items and thread.state != "resolved"
    ]
    if missing:
        raise ValueError(
            f"response draft omits unresolved threads: {', '.join(missing)}"
        )
    for thread in threads.threads:
        if thread.thread_id not in items:
            items[thread.thread_id] = ReviewResponseItem(
                thread_id=thread.thread_id,
                classification="resolved",
                evaluation="No response decision was supplied.",
                evidence="Thread retained as missing response coverage.",
                selected_action="skip",
            )
    return tuple(items[thread.thread_id] for thread in threads.threads)
