"""Tests for canonical shared coding-agent instructions."""

from __future__ import annotations

from pathlib import Path

import pytest

from ballen_config.assistants.instructions import render_native_instructions
from ballen_config.assistants.inventory import load_inventory
from ballen_config.assistants.models import (
    CatalogResource,
    FileResource,
    HookResource,
)


def test_engineering_defaults_are_exact(repo_root: Path) -> None:
    """Keep the authored defaults limited to portable root guidance."""
    path = repo_root / "assistants/shared/instructions/engineering.md"
    assert path.read_text() == (
        "# Engineering defaults\n\n"
        "- Use Python 3.12.\n"
        "- Use type hints, TypedDict for external mappings, and Pydantic 2.8 "
        "for\n"
        "  validated models.\n"
        "- Use Google-style docstrings.\n"
        "- Use pytest fixtures.\n"
        "- Prefer Jujutsu for source control.\n"
    )


def test_rtk_guidance_is_portable_and_clean_machine_safe(
    repo_root: Path,
) -> None:
    """Retain supported RTK patterns without local or Codex-only framing."""
    text = (repo_root / "assistants/shared/instructions/rtk.md").read_text()
    assert "agent-run shell commands" in text
    assert "prefixed with `rtk`" in text
    for command in (
        "rtk git status",
        "rtk cargo test",
        "rtk npm run build",
        "rtk pytest -q",
        "rtk gain",
        "rtk gain --history",
        "rtk proxy <cmd>",
        "rtk --version",
        "which rtk",
    ):
        assert command in text
    assert "/Users/" not in text
    assert "plugins/cache/" not in text
    assert "Codex CLI" not in text


def test_render_order_and_trailing_newline_are_exact() -> None:
    """Render engineering, RTK, and suffix sections in canonical order."""
    rendered = render_native_instructions(
        engineering="engineering\n\n",
        rtk="rtk\n",
        agent_suffix="suffix\n\n",
    )
    assert rendered == "engineering\n\nrtk\n\nsuffix\n"
    assert not rendered.endswith("\n\n")


@pytest.mark.parametrize("suffix", ["# Cursor additions\n", "# Claude additions\n"])
def test_cursor_and_claude_embed_canonical_sections(
    repo_root: Path,
    suffix: str,
) -> None:
    """Embed reviewed engineering and RTK text without transformations."""
    engineering = (
        repo_root / "assistants/shared/instructions/engineering.md"
    ).read_text()
    rtk = (repo_root / "assistants/shared/instructions/rtk.md").read_text()
    rendered = render_native_instructions(
        engineering=engineering,
        rtk=rtk,
        agent_suffix=suffix,
    )
    assert rendered == (
        f"{engineering.rstrip()}\n\n{rtk.rstrip()}\n\n{suffix.rstrip()}\n"
    )


def test_codex_uses_absolute_rtk_include_without_embedding(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Reference the separately managed Codex RTK file by absolute path."""
    engineering = (
        repo_root / "assistants/shared/instructions/engineering.md"
    ).read_text()
    rtk = (repo_root / "assistants/shared/instructions/rtk.md").read_text()
    include = temporary_home / ".codex/RTK.md"
    rendered = render_native_instructions(
        engineering=engineering,
        rtk=rtk,
        agent_suffix="# Codex additions\n",
        rtk_include=include,
    )
    assert rendered == (f"{engineering.rstrip()}\n\n@{include}\n\n# Codex additions\n")
    assert rtk.rstrip() not in rendered


def test_relative_rtk_include_is_rejected() -> None:
    """Require injected Codex includes to use an explicit absolute path."""
    with pytest.raises(ValueError, match="absolute"):
        render_native_instructions(
            engineering="engineering",
            rtk="rtk",
            agent_suffix="suffix",
            rtk_include=Path(".codex/RTK.md"),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("engineering", "{{ generated }}"),
        ("rtk", "plugins/cache/generated"),
        ("agent_suffix", "{{ native-template }}"),
    ],
)
def test_rendered_instructions_reject_generated_state(
    field: str,
    value: str,
) -> None:
    """Keep template markers and plugin-cache paths out of native output."""
    sections = {
        "engineering": "engineering",
        "rtk": "rtk",
        "agent_suffix": "suffix",
        field: value,
    }
    with pytest.raises(ValueError, match="generated state"):
        render_native_instructions(
            engineering=sections["engineering"],
            rtk=sections["rtk"],
            agent_suffix=sections["agent_suffix"],
        )


def test_inventory_loads_reviewed_shared_instruction_and_hook_resources(
    repo_root: Path,
) -> None:
    """Keep Task 3 sources reviewed and the empty skill catalog synchronized."""
    inventory = load_inventory(repo_root / "assistants/inventory.yaml", repo_root)
    by_id = {resource.id: resource for resource in inventory.resources}
    assert set(by_id) == {
        "shared.engineering",
        "shared.rtk",
        "shared.rtk-hook",
        "shared.skills.catalog",
    }
    engineering = by_id["shared.engineering"]
    rtk = by_id["shared.rtk"]
    hook = by_id["shared.rtk-hook"]
    assert isinstance(engineering, FileResource)
    assert isinstance(rtk, FileResource)
    assert isinstance(hook, HookResource)
    assert engineering.targets == rtk.targets
    assert set(engineering.targets) == {"cursor", "claude-code", "codex"}
    assert set(hook.targets) == {"cursor", "claude-code"}
    catalog = by_id["shared.skills.catalog"]
    assert isinstance(catalog, CatalogResource)
    assert catalog.item_ids == ()
