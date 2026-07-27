# Laptop Migration Bootstrap Design

**Status:** Approved

**Date:** 2026-07-25

**Implementation status:** The core bootstrap and coding-agent defaults are
implemented. Encrypted memory transfer remains a deferred add-on.

## Objective

Turn `ballen-config` from a mostly manual dotfile snapshot into a small,
agent-friendly macOS bootstrap that can reproduce the useful parts of the
current laptop on a replacement machine.

The bootstrap should be understandable and repairable by a coding agent. It
does not need to be a fully unattended fleet-management system. The design
therefore favors explicit manifests, readable Python, dry-run output, and
diagnostic guidance over elaborate automation.

## Goals

- Install the command-line tools, applications, fonts, and shell components
  used on the current laptop.
- Configure shell, Git, Jujutsu, Wave Terminal, Cursor, Claude Code, and Codex
  from stable, human-authored source files.
- Allow each coding agent to be skipped independently.
- Support a base personal-development setup and a small additive work profile.
- Replace brittle absolute paths and duplicated hooks with portable,
  repository-owned paths.
- Exclude secrets, authentication state, sessions, histories, caches, and
  machine-generated indexes.
- Design an optional encrypted transfer path for semantic memories and notes
  that may be deferred until after the core bootstrap is usable.
- Give a coding agent enough structure and diagnostics to finish any
  machine-specific setup interactively.
- Safely converge both the current laptop and a replacement laptop on the same
  configuration.

## Non-goals

- Fully unattended setup, including password, OAuth, or security-key prompts.
- Storing or transferring authentication material through Git.
- Reproducing IT-managed applications.
- Reproducing caches, chat transcripts, sessions, indexes, or generated plugin
  runtimes.
- Installing repository-specific development dependencies or configuration.
- Migrating or automatically deleting Cursor-created Git worktrees.
- Pinning one Python 3.12 patch release indefinitely.
- Guaranteeing that every third-party application continues to expose the same
  configuration format.

## Design Principles

1. **Human-readable state is authoritative.** The repository contains manifests
   and authored configuration rather than opaque application databases.
2. **Plan before mutation.** Every operation has a non-mutating preview.
3. **Back up before replacement.** Existing unmanaged files are preserved
   before a managed file changes.
4. **First-party integrations first.** Built-in browser tools and official
   authenticated connectors are preferred over locally maintained MCP servers.
5. **Repository configuration stays with the repository.** The generic laptop
   bootstrap has no repository profile or `--repo` option.
6. **Authentication is a destination-machine action.** The repository explains
   what to authenticate but never captures credentials.
7. **Minor-version stability is sufficient.** The bootstrap requests Python
   3.12 and accepts the latest available 3.12 patch.

## User Experience

The common path is a single command from a clone of this repository:

```bash
./bootstrap --profile work
```

With no stage argument, the command runs `plan`, `install`, `configure`, and
`doctor` in order. If the stage-zero runtime is missing, it first previews and
confirms the small `prepare` step. After the complete Python plan is displayed,
the combined command pauses again before package or configuration changes.
Each stage can also run independently:

```bash
./bootstrap prepare
./bootstrap plan --profile work
./bootstrap install --profile work
./bootstrap configure --profile work
./bootstrap doctor --profile work
```

Agent applications can be skipped independently:

```bash
./bootstrap --profile work --skip cursor --skip claude-code
```

`--skip codex` and `--skip wave` work the same way. Optional personal
applications are selected explicitly:

```bash
./bootstrap --profile work --include obsidian --include signal
./bootstrap install --include mactex
```

The option parser accepts repeated `--skip` and `--include` component values
and rejects unknown components before making changes. `plan` prints the
resolved profile, packages, applications, configuration actions, expected
prompts, and deferred manual work. A future memory-transfer add-on may
introduce a separate repeated `--source` option; it is not part of the current
command grammar or manifests.

A skipped component is removed as a unit from installation, configuration,
extensions, plugins, hooks, authentication prompts, and required diagnostics.
`doctor` reports it as intentionally skipped rather than missing. This applies
equally to Cursor, Claude Code, Codex, and Wave.

## Bootstrap Architecture

### Stage-zero shell shim

The top-level `bootstrap` file is a deliberately small Zsh script. It:

