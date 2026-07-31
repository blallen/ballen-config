"""Deterministic parser for human-editable review Markdown."""

import re
from collections.abc import Iterable

from ballen_review_tools.canonical import deduplication_key
from ballen_review_tools.models import ReviewAction, ReviewIdentity

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


def _sections(lines: list[str]) -> Iterable[tuple[str, list[str]]]:
    """Yield action IDs and bodies from level-three headings outside fences."""
    current_id: str | None = None
    current_lines: list[str] = []
    fenced = False
    for line in lines:
        if line.startswith("```"):
            fenced = not fenced
        if not fenced:
            match = _HEADING.match(line)
            if match is not None:
                if current_id is not None:
                    yield current_id, current_lines
                current_id = match.group(1)
                current_lines = []
                continue
            if line.startswith("### "):
                raise ValueError("action heading must contain a stable ID")
        if current_id is not None:
            current_lines.append(line)
    if current_id is not None:
        yield current_id, current_lines


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
            metadata[key] = value.strip("`")
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
) -> tuple[ReviewAction, ...]:
    """Parse all review actions, retaining selected and skipped items.

    Args:
        text: Human-editable review Markdown.
        identity: Provider and change identity used for deduplication keys.

    Returns:
        Parsed logical actions in document order.

    Raises:
        ValueError: If headings, metadata, locations, or action kinds are
            malformed.
    """
    actions: list[ReviewAction] = []
    seen_ids: set[str] = set()
    for action_id, lines in _sections(text.splitlines()):
        if action_id in seen_ids:
            raise ValueError(f"duplicate action ID: {action_id}")
        seen_ids.add(action_id)
        metadata, body = _metadata_and_body(lines)
        if not body:
            raise ValueError(f"empty body for action: {action_id}")
        kind = _required(metadata, "Type").lower()
        if kind not in {"inline", "general", "reply"}:
            raise ValueError(f"unsupported action type: {kind}")
        selected_value = _required(metadata, "POST").lower()
        if selected_value not in {"yes", "no"}:
            raise ValueError("POST must be YES or NO")
        path_text = metadata.get("File")
        path = None if path_text is None else path_text
        line = _line(metadata, "Line")
        start_line = _line(metadata, "Start line")
        side = metadata.get("Side")
        start_side = metadata.get("Start side")
        thread_id = metadata.get("Discussion") or metadata.get("Thread")
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
                    repository=identity.repository,
                    change_number=identity.change_number,
                    kind=kind,
                    body=body,
                    path=path,
                    line=line,
                    thread_id=thread_id,
                ),
                "validation_state": "valid",
                "intended_action": intended,
                "outcome": "pending",
            }
        )
        actions.append(action)
    if not actions:
        raise ValueError("review contains no action headings")
    return tuple(actions)
