# Cursor CLI, T3 Code, and Configuration Drift Plan

**Status:** Implemented and applied on the `wsh` profile with `--include t3-code`.

**Goal:** Make Cursor CLI and T3 Code reproducible on a new Mac, and resolve
configuration drift without replacing intentional local settings or private state.

**Architecture:** Extend the existing manifests and native diagnostics. Use
Homebrew for new installations, recognize existing installations, and manage
only explicitly selected portable settings through structural adapters.

**Tech stack:** Existing Python 3.12, uv, Pydantic, pytest, and Homebrew.

**Authority:** [Repository README](../../../README.md) and the
[profile and Wave removal design](../specs/2026-08-26-employer-profiles-and-wave-removal-design.md).

## Constraints

- Use Fable for Claude and Astra for Codex, with 1M context where the provider
  supports it. Verify exact identifiers and settings before declaring them.
- Use the default service tier, not priority. Preserve existing reasoning
  effort unless a supported-model constraint requires a change.
- Remove obsolete Wave settings. Verify Ponytail's actual Codex and Cursor
  compatibility before installing it or declaring support.
- Add T3 installation support now; leave its settings unmanaged because no
  portable keybinding or UI preferences have been selected.

- Use `wsh` for this machine's investigation; preserve its include/skip choices
  through plan, install, configure, and doctor. Confirm optional selections
  before applying a plan that would prune configuration.
- Never copy authentication, trust, sessions, histories, project paths, or
  generated plugin state into desired state. Keep diagnostic output normalized.
- Review a fresh bootstrap plan before mutation. Preserve existing files using
  the bootstrap's private backups and ownership checks.
- Do not run a broad configure operation until every proposed update/removal
  has a disposition. A changed file is not by itself evidence of a bad setting.

## Findings from the initial checks

The default-profile doctor exited 1. A fresh `wsh` plan succeeded, but its
doctor also exited 1 with the remaining findings below.

| Finding | Interpretation and next action |
| --- | --- |
| Work shell profile | The `default` plan proposed removing `.zprofile.work`; the `wsh` check clears this finding. Keep the work profile. |
| Claude settings | Owned `model` is locally `opus[1m]`, versus declared `opus`. Other inspected owned settings and the managed RTK hook match. Decide whether the larger-context model is the new portable default or a local preference before changing it. |
| Codex settings | Owned `model` is locally `gpt-5.6-luna`, versus declared `gpt-5.6-sol`; `service_tier` is locally `default`, versus declared `priority`. Reasoning effort matches. Resolve these cost/model preferences before resetting them. |
| Cursor settings | Every renderer-owned base setting is absent from the native settings file. Restore the reviewed `assistants/cursor/settings.base.json` values through its adapter after reviewing them; preserve unowned additions. Do not apply the `fsp` Bedrock overlay under `wsh`. |
| Wave settings | Wave was removed from desired state. Its old settings file exists with a matching ownership receipt and digest, so the planned prune is eligible. Recheck ownership at application time and retain the private backup; leave unrelated Wave data alone. |
| Codex Ponytail | Doctor reports its marketplace and plugin missing. Check the native installed inventory and catalog identifiers before installing or changing the declaration. |
| Cursor native inspection | `cursor-agent` works, but the separate editor command `cursor` is absent from PATH. Extension inspection invokes `cursor --list-extensions`. Verify the bundled editor CLI and restore reliable discovery. |
| Cursor MCP | Doctor reports a manual review item. Classify the existing entry locally against the `wsh`/`fsp` boundary; do not copy the live file into the repo or invent a replacement. |

Approved dispositions: use `fable` (native 1M context) and `gpt-6-astra` with
`service_tier = "default"`. Preserve Codex `xhigh` reasoning, set
`model_context_window = 872000` from the installed Codex 0.154.0 model catalog,
and leave compaction policy to native defaults. The current Cursor MCP document
exactly matches the secret-free `fsp` Atlassian exception; move it to a private
backup for this `wsh` setup. Wave's app is already absent; prune its stale
managed settings after rechecking ownership.

Ponytail v4.10.0 has a native Codex manifest and compatible lifecycle hooks.
Keep its existing Claude/Codex catalog targets and install the missing Codex
marketplace/plugin. Codex hook trust remains a local `/hooks` action. Cursor
currently has only Ponytail's manual checkout-based hook integration, with
subagent and version limitations; do not add a managed Cursor target.

## 1. Resolve drift first

**Files:** `assistants/{claude,codex,cursor}/`,
`src/ballen_config/assistants/{claude,codex,cursor,checks}.py`,
`src/ballen_config/configure.py`, and `docs/manual-steps.md`, as warranted by findings.

- [x] Produce a private, read-only comparison using each native renderer, with
  changed key names and safe portable values only. Distinguish owned keys from
  preserved local additions and formatting-only differences.
- [x] Assign each difference one disposition: promote an intentional portable
  preference into the repo, restore the declared value, or preserve local state
  and correct an overly broad comparison. Resolve ambiguous preferences before
  overwriting them.
- [x] Verify `cursor --list-extensions` through the app's bundled CLI. Choose a
  supported launcher setup or a shared bundled-CLI fallback for both extension
  installation and inspection; keep `cursor` distinct from `cursor-agent`.
