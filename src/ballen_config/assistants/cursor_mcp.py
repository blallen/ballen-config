"""Validate the single approved Cursor Atlassian MCP workaround."""

import json
from pathlib import PurePath
from typing import Final, Literal, TypedDict

from ballen_config.assistants.json import StrictJsonError, strict_json_loads


class AtlassianMcpServer(TypedDict):
    """Exact fields for the OAuth-backed Atlassian HTTP server."""

    type: Literal["http"]
    url: Literal["https://mcp.atlassian.com/v1/mcp/authv2"]


class CursorMcpDocument(TypedDict):
    """Exact Cursor MCP document accepted by portable desired state."""

    mcpServers: dict[Literal["atlassian"], AtlassianMcpServer]


APPROVED_ATLASSIAN_MCP_SOURCE: Final = PurePath(
    "assistants/cursor/atlassian-workaround.json"
)
APPROVED_ATLASSIAN_MCP: Final[CursorMcpDocument] = {
    "mcpServers": {
        "atlassian": {
            "type": "http",
            "url": "https://mcp.atlassian.com/v1/mcp/authv2",
        }
    }
}
_MAX_CURSOR_MCP_BYTES: Final = 4096


def is_approved_atlassian_mcp(source: bytes) -> bool:
    """Return whether bytes are exactly the approved logical document.

    Args:
        source: Candidate Cursor MCP bytes.

    Returns:
        True only for the secret-free Atlassian HTTP workaround.
    """
    if len(source) > _MAX_CURSOR_MCP_BYTES:
        return False
    try:
        document = strict_json_loads(source)
    except (json.JSONDecodeError, StrictJsonError, UnicodeDecodeError):
        return False
    return document == APPROVED_ATLASSIAN_MCP


def is_approved_atlassian_mcp_source(path: PurePath, source: bytes) -> bool:
    """Return whether one tracked source is the path-bound approved document.

    Args:
        path: Repository-relative candidate path.
        source: Candidate file bytes.

    Returns:
        True only for the reviewed source path and exact logical document.
    """
    return PurePath(
        path.as_posix()
    ) == APPROVED_ATLASSIAN_MCP_SOURCE and is_approved_atlassian_mcp(source)
