"""Deterministic parser for human-editable review Markdown."""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from ballen_review_tools.canonical import deduplication_key
from ballen_review_tools.models import ReviewAction, ReviewDiagnostic, ReviewIdentity

_HEADING = re.compile(r"^###\s+([A-Za-z0-9][A-Za-z0-9._-]*):\s+(.+?)\s*$")
_FIELD = re.compile(r"^\*\*([^*]+):\*\*\s*(.*?)\s*$")
_KNOWN_FIELDS = {
    "Type",
    "File",
    "Line",
    "Side",
    "Start line",
    "Start side",
    "Discussion",
    "Thread",
    "POST",
}
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


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
