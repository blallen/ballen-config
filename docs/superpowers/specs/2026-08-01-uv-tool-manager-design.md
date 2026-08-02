# uv Tool Manager Design

## Status

Implemented on 2026-08-01 in the `uv-tool-manager` branch, across the model,
install, doctor, CLI, and manifest changes described below. The accompanying
[implementation plan](../plans/2026-08-01-uv-tool-manager.md) records one task
withdrawn during execution.

The one-time local cleanup in the Migration section is a human action and is
deliberately not part of the branch.

Both scope decisions below were assumed at design time and confirmed during
implementation:

- The manager owns both `pre-commit` and `ruff`.
- Manifest entries name a tool, not a pinned version.

## Purpose

The bootstrap can express only three managers: `brew_formula`, `brew_cask`,
and `git`. Python tools installed with `uv tool install` therefore cannot be
declared at all, which produces two defects in the current desired state.

`pre-commit` is declared as a `brew_formula`. The Homebrew copy is never the
one that runs: `~/.local/bin` precedes `/opt/homebrew/bin` on `PATH`, so the
uv-managed copy shadows it. The declared component is inert, and it pulls
`python@3.14` in as a dependency purely to satisfy a formula nothing uses.

`ruff` is installed as a uv tool on the current machine but appears in no
manifest. The repository does not own it, `doctor` cannot report on it, and a
new machine does not get it.

A `uv_tool` manager closes both gaps and makes uv the single owner of the
Python toolchain, consistent with Homebrew owning uv itself.

## Desired state

Homebrew installs `uv`. `uv` installs and owns Python interpreters and Python
tools. The repository declares which tools are desired; it does not vendor
their versions or duplicate them through a second package manager.

## Approaches considered

**Add a `uv_tool` manager.** Recommended. One new enum member and one branch
at each of the three existing dispatch sites. It reuses `depends_on` for
ordering and the existing `runner` abstraction for execution, so it introduces
no new concepts. The manifest gains the vocabulary to say what is already
true.

**Keep `pre-commit` as a Homebrew formula and drop `ruff`.** Rejected. This is
the status quo. It leaves a declared component that never executes, keeps a
`python@3.14` dependency that exists only to satisfy it, and leaves `ruff`
unowned. It is the cheapest option and the only one that preserves a known
defect.

**Install tools through a post-configure shell step.** Rejected. A hook that
runs `uv tool install` outside the manifest would work, but it would place
part of the desired state outside the resolver, outside `doctor`, and outside
the skip and profile machinery. Every other package in this repository is a
declared component; tools should not be the exception.

## Design

### Model

Add `UV_TOOL = "uv_tool"` to `Manager` in `src/ballen_config/models.py:11`.
`Component` already carries `package`, `depends_on`, `profiles`, and
`required`, which is the full field set a tool entry needs. No new fields.

### Ordering

`Component.depends_on` exists at `src/ballen_config/models.py:27`, and
`ManifestRepository.resolve` already topologically orders dependencies and
fails closed on an unselected one at `src/ballen_config/manifests.py:138`.
Each `uv_tool` entry declares `depends_on: [uv]`. Installing a tool before uv
exists is therefore a resolution error, not a runtime failure.

This is the mechanism that already orders Oh My Zsh before the plugin
repositories nested beneath it, covered by
`test_shell_parent_precedes_nested_git_components`.

### Install

Add a `_uv_tool` branch to `Installer.install` at
`src/ballen_config/install.py:246`, mirroring `_brew`:

- Presence: `uv tool list`, matching the tool name at the start of a line.
- Install: `uv tool install <package>`.
- Return `present`, `installed`, or `optional-failure`, and raise
  `InstallError` when a required component fails.

The outcome vocabulary is unchanged, so planning, state, and reporting need no
modification.

### Doctor

Extend the manager set at `src/ballen_config/doctor.py:154` with the same
`uv tool list` probe, reporting `ready` or `missing` to match the existing
package diagnostics.

### CLI

`src/ballen_config/cli.py:156` branches on the brew managers when it builds
its presence check. Add the `uv_tool` case there so the three dispatch sites
stay consistent. Keeping these three in sync is the main maintenance cost of
the design, and a reviewer should check all three together.

**Update:** after all three sites landed, this triplication was reversed.
The `uv tool list` parsing rule was extracted into
`src/ballen_config/probes.py` as `uv_tool_listed`, called from all three
sites; the returncode check and each site's own presence semantics stayed
put. Reasons: the "no cross-module coupling" argument for keeping it
triplicated didn't hold, since `cli.py` already imports from `doctor.py` and
`install.py`; the parallel brew probe, left triplicated, had already drifted
across the three files (`install.py` checks returncode only, `doctor.py` ORs
in `application_paths`, `cli.py` checks `application_paths` before
dispatching); and the parsing rule encodes an assumption about `uv tool
list`'s output format that should live in one place rather than three.

### Manifest changes

In `manifests/packages.yaml`, change `pre-commit` from `brew_formula` to
`uv_tool` and add `ruff`, both with `depends_on: [uv]` and the `default`
profile.

`tests/test_manifests.py:41` asserts that `pre-commit` resolves for the work
profile. It keeps passing unchanged, because only the manager changes.

### Error handling

Three failure modes, all resolved by existing behavior:

- uv missing at resolution: `resolve` raises on the unselected dependency.
- `uv tool install` fails: required components raise `InstallError`; optional
  ones return `optional-failure`, as with brew.
- `uv tool list` unreadable: treated as not present, so the run attempts an
  install rather than reporting a false `ready`.

## Testing

- `tests/test_models.py`: the new enum member.
- `tests/test_manifests.py`: a `uv_tool` component orders after `uv`, and a
  `uv_tool` component without `uv` selected fails to resolve.
- `tests/test_install.py`: present, installed, and failure paths against the
  fake runner already used for brew.
- `tests/test_doctor.py`: ready and missing.
- `tests/test_policy.py`: unchanged; this design adds no tracked secrets,
  absolute paths, or machine-specific values.

## Migration

After the manifest change, `brew uninstall pre-commit` followed by
`brew autoremove` drops the redundant formula and the `python@3.14`
dependency it carried. `doctor` should then report `pre-commit` and `ruff`
ready from uv.

This is a one-time local cleanup, not a bootstrap step. Nothing in the
repository should uninstall Homebrew packages on a user's behalf.

## Out of scope

- Version pinning in manifest entries. `uv tool install <name>` takes the
  latest. This repository's authoritative versions are resolved from
  `uv.lock`, which is what CI, the pre-commit hooks, and `uv run --frozen`
  use. Global tools are convenience copies. Pinning here would need a field
  separate from `package`, because the presence probe matches `uv tool list`
  on the bare tool name, so a `name==version` spec would never match.

  **Update:** this section originally named `.pre-commit-config.yaml` as a
  second authoritative source. That duplication was removed; see
  [Ruff single source](2026-08-02-ruff-single-source-design.md).
- `uv tool upgrade`. Reconciling an installed-but-outdated tool is a separate
  concern from declaring it, and no existing manager upgrades either.
- Promoting `mypy` to a global tool. It is a dev dependency and has no use
  outside a project checkout.
