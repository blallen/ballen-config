"""No-shell command execution primitives for provider adapters."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CompletedCommand:
    """Bounded result from one reviewed command invocation."""

    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    """Run one reviewed argument vector without a shell."""

    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CompletedCommand:
        """Return bounded stdout, stderr, and status."""
