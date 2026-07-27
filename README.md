# ballen-config

Portable, agent-friendly setup for a personal/work macOS development machine.

## Quick start

Run `./bootstrap --profile work` for the work setup, or `./bootstrap` for the
default personal development baseline.

Run `prepare`, `plan`, `install`, `configure`, and `doctor` independently when
reviewing or repairing one stage. In particular, use `./bootstrap plan` before
allowing any mutation.

## Why this bootstrap is structured this way

The Zsh entry point exists only to bridge a clean Mac to Command Line Tools,
Homebrew, `uv`, and Python 3.12. Everything after that boundary runs in the
frozen Python environment, so manifest parsing, validation, path safety,
installation, and diagnostics are typed and testable.

The manifests are the inventory authority. This repository records intentional
software and configuration rather than replaying every transitive package that
Homebrew happened to install. Every mutating flow prints a structural plan
before confirmation. Existing unmanaged files are preserved beneath a
timestamped private backup before replacement, and a second run is a no-op when
desired and actual state match.

The bootstrap is intentionally readable rather than fully unattended. Its
reports and exceptions use normalized, agent-readable outcomes instead of
native command output, so a coding agent can help resolve machine-specific
exceptions without weakening the safety boundary.

## Profiles

`default` installs the broad portable development baseline. `work` extends it
with AWS tooling, work-specific prerequisites, and reviewed coding-agent
overlays. Repository-specific behavior belongs in add-ons, not the base
profile.

Repeated `--include` flags opt into personal applications such as Obsidian,
Signal, and full MacTeX. Repeated `--skip` flags are global selections: they
remove Cursor, Claude Code, Codex, or Wave as whole components from every
applicable stage. For example, `./bootstrap --profile work --skip wave` keeps
the remainder of the work profile while leaving the terminal choice unmanaged.

## Software choices

Wave is the default terminal trial. The bootstrap does not uninstall iTerm, so
it remains an easy fallback while Wave is evaluated.

The `mactex` include installs the full MacTeX distribution matching this
laptop's TUG MacTeX/TeX Live setup, not BasicTeX. It is opt-in because the
download and disk footprint are large.

`libmagic` belongs to the work profile because it is a direct runtime
prerequisite for repositories using `python-magic`, including Plato and code
inherited by Avogadro. Homebrew resolves its transitive dependencies; only
intentional formulae and casks are declared here.

`glab` is included so GitLab authentication, merge-request work, and other
reviewed GitLab operations use the supported CLI rather than stored tokens or
ad hoc API scripts.

## Coding-agent portability

Cursor, Claude Code, and Codex are optional whole components. Skipping one
with `--skip cursor|claude-code|codex` removes its application, native
configuration, extensions or plugins, hooks, skills, sign-in reminders, and
required diagnostics while remaining agents still receive targeted shared
resources. Canonical shared sources are translated by native adapters with
explicit collision rejection; the agents do not share configuration formats.

Cursor uses a base settings file plus a work-only Bedrock overlay. Curated
feature extensions include Jupyter's transitive support, and the optional JJ
Graph extension is a pinned VSIX. Claude and Codex use their native plugin
catalogs. The abandoned experimental marketplace setup is not part of desired
state. Use each agent's first-party browser capability rather than a global
Playwright MCP, GitLab through `glab`, and official Notion integrations. Cursor
User Rules and some first-party capabilities are deliberate manual steps.

`jujutsu-workflow` is the first reviewed shared skill. It is stored once in
this desired-state repository and independently copied into each selected
agent's native skill root; this does not depend on Cursor third-party
auto-import. Only generic skills are promoted into the shared catalog;
repository-specific skills remain in add-ons. Sessions, history, memories,
auth, trust, worktrees, caches, indexes, and generated plugin state are
excluded. Memory migration is not an MVP capability.

## Security and state boundary

Git owns reviewed manifests, dotfiles, application settings, instructions, and
portable tooling declarations. Credentials, OAuth state, SSH private keys,
sessions, histories, caches, indexes, trust databases, worktrees, and
repository-specific setup never enter this repository.

Local ownership checksums and timestamped backups live mode-private beneath
`~/.local/state/ballen-config`. Configuration destinations remain constrained
to the user's home directory, and source or destination symlink escapes are
rejected before mutation.

## Manual steps

Use [manual steps](docs/manual-steps.md) for GitHub, GitLab, work AWS, SSH, and
IT-managed applications. Use the
[SSH transfer guide](docs/ssh-transfer.md) for keys and private host entries;
the repository never stores keys. The bootstrap installs portable GitHub and
GitLab SSH defaults in `~/.ssh/config` and keeps machine-specific entries in
the included `~/.ssh/config.local`. The approved design remains in the
[laptop migration bootstrap design](docs/superpowers/specs/2026-07-25-laptop-migration-bootstrap-design.md).
