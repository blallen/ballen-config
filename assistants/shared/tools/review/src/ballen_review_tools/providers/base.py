"""No-shell command execution primitives for provider adapters."""

import subprocess
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


class SubprocessRunner:
    """Run fixed provider argument arrays without a shell."""

    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CompletedCommand:
        """Return bounded subprocess output and status."""
        result = subprocess.run(
            list(argv),
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
        return CompletedCommand(result.returncode, result.stdout, result.stderr)


def failure_detail(result: CompletedCommand, *, limit: int = 200) -> str:
    """Summarize a failed command without its response body.

    `gh` and `glab` print the HTTP status line first on stderr and the
    response body after it, so only that first line is kept.

    Args:
        result: The failed command result.
        limit: Maximum characters kept from the stderr line.

    Returns:
        The first non-empty stderr line, truncated to `limit`, or the exit
        status when stderr is empty.
    """
    line = next(
        (line.strip() for line in result.stderr.splitlines() if line.strip()), ""
    )
    return line[:limit] or f"exit status {result.returncode}"
