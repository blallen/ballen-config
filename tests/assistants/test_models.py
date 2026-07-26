"""Tests for strict coding-agent inventory models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ballen_config.assistants.models import (
    AssistantInventory,
    ExtensionSpec,
    PluginCatalog,
    SkillCatalog,
)


@pytest.mark.parametrize(
    ("resource", "missing_field"),
    [
        (
            {
                "id": "cursor.settings",
                "kind": "file",
                "owner": "cursor",
                "source": "assistants/cursor/settings.json",
            },
            "destination",
        ),
        (
            {
                "id": "shared.rtk-hook",
                "kind": "hook",
                "owner": "shared",
                "source": "assistants/shared/hooks/rtk-hook",
                "targets": ["cursor"],
            },
            "event",
        ),
        (
            {
                "id": "shared.skills.catalog",
                "kind": "catalog",
                "owner": "shared",
                "source": "assistants/shared/skills/catalog.yaml",
                "catalog_kind": "skill",
            },
            "item_ids",
        ),
        (
            {
                "id": "cursor.user-rules",
                "kind": "manual",
                "owner": "cursor",
            },
            "summary",
        ),
    ],
)
def test_kind_specific_fields_are_required(
    resource: dict[str, object],
    missing_field: str,
) -> None:
    """Reject incomplete resource declarations."""
    with pytest.raises(ValidationError, match=missing_field):
        AssistantInventory.model_validate({"resources": [resource]})


def test_inventory_rejects_duplicate_ids() -> None:
    """Reject ambiguous inventory identifiers."""
    item = {
        "id": "cursor.settings",
        "kind": "manual",
        "owner": "cursor",
        "summary": "Configure Cursor.",
    }
    with pytest.raises(ValidationError, match="duplicate resource id"):
        AssistantInventory.model_validate({"resources": [item, item]})


def test_inventory_has_no_mcp_resource_kind() -> None:
    """Keep MCP servers outside the portable inventory."""
    with pytest.raises(ValidationError, match="kind"):
        AssistantInventory.model_validate(
            {
                "resources": [
                    {
                        "id": "cursor.playwright",
                        "kind": "mcp",
                        "owner": "cursor",
                    }
                ]
            }
        )


@pytest.mark.parametrize(
    "resource",
    [
        {
            "id": "cursor.settings",
            "kind": "file",
            "owner": "cursor",
            "source": "assistants/cursor/settings.json",
            "destination": ".cursor/settings.json",
            "mode": 0o644,
        },
        {
            "id": "shared.hook",
            "kind": "hook",
            "owner": "shared",
            "source": "assistants/shared/hooks/rtk-hook",
            "event": "",
            "targets": ["cursor"],
        },
        {
            "id": "shared.hook",
            "kind": "hook",
            "owner": "shared",
            "source": "assistants/shared/hooks/rtk-hook",
            "event": "shell-command",
            "targets": [],
        },
    ],
)
def test_resources_reject_unsafe_modes_and_empty_hook_fields(
    resource: dict[str, object],
) -> None:
    """Reject unsafe file modes and hooks that cannot target an event."""
    with pytest.raises(ValidationError):
        AssistantInventory.model_validate({"resources": [resource]})


def test_models_are_frozen_and_forbid_extra_fields() -> None:
    """Prevent runtime mutation and silent schema expansion."""
    inventory = AssistantInventory.model_validate(
        {
            "resources": [
                {
                    "id": "cursor.manual",
                    "kind": "manual",
                    "owner": "cursor",
                    "summary": "Manual step.",
                }
            ]
        }
    )
    with pytest.raises(ValidationError):
        inventory.resources[0].required = False
    with pytest.raises(ValidationError):
        AssistantInventory.model_validate({"resources": [], "unknown": True})


def test_vsix_requires_complete_immutable_https_metadata() -> None:
    """Require every immutable VSIX download boundary field."""
    with pytest.raises(ValidationError, match="VSIX"):
        ExtensionSpec.model_validate(
            {
                "id": "publisher.extension",
                "install_mode": "vsix",
                "version": "1.0.0",
                "size_bytes": 1,
                "url": "http://example.invalid/extension.vsix",
                "sha256": "a" * 64,
            }
        )
    with pytest.raises(ValidationError, match="VSIX"):
        ExtensionSpec.model_validate(
            {
                "id": "publisher.extension",
                "install_mode": "vsix",
            }
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", "1.0.0"),
        ("size_bytes", 1),
        ("url", "https://example.invalid/extension.vsix"),
        ("sha256", "a" * 64),
    ],
)
def test_gallery_extensions_forbid_vsix_metadata(
    field: str,
    value: object,
) -> None:
    """Keep gallery installs free of misleading download metadata."""
    with pytest.raises(ValidationError, match="gallery"):
        ExtensionSpec.model_validate(
            {"id": "publisher.extension", "install_mode": "gallery", field: value}
        )


def test_plugin_catalog_rejects_unknown_marketplace() -> None:
    """Require every plugin marketplace to be declared."""
    with pytest.raises(ValidationError, match="unknown marketplaces"):
        PluginCatalog.model_validate(
            {
                "marketplaces": [],
                "plugins": [
                    {
                        "id": "example@missing",
                        "marketplace": "missing",
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    ("skills", "message"),
    [
        (
            [
                {
                    "name": "example",
                    "source": "skills/example",
                    "targets": ["cursor"],
                    "provenance": "reviewed",
                    "portability_status": "reviewed-generic",
                },
                {
                    "name": "example",
                    "source": "skills/example-copy",
                    "targets": ["codex"],
                    "provenance": "reviewed",
                    "portability_status": "reviewed-generic",
                },
            ],
            "duplicate skill name",
        ),
        (
            [
                {
                    "name": "example",
                    "source": "skills/example",
                    "targets": ["cursor"],
                    "dependencies": ["missing"],
                    "provenance": "reviewed",
                    "portability_status": "reviewed-generic",
                }
            ],
            "unknown skill dependencies",
        ),
        (
            [
                {
                    "name": "first",
                    "source": "skills/first",
                    "targets": ["cursor"],
                    "dependencies": ["second"],
                    "provenance": "reviewed",
                    "portability_status": "reviewed-generic",
                },
                {
                    "name": "second",
                    "source": "skills/second",
                    "targets": ["cursor"],
                    "dependencies": ["first"],
                    "provenance": "reviewed",
                    "portability_status": "reviewed-generic",
                },
            ],
            "skill dependency cycle",
        ),
    ],
)
def test_skill_catalog_rejects_invalid_dependency_graphs(
    skills: list[dict[str, object]],
    message: str,
) -> None:
    """Reject ambiguous or incomplete skill dependency graphs."""
    with pytest.raises(ValidationError, match=message):
        SkillCatalog.model_validate({"skills": skills})
