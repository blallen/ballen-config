# ballen-config

Portable, agent-friendly setup for a personal/work macOS development machine.

## Quick start

Run `./bootstrap --profile wsh` for the current-job setup, `./bootstrap --profile fsp`
for the previous-job setup, or `./bootstrap` for the default personal development
baseline.

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

`default` is the baseline. `wsh` adds current-job extra env. `fsp` adds AWS CLI,
`libmagic`, Bedrock overlay, and Atlassian MCP. Includes: Obsidian, Signal,
MacTeX, `glab`. Skips: Cursor, Claude Code, Codex. Example:
`./bootstrap --profile wsh --skip codex`.

## Software choices

There is no dedicated terminal in desired state. iTerm remains an unmanaged
fallback.

The `mactex` include installs the full MacTeX distribution matching this
laptop's TUG MacTeX/TeX Live setup, not BasicTeX. It is opt-in because the
download and disk footprint are large.

`libmagic` belongs to the `fsp` profile because it is a direct runtime
prerequisite for repositories using `python-magic`. Homebrew resolves its
transitive dependencies; only intentional formulae and casks are declared here.

`glab` is included with `--include glab` so GitLab authentication,
merge-request work, and other reviewed GitLab operations use the supported CLI
rather than stored tokens or ad hoc API scripts.

## Coding-agent portability

Cursor, Claude Code, and Codex are optional whole components. Skipping one
with `--skip cursor|claude-code|codex` removes its application, native
configuration, extensions or plugins, hooks, skills, sign-in reminders, and
required diagnostics while remaining agents still receive targeted shared
resources. Canonical shared sources are translated by native adapters with
explicit collision rejection; the agents do not share configuration formats.

`ballen-config` is the only desired-state source for coding agents. A shared,
target-aware catalog can declare a capability for several agents, while native
Cursor, Claude Code, and Codex adapters independently install and inspect only
their own destinations and native identifiers. The adapters do not synchronize
live configuration between agents or use one agent's installed files as input.

Cursor uses a base settings file plus an `fsp`-only Bedrock overlay. Curated
feature extensions include Jupyter's transitive support, and the optional JJ
Graph extension is a pinned VSIX. Claude Code and Codex use their respective
native marketplace commands. The production Cursor marketplace and local-plugin
lists are intentionally empty; a later reviewed Cursor marketplace entry stays
a visible manual Customize checklist item, and a reviewed local plugin is copied
only to `~/.cursor/plugins/local/<name>/`. Cursor User Rules and some
first-party capabilities are deliberate manual steps. Cursor User Rules are
imported as three separate handoffs (engineering defaults, RTK, and Cursor
additions). Use each agent's first-party browser capability rather than a
global Playwright MCP, GitHub through `gh` by default (GitLab through `glab`
when the remote is GitLab), and official Notion integrations.

The `fsp` profile has one narrow MCP exception: it manages a secret-free
Atlassian HTTP entry in `~/.cursor/mcp.json` because Cursor's official
Atlassian integration is currently unreliable for this account. The reviewed
endpoint is `https://mcp.atlassian.com/v1/mcp/authv2`; OAuth still happens on
the destination machine, and no token is stored here. Any additional server,
field, or endpoint remains unmanaged drift. Playwright and GitLab MCP servers
remain excluded.

`using-jujutsu` is the first reviewed shared skill. It is stored once in
this desired-state repository and independently copied into each selected
agent's native skill root. Cursor cross-tool import is neither configured nor
required: disabling **Include Third-Party Plugins, Skills, and Other Configs**
is recommended for a clearer independently managed view, but bootstrap
correctness and idempotency are the same when that Cursor preference is enabled.
Only generic skills are promoted into the shared catalog; repository-specific
skills remain in add-ons. A reviewed Cursor local plugin is a separate,
repository-owned tree, and its declared skills must not collide with any
Cursor-targeted shared skill. Sessions, history, memories, auth, trust,
worktrees, caches, indexes, and generated plugin state are excluded. Memory
migration is not an MVP capability.

## Security and state boundary

Git owns reviewed manifests, dotfiles, application settings, instructions, and
portable tooling declarations. Credentials, OAuth state, SSH private keys,
sessions, histories, caches, indexes, trust databases, worktrees, and
repository-specific setup never enter this repository.

Local ownership checksums and timestamped backups live mode-private beneath
`~/.local/state/ballen-config`. Configuration destinations remain constrained
to the user's home directory, and source or destination symlink escapes are
rejected before mutation.

Executable bootstrap inputs are immutable at the repository boundary. The
stage-zero Homebrew installer is pinned to a reviewed revision and verified by
SHA-256 before Bash runs it. Git-managed shell components likewise declare an
exact commit. Existing checkouts are reused or advanced only when they have the
expected HTTPS origin and a clean worktree; a dirty checkout or unexpected
origin is left untouched for manual review.

## Manual steps

Use [manual steps](docs/manual-steps.md) for GitHub, GitLab, work AWS, SSH, and
IT-managed applications. Use the
[SSH transfer guide](docs/ssh-transfer.md) for keys and private host entries;
the repository never stores keys. The bootstrap installs portable GitHub and
GitLab SSH defaults in `~/.ssh/config` and keeps machine-specific entries in
the included `~/.ssh/config.local`. The approved design remains in the
[laptop migration bootstrap design](docs/superpowers/specs/2026-07-25-laptop-migration-bootstrap-design.md)
and its [coding-agent desired-state amendment](docs/superpowers/specs/2026-07-26-coding-agent-desired-state-consolidation-design.md).
