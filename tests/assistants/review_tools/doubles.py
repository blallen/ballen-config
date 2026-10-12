"""Shared test doubles for the review-tool tests."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from ballen_review_tools.providers.base import CompletedCommand


@dataclass
class RecordingRunner:
    """Return queued command responses and record every invocation."""

    responses: list[CompletedCommand] = field(default_factory=list)
    calls: list[tuple[Sequence[str], str | None]] = field(default_factory=list)

    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CompletedCommand:
        """Record one no-shell command and return its next queued response."""
        self.calls.append((tuple(argv), input_text))
        return self.responses.pop(0)
