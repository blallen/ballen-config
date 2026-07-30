"""Tests for strict coding-agent inventory models."""

from collections.abc import Callable

import pytest
from pydantic import ValidationError

from ballen_config.assistants.models import (
    AgentName,
    AssistantInventory,
    CursorLocalPlugin,
    CursorMarketplacePlugin,
    ExtensionCatalog,
    ExtensionSpec,
    FileResource,
    NativeMarketplacePlugin,
    PluginCatalog,
    SkillCatalog,
)


@pytest.fixture
def skill_catalog_payload() -> Callable[[], dict[str, object]]:
    """Build independent valid catalog payloads with one successor skill."""

    def build() -> dict[str, object]:
        """Return one valid catalog payload ready for a rename declaration."""
        return {
            "skills": [
                {
                    "name": "using-jujutsu",
                    "source": "assistants/shared/skills/using-jujutsu",
                    "targets": ["cursor"],
                    "profiles": ["default"],
                    "dependencies": [],
                    "provenance": "renamed",
                    "portability_status": "reviewed-generic",
                }
            ],
            "renames": [{"from": "jujutsu-workflow", "to": "using-jujutsu"}],
        }

    return build


@pytest.mark.parametrize(
    ("resource", "missing_field"),
    [
        pytest.param(
            {
                "id": "cursor.settings",
                "kind": "file",
                "owner": "cursor",
                "source": "assistants/cursor/settings.json",
            },
            "destination",
            id="file-destination",
        ),
        pytest.param(
            {
                "id": "shared.rtk-hook",
                "kind": "hook",
                "owner": "shared",
                "source": "assistants/shared/hooks/rtk-hook",
                "targets": ["cursor"],
            },
            "event",
            id="hook-event",
        ),
        pytest.param(
            {
                "id": "cursor.user-rules",
                "kind": "manual",
                "owner": "cursor",
            },
            "summary",
            id="manual-summary",
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
        pytest.param(
            {
                "id": "cursor.settings",
                "kind": "file",
                "owner": "cursor",
                "source": "assistants/cursor/settings.json",
                "destination": ".cursor/settings.json",
                "mode": 0o644,
            },
            id="unsafe-file-mode",
        ),
        pytest.param(
            {
                "id": "shared.hook",
                "kind": "hook",
                "owner": "shared",
                "source": "assistants/shared/hooks/rtk-hook",
                "event": "",
                "targets": ["cursor"],
            },
            id="empty-hook-event",
        ),
        pytest.param(
            {
                "id": "shared.hook",
                "kind": "hook",
                "owner": "shared",
                "source": "assistants/shared/hooks/rtk-hook",
                "event": "shell-command",
                "targets": [],
            },
            id="empty-hook-targets",
        ),
    ],
)
def test_resources_reject_unsafe_modes_and_empty_hook_fields(
    resource: dict[str, object],
) -> None:
    """Reject unsafe file modes and hooks that cannot target an event."""
    with pytest.raises(ValidationError):
        AssistantInventory.model_validate({"resources": [resource]})


def test_inventory_forbids_undeclared_fields() -> None:
    """Reject inventory input that would silently widen the public schema."""
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
        pytest.param("version", "1.0.0", id="version"),
        pytest.param("size_bytes", 1, id="size-bytes"),
        pytest.param("url", "https://example.invalid/extension.vsix", id="url"),
        pytest.param("sha256", "a" * 64, id="sha256"),
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


def test_extension_catalog_rejects_duplicate_ids() -> None:
    """Reject ambiguous extension identifiers."""
    with pytest.raises(ValidationError, match="duplicate extension id"):
        ExtensionCatalog.model_validate(
            {
                "extensions": [
                    {"id": "publisher.extension"},
                    {"id": "publisher.extension"},
                ]
            }
        )


def test_plugin_catalog_accepts_shared_native_and_cursor_variants() -> None:
    """Accept each targeted plugin representation in the shared catalog."""
    catalog = PluginCatalog.model_validate(
        {
            "marketplaces": [
                {
                    "name": "official",
                    "source": "owner/repository",
                    "targets": ["claude-code", "codex"],
                    "profiles": ["default"],
                }
            ],
            "plugins": [
                {
                    "kind": "native-marketplace",
                    "id": "example@official",
                    "marketplace": "official",
                    "targets": ["claude-code", "codex"],
                    "profiles": ["default"],
                    "required": True,
                },
                {
                    "kind": "cursor-marketplace",
                    "id": "cursor-example",
                    "targets": ["cursor"],
                    "profiles": ["default"],
                    "required": False,
                    "scope": "user",
                    "verification": "manual",
                },
                {
                    "kind": "cursor-local",
                    "id": "local-example",
                    "source": "assistants/shared/plugins/local/local-example",
                    "targets": ["cursor"],
                    "profiles": ["default"],
                    "required": True,
                },
            ],
        }
    )
    native, cursor_marketplace, cursor_local = catalog.plugins
    assert isinstance(native, NativeMarketplacePlugin)
    assert native.marketplace == "official"
    assert native.targets == (AgentName.CLAUDE, AgentName.CODEX)
    assert native.required is True
    assert isinstance(cursor_marketplace, CursorMarketplacePlugin)
    assert cursor_marketplace.scope == "user"
    assert cursor_marketplace.verification == "manual"
    assert cursor_marketplace.required is False
    assert isinstance(cursor_local, CursorLocalPlugin)
    assert cursor_local.source.as_posix() == (
        "assistants/shared/plugins/local/local-example"
    )
    assert cursor_local.targets == (AgentName.CURSOR,)
    assert cursor_local.required is True


@pytest.mark.parametrize(
    "targets",
    [
        pytest.param([], id="empty"),
        pytest.param(["shared"], id="shared"),
        pytest.param(["cursor", "cursor"], id="duplicate"),
    ],
)
def test_plugin_catalog_rejects_invalid_target_sets(targets: list[str]) -> None:
    """Reject empty, non-concrete, and duplicate target selections."""
    payload = {
        "marketplaces": [
            {
                "name": "official",
                "source": "owner/repository",
                "targets": targets,
                "profiles": ["default"],
            }
        ],
        "plugins": [],
    }
    with pytest.raises(ValidationError):
        PluginCatalog.model_validate(payload)


def test_plugin_catalog_rejects_duplicate_identity_for_overlapping_target() -> None:
    """Prevent one native alias from resolving to different sources per target."""
    payload = {
        "marketplaces": [
            {
                "name": "official",
                "source": "owner/one",
                "targets": ["claude-code", "codex"],
            },
            {
                "name": "official",
                "source": "owner/two",
                "targets": ["codex"],
            },
        ],
        "plugins": [],
    }
    with pytest.raises(ValidationError, match="duplicate marketplace identity"):
        PluginCatalog.model_validate(payload)


def test_plugin_catalog_rejects_duplicate_plugin_identity_for_overlapping_target() -> (
    None
):
    """Prevent a target from receiving conflicting declarations for one plugin ID."""
    payload = {
        "marketplaces": [
            {
                "name": "official",
                "source": "owner/repository",
                "targets": ["claude-code", "codex"],
            }
        ],
        "plugins": [
            {
                "kind": "native-marketplace",
                "id": "example@official",
                "marketplace": "official",
                "targets": ["claude-code", "codex"],
            },
            {
                "kind": "native-marketplace",
                "id": "example@official",
                "marketplace": "official",
                "targets": ["codex"],
            },
        ],
    }
    with pytest.raises(ValidationError, match="duplicate plugin identity"):
        PluginCatalog.model_validate(payload)


def test_disjoint_targets_may_reuse_marketplace_name() -> None:
    """Allow target-specific aliases that happen to share a display name."""
    catalog = PluginCatalog.model_validate(
        {
            "marketplaces": [
                {
                    "name": "official",
                    "source": "owner/claude",
                    "targets": ["claude-code"],
                },
                {
                    "name": "official",
                    "source": "owner/codex",
                    "targets": ["codex"],
                },
            ],
            "plugins": [],
        }
    )
    assert len(catalog.marketplaces) == 2


@pytest.mark.parametrize(
    ("marketplace", "plugin", "message"),
    [
        pytest.param(
            {
                "name": "official",
                "source": "owner/repository",
                "targets": ["claude-code"],
            },
            {
                "kind": "native-marketplace",
                "id": "example@official",
                "marketplace": "official",
                "targets": ["codex"],
            },
            "not covered",
            id="target",
        ),
        pytest.param(
            {
                "name": "official",
                "source": "owner/repository",
                "targets": ["claude-code"],
                "profiles": ["default"],
            },
            {
                "kind": "native-marketplace",
                "id": "example@official",
                "marketplace": "official",
                "targets": ["claude-code"],
                "profiles": ["work"],
            },
            "profiles must be a subset",
            id="profile",
        ),
    ],
)
def test_native_plugin_requires_marketplace_coverage(
    marketplace: dict[str, object], plugin: dict[str, object], message: str
) -> None:
    """Require native plugins to be eligible wherever their marketplace is used."""
    with pytest.raises(ValidationError, match=message):
        PluginCatalog.model_validate(
            {"marketplaces": [marketplace], "plugins": [plugin]}
        )


def test_native_plugin_suffix_matches_marketplace_alias() -> None:
    """Keep native plugin IDs coupled to their declared marketplace alias."""
    with pytest.raises(ValidationError, match="suffix mismatch"):
        PluginCatalog.model_validate(
            {
                "marketplaces": [
                    {
                        "name": "official",
                        "source": "owner/repository",
                        "targets": ["claude-code"],
                    }
                ],
                "plugins": [
                    {
                        "kind": "native-marketplace",
                        "id": "example@other",
                        "marketplace": "official",
                        "targets": ["claude-code"],
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    "kind",
    [
        pytest.param("cursor-marketplace", id="marketplace"),
        pytest.param("cursor-local", id="local"),
    ],
)
def test_cursor_variants_reject_non_cursor_targets(kind: str) -> None:
    """Restrict Cursor-specific representations to Cursor alone."""
    plugin: dict[str, object] = {
        "kind": kind,
        "id": "example",
        "targets": ["claude-code"],
    }
    if kind == "cursor-marketplace":
        plugin.update(scope="user", verification="manual")
    else:
        plugin["source"] = "assistants/shared/plugins/local/example"
    with pytest.raises(ValidationError, match="target only cursor"):
        PluginCatalog.model_validate({"marketplaces": [], "plugins": [plugin]})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("scope", "workspace", id="scope"),
        pytest.param("verification", "automatic", id="verification"),
    ],
)
def test_cursor_marketplace_requires_manual_user_selection(
    field: str, value: str
) -> None:
    """Keep marketplace-only Cursor entries explicitly manual and user-scoped."""
    plugin = {
        "kind": "cursor-marketplace",
        "id": "example",
        "targets": ["cursor"],
        "scope": "user",
        "verification": "manual",
        field: value,
    }
    with pytest.raises(ValidationError):
        PluginCatalog.model_validate({"marketplaces": [], "plugins": [plugin]})


@pytest.mark.parametrize(
    ("dependency_targets", "dependency_profiles", "message"),
    [
        pytest.param(
            ["cursor"], ["default", "work"], "dependency targets", id="target"
        ),
        pytest.param(
            ["cursor", "codex"], ["default"], "dependency profiles", id="profile"
        ),
    ],
)
def test_skill_dependencies_cover_dependent_eligibility(
    dependency_targets: list[str], dependency_profiles: list[str], message: str
) -> None:
    """Require every dependency to be eligible for each dependent invocation."""
    with pytest.raises(ValidationError, match=message):
        SkillCatalog.model_validate(
            {
                "skills": [
                    {
                        "name": "base",
                        "source": "assistants/shared/skills/base",
                        "targets": dependency_targets,
                        "profiles": dependency_profiles,
                        "dependencies": [],
                        "provenance": "reviewed",
                        "portability_status": "reviewed-generic",
                    },
                    {
                        "name": "dependent",
                        "source": "assistants/shared/skills/dependent",
                        "targets": ["cursor", "codex"],
                        "profiles": ["default", "work"],
                        "dependencies": ["base"],
                        "provenance": "reviewed",
                        "portability_status": "reviewed-generic",
                    },
                ]
            }
        )


def test_shared_skill_dependency_may_cover_more_targets_and_profiles() -> None:
    """Permit dependencies with a broader eligibility envelope."""
    catalog = SkillCatalog.model_validate(
        {
            "skills": [
                {
                    "name": "base",
                    "source": "assistants/shared/skills/base",
                    "targets": ["cursor", "claude-code", "codex"],
                    "profiles": ["default", "work"],
                    "dependencies": [],
                    "provenance": "reviewed",
                    "portability_status": "reviewed-generic",
                },
                {
                    "name": "dependent",
                    "source": "assistants/shared/skills/dependent",
                    "targets": ["cursor", "codex"],
                    "profiles": ["work"],
                    "dependencies": ["base"],
                    "provenance": "reviewed",
                    "portability_status": "reviewed-generic",
                },
            ]
        }
    )
    assert catalog.skills[1].dependencies == ("base",)


@pytest.mark.parametrize(
    ("collection", "item"),
    [
        pytest.param(
            "resources",
            {
                "id": "shared.settings",
                "kind": "file",
                "owner": "shared",
                "source": "assistants/shared/settings.json",
                "destination": ".cursor/settings.json",
                "targets": ["shared"],
            },
            id="file-resource",
        ),
        pytest.param(
            "resources",
            {
                "id": "shared.hook",
                "kind": "hook",
                "owner": "shared",
                "source": "assistants/shared/hooks/rtk-hook",
                "event": "shell-command",
                "targets": ["shared"],
            },
            id="hook-resource",
        ),
        pytest.param(
            "resources",
            {
                "id": "shared.skills",
                "kind": "catalog",
                "owner": "shared",
                "source": "assistants/shared/skills/catalog.yaml",
                "catalog_kind": "skill",
                "targets": ["shared"],
                "item_ids": [],
            },
            id="catalog-resource",
        ),
        pytest.param(
            "skills",
            {
                "name": "example",
                "source": "assistants/shared/skills/example",
                "targets": ["shared"],
                "provenance": "reviewed",
                "portability_status": "reviewed-generic",
            },
            id="skill",
        ),
    ],
)
def test_concrete_target_lists_reject_shared(
    collection: str,
    item: dict[str, object],
) -> None:
    """Require every concrete target to name an installable agent."""
    model = AssistantInventory if collection == "resources" else SkillCatalog
    with pytest.raises(ValidationError, match="shared is not a concrete target"):
        model.model_validate({collection: [item]})


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("source", id="source"),
        pytest.param("destination", id="destination"),
    ],
)
@pytest.mark.parametrize(
    "path",
    [
        pytest.param("assistants/codex/auth.json", id="auth"),
        pytest.param("assistants/claude/session-env/current.json", id="session"),
        pytest.param("assistants/cursor/history.jsonl", id="history"),
        pytest.param("assistants/cursor/transcripts/chat.json", id="transcript"),
        pytest.param("assistants/codex/memories/notes.md", id="memory"),
        pytest.param("assistants/cursor/worktrees/project.json", id="worktree"),
        pytest.param("assistants/cursor/index.sqlite", id="index"),
        pytest.param("assistants/cursor/cache/extensions.json", id="cache"),
        pytest.param("assistants/codex/trust.toml", id="trust"),
        pytest.param("assistants/claude/credentials.json", id="credentials"),
        pytest.param("assistants/cursor/tokens.json", id="token"),
        pytest.param("assistants/cursor/mcp.json", id="mcp"),
    ],
)
def test_file_resources_reject_managed_local_state_paths(
    field: str,
    path: str,
) -> None:
    """Exclude local agent state from both sides of managed file copies."""
    resource = {
        "id": "cursor.settings",
        "kind": "file",
        "owner": "cursor",
        "source": "assistants/cursor/settings.base.json",
        "destination": ".cursor/settings.json",
        field: path,
    }
    with pytest.raises(ValidationError, match="managed local state"):
        AssistantInventory.model_validate({"resources": [resource]})


