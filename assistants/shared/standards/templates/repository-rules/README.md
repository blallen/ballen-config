# Repository rule starter

## Ownership

ballen-config is the canonical source for reusable guidance. Copy the declared
files unchanged as vendored snapshots, and record the source revision in the
downstream guidance commit message. Make generic corrections here first, then
refresh downstream copies.

Keep repository-specific instructions and explicit exceptions outside the
vendored topic files. Before refreshing an existing copy, inspect local changes
and preserve them deliberately; never overwrite repository instructions silently.

## Default

The Default copy uses `AGENTS.md` as the single concise baseline:

- Copy `AGENTS.md` for Codex, Cursor, and current Claude Code, including
  repositories used by several agents.
- Claude Code can read `AGENTS.md` directly when no project or parent
  `CLAUDE.md` or `CLAUDE.local.md` takes precedence. A wrapper is unnecessary
  in that setup.
- `CLAUDE.md` remains an optional compatibility entry for clients or sessions
  that cannot load `AGENTS.md` directly, or for Claude-specific instructions.
  Its `@AGENTS.md` import keeps the shared instructions in one place.

See [Claude Code's AGENTS.md documentation](https://code.claude.com/docs/en/memory#agentsmd)
for supported versions, instruction-file precedence, and compatibility cases.

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
