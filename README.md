# ballen-config

Files and instructions to set up computers the way I like.

# Shell Setup

## Install zsh (Ubuntu only)

Install using `apt`. macOS has zsh pre-installed.

```bash
sudo apt update
sudo apt install zsh -y
zsh --version
```

## Set up Oh My Zsh

Install Oh My Zsh and recommended plugins. Shortened version of the guide [here](https://github.com/magicdude4eva/iterm-oh-my-zsh-powerlevel10k).

```bash
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-completions ${ZSH_CUSTOM:=~/.oh-my-zsh/custom}/plugins/zsh-completions
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
git clone https://github.com/wfxr/forgit ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/forgit
```

After everything is installed, copy over settings to your home directory.

```bash
cp .zshrc ~/.zshrc
cp .p10k.zsh ~/.p10k.zsh
cp .zprofile ~/.zprofile
```

# Git Setup

Copy the included `.gitconfig` to your home directory (or update the name/email to your own).

```bash
cp .gitconfig ~/.gitconfig
```

Copy the global gitignore.

```bash
mkdir -p ~/.config/git
cp .config/git/ignore ~/.config/git/ignore
```

## SSH Setup

Create an SSH key for this machine (or copy existing keys from your old machine).

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

Copy the SSH config template and update with your hosts.

```bash
cp ssh/config ~/.ssh/config
chmod 600 ~/.ssh/config
```

Remember to add your new public key to GitHub and GitLab after generating it.

# Jujutsu (jj) Setup

[Jujutsu](https://github.com/jj-vcs/jj) is a modern VCS that works alongside git. Install it using your package manager.

```bash
# macOS
brew install jj

# or via cargo
cargo install --locked jj-cli
```

Copy the jj config to your home directory.

```bash
mkdir -p ~/.config/jj
cp .config/jj/config.toml ~/.config/jj/config.toml
```

The included config provides:

- **Quick aliases:** `jj c` (commit), `jj p` (push)
- **Checked aliases:** `jj cc` (commit with pre-commit checks), `jj pp` (push with checks)
- **`jj fix` integration:** Runs pre-commit, ruff lint, and ruff format across mutable commits

# Python Setup (uv)

[uv](https://docs.astral.sh/uv/) replaces pyenv, poetry, and pipx as a single tool for Python version management, dependency management, and CLI tool installation.

## Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

This installs uv to `~/.local/bin/` and updates your shell profile. The `.zshrc` and `.zprofile` in this repo already have the PATH configured.

## Install Python

uv downloads pre-built Python binaries (no compilation needed).

```bash
# Install a Python version
uv python install 3.12

# Make it the default (creates python3 and python symlinks in ~/.local/bin)
uv python install --default 3.12

# List installed versions
uv python list

# Pin a version for a specific project
uv python pin 3.12
```

## Project workflow

uv replaces poetry for dependency and project management.

```bash
# Create a new project
uv init my-project
cd my-project

# Add dependencies
uv add requests pandas

# Add dev dependencies
uv add --dev pytest ruff

# Sync environment (install all deps)
uv sync

# Run commands in the project's virtual environment
uv run python my_script.py
uv run pytest
```

## Global CLI tools

uv replaces pipx for installing standalone CLI tools.

```bash
# Install global tools
uv tool install pre-commit
uv tool install ruff

# Run a tool without installing
uvx cowsay "hello"
```

# Pre-commit and Ruff

Install both `pre-commit` and `ruff` as global tools using uv.

```bash
uv tool install pre-commit
uv tool install ruff
```

Copy the `.pre-commit-config.yaml` and `ruff.toml` files to the root of your repository to enable pre-commit hooks and linting.

Run the following commands to install the pre-commit hooks and run `ruff` on existing files.

```bash
pre-commit install
pre-commit run --all-files
```

# Cursor IDE Setup

Copy the Cursor settings and keybindings to the Cursor config directory.

```bash
cp cursor/settings.json ~/Library/Application\ Support/Cursor/User/settings.json
cp cursor/keybindings.json ~/Library/Application\ Support/Cursor/User/keybindings.json
```

Copy the MCP server config and update the placeholder tokens.

```bash
cp cursor/mcp.json ~/.cursor/mcp.json
```

Edit `~/.cursor/mcp.json` and replace `<YOUR_GITLAB_TOKEN>` with your actual token. Add any additional project-specific MCP servers as needed.

Required font: [MesloLGS Nerd Font](https://github.com/romkatv/powerlevel10k#manual-font-installation) (also needed for Powerlevel10k).

# Claude Code Setup

Install [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and copy the plugin settings.

```bash
mkdir -p ~/.claude
cp claude-code/settings.json ~/.claude/settings.json
```

This enables the [superpowers](https://github.com/anthropics/claude-code-plugins) plugin. Claude Code will download plugins automatically on first run.

Note: The Cursor `settings.json` includes `claudeCode.environmentVariables` for Bedrock — update these if your setup differs.

# New Machine Migration Checklist

## Credentials to port securely (not in this repo)

These must be transferred securely (e.g., AirDrop, encrypted USB, or password manager):

- `~/.ssh/id_ed25519_*` — SSH key pairs (private + public)
- `~/.ssh/*.pem` — AWS keypairs
- `~/.aws/credentials` — AWS credentials
- `~/.aws/config` — AWS CLI config

## Local-Only Configuration

After copying configs to a new machine, add machine-specific environment variables directly to `~/.zshrc`. These should NOT be committed to this repo.

Examples:

- API tokens and secrets (`GITLAB_TOKEN`, etc.)
- Cloud provider settings (`AWS_REGION`, etc.)
- Machine-specific PATH additions
