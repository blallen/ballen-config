# Manual post-install steps

1. Complete any Command Line Tools or Homebrew prompt from `prepare`, then run
   `./bootstrap prepare` again.
2. Authenticate GitHub with `gh auth login` and GitLab with
   `glab auth login`. Authentication status output is diagnostic and is not
   committed to this repository.
3. For the work profile, complete the organization's AWS sign-in flow. Verify
   it only through `./bootstrap doctor --profile work`; do not copy identity or
   credential output into Git.
4. Follow the [SSH transfer guide](ssh-transfer.md) in
   `docs/ssh-transfer.md` for any SSH key work.
5. Install IT-managed applications through the company-supported channel.
6. Before `--include mactex`, allow for the full MacTeX download and disk
   footprint.
7. Sign in to each enabled coding agent: Cursor, Claude Code, and Codex.
8. Import the rendered Cursor User Rules in Cursor Customize > Rules when
   Cursor is enabled.
9. Enable each enabled agent's first-party browser capability and authorize
   the official Notion integration when needed.
10. Finish with `./bootstrap doctor --profile work`, or use
   `./bootstrap doctor --profile default` for the default profile. Resolve only
   the normalized manual findings.
