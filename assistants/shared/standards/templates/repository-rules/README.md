# Repository rule starter

## Ownership

These files are passive, copy-once seeds. After copying, each target becomes a
repository-owned snapshot. Inspect an existing target and merge or adapt the
baseline deliberately; never overwrite repository instructions silently.

## Default

The Default copy uses `AGENTS.md` as the single concise baseline:

- Copy `AGENTS.md` for Codex, Cursor, or a multi-agent repository. Both Codex
  and Cursor discover it natively.
- Also copy `CLAUDE.md` when using Claude Code. Its native `@AGENTS.md` import
  delegates to the canonical baseline instead of storing another copy.

Use `.cursor/rules/` only for genuinely Cursor-specific or scoped additions.
Cursor CLI loads root `AGENTS.md` and `CLAUDE.md` alongside project rules, so
duplicating the baseline there wastes context and creates another copy that can
drift.

## All

The All copy includes the Default entries plus these detailed standards:

- `../../README.md` to `docs/engineering-standards/README.md`
- `../../python.md` to `docs/engineering-standards/python.md`
- `../../pydantic.md` to `docs/engineering-standards/pydantic.md`
- `../../validation.md` to `docs/engineering-standards/validation.md`
- `../../api-design.md` to `docs/engineering-standards/api-design.md`
- `../../testing.md` to `docs/engineering-standards/testing.md`
- `../../documentation.md` to `docs/engineering-standards/documentation.md`
- `../../source-control.md` to `docs/engineering-standards/source-control.md`
- `../../dependency-management.md` to
  `docs/engineering-standards/dependency-management.md`

Tooling templates remain a separate, opt-in bundle. Do not copy the standards
directory wholesale.

## Narrower migrations

For a narrower migration, copy the required source and destination paths
directly. There is no installer or file-selector command.
