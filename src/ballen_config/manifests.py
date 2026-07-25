from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ballen_config.models import (
    Component,
    ComponentFile,
    Profile,
    ResolutionRequest,
    ResolvedSetup,
)


def _yaml(path: Path) -> Any:
    """Load one YAML document at the external data boundary."""
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


class ManifestRepository:
    """Load and resolve declarative bootstrap manifests."""

    def __init__(
        self,
        root: Path,
        profiles: dict[str, Profile],
        components: tuple[Component, ...],
    ) -> None:
        """Initialize a manifest repository.

        Args:
            root: Root directory containing the manifest files.
            profiles: Profiles keyed by their manifest file stem.
            components: All installable components.
        """
        self.root = root
        self.profiles = profiles
        self.components = components

    @classmethod
    def load(cls, root: Path) -> ManifestRepository:
        """Load profiles and component manifests from a directory.

        Args:
            root: Root directory containing the manifest files.

        Returns:
            A validated manifest repository.

        Raises:
            ValueError: If component identifiers are duplicated.
        """
        profiles = {
            path.stem: Profile.model_validate(_yaml(path))
            for path in sorted((root / "profiles").glob("*.yaml"))
        }
        component_files = (
            ComponentFile.model_validate(_yaml(root / "packages.yaml")),
            ComponentFile.model_validate(_yaml(root / "applications.yaml")),
        )
        components = tuple(
            component
            for component_file in component_files
            for component in component_file.components
        )
        component_ids = [component.id for component in components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("component ids must be unique")
        return cls(root, profiles, components)

    def _profile_names(
        self,
        name: str,
        visiting: frozenset[str] = frozenset(),
    ) -> set[str]:
        """Return a profile and all of its recursive ancestors.

        Args:
            name: Profile name to resolve.
            visiting: Profiles already on the current recursion path.

        Returns:
            All selected profile names.

        Raises:
            ValueError: If a profile is unknown or inheritance is cyclic.
        """
        if name not in self.profiles:
            raise ValueError(f"unknown profile: {name}")
        if name in visiting:
            raise ValueError(f"profile inheritance cycle: {name}")
        names = {name}
        for parent in self.profiles[name].extends:
            names.update(self._profile_names(parent, visiting | {name}))
        return names

    @staticmethod
    def _dependency_order(
        components: list[Component],
    ) -> tuple[Component, ...]:
        """Return components in stable dependency-first order.

        Args:
            components: Selected components to order.

        Returns:
            Components sorted deterministically with dependencies first.

        Raises:
            ValueError: If dependencies are cyclic or unselected.
        """
        by_id = {component.id: component for component in components}
        ordered: list[Component] = []
        permanent: set[str] = set()
        temporary: set[str] = set()

        def visit(component_id: str) -> None:
            if component_id in permanent:
                return
            if component_id in temporary:
                raise ValueError(f"component dependency cycle: {component_id}")
            temporary.add(component_id)
            component = by_id[component_id]
            for dependency in sorted(component.depends_on):
                if dependency not in by_id:
                    raise ValueError(
                        f"{component_id} requires unselected {dependency}"
                    )
                visit(dependency)
            temporary.remove(component_id)
            permanent.add(component_id)
            ordered.append(component)

        for component_id in sorted(by_id):
            visit(component_id)
        return tuple(ordered)

    def resolve(self, request: ResolutionRequest) -> ResolvedSetup:
        """Resolve one request to a deterministic component set.

        Args:
            request: Profile, opt-in, and skip selection.

        Returns:
            The resolved profiles, ordered components, and recorded skips.

        Raises:
            ValueError: If the profile or selection keys are unknown, or if
                selected component dependencies cannot be ordered.
        """
        profile_names = self._profile_names(request.profile)
        include_keys = set(request.includes)
        skip_keys = set(request.skips)
        known_includes = {
            component.include_key
            for component in self.components
            if component.include_key is not None
        }
        known_skips = {
            component.skip_key
            for component in self.components
            if component.skip_key is not None
        }
        unknown_includes = include_keys - known_includes
        unknown_skips = skip_keys - known_skips
        if unknown_includes:
            raise ValueError(f"unknown includes: {sorted(unknown_includes)}")
        if unknown_skips:
            raise ValueError(f"unknown skips: {sorted(unknown_skips)}")

        selected: list[Component] = []
        for component in self.components:
            if not profile_names.intersection(component.profiles):
                continue
            if component.skip_key in skip_keys:
                continue
            if (
                not component.enabled_by_default
                and component.include_key not in include_keys
            ):
                continue
            selected.append(component)
        return ResolvedSetup(
            profiles=tuple(sorted(profile_names)),
            components=self._dependency_order(selected),
            skipped=tuple(sorted(skip_keys)),
        )

    def interface_lines(self) -> tuple[str, ...]:
        """Return the stable profile, include, and skip interface."""
        includes = {
            component.include_key
            for component in self.components
            if component.include_key
        }
        skips = {
            component.skip_key
            for component in self.components
            if component.skip_key
        }
        return tuple(
            [f"profile {name}" for name in sorted(self.profiles)]
            + [f"include {name}" for name in sorted(includes)]
            + [f"skip {name}" for name in sorted(skips)]
        )
