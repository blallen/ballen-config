# Ruff Single Source Design

## Status

Implemented on 2026-08-02 in the `ruff-single-source` branch, which follows the
uv tool manager and Homebrew presence work already in `main`. It amends the
*Out of scope* section of the
[uv tool manager design](2026-08-01-uv-tool-manager-design.md), which named
`.pre-commit-config.yaml` as a second authoritative version source.

## Context

Ruff's version was declared twice:

- `.pre-commit-config.yaml` pinned `ruff-pre-commit` at `rev: v0.15.1`, and
  pre-commit built an isolated environment from it.
- `pyproject.toml` carried a floating `ruff>=0.15` in the `dev` group, which
  `uv.lock` resolved to `0.16.0`.

Nothing forced the two to agree, and they had already diverged. Ruff 0.16
formats Python code blocks inside Markdown and 0.15 does not, so
`uv run ruff format --check .` reported nine plan documents as unformatted
while CI passed on the pinned hook. A self-review of the uv tool manager
branch reproduced the split.

The immediate repair pinned `pyproject.toml` to `==0.15.1` so both
declarations matched. That closed the divergence but left the parity as a
comment-enforced invariant: a later edit could bump one side and not the
other, reproducing the same failure.

## Decision

Make `uv.lock` the single source of the Ruff version.

`.pre-commit-config.yaml` no longer declares a Ruff version. The
`ruff-pre-commit` repository entry is replaced by two `local` hooks that
invoke the locked environment directly, matching the existing
`ballen-config policy` hook:

```yaml
- id: ruff-check
  name: ruff check
  entry: uv run --frozen --no-sync ruff check --force-exclude --fix
  language: system
  types_or: [python, pyi, jupyter]
  require_serial: true
```

`--force-exclude` is required because pre-commit passes explicit filenames,
which otherwise cause Ruff to ignore `extend-exclude`.

`types_or` and `require_serial` are copied from the upstream `ruff-pre-commit`
hook definition these replace, so the only intended difference is where Ruff
comes from. `jupyter` matches upstream even though no notebook is tracked
today, because a hook that silently skips a file type is worse than one that
covers a type the repository does not yet have.

`pyproject.toml` returns to a floating `ruff>=0.15` constraint. The exact
version is whatever `uv.lock` records, so upgrading is one deliberate command:

```bash
uv lock --upgrade-package ruff
```

CI already runs `uv sync --frozen` before the hooks, so the locked interpreter
and tools are present when they execute.

## Markdown scope

Ruff 0.16 formats Python code blocks inside Markdown, which the pinned 0.15.1
did not. This change takes the upgrade and formats the nine affected plan
documents rather than excluding Markdown from Ruff.

Excluding it was the first approach, on the argument that the documents are
historical records whose snippets are transcripts rather than maintained
source. Inspecting the actual reformat did not support that:

- No prose changed. All 917 changed lines fall inside `python` fences, and the
  fence count per document is unchanged.
- The churn is line rewrapping. Over-wrapped calls collapse onto one line, and
  five snippets that exceeded the repository's own 88-character limit gained
  the wrapping the limit requires.
- Formatting made the snippets consistent with the style enforced on real
  source, which is the opposite of damaging the record.

An exclusion would also have been an inert guard: with Ruff pinned at 0.15.1,
deleting `"*.md"` from `extend-exclude` changed no check result, because that
version does not format Markdown at all. Nothing in CI or the hook set would
have failed if the line were removed, yet removing it is precisely what makes
a later upgrade rewrite the documents. The protection would only have been
observable at the moment it was already too late to notice.

### Snippet indentation

Ruff formats each fenced block as a standalone module, so a block it rewrites
is also dedented to column zero. Counting blocks that fail to parse makes the
effect visible: across the change that count falls from twenty-one to sixteen.

The formatter dedented four of those five. One mattered: a method snippet in
the uv tool manager plan lost the four-space indent that showed it belonged
inside `Installer`, leaving a top-level `def _uv_tool(self, ...)` whose `self`
no longer made sense. The other three are statement-level snippets in the PR 2
agent review fixes plan, and they keep their meaning because the prose above
each one names the test function the statements belong to. There the
indentation was carrying information the sentence already gave.

Blocks are only rewritten when they need formatting, so the `install` snippet
beside `_uv_tool` kept its indentation and stayed an unparseable fragment.
Left alone, the two presentations in one document would diverge further as
individual blocks happened to need changes.

Both are now written as an explicit `class Installer:` with the method nested
inside, which accounts for the fifth block. That form is a valid module, so the
formatter preserves its indentation and the class context survives future
upgrades.

Sixty-eight indented method snippets remain across the other plan documents.
They are untouched here and will dedent individually whenever they next need
formatting; converting them is not worth a mechanical sweep of historical
documents.

## Tradeoffs

The `local` hooks depend on a synced environment, so `uv sync` must have run
before `pre-commit` on a fresh checkout. The previous configuration let
pre-commit build Ruff itself. This repository already accepted that dependency
for the `ballen-config policy` hook, and CI syncs before running hooks, so the
cost is a clearer error on an unprepared checkout rather than a new class of
failure.

Pinning both declarations to the same literal version was the alternative. It
is a smaller diff, but it keeps two declarations and relies on a comment to
hold them together, which is the arrangement that failed.

Taking the upgrade puts roughly 900 lines of documentation reformatting in the
same change as the configuration it justifies. The alternative was a separate
follow-up, which would have left an inert exclusion on `main` in the meantime
and split one decision across two reviews.

## Out of scope

- `assistants/shared/standards/templates/python/.pre-commit-config.yaml`. That
  starter configuration is data for other repositories, some of which will not
  use uv, so it keeps the pinned `ruff-pre-commit` entry.
- Automated dependency upgrades. Whether a bot proposes
  `uv lock --upgrade-package` runs is a separate decision from where the
  version is declared.