- [x] Resolve Ponytail using native marketplace/plugin commands if the catalog
  still represents the intended installation. Review the MCP item separately.
- [x] Apply the reviewed settings and owned Wave cleanup with the same `wsh`
  selections. Re-run plan and doctor; retain any unresolved manual items with
  explicit reasons.

## 2. Add Cursor CLI to desired state

**Files:** `manifests/applications.yaml`, presence/planning code in
`src/ballen_config/{models,probes,install,planning,doctor}.py` as needed,
`src/ballen_config/assistants/checks.py`, `README.md`, and `docs/manual-steps.md`.

- [x] Declare `cursor-cli` using the existing `brew_cask` manager, tied to
  `--skip cursor`. Keep this independent of the editor's extension launcher.
- [x] Recognize the existing vendor executable on this machine before
  scheduling installation. Keep plan/install/doctor presence rules consistent,
  and check runtime health separately. Preserve a broken existing executable
  for explicit repair rather than installing another copy over it. Generic
  installation-owner reporting is outside this change; do not infer ownership
  from the executable name alone.
- [x] On clean machines, install the cask and verify `cursor-agent --version`.
  Use the unambiguous `cursor-agent` name in T3 and bootstrap instructions;
  Homebrew currently exposes that command, while the vendor installer also
  exposes `agent`.
- [x] Add normalized command and sign-in diagnostics. Browser login remains
  local; no credentials are rendered, imported, or committed.

## 3. Add T3 Code as an optional application

**Files:** `manifests/applications.yaml`, `manifests/component-ids.txt`,
`README.md`, and `docs/manual-steps.md`.

- [x] Add `--include t3-code` backed by the `t3-code` cask. Recognize the current
  `/Applications/T3 Code (Alpha).app` bundle so this machine is not reinstalled
  or downgraded. Recheck the cask's bundle name during implementation.
- [x] Keep T3 independent of provider selection: it must not force-enable an
  agent the user skipped. Document provider installation, login, and refresh.
- [x] Add installation/readiness coverage using existing component checks.
  Do not add a second T3 server installation, background service, or remote
  pairing as part of this change.

## 4. T3 settings boundary

T3's settings remain unmanaged by the bootstrap. No portable keybindings or UI
preferences were selected, so no settings adapter was added. A future adapter
must merge only declared keys and preserve unrelated additions; never copy or
symlink the complete settings file or `.t3` directory. Credentials, provider
secret variables, account/connection data, databases, conversations, logs,
attachments, IDs, caches, worktrees, and machine paths remain excluded. Project
`t3.json` files belong with their projects.

## Verification and completion

- [x] Cover fresh installation, existing vendor installation, repeated no-op,
  `--skip cursor`, optional T3 selection, and consistent presence diagnostics in
  `tests/test_{manifests,install,planning,doctor,probes}.py` as applicable.
- [x] Add focused regressions for any actual adapter/discovery defect. Exercise
  preservation of unowned keys and refusal to remove modified/unowned files;
  use synthetic fixtures rather than copied live settings.
- [x] Run affected pytest modules, Ruff, mypy, repository policy, and configured
  pre-commit checks through the frozen uv environment.
- [x] On this Mac, run plan before application and doctor afterwards with
  identical profile/include/skip selections. A second plan should contain no
  unintended updates/removals. Verify T3 detects the enabled authenticated
  providers, and explain any remaining manual findings.

## Applied result

The `wsh` profile with `--include t3-code` is converged: the final plan reports
zero configuration changes, and doctor reports no non-ready findings. Fable,
Astra, the default service tier, and the declared Codex context window are
applied. Obsolete owned Wave settings and the old work-profile Atlassian MCP
entry are removed with private backups. T3's current global model selections
contain no service-tier override; its settings remain unmanaged.

Ponytail is installed in Codex. Automatic hook activation still requires local
review and approval through Codex `/hooks`, followed by a new thread. Cursor's
manual Ponytail hook integration is not installed or managed.

Validation: 796 tests passed, all configured pre-commit checks passed, and mypy
passed.

## Current upstream references

- [Cursor CLI installation](https://cursor.com/docs/cli/installation)
- [Homebrew Cursor CLI cask](https://formulae.brew.sh/cask/cursor-cli)
- [T3 installation and providers](https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md)
- [Homebrew T3 cask](https://github.com/Homebrew/homebrew-cask/blob/master/Casks/t/t3-code.rb)
- [T3 keybindings](https://github.com/pingdotgg/t3code/blob/main/docs/user/keybindings.md)
- [Claude model and context configuration](https://code.claude.com/docs/en/model-config)
- [Astra model](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Ponytail Codex manifest](https://github.com/DietrichGebert/ponytail/blob/e3ba2aa6f1e6f0bc4d69eb09c9f0d0a93af56156/.codex-plugin/plugin.json)
- [Ponytail Cursor hook contract](https://github.com/DietrichGebert/ponytail/blob/e3ba2aa6f1e6f0bc4d69eb09c9f0d0a93af56156/docs/cursor-hooks.md)
