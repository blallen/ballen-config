"""Managed installation contribution for shared review tooling."""

from pathlib import Path

from ballen_config.configure import (
    ConfigurationContribution,
    ManagedTreeSpec,
    digest_tree,
)

_SUPPORTED_AGENTS = frozenset({"cursor", "claude-code", "codex"})
_SOURCE = Path("assistants/shared/tools/review")


def review_tools_contribution(
    *,
    repo_root: Path,
    enabled: frozenset[str],
) -> ConfigurationContribution:
    """Install the shared review tool tree for any supported agent.

    Args:
        repo_root: Approved checkout root.
        enabled: Resolved enabled agent identifiers.

    Returns:
        A digest-bound managed tree contribution, or an empty contribution
        when all supported agents are disabled.
    """
    if not enabled.intersection(_SUPPORTED_AGENTS):
        return ConfigurationContribution()
    source = repo_root / _SOURCE
    return ConfigurationContribution(
        specs=(
            ManagedTreeSpec(
                id="shared-review-tools",
                source=source,
                destination=Path(".local/share/ballen-config/review-tools"),
                component="shared",
                expected_source_digest=digest_tree(source),
            ),
        )
    )