1. Confirms that the host is macOS.
2. Pre-parses the stage and supported option grammar.
3. Validates profile, include, and skip identifiers against a small
   `component-ids.txt` interface generated from and tested against the
   authoritative manifests.
4. Reports whether Xcode Command Line Tools, Homebrew, `uv`, and Python 3.12
   are available.
5. Runs the typed Python CLI with the original arguments when the runtime is
   ready.

The shim contains no package inventory or configuration policy. Its only job is
to validate the stable command interface and cross the bootstrapping gap before
Python is available.

`prepare` is the only stage whose purpose is to install stage-zero
prerequisites. It previews those actions and requires confirmation before
starting the standard interactive Apple installer or Homebrew operations.
After Python is present, it creates the repository's locked bootstrap
environment, including Pydantic 2.8, from the committed `uv.lock`. `install`
and the combined command may invoke the same confirmed preparation flow.

`plan` and `doctor` never install stage-zero dependencies. On a pristine
machine they print a shell-only prerequisite report and exit with a distinct
status directing the user to `./bootstrap prepare`. `configure` also refuses to
prepare its own runtime. A prepared runtime is executed with
`uv run --frozen --no-sync`; if the lock file or environment is absent or
inconsistent, read-only stages refuse to run rather than synchronize it.
Consequently, invalid input and every read-only stage remain non-mutating even
when Python or a project dependency is absent.

### Typed Python CLI

The implementation targets Python 3.12 and runs through `uv`. It uses:

- `argparse` for the command-line interface;
- Pydantic 2.8 models for manifest validation and profile resolution;
- typed subprocess and filesystem boundaries, including `TypedDict` where a
  dictionary-shaped external result is appropriate;
- Google-style docstrings;
- dependency injection for command execution and filesystem locations so tests
  never mutate the real machine.

The project requests `>=3.12,<3.13`. `uv` selects the latest compatible 3.12
patch, so the bootstrap gains patch-level security and bug fixes without
requiring updates to this repository.

### Repository layout

| Path | Responsibility |
|---|---|
| `bootstrap` | Cross the stage-zero runtime gap and dispatch the typed CLI. |
| `pyproject.toml`, `uv.lock` | Pin the Python 3.12 application environment. |
| `src/ballen_config/` | Resolve, install, configure, diagnose, and enforce policy. |
| `manifests/` | Define profiles, packages, applications, and stable component IDs. |
| `dotfiles/` | Store portable shell and version-control defaults. |
| `assistants/` | Store shared and agent-native reviewed configuration. |
| `terminal/wave/` | Store Wave Terminal settings. |
| `docs/` | Explain operation, manual work, and secure SSH transfer. |

The future memory-transfer add-on may add a Python module, manifests, commands,
and documentation after its encryption and conflict contracts are designed.

Tests mirror the Python package under `tests/`.

## Profiles and Software Inventory

Profiles are additive. `work` extends `default`; it does not duplicate the base
inventory. Optional personal applications remain command-line selections
rather than a third profile.

### Default profile

The default command-line inventory includes:

- `uv` and Python 3.12;
- `gh`;
- `glab`;
- `jj`;
- `node`;
- `ripgrep`;
- `rtk`;
- `pre-commit`;
- Oh My Zsh, Powerlevel10k, `zsh-autosuggestions`, `zsh-completions`,
  `zsh-syntax-highlighting`, and `forgit`.

The default application inventory includes:

- Wave Terminal;
- Cursor;
- Claude Code;
- Codex;
- Brave Browser;
- MesloLGS Nerd Font.

Cursor, Claude Code, Codex, and Wave are individually skippable. Wave is the
new default terminal on a trial basis. The bootstrap does not uninstall iTerm
or restore its configuration; iTerm remains an explicit fallback if the Wave
trial is unsuccessful.

### Work profile

The work profile adds:

- `libmagic`;
- AWS CLI;
- documentation and diagnostics for work-wide authenticated integrations.

`libmagic` is a direct runtime prerequisite for repositories that use
`python-magic`, including Plato and code inherited by Avogadro. It is therefore
an intentional work-profile formula rather than an accidental Homebrew leaf.

Repository dependencies, virtual environments, project MCP servers, and
project-specific rules remain in their owning repositories.

### Optional personal applications

The following Homebrew casks are opt-in:

- Obsidian;
- Signal;
- MacTeX.

