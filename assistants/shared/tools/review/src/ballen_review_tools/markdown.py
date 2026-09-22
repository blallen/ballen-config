"""Deterministic parser for human-editable review Markdown."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, cast

from ballen_review_tools.canonical import deduplication_key
from ballen_review_tools.models import (
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
    """Yield action IDs and bodies from level-three headings outside fences."""
    current_id: str | None = None
    current_lines: list[str] = []
    heading_error: str | None = None
    fence_character: str | None = None
    fence_length = 0
    section_number = 0
    for line in lines:
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
                section_number += 1
                current_id = f"section-{section_number}"
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
    """Split leading bold metadata from the Markdown body."""
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
        if metadata_mode and not line.strip():
            continue
        metadata_mode = False
        body_lines.append(line)
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
            if kind not in {"inline", "general", "reply"}:
                raise ValueError(f"unsupported action type: {kind}")
            selected_value = _required(metadata, "POST").strip().lower()
            if selected_value not in {"yes", "no"}:
                raise ValueError("POST must be YES or NO")
            path_text = metadata.get("File")
            path = None if path_text is None else path_text
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
            intended = {
                "inline": "create-inline",
                "general": "create-general",
                "reply": "reply",
            }[kind]
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
    """Parse response decisions while retaining every normalized thread."""
    thread_by_id = {thread.thread_id: thread for thread in threads.threads}
    items: dict[str, ReviewResponseItem] = {}
    for thread_id, lines, heading_error in _sections(text.splitlines()):
        if heading_error is not None:
            raise ValueError(f"{thread_id}: {heading_error}")
        if thread_id not in thread_by_id:
            raise ValueError(f"response references unknown thread: {thread_id}")
        metadata, _body = _metadata_and_body(lines)
        classification = _required(metadata, "Classification").strip().lower()
        if classification not in {
            "actionable",
            "question",
            "discussion",
            "resolved",
            "informational",
        }:
            raise ValueError(f"unsupported response classification: {classification}")
        selected_action = _required(metadata, "Selected action").strip().lower()
        if selected_action not in {"skip", "propose-change", "propose-response"}:
            raise ValueError(f"unsupported response action: {selected_action}")
        if thread_id in items:
            raise ValueError(f"duplicate response thread: {thread_id}")
        items[thread_id] = ReviewResponseItem(
            thread_id=thread_id,
            classification=cast(ResponseClassification, classification),
            evaluation=_required(metadata, "Evaluation"),
            evidence=_required(metadata, "Evidence"),
            proposed_changes=_list_field(metadata, "Proposed changes"),
            proposed_response=_optional_text(metadata, "Proposed response"),
            verification=_list_field(metadata, "Verification"),
            selected_action=cast(ResponseAction, selected_action),
        )
    for thread in threads.threads:
        if thread.thread_id not in items:
            classification = (
                "resolved" if thread.state == "resolved" else "informational"
            )
            items[thread.thread_id] = ReviewResponseItem(
                thread_id=thread.thread_id,
                classification=cast(ResponseClassification, classification),
                evaluation="No response decision was supplied.",
                evidence="Thread retained as missing response coverage.",
                selected_action="skip",
            )
    return tuple(items[thread.thread_id] for thread in threads.threads)