def test_file_resource_allows_exact_work_cursor_atlassian_mcp_destination() -> None:
    """Permit only the reviewed work-profile Cursor MCP destination."""
    inventory = AssistantInventory.model_validate(
        {
            "resources": [
                {
                    "id": "cursor.atlassian-mcp",
                    "kind": "file",
                    "owner": "cursor",
                    "source": "assistants/cursor/atlassian-workaround.json",
                    "destination": ".cursor/mcp.json",
                    "profiles": ["work"],
                }
            ]
        }
    )

    resource = inventory.resources[0]
    assert isinstance(resource, FileResource)
    assert resource.destination.as_posix() == ".cursor/mcp.json"
    assert resource.profiles == ("work",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("id", "cursor.other", id="wrong-id"),
        pytest.param("owner", "shared", id="wrong-owner"),
        pytest.param(
            "source",
            "assistants/cursor/settings.base.json",
            id="wrong-source",
        ),
        pytest.param("profiles", ["default"], id="default-profile"),
        pytest.param("profiles", ["default", "work"], id="extra-profile"),
        pytest.param("mode", 0o700, id="wrong-mode"),
        pytest.param("role", "overlay", id="wrong-role"),
        pytest.param("required", False, id="optional"),
        pytest.param("targets", ["cursor"], id="unexpected-target"),
    ],
)
def test_cursor_atlassian_mcp_path_rejects_every_other_resource_shape(
    field: str,
    value: object,
) -> None:
    """Keep the local-state exception bound to one complete declaration."""
    resource: dict[str, object] = {
        "id": "cursor.atlassian-mcp",
        "kind": "file",
        "owner": "cursor",
        "source": "assistants/cursor/atlassian-workaround.json",
        "destination": ".cursor/mcp.json",
        "profiles": ["work"],
    }
    resource[field] = value

    with pytest.raises(ValidationError, match="managed local state"):
        AssistantInventory.model_validate({"resources": [resource]})