The current machine has the full MacTeX 2025 distribution, including its GUI
and TeX Live 2025, installed through the TUG vendor packages rather than
Homebrew. The opt-in `mactex` cask reproduces that full distribution; it is not
the smaller BasicTeX package. It remains opt-in because of its download and
disk size.

If the post-MVP memory-transfer capability is implemented, `age` is installed
only through an explicit `--include memory-transfer` selection. It is not part
of the default profile.

Cyberduck and the Notion desktop application are omitted. IT-managed
applications are represented only by a manual checklist.

Homebrew dependencies are not copied from `brew list`. The manifests declare
only intentional formulae and casks; Homebrew resolves their transitive
dependencies.

## Configuration Ownership and Application

Configuration is divided by how safely an application tolerates external
management.

| Category | Examples | Application method |
| --- | --- | --- |
| Stable dotfiles | Zsh, Powerlevel10k, Git, global Git ignore, Jujutsu | Symlink to repository-owned source |
| App-managed JSON | Cursor settings and keybindings, Wave settings | Validate, back up, then copy or render |
| Assistant policy | Global instructions, rules, authored skills, hooks | Copy or symlink stable source |
| Enumerated installs | Editor extensions and plugin identifiers | Reinstall from a declarative catalog |
| Runtime state | Caches, indexes, plugin downloads, registries | Regenerate; never version |
| Authentication | OAuth, tokens, Keychain entries, trust state | Reauthenticate; never version |

The bootstrap records checksums and ownership metadata under
`~/.local/state/ballen-config`. Before changing an unmanaged destination, it
copies the original into a timestamped directory beneath
`~/.local/state/ballen-config/backups/`.

When the destination already matches the desired content, `configure` is a
no-op. When a managed destination has drifted, `plan` shows the structural
action and `configure` applies it after preserving the existing version.

Planning output is structural: it reports paths, ownership, action types, and
redacted field names, never raw destination values. This prevents a token in an
unmanaged JSON file from appearing in terminal output or an agent transcript.

The central inventory references each shared catalog once; it does not mirror
catalog entries in flattened `item_ids` lists. The referenced catalog is the
authoritative declaration of its entries, while the inventory records its
owner, source, and target scope.

Configuration and backup code runs with `umask 077`. State and backup
directories are mode `0700`; newly created files are mode `0600` or retain a
more restrictive source mode. Every source and destination is checked with
`lstat`, and unsafe symlink traversal is refused. Replacement uses a temporary
file in the destination directory followed by an atomic rename. Backup
retention and manual pruning are documented because backups may contain
sensitive values copied from pre-existing local configuration.

## Migration of Existing Repository Content

Implementation must leave no contradictory legacy setup path alongside the new
bootstrap:

- `README.md` becomes the primary operational and rationale guide rather than
  only a concise command index. It explains the staged architecture, profiles,
  package choices, configuration ownership, agent-sharing model, security
  boundary, and important decisions such as Wave, full MacTeX, `libmagic`,
  `glab`-only GitLab, first-party browser tools, and official Notion
  integrations. It links to the design record for full detail and to focused
  manual transfer and authentication documents.
- `CLAUDE.md` is rewritten around the new staged workflow. Its instructions to
  copy `~/.aws`, inject GitLab tokens, and automate the old Cursor MCP file are
  removed.
- `cursor/mcp.json` is removed. It currently configures global Playwright,
  GitLab, and Notion servers that are intentionally absent from the new design.
- The GitLab Workflow editor extension is removed from
  `cursor/extensions.txt`; GitLab support is `glab` only.
- `cursor/extensions.txt` is rebuilt from the current Cursor profile rather
  than retained as a stale historical list. Generated/bundled extensions are
  excluded, agent extensions are conditional, and a separate diagnostic
  snapshot may record versions.
- `ssh/config` is replaced by a host-neutral template or documentation. Its
  fixed `id_ed25519_2025` identity path is not portable.
- `.zprofile` derives the Homebrew environment from the detected installation
  and supports both Apple Silicon and Intel prefixes.
- Cursor's Bedrock and AWS-region settings move into a work-only overlay or are
  omitted; they never affect the default profile.
- Existing root dotfiles move into `dotfiles/` without changing their approved
  behavior, and temporary compatibility links are used only if needed during
  the transition.
- Codex and Wave configuration are added from reviewed current-machine state;
  duplicated hooks and cache-derived paths are replaced by the canonical
  shared hook location.

