# Ballen Review Tools

This locked Python project provides deterministic local review planning and
provider-specific publication commands. The canonical source is installed by
`ballen-config`; credentials and provider authentication remain owned by the
existing `gh`, `glab`, or connected provider environment.

## `review-plan`

Run every subcommand through the installed launcher,
`~/.local/share/ballen-config/review-tools/bin/review-plan`. The `digest`,
`validate`, and `workspace-check` subcommands only read their inputs. Each
other subcommand writes one JSON artifact after proving that its output path is
safe. No subcommand contacts a forge.

### `compile-review`

`compile-review` turns a Markdown review draft into a `review-comment-plan/v1`
JSON plan. It takes an identity file that names the change under review:

```json
{
  "provider": "github",
  "host": "github.com",
  "repository": "owner/name",
  "change_number": 17,
  "base_revision": "<base commit SHA>",
  "head_revision": "<head commit SHA>"
}
```

- `provider` is `github` or `gitlab`, and `change_number` is the pull-request
  or merge-request number.
- `host` and `repository` must match the checkout's `origin` remote.
  `repository` should be the full `owner/name` (GitHub) or
  `namespace/project` (GitLab) path, because publication requires it.
- `head_revision` must equal the checked-out `HEAD`.
- No value may start with `/` or contain a backslash or whitespace.

The draft holds one section per review action:

```markdown
### R001: Guard the empty case

**Type:** inline
**File:** src/example.py
**Line:** 20
**Side:** RIGHT
**POST:** YES

The empty result is dereferenced. Return early when it is empty.
```

- Each action starts with a level-three heading, `### <ID>: <title>`, outside
  fenced code blocks. The ID starts with a letter or digit and continues with
  letters, digits, `.`, `_`, or `-`. IDs are unique within a draft.
- The metadata fields form one contiguous block of `**Field:** value` lines
  under the heading. The comment body starts after the first blank line below
  that block and must not be empty.
- `**Type:**` is `inline`, `general`, or `reply`, and `**POST:**` is `YES` or
  `NO`. Both are required.
- An `inline` action needs `**File:**` (a repository-relative path),
  `**Line:**`, and `**Side:**` (`LEFT` or `RIGHT`). A range adds
  `**Start line:**` and `**Start side:**`.
- A `reply` action names its thread in `**Thread:**` or `**Discussion:**`, not
  both, and has no location.
- A `general` action has no location or thread.

`POST: YES` selects an action for a later preview; it does not authorize
publication. A malformed section becomes a diagnostic in the plan instead of an
action, so the sections after it still compile.

Run it from the repository root. The output directory must already exist, and
Git must ignore it and track nothing in it:

```sh
~/.local/share/ballen-config/review-tools/bin/review-plan compile-review \
  --draft .reviews/pr-17/review.md \
  --identity .reviews/pr-17/identity.json \
  --output .reviews/pr-17/review-plan.json \
  --repo-root .
~/.local/share/ballen-config/review-tools/bin/review-plan validate \
  --artifact .reviews/pr-17/review-plan.json
```

The second command prints `valid`.
