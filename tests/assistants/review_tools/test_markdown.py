"""Tests for the deterministic review Markdown grammar."""

from ballen_review_tools.markdown import parse_review_markdown
from ballen_review_tools.models import ReviewIdentity

IDENTITY = ReviewIdentity(
    provider="github",
    host="github.com",
    repository="ballen-config",
    change_number=17,
    base_revision="a" * 40,
    head_revision="b" * 40,
)

REVIEW = """### R001: Guard the empty case

**Type:** inline
**File:** src/example.py
**Line:** 20
**Side:** RIGHT
**POST:** YES

Guard the empty case.

### R002: Explain the tradeoff

**Type:** general
**POST:** NO

This remains useful context.
"""


def test_parser_retains_selected_and_unselected_items() -> None:
    """Keep skipped evidence in the logical action list."""
    parsed = parse_review_markdown(REVIEW, identity=IDENTITY)
    actions = parsed.actions

    assert [action.action_id for action in actions] == ["R001", "R002"]
    assert [action.selected for action in actions] == [True, False]
    assert actions[1].body == "This remains useful context."
    assert parsed.diagnostics == ()


def test_heading_inside_a_fence_does_not_start_an_action() -> None:
    """Do not split a comment body on fenced example Markdown."""
    draft = """### R001: Explain the parser

**Type:** general
**POST:** YES

```markdown
### R999: This is body text
```
"""

    actions = parse_review_markdown(draft, identity=IDENTITY).actions

    assert len(actions) == 1
    assert "R999" in actions[0].body


def test_parser_supports_tilde_fences() -> None:
    """Do not split a comment body on a tilde-fenced heading."""
    draft = REVIEW.replace(
        "Guard the empty case.\n\n### R002",
        "~~~markdown\n### R999: This is body text\n~~~\n\nGuard the empty case.\n\n### R002",
    )

    parsed = parse_review_markdown(draft, identity=IDENTITY)

    assert [action.action_id for action in parsed.actions] == ["R001", "R002"]


def test_parser_reports_an_unclosed_fence() -> None:
    """Preserve incomplete coverage when a fence remains open at EOF."""
    draft = """### R001: Explain the parser

**Type:** general
**POST:** YES

```markdown
### R002: This heading is swallowed by the open fence

**Type:** general
**POST:** YES

This coverage cannot be classified safely.
"""

    parsed = parse_review_markdown(draft, identity=IDENTITY)

    assert parsed.actions == ()
    assert [diagnostic.action_id for diagnostic in parsed.diagnostics] == ["R001"]
    assert "unclosed fenced block" in parsed.diagnostics[0].reason


def test_parser_reports_all_malformed_sections() -> None:
    """Retain bounded diagnostics instead of stopping at the first error."""
    draft = """### R001: Missing line

**Type:** inline
**File:** src/example.py
**Side:** RIGHT
**POST:** YES

Body.

### R002: Unknown type

**Type:** mystery
**POST:** YES

Body.
"""

    parsed = parse_review_markdown(draft, identity=IDENTITY)

    assert parsed.actions == ()
    assert [diagnostic.action_id for diagnostic in parsed.diagnostics] == [
        "R001",
        "R002",
    ]


def test_parser_rejects_ambiguous_thread_metadata() -> None:
    """Do not choose silently between provider-native thread fields."""
    draft = """### R001: Reply

**Type:** reply
**Discussion:** discussion-1
**Thread:** thread-1
**POST:** YES

Reply.
"""

    parsed = parse_review_markdown(draft, identity=IDENTITY)

    assert parsed.actions == ()
    assert "ambiguous" in parsed.diagnostics[0].reason
