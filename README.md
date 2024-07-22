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

After everything is installed, copy over settings to your home directory. (Not sure if `.zprofile` is needed, testing on two different machines.)

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