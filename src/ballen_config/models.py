from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Manager(StrEnum):
    """Supported installation mechanisms."""

    BREW_FORMULA = "brew_formula"
    BREW_CASK = "brew_cask"
    GIT = "git"


class Component(BaseModel):
    """One intentional installable component."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    manager: Manager
    package: str
    profiles: tuple[str, ...] = ("default",)
    destination: str | None = None
    depends_on: tuple[str, ...] = ()
    application_paths: tuple[str, ...] = ()
    receipt_prefixes: tuple[str, ...] = ()
    enabled_by_default: bool = True
    include_key: str | None = None
    skip_key: str | None = None
    required: bool = True
    large: bool = False

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        """Validate selection metadata and destination safety."""
        if not self.enabled_by_default and self.include_key is None:
            raise ValueError("optional components require include_key")
        if self.manager is Manager.GIT and self.destination is None:
            raise ValueError("git components require destination")
        if self.destination is not None:
            destination = Path(self.destination)
            if destination.is_absolute() or ".." in destination.parts:
                raise ValueError("component destination must be home-relative")
        return self


class ComponentFile(BaseModel):
    """Manifest file containing components."""

    model_config = ConfigDict(extra="forbid")

    components: tuple[Component, ...]


class Profile(BaseModel):
    """Named additive profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    extends: tuple[str, ...] = ()


class ResolutionRequest(BaseModel):
    """User selection supplied to all stages."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str = "default"
    includes: tuple[str, ...] = ()
    skips: tuple[str, ...] = ()


class ResolvedSetup(BaseModel):
    """Deterministic resolved component set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profiles: tuple[str, ...]
    components: tuple[Component, ...]
    skipped: tuple[str, ...]

    def is_enabled(self, component_id: str) -> bool:
        """Return whether a component survived selection."""
        return any(component.id == component_id for component in self.components)
