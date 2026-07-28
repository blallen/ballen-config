from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict


class RuntimePaths(BaseModel):
    """Approved roots injected into every filesystem operation."""

    model_config = ConfigDict(frozen=True)

    repo_root: Path
    home: Path
    state_root: Path
    backup_root: Path

    @classmethod
    def from_roots(
        cls,
        *,
        repo_root: Path,
        home: Path,
    ) -> Self:
        """Construct normalized repository and private state roots."""
        normalized_home = home.resolve()
        state_root = normalized_home / ".local/state/ballen-config"
        return cls(
            repo_root=repo_root.resolve(),
            home=normalized_home,
            state_root=state_root,
            backup_root=state_root / "backups",
        )
