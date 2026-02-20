# CLAUDE.md

This is a personal dev environment config repo. It contains dotfiles, tool configs, and setup instructions for new machines.

## Automated Setup with Claude Code

Clone this repo and run Claude Code from the repo root. Tell it to read the README and do the setup. The instructions below tell you what to expect.

### Setup order (dependency-aware)

1. **Homebrew** — REQUIRES SUDO, cannot be automated without user present
2. **Oh My Zsh + Powerlevel10k + plugins** — no sudo needed, fully automatable
3. **Shell configs** — copy `.zshrc`, `.p10k.zsh`, `.zprofile` to `~`
4. **MesloLGS Nerd Font** — curl to `~/Library/Fonts`, fully automatable
5. **Git configs** — copy `.gitconfig` and `.config/git/ignore`, fully automatable
6. **SSH config** — copy `ssh/config` to `~/.ssh/config`, fully automatable
7. **uv** — curl installer, no sudo, fully automatable
8. **Python 3.12** — `uv python install --default 3.12`, fully automatable
9. **pre-commit + ruff** — `uv tool install`, fully automatable (depends on uv)
10. **jj** — `brew install jj` + copy config (depends on Homebrew)
11. **Cursor IDE configs** — copy settings, keybindings, mcp.json, fully automatable
12. **Claude Code settings** — copy to `~/.claude/settings.json`, fully automatable

### What Claude Code can do autonomously

Everything except steps that need sudo or secrets:

- Install Oh My Zsh, Powerlevel10k theme, and all 4 plugins (autosuggestions, completions, syntax-highlighting, forgit)
- Copy all config files to their destinations
- Install uv, Python 3.12, pre-commit, and ruff
- Install MesloLGS Nerd Font via curl
- Install jj via brew (only after Homebrew is installed)

### What requires human intervention

- **Homebrew install** — needs sudo password. User must run the installer or be present to enter password.
- **SSH key generation or transfer** — needs user's email for new keys, or manual file transfer for existing keys. iCloud Drive drag-and-drop is the most reliable transfer method (AirDrop is flaky with hidden directories).
- **Credential migration** — `~/.ssh/`, `~/.aws/` must be transferred securely from old machine.
- **Cursor MCP tokens** — after copying `mcp.json`, user must replace `<YOUR_GITLAB_TOKEN>` with their actual token.
- **Machine-specific env vars** — API tokens, cloud settings, etc. added to `~/.zshrc` per user's needs.

### Gotchas from experience

- **Homebrew not on PATH after install**: The installer prints instructions to add `eval "$(/opt/homebrew/bin/brew shellenv zsh)"` to `.zprofile`, but this doesn't take effect until a new shell. The `.zprofile` in this repo already includes it, but you need to either `source ~/.zprofile` or use the full path `/opt/homebrew/bin/brew` in the current session.
- **Oh My Zsh overwrites .zshrc**: The Oh My Zsh installer creates its own `.zshrc`. Copy the repo's `.zshrc` AFTER installing Oh My Zsh, not before.
- **uv not on PATH in current session**: After installing uv, use `~/.local/bin/uv` for the first commands until the shell profile is sourced.
- **AirDrop rejects transfers silently**: If transferring credentials between Macs, check that the receiving machine has AirDrop set to "Everyone" in System Settings. If it still fails, use iCloud Drive or USB instead.
- **Permissions after file transfer**: iCloud/AirDrop can loosen file permissions. Always run chmod after transferring SSH keys and AWS credentials.
- **SSH key not loaded after transfer**: Transferred keys won't be in the SSH agent. Run `ssh-add --apple-use-keychain ~/.ssh/id_ed25519_2025` to add with Keychain persistence.
- **Git remote uses HTTPS after clone**: If the repo was cloned via HTTPS, `git push` will fail with 401 after credential transfer. Switch to SSH: `git remote set-url origin git@github.com:blallen/ballen-config.git`.
