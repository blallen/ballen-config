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

## `compile-response`

`review-plan compile-response` turns a Markdown response draft into a
`review-response-plan/v1` artifact for one `normalized-review-threads/v1`
file. It does not construct provider clients. It writes the plan only when the
checkout's origin and head match the threads identity and the output is inside
an ignored, untracked workspace directory.

The draft has one section per thread. A section starts with a level-three
heading, `### <thread-id>: <title>`, where `<thread-id>` is a `thread_id` from
the threads file. Bold fields follow, one per line, with no blank line between
them:

| Field | Required | Value |
| --- | --- | --- |
| `**Classification:**` | Yes | `actionable`, `question`, `discussion`, `resolved`, or `informational` |
| `**Selected action:**` | Yes | `skip`, `propose-change`, or `propose-response` |
| `**Evaluation:**` | Yes | Whether the feedback is technically valid |
| `**Evidence:**` | Yes | What the evaluation rests on |
| `**Proposed changes:**` | For `propose-change` | One proposed change |
| `**Proposed response:**` | For `propose-response`, unless the section has text | The reply to propose |
| `**Verification:**` | No | One verification step |

Text after the fields, separated by a blank line, is the proposed response and
may span paragraphs. A section that has both that text and a
`Proposed response` field is rejected. `none`, `null`, or `-` leaves an
optional field empty.

Every thread that is not resolved needs a section. A resolved thread without
one is kept as a `skip` item classified `resolved`. The plan's
`source_threads_digest` is the value `review-plan digest --artifact` prints for
the threads file. Thread limitations stay in the threads file; the plan does
not copy them.

For example, with `.reviews/` ignored and `.reviews/threads.json` holding one
open thread `T001`, write `.reviews/response.md`:

```markdown
### T001: Guard the empty case

**Classification:** actionable
**Selected action:** propose-change
**Evaluation:** The feedback is valid.
**Evidence:** `load_items` iterates the result without checking it.
**Proposed changes:** Return early when the result is empty.
**Verification:** focused unit test for the empty result

I will add the guard and a focused test for the empty result.
```

Then validate the threads file and compile the plan from the repository root:

```bash
~/.local/share/ballen-config/review-tools/bin/review-plan validate --artifact .reviews/threads.json
~/.local/share/ballen-config/review-tools/bin/review-plan compile-response \
  --threads .reviews/threads.json \
  --draft .reviews/response.md \
  --output .reviews/response-plan.json \
  --repo-root .
```

## `review-plan normalize-threads`

`normalize-threads` turns one captured provider response into a
`normalized-review-threads/v1` snapshot. It reads local files only and never
calls GitHub or GitLab. The output must sit in an ignored, untracked workspace
directory such as `.reviews/`.

### GitHub

Use `using-github` to read the pull request's current head SHA and every page
of its review comments (`GET /repos/{owner}/{repo}/pulls/{number}/comments`).
Save them as one JSON object, keeping each comment as GitHub returns it:

```json
{
  "head_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "review_comments": [
    {
      "id": 10,
      "user": {"login": "reviewer"},
      "body": "Guard the empty case.",
      "path": "src/example.py",
      "line": 20,
      "side": "RIGHT"
    },
    {"id": 11, "in_reply_to_id": 10, "user": {"login": "author"}, "body": "Done."}
  ]
}
```

`head_sha` must equal `head_revision` in the same identity file that
`compile-review` reads. From the repository root:

```bash
~/.local/share/ballen-config/review-tools/bin/review-plan normalize-threads \
  --provider github \
  --identity .reviews/identity.json \
  --input .reviews/github-comments.json \
  --output .reviews/threads.json \
  --repo-root .
```

Each root comment becomes one thread that lists the root and its replies in
order. A comment side other than `LEFT` or `RIGHT` stops normalization with an
error. The snapshot records what the REST capture cannot show instead of
guessing:

- REST comments carry no resolution state, so threads are `open` or `outdated`.
- A body over 10,000 characters is truncated, and its thread records that.
- Replies not attached to a captured root comment, such as a reply to a reply,
  are listed by ID in one snapshot limitation.

For GitLab, `using-gitlab` supplies a captured MR response containing
`diff_refs` and `discussions`; normalization remains local and read-only:

```text
review-plan normalize-threads --provider gitlab --identity PATH \
  --input PATH --output PATH --repo-root PATH
```