A tracked-tree policy check rejects legacy MCP entries, credential-copy
instructions, fixed user-home paths, private-key material, authentication
tokens, session databases, and encrypted memory-export artifacts.

## Coding-Agent Configuration

### Shared components

Shared components use one canonical source but are installed through
agent-specific adapters. Skills have a sufficiently portable common format;
hooks, global instructions, plugins, and settings do not.

Canonical notification and lifecycle hook programs live under:

```text
~/.local/share/ballen-config/hooks/
```

Cursor, Claude Code, and Codex each receive their own hook registration in the
format that agent expects, pointing to the canonical programs when the event
semantics match. Thin agent-specific wrappers normalize incompatible event
names and payloads. This replaces duplicated hook implementations and
references into versioned plugin-cache directories without pretending that
the three hook schemas are identical.

Reviewed, general-purpose skills use the open Agent Skills directory structure
under `assistants/shared/skills/<skill-name>/`:

```text
<skill-name>/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

Only `SKILL.md` is required; the other directories are present when needed.
The bootstrap copies each canonical skill into the native global root for every
enabled target:

- Cursor: `~/.cursor/skills/<skill-name>/`;
- Claude Code: `~/.claude/skills/<skill-name>/`;
- Codex: `~/.agents/skills/<skill-name>/`.

Copies are used instead of assuming that every client follows directory
symlinks. Existing unmanaged collisions are preserved and reported, while
`doctor` compares managed hashes. Cursor scans its own skill root as well as
the Claude, Codex, and shared Agent Skills roots, so every deployed copy of a
portable `SKILL.md` must remain byte-identical. `doctor` scans all of those
roots and reports a same-name, different-hash skill as an error.

Agent-specific behavior stays in an external wrapper or registration whenever
possible. A genuinely different `SKILL.md` receives a unique agent-qualified
name and targets only that agent; an adapter must never silently create
different same-name skills across Cursor-scanned roots.

`assistants/shared/skills/catalog.yaml` declares each skill's targets,
dependencies, provenance, and portability status. This gives future promotion
work a stable path: selected Plato tooling, MR, and `using-*` skills can be
copied into the catalog only after Plato paths, imports, assumptions, and
repository-specific language are removed. The original repository skill
remains authoritative until the generic version passes its own portability
review.

Generated plugin caches and third-party plugin source are reinstalled from
identifiers rather than copied. Repository-specific skills and instructions
remain in their repositories.

`assistants/inventory.yaml` is a mandatory, auditable inventory of every
managed instruction file, authored skill, hook, extension, and plugin
identifier. Each entry declares its owner (`shared`, `cursor`, `claude`, or
`codex`), source, destination or install identifier, applicable profile, and
whether it is required or optional. The initial inventory is derived from the
reviewed current-machine audit rather than copied wholesale. No locally managed
MCP server is enabled by default.

### Cursor

The repository tracks a reviewed base for settings, keybindings, desired
extensions, readable User Rules source, hooks, and authored general-purpose
skills. The Cursor adapter writes `~/.cursor/hooks.json` and installs managed
hook programs beneath `~/.cursor/hooks/` or points to the canonical shared
programs. Global User Rules are configured through Cursor's Customize UI, so
the bootstrap preserves their reviewed source and setup checklist rather than
editing Cursor's internal storage.

Managed macOS destinations are:

- settings destination:
  `~/Library/Application Support/Cursor/User/settings.json`;
- keybindings destination:
  `~/Library/Application Support/Cursor/User/keybindings.json`.

The following items remain excluded:

- chat and agent history;
- indexes and caches;
- authentication state;
- Cursor worktrees;
- machine-specific workspace storage;
- links or rules that point specifically to Plato or another repository.

Cursor extensions are restored through the CLI, not by copying
`~/.cursor/extensions`:

```bash
cursor --install-extension <publisher.extension>
```

The repository tracks curated, unversioned extension IDs so a replacement
machine receives the current Cursor-compatible release. A generated
`id@version` snapshot is diagnostic only and is not an installation lock.
`doctor` compares the desired list with `cursor --list-extensions` and explains
missing, extra, bundled, and conditional entries.

The current audit found 31 profile extensions and 115 Cursor-bundled
extensions. The reviewed initial policy:

- excludes bundled and transitive components such as Cursor Pyright and
  Debugpy;
- removes `gitlab.gitlab-workflow` in favor of `glab`;
- installs the Claude Code and OpenAI extensions only when their corresponding
  agents are enabled;
- uses Cursor's current Remote SSH and Remote Containers extensions instead of
  stale Microsoft IDs;
- treats the JJ Graph VSIX as an optional extension with a pinned source and
  checksum;
- declares `ms-toolsai.jupyter` as the notebook feature root and treats its
  satellite extensions as transitive rather than tracking the current
  inconsistent set.

`cursor --list-extensions` reports profile extensions but not Cursor's bundled
set. `doctor` therefore treats a compatible bundled extension as satisfying a
feature by inspecting Cursor's packaged manifest when necessary; it does not
infer bundled state from the CLI list.

As amended by the approved [Coding-Agent Desired-State Consolidation
Design](2026-07-26-coding-agent-desired-state-consolidation-design.md), a
deliberately declared Cursor marketplace plugin is a visible manual Customize
checklist action unless Cursor exposes a supported installer and inspection
interface. The production Cursor marketplace and local-plugin lists are
intentionally empty. A reviewed local plugin is copied only to
`~/.cursor/plugins/local/<name>/` through the managed atomic tree engine; the
bootstrap never copies
`~/.cursor/plugins/cache` or infers desired state from imported Cursor content.

The current token-bearing GitLab MCP configuration is removed.

### Claude Code

The repository tracks global instructions, stable settings, authored
general-purpose skills, and canonical hook references. Claude Code marketplace
identifiers are target-aware records in the shared plugin catalog and are
installed through Claude Code's native adapter. It excludes:

- `~/.claude.json` runtime and authentication state;
- transcripts, sessions, and command history;
- caches and downloaded plugin implementations;
- machine-specific project registries.

### Codex

The repository tracks global instructions, `RTK.md`, a small portable
configuration overlay, stable rules, authored skills, and canonical hook
references. Codex marketplace identifiers are target-aware records in the
shared plugin catalog and are installed through Codex's native adapter. It
excludes:

- session and history data;
- authentication and trust state;
- SQLite databases and write-ahead logs;
- bundled runtimes and downloaded plugin caches;
- paths that identify this laptop or a repository checkout.

### Browser and MCP policy

There is no generic Playwright MCP installation:

- Cursor uses its native browser-agent capabilities.
- Codex Desktop uses its bundled Browser or Chrome tooling.
- Claude Code uses the official Chrome integration after its one-time setup.

A repository that runs Playwright tests must declare `@playwright/test` and its
browser binaries in that repository. Agent browser tooling does not satisfy
test dependencies.

GitLab support consists of the `glab` CLI. The bootstrap installs it, and
`doctor` checks `glab auth status`. There is no GitLab MCP server, local token
template, or separate PAT workflow.

Notion uses account-managed, official integrations in Cursor, Claude, and
OpenAI surfaces. The bootstrap does not install the Notion desktop application,
run a local Notion server, or store Notion authentication.

Other services, such as Atlassian, follow the same preference order:

1. built-in capability;
2. official authenticated remote connector;
3. established CLI;
4. custom or local MCP only when a demonstrated gap remains.

Account-managed connectors appear in setup documentation and diagnostics, not
as copied credentials.

## Secrets, Authentication, and SSH

The following never enter Git or the memory archive:

- private SSH keys;
- macOS Keychain material;
- `~/.aws` credentials and cached SSO sessions;
- GitHub, GitLab, Notion, Atlassian, Cursor, Claude, or OpenAI tokens;
- OAuth refresh state;
- remote-login credentials;
- machine-specific environment-variable files.

`docs/manual-steps.md` provides a post-install authentication checklist,
including `gh auth login`, `glab auth login`, AWS authentication, coding-agent
sign-in, browser integration enablement, and official connector sign-in.
`doctor` reports whether those capabilities appear ready without reading or
printing credential contents. It captures and discards raw output from
authentication status commands and emits only normalized states such as
`ready`, `not authenticated`, `unavailable`, or `manual check required`.

SSH keys are transferred manually through an encrypted local medium or a direct
trusted connection. `docs/ssh-transfer.md` explains:

- which files are keys, public keys, configuration, and expendable
  `known_hosts` state;
- how to inspect the source before transfer;
- why a fresh per-machine key is preferred when practical;
- why plaintext cloud folders and unencrypted removable media must not be used;
- how to restore directory and file permissions;
- how to add a key to the macOS SSH agent and Keychain;
- how to verify GitHub, GitLab, and required hosts;
- how to verify unfamiliar host fingerprints out of band rather than blindly
  accepting regenerated `known_hosts` entries;
- how to remove any temporary encrypted transfer copy after verification;
- how to generate a fresh key instead.

The repository retains a sanitized SSH configuration template with portable
defaults for the public GitHub and GitLab endpoints. Private or internal
hostnames, usernames, aliases, jump hosts, identity paths, and other
remote-login details stay in the included `~/.ssh/config.local` and are not
treated as portable dotfiles. The destination directory is mode `0700`; the
configuration and private keys are mode `0600`; and those permissions are
applied before the first SSH use.

## Optional Memory Transfer

Memory transfer is a post-MVP capability and does not block delivery or
acceptance of the core bootstrap. If its security and conflict-handling work is
disproportionate, implementation may defer the commands, manifests, tests, and
`age` installation together. It must not ship a reduced unsafe version. The
core README should then document the deferral and retain the rule that sessions
and histories are never copied.

When implemented, semantic memories remain outside the Git repository. The
bootstrap provides explicit export and import commands:

```bash
./bootstrap install --include memory-transfer

