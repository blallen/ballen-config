# Manual post-install steps

1. Complete any Command Line Tools or Homebrew prompt from `prepare`, then run
   `./bootstrap prepare` again.
2. Authenticate GitHub with `gh auth login`. Authenticate GitLab with
   `glab auth login` when you need GitLab remotes. Authentication status output
   is diagnostic and is not committed to this repository.
3. For the work profile, complete the organization's AWS sign-in flow. Verify
   it only through `./bootstrap doctor --profile work`; do not copy identity or
   credential output into Git.
4. Follow the [SSH transfer guide](ssh-transfer.md) in
   `docs/ssh-transfer.md` for any SSH key work.
5. Install IT-managed applications through the company-supported channel.
6. Before `--include mactex`, allow for the full MacTeX download and disk
   footprint.
7. Sign in to each enabled coding agent: Cursor, Claude Code, and Codex.
8. When Cursor is enabled, import each of these state-dir handoffs as its own
   User Rule in Cursor Customize > Rules:
   `~/.local/state/ballen-config/manual/cursor-user-rules-engineering.md`,
   `cursor-user-rules-rtk.md`, and `cursor-user-rules-cursor.md`. The legacy
   concatenated `cursor-user-rules.md` is obsolete if present.
9. In Cursor, open **Settings → Rules, Skills, Subagents** (or **Customize**)
   and turn off **Include Third-Party Plugins, Skills, and Other Configs** so
   each coding agent's desired state stays explicit. This is a recommendation,
   not a prerequisite: the bootstrap remains correct and idempotent if the
   setting stays enabled.
10. The production Cursor marketplace and local-plugin lists are intentionally
    empty. If a later reviewed catalog entry names a Cursor marketplace plugin,
    complete its visible Customize checklist action; do not treat imported
    capabilities or `~/.cursor/plugins/cache` as desired state. A reviewed
    local plugin is managed only at `~/.cursor/plugins/local/<name>/`.
11. Enable each enabled agent's first-party browser capability and authorize
    the official Notion integration when needed. Prefer one Notion connector:
    use a team install when it opens the right workspace; otherwise keep a
    user install and remove the duplicate. For work-profile Cursor, complete
    OAuth for the reviewed Atlassian HTTP compatibility entry when prompted.
    The bootstrap manages only its secret-free endpoint; do not add Playwright
    or GitLab servers to that file.
12. Do not manually install the abandoned experimental marketplace setup; it is
    not part of desired state.
13. Finish with `./bootstrap doctor --profile work`, or use
    `./bootstrap doctor --profile default` for the default profile. Resolve only
    the normalized manual findings.