@pytest.mark.parametrize(
    ("resource", "critical_field", "critical_value"),
    [
        pytest.param(
            {
                "id": "cursor.settings",
                "kind": "file",
                "owner": "cursor",
                "source": "assistants/cursor/settings.base.json",
                "destination": ".cursor/settings.json",
            },
            "destination",
            ".cursor/settings.json",
            id="cursor-file",
        ),
        pytest.param(
            {
                "id": "shared.instructions",
                "kind": "file",
                "owner": "shared",
                "source": "assistants/shared/instructions/core.md",
                "destination": ".claude/CLAUDE.md",
                "targets": ["claude-code"],
            },
            "destination",
            ".claude/CLAUDE.md",
            id="shared-file",
        ),
        pytest.param(
            {
                "id": "shared.hook",
                "kind": "hook",
                "owner": "shared",
                "source": "assistants/shared/hooks/rtk-hook",
                "event": "shell-command",
                "targets": ["codex"],
            },
            "event",
            "shell-command",
            id="shared-hook",
        ),
        pytest.param(
            {
                "id": "shared.skills",
                "kind": "catalog",
                "owner": "shared",
                "source": "assistants/shared/skills/catalog.yaml",
                "catalog_kind": "skill",
                "targets": ["cursor"],
            },
            "catalog_kind",
            "skill",
            id="shared-catalog",
        ),
    ],
)
def test_reviewed_configuration_paths_remain_allowed(
    resource: dict[str, object],
    critical_field: str,
    critical_value: object,
) -> None:
    """Allow ordinary settings, instruction, hook, and catalog paths."""
    validated = AssistantInventory.model_validate({"resources": [resource]})

    assert validated.resources[0].kind == resource["kind"]
    assert str(getattr(validated.resources[0], critical_field)) == critical_value


