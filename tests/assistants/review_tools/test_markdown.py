"""Tests for the deterministic review Markdown grammar."""

from ballen_review_tools.markdown import parse_review_markdown
from ballen_review_tools.models import ReviewIdentity

IDENTITY = ReviewIdentity(
    provider="github",
    host="github.com",
    repository="ballen-config",
    change_number=17,
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
    actions = parse_review_markdown(REVIEW, identity=IDENTITY)

    assert [action.action_id for action in actions] == ["R001", "R002"]
    assert [action.selected for action in actions] == [True, False]
    assert actions[1].body == "This remains useful context."


def test_heading_inside_a_fence_does_not_start_an_action() -> None:
    """Do not split a comment body on fenced example Markdown."""
    draft = """### R001: Explain the parser

**Type:** general
**POST:** YES

```markdown
### R999: This is body text
```
"""

    actions = parse_review_markdown(draft, identity=IDENTITY)

    assert len(actions) == 1
    assert "R999" in actions[0].body
