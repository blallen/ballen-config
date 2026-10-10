"""Unified-diff hunk walking shared by the provider adapters."""

import re
from collections.abc import Iterator
from typing import Final, NamedTuple

_HUNK: Final[re.Pattern[str]] = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class HunkLine(NamedTuple):
    """Line numbers of one commentable line in a unified diff."""

    old_line: int | None
    new_line: int | None


def hunk_lines(patch: str) -> Iterator[HunkLine]:
    """Yield the line numbers of every added, removed, and context line.

    An added line has no `old_line`, a removed line has no `new_line`, and an
    unchanged context line has both. Text before the first hunk header and
    `\\ No newline at end of file` markers advance neither counter. The patch is
    split on newlines only: `str.splitlines()` also splits on characters such
    as form feed, which can occur inside a source line.

    Args:
        patch: Unified diff hunks for one file.

    Yields:
        One `HunkLine` per commentable line, in diff order.
    """
    old_line: int | None = None
    new_line: int | None = None
    for text in patch.split("\n"):
        hunk = _HUNK.match(text)
        if hunk is not None:
            old_line, new_line = int(hunk.group(1)), int(hunk.group(2))
        elif old_line is None or new_line is None:
            continue
        elif text.startswith("+"):
            yield HunkLine(None, new_line)
            new_line += 1
        elif text.startswith("-"):
            yield HunkLine(old_line, None)
            old_line += 1
        elif text.startswith(" "):
            yield HunkLine(old_line, new_line)
            old_line += 1
            new_line += 1