./bootstrap memories export \
  --source codex \
  --source claude \
  --output ~/Desktop/agent-memories.tar.age

./bootstrap memories import \
  --archive ~/Desktop/agent-memories.tar.age
```

`age` supplies passphrase-based encryption and prompts interactively so the
passphrase is not placed on the command line. Before export, the command prints
the selected files, counts, and total sizes and requires confirmation.
Documentation asks for a strong, unique passphrase that is communicated
separately from the archive.

Export performs a non-mutating `age` preflight. If the executable is missing,
it exits with an instruction to run the explicit memory-transfer install; it
never installs a dependency as a side effect of exporting data.

`manifests/memories.yaml` declares fixed logical source identifiers, roots, and
relative globs. The initial allowlist is:

| Source identifier | Fixed root | Allowed relative files |
| --- | --- | --- |
| `codex` | `~/.codex/memories` | `**/*.md` |
| `claude` | `~/.claude/projects` | `*/memory/**/*.md` |
| `cursor-plans` | `~/.cursor/plans` | `**/*.md` |
| `cursor-notes` | `~/.cursor/notes` | `**/*.md` |

Cursor entries are labeled as plans or notes because Cursor has no equivalent
dedicated semantic-memory store. Missing optional roots simply contribute no
files.

All sources share mandatory exclusions for `.git`, session, history,
transcript, cache, registry, database, WAL, and runtime-state paths. Only
regular Markdown files returned by `lstat` are accepted. Symlinks, hardlinks,
devices, sockets, and files whose canonical paths escape their fixed root are
rejected. Reviewed manifest limits bound individual file size, total bytes, and
file count; the initial limits are 10 MiB per file, 250 MiB total, and 10,000
files.

The archive manifest is the first entry and contains logical source
identifiers, root-relative paths, sizes, SHA-256 hashes, source date, and format
version. It never stores a source username or trusts an absolute destination.
The exporter refuses an output path inside this repository, inside a selected
source root, or over an existing file.

Export streams the deterministic archive directly into `age`; no plaintext tar
file is written. Under `umask 077`, the exporter canonicalizes and
no-follow-checks the existing output parent, then writes ciphertext to a
same-directory temporary file with mode `0600`. It removes partial output on
failure or interruption and publishes the archive with an atomic rename only
after `age` succeeds.

Import decrypts into a mode-`0700` temporary staging directory, using a
streaming reader that rejects absolute paths, `..` traversal, duplicates,
links, special files, undeclared entries, and size-limit violations before
materializing each file. The staging directory is removed on success, failure,
and handled interruption. Documentation notes that secure erasure cannot be
guaranteed on APFS, so plaintext staging is deliberately short-lived.

Import maps logical source identifiers to the destination machine's fixed
roots, validates every hash, and previews all actions. Identical destinations
are no-ops. New files are written atomically with mode `0600`. A differing
destination is never overwritten by default: the existing file remains in
place and the incoming file is retained in a mode-`0700` conflict directory
for manual review. An explicit replace option requires confirmation and a
timestamped backup first.

Individual sources are opt-in. Sessions, histories, authentication, and SSH
material remain excluded even when memory transfer is enabled.

## Stage Behavior and Failure Handling

### `prepare`

- Is implemented by the stage-zero shim and is the only prerequisite stage
  available before Python 3.12.
- Prints the missing prerequisite actions and asks for confirmation.
- Installs or initiates only Xcode Command Line Tools, Homebrew, `uv`, and
  Python 3.12, then synchronizes the committed, frozen bootstrap environment.
- Makes no application, dotfile, assistant, or authentication changes.

### `plan`

- Performs no writes.
- Resolves profiles, includes, and skips.
- Shows installed, missing, structurally changed, and manual components without
  printing current configuration values.
- Identifies paths containing brittle absolute references.
- Reports expected interactive prompts.

### `install`

- Checks current Homebrew and component state before acting.
- Installs only missing intentional formulae, casks, shell components,
  extensions, and plugin identifiers.
- Applies skips to the complete component, including its extensions and
  plugins.
- Treats a required component failure as a stage failure.
- Records optional-component failures and continues so `doctor` can summarize
  them.
- Never removes an installed package or application.

### `configure`

- Validates source configuration before touching destinations.
- Makes timestamped backups of conflicting destinations.
- Creates stable symlinks where supported.
- Renders or copies application-managed formats where symlinks are brittle.
- Rewrites managed hook paths to the canonical shared location.
- Uses no-follow checks, restrictive modes, and atomic replacement.
- Never modifies authentication or session state.

### `doctor`

- Is always non-mutating.
- Checks tools, expected versions, applications, fonts, managed-file drift,
  shell components, hooks, and known configuration hazards.
- Reports normalized authentication readiness while suppressing the raw output
  of status commands.
- Reports first-party browser and official connector setup as actionable
  manual checks.
- Reports skipped components as intentional rather than missing.
- Warns about Cursor worktrees that may be stale but never deletes them.
- Distinguishes required failures, optional omissions, and informational manual
  actions in its output and exit status.

The recovered Plato topology-generation v2 plan is already preserved on its
own local branch. The three audited Cursor worktrees were removed on
2026-07-25 after their remaining content was confirmed as superseded,
generated, or recovered. Future cleanup remains a separate explicit action;
`doctor` only reports candidates.

## Source and Destination Workflow

### Current laptop

1. Run `plan` and `doctor` against the current machine.
2. Review the proposed inventory and configuration drift.
3. If the post-MVP memory capability is delivered and desired, install the
   memory-transfer component and export selected semantic memories.
4. Prepare SSH keys separately using the documented manual method.
5. Run `configure` locally to replace brittle paths and duplicated hooks.
6. Commit only reviewed, secret-free source configuration.

### Replacement laptop

1. Install Xcode Command Line Tools when prompted.
2. Clone `ballen-config`.
3. Run `./bootstrap --profile work` with any desired skips and optional apps.
4. Complete the manual authentication checklist.
5. Transfer SSH keys through the documented secure path.
6. If the post-MVP capability was used, optionally import its encrypted memory
   archive.
7. Clone work repositories and run their repository-owned setup.
8. Run `doctor` again and use a coding agent to resolve remaining
   machine-specific warnings.

## Testing and Verification

Tests use Pytest fixtures and temporary home directories. No test installs real
packages or modifies a developer's actual configuration.

Coverage includes:

- stage-zero argument validation, read-only refusal, and confirmed preparation;
- frozen bootstrap-environment creation and no-sync read-only execution;
- Pydantic manifest validation and helpful invalid-manifest errors;
- profile inheritance and de-duplication;
- `--include` and whole-component `--skip` resolution;
- deterministic plan generation;
- package and application state detection through a fake command runner;
- managed-file no-op, backup, copy, render, and symlink behavior;
- structural drift reports that cannot reveal destination values;
- no-follow path handling, restrictive modes, and atomic replacement;
- rejection of paths outside approved destinations;
- secret-pattern and machine-path checks for tracked templates;
- generic-skill catalog validation, per-agent target resolution, collision
  preservation, hash-based drift reporting, and rejection of same-name
  different-content skills across Cursor-scanned roots;
- Cursor extension feature resolution, conditional agent entries, and
  bundled-extension satisfaction through the packaged manifest;
- doctor severity and exit-code behavior;
- a temporary-home integration test for the complete configure flow.

If memory transfer is delivered, its additional coverage includes allowlists,
mandatory exclusions, manifests, hashes, conflict handling, adversarial archive
entries, encrypted-output containment and atomicity, cleanup, and missing-`age`
preflight behavior.

The verification suite includes Ruff formatting and linting, static type
checking, Pytest, ShellCheck for the stage-zero shim, manifest parsing, and a
macOS dry-run smoke test.

Pre-commit and CI enforce the tracked-tree boundary with private-key and
credential scanners plus repository-specific checks for user-home paths,
sessions, histories, caches, databases, credential-copy instructions, and
forbidden MCP entries. A root `.gitignore` excludes Python/build state, local
agent state, and `*.age` transfer artifacts. The exporter independently refuses
to write an archive beneath the checkout, so ignore rules cannot mask a
mistake.

Before using the bootstrap on a replacement laptop, the current laptop must
pass:

```bash
./bootstrap plan --profile work
./bootstrap doctor --profile work
```

The plan output must contain no secret values, and a second local `configure`
run must be a no-op.

## Alternatives Considered

### Continue with manual documentation

The current README is easy to understand but has already drifted from the
machine. It cannot reliably distinguish intentional software from transitive
dependencies, detect configuration drift, or enforce secret boundaries.

### Use only a Brewfile

A Brewfile is useful for package installation but cannot safely manage
dotfiles, application configuration, agent hooks, memory transfer, backups, or
diagnostics. The design keeps package intent declarative while using the Python
CLI for orchestration.

### Use only shell

Shell would eliminate the stage-zero Python step but would make manifest
validation, typed planning, safe path handling, test isolation, and structured
diagnostics unnecessarily difficult.

### Use only Python

Python is the best fit for the main logic, but assuming the correct interpreter
already exists creates a circular dependency on a new laptop.

### Selected approach

A tiny Zsh stage-zero shim plus a Python 3.12 application offers the best
balance: minimal bootstrap requirements, readable typed implementation, strong
tests, and straightforward repair by a coding agent.

## Acceptance Criteria

The design is complete when its implementation can demonstrate that:

- a clean macOS account can preview and run the default or work setup;
- a pristine account can inspect stage-zero prerequisites without changing
  them;
- each coding agent and Wave can be independently skipped across every stage;
- optional personal applications are opt-in;
- the README explains the operating model and major rationale without requiring
  readers to discover the design record first;
- package manifests contain intentional dependencies rather than a raw machine
  dump;
- the tracked tree contains no credentials, sessions, histories, or
  machine-generated databases;
- repository-specific configuration is absent from the generic bootstrap;
- generic skills have one canonical catalog and install into Cursor, Claude
  Code, and Codex through explicit agent targets;
- repeated configuration is safe and reaches a no-op state;
- overwritten user configuration is recoverable from timestamped backups;
- browser automation does not require a global Playwright MCP;
- GitLab works through `glab` without a GitLab MCP or stored PAT;
- Notion relies on official authenticated integrations rather than a local
  installation;
- Cursor's curated VS Code extension set is restorable from IDs, while bundled,
  transitive, stale GitLab, and disabled-agent extensions are excluded;
- the old Playwright/GitLab/Notion MCP file, GitLab editor extension,
  credential-copy guidance, fixed SSH identity, and default-profile Bedrock
  settings are gone;
- SSH transfer remains a documented, manual, secure operation;
- `doctor` clearly separates automatic fixes from actions requiring the user;
- drift and authentication diagnostics reveal no local values or command
  output;
- pre-commit and CI enforce the secret and generated-state boundary;
- a coding agent can understand and complete the remaining setup from the
  repository alone.

### Optional memory-transfer acceptance

The core bootstrap is accepted without memory-transfer commands. If that
post-MVP capability is delivered, it additionally demonstrates that:

- export is explicit, encrypted, inspectable, and excludes all session and
  authentication state;
- hostile archive entries, source symlinks, unsafe destination links, and
  plaintext archive residue are rejected;
- omitting the memory-transfer component installs neither `age` nor memory
  configuration.

## Deferred Decisions

- Whether Wave fully replaces iTerm after the trial period.
- Which Plato tooling, MR, and `using-*` skills should be generalized first.
- Whether memory transfer is worth implementing after the core bootstrap is
  working.
- Whether additional work-wide official connectors belong in the documented
  checklist after the first bootstrap is exercised.
