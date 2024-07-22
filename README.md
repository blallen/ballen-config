# ballen-config
Files and instructions to set up computer's the way I like

# Shell Setup

## Install zsh (Ubuntu only)

Install using `apt`. MacOS has zsh pre-installed.

```
sudo apt update
sudo apt install zsh -y
zsh --version
```

## Set up Oh My Zsh

Install Oh My Zsh and recommended plugins. Shortened version of the guide [here](https://github.com/magicdude4eva/iterm-oh-my-zsh-powerlevel10k).

```
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-completions ${ZSH_CUSTOM:=~/.oh-my-zsh/custom}/plugins/zsh-completions
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
git clone https://github.com/wfxr/forgit ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/forgit
```

After everything is installed, copy over settings to your home directory.

```
cp .zshrc ~/.zshrc
cp .p10k.zsh ~/.p10k.zsh
cp .zprofile ~/.zprofile
```

# Git Setup

When using git for the first time on a new machine, make sure to setup your local git config.

```
git config --global user.name "John Doe"
git config --global user.email johndoe@example.com
```

Set up your default git text editor (vim is nice to avoid conflicts when using the built-in terminal in VSCode and Cursor).

```
git config --global core.editor "vim"
```

Create an ssh key for this machine.

```
ssh-keygen -t ed255519 -C "john.doe@example.com"
```

# Python Setup

Using `pyenv` and `poetry` to manage python environments is great. `pipx` is nice to install global tools.

## pipx

Below is a OS independent way to install `pipx` if you already have a python installation. Otherwise, you can install `pipx` using the OS specific instructions [here](https://github.com/pypa/pipx?tab=readme-ov-file#install-pipx).

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
sudo pipx ensurepath --global # optional to allow pipx actions with --global argument
```

## pyenv

1. Download and run the official installer.

```
curl https://pyenv.run | bash
```

2. Configure your zsh environment by adding the following lines near the end of your `.zshrc`. (Not necessary if you copied the `.zshrc` from earlier.)

```
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

3. Create a `.zprofile` with the following lines.

```
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
```

4. Check that pyenv works and see what pythons you have installed.

```
pyenv --version
pyenv versions
```

5. Install python build dependencies. Follow [the instructions here](https://github.com/pyenv/pyenv/wiki#suggested-build-environment), really different based on OS and what package manager you are using.

6. Install a new python version (change version number as necessary).

```
pyenv install 3.11.7
```

## poetry

1. Download and run the official installer.

```
curl -sSL https://install.python-poetry.org | python3 -
```

a.  Need a different command on macOS because of [good old Mac Weirdness](https://github.com/python-poetry/install.python-poetry.org/issues/24#issuecomment-2016821135).

```
curl -sSL https://install.python-poetry.org | sed 's/symlinks=False/symlinks=True/' | python3
```

2. Add poetry to your path in `.zshrc`. (Not needed if you copied the `.zshrc` from earlier.)

```
export PATH="$HOME/.local/bin:$PATH"
```

3. Check that poetry works.

```
poetry --version
```

4. Setup poetry to create virtual environments in the repository directory and to use the python version you’ve selected using `pyenv`

```
poetry config virtualenvs.in-project true
poetry config virtualenvs.prefer-active-python true
```

5. Add poetry completions to your Oh My Zsh plugins.

```
mkdir $ZSH_CUSTOM/plugins/poetry
poetry completions zsh > $ZSH_CUSTOM/plugins/poetry/_poetry
```

## pre-commit and ruff

Install both `pre-commit` and `ruff` using `pipx`.

```
pipx install pre-commit
pipx install ruff
```

Copy over the `.pre-commit-config.yaml` and `ruff.toml` files to the root of your repository to enable pre-commit hooks and linting.

Run the following commands to install the pre-commit hooks and run `ruff` on the existing files.

```
pre-commit install
pre-commit run --all-files
```
