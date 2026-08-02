# Ruff Single Source Design

## Status

Implemented on 2026-08-02 in the `ruff-single-source` branch, stacked on the
Homebrew presence work. It amends the *Out of scope* section of the
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
  entry: uv run --frozen --no-sync ruff check --force-exclude --fix
  language: system
  types_or: [python, pyi]
```

`--force-exclude` is required because pre-commit passes explicit filenames,
which otherwise cause Ruff to ignore `extend-exclude`.

`pyproject.toml` returns to a floating `ruff>=0.15` constraint. The exact
version is whatever `uv.lock` records, so upgrading is one deliberate command:

```bash
uv lock --upgrade-package ruff
```

CI already runs `uv sync --frozen` before the hooks, so the locked interpreter
and tools are present when they execute.

## Markdown scope

Ruff 0.16 would reformat Python code blocks in nine plan and spec documents.
Those documents are historical records of work already done; their embedded
snippets are transcripts, not source this repository maintains. Formatting
them would rewrite the record for no benefit and would make every future Ruff
upgrade produce unrelated documentation churn.

`extend-exclude` therefore gains `*.md`. Verified against both versions from
the repository root:

| Ruff | `extend-exclude` includes `*.md` | `ruff format --check .` |
| --- | --- | --- |
| 0.15.1 | yes | 70 files already formatted |
| 0.16.0 | yes | 70 files already formatted |
| 0.16.0 | no | 9 files would be reformatted |

The exclusion also keeps a bare `ruff format` in agreement with the hooks,
which pass only Python files.

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

## Out of scope

- `assistants/shared/standards/templates/python/.pre-commit-config.yaml`. That
  starter configuration is data for other repositories, some of which will not
  use uv, so it keeps the pinned `ruff-pre-commit` entry.
- Automated dependency upgrades. Whether a bot proposes
  `uv lock --upgrade-package` runs is a separate decision from where the
  version is declared.