def test_manual_authentication_summary_remains_allowed() -> None:
    """Allow informational login guidance that does not manage auth state."""
    inventory = AssistantInventory.model_validate(
        {
            "resources": [
                {
                    "id": "codex.login",
                    "kind": "manual",
                    "owner": "codex",
                    "summary": "Run codex login using the native authentication flow.",
                    "source": "assistants/codex/authentication.md",
                }
            ]
        }
    )
    assert inventory.resources[0].id == "codex.login"


@pytest.mark.parametrize(
    ("skills", "message"),
    [
        pytest.param(
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
            id="duplicate-name",
        ),
        pytest.param(
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
            id="unknown-dependency",
        ),
        pytest.param(
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
            id="cycle",
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


def test_skill_rename_requires_successor_absent_from_and_present_to(
    skill_catalog_payload: Callable[[], dict[str, object]],
) -> None:
    """Accept a rename only when its successor is the declared skill."""
    catalog = SkillCatalog.model_validate(skill_catalog_payload())
    assert catalog.renames[0].from_name == "jujutsu-workflow"
    assert catalog.renames[0].to_name == "using-jujutsu"


@pytest.mark.parametrize(
    ("include_legacy_skill", "renames", "match"),
    [
        pytest.param(
            True,
            [{"from": "jujutsu-workflow", "to": "using-jujutsu"}],
            "rename from still present in skills",
            id="from-still-present",
        ),
        pytest.param(
            False,
            [
                {"from": "old-a", "to": "using-jujutsu"},
                {"from": "old-a", "to": "using-jujutsu"},
            ],
            "duplicate rename from",
            id="duplicate-from",
        ),
        pytest.param(
            False,
            [{"from": "jujutsu-workflow", "to": "missing-skill"}],
            "rename to absent from skills",
            id="missing-successor",
        ),
    ],
)
def test_skill_rename_validation_rejects_invalid_declarations(
    skill_catalog_payload: Callable[[], dict[str, object]],
    include_legacy_skill: bool,
    renames: list[dict[str, str]],
    match: str,
) -> None:
    """Reject rename declarations that violate catalog identity constraints."""
    payload = skill_catalog_payload()
    if include_legacy_skill:
        payload["skills"] = [
            {
                "name": "jujutsu-workflow",
                "source": "assistants/shared/skills/jujutsu-workflow",
                "targets": ["cursor"],
                "profiles": ["default"],
                "dependencies": [],
                "provenance": "renamed",
                "portability_status": "reviewed-generic",
            },
            *payload["skills"],
        ]
    payload["renames"] = renames

    with pytest.raises(ValidationError, match=match):
        SkillCatalog.model_validate(payload)
