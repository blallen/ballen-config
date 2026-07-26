"""Render canonical guidance into agent-native instruction documents."""

from __future__ import annotations

from pathlib import Path

_FORBIDDEN_OUTPUT_MARKERS = ("{{", "plugins/cache/")


def render_native_instructions(
    *,
    engineering: str,
    rtk: str,
    agent_suffix: str,
    rtk_include: Path | None = None,
) -> str:
    """Render canonical instructions in stable native section order.

    Args:
        engineering: Repository-owned portable engineering defaults.
        rtk: Repository-owned portable RTK guidance.
        agent_suffix: Reviewed agent-specific additions.
        rtk_include: Optional absolute Codex RTK include path.

    Returns:
        Rendered instructions with exactly one trailing newline.

    Raises:
        ValueError: If output would contain generated-state markers or an
            include path is not absolute.
    """
    if any(
        marker in section
        for section in (engineering, rtk, agent_suffix)
        for marker in _FORBIDDEN_OUTPUT_MARKERS
    ):
        raise ValueError("instructions contain generated state")
    if rtk_include is not None and not rtk_include.is_absolute():
        raise ValueError("RTK include must be absolute")

    sections = [engineering.rstrip()]
    sections.append(rtk.rstrip() if rtk_include is None else f"@{rtk_include}")
    sections.append(agent_suffix.rstrip())
    rendered = "\n\n".join(sections) + "\n"
    if any(marker in rendered for marker in _FORBIDDEN_OUTPUT_MARKERS):
        raise ValueError("instructions contain generated state")
    return rendered
