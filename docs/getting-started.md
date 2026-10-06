# Getting started

[English](getting-started.md) | [简体中文](zh-CN/getting-started.md) · [Documentation](README.md)

This guide gets you from a new installation to checking the identity Git will use. You do not need a GitHub login or a test commit for the first run.

These instructions install the **currently available Python compatibility core**. Independent Go, Rust, and Bash alternatives are [available](../implementations/README.md); the separate [native environment convention](../spec/environment-v1.md) is a draft and needs no Python library in consumer applications.

## Check your terminal and tools

Use Bash or Zsh on Linux, WSL, or macOS. On Windows, open your WSL terminal and run all steps there. Native PowerShell and VS Code account switching are not supported in v0.1.

```sh
python3 --version
git --version
```

You need Python 3.11 or later and Git 2.31 or later for the Git workflow. Git's environment-based configuration arrived in [Git 2.31](https://github.com/git/git/blob/master/Documentation/RelNotes/2.31.0.adoc). If either command is missing or too old, install or update it with your OS's usual package manager, then repeat the check. DevWho reuses those tools; it does not install a Python or Git copy for each identity.

Not sure which shell you are in? `echo "$BASH_VERSION"` prints a version in Bash; `echo "$ZSH_VERSION"` prints one in Zsh. Use the matching initialization line later.

## Install the single-file version

If `devwho --version` already works, skip to configuration. Otherwise, from a directory where you keep tools or source projects:

```sh
git clone https://github.com/lin594/devwho.git
cd devwho
python3 scripts/build_zipapp.py
mkdir -p "$HOME/.local/bin"
install -m 755 dist/devwho-0.1.0rc1.pyz "$HOME/.local/bin/devwho"
export PATH="$HOME/.local/bin:$PATH"
devwho --version
```

You should see `devwho 0.1.0-rc.1`. The installed file contains DevWho, but still uses your system's Python 3.11+. It has no third-party runtime dependencies. Retain the source checkout if you want to update from it later.

If you already use pipx, you may instead run `pipx install .` from the checkout. Ensure pipx's executable directory is on PATH, then check `devwho --version`. Choose one installation method so you know which executable you are updating. There is no PyPI release yet; these instructions install this repository's code.

## Create two profiles

A **profile** is a named group of settings. `personal` and `work` are example names, not required account names.

```sh
devwho config init
devwho config path
```

Open the printed path in your usual text editor. The default is `~/.config/devwho/config.toml`; if you set `XDG_CONFIG_HOME` or `DEVWHO_CONFIG`, use the path printed by the command. `config init` refuses to overwrite an existing file.

For a new configuration, replace the starter file with this example, using your chosen commit names and emails. If the file already contains your profiles, keep them and only add or adjust the entries you need:

```toml
version = 1

[profiles.personal.git]
name = "Jane Doe"
email = "jane.personal@example.test"

[profiles.work.git]
name = "Jane Doe"
email = "jane.work@example.test"
```

TOML is a text configuration format: keep the brackets and quotes, and edit the values inside the quotes. `name` is the name displayed on commits. `email` should be the address you want on those commits, which can be a GitHub noreply address. Neither value authenticates you to GitHub.

## Activate and verify

For Bash:

```sh
eval "$(devwho init bash)"
```

For Zsh:

```sh
eval "$(devwho init zsh)"
```

Run only the line matching your current shell. It defines `setdev` and `unsetdev` in that shell. Now try:

```sh
devwho list
setdev work
devwho current
git config user.email
devwho doctor --offline
unsetdev
devwho current
```

`list` shows `personal` and `work`. After switching, `current` shows `work` and Git shows your work email. With this Git-only configuration, `doctor --offline` should report `OK`. After restoring in a fresh terminal, `current` shows `none`; your original Git configuration applies again. An inherited or default profile can have a different restoration result, explained in [Everyday workflows](use-cases.md).

## Make it available in new terminals

Once the trial works, open **one** startup file: `~/.bashrc` for Bash or `~/.zshrc` for Zsh. Add the appropriate block once.

Bash:

```sh
export PATH="$HOME/.local/bin:$PATH"
eval "$(devwho init bash)"
```

Zsh:

```sh
export PATH="$HOME/.local/bin:$PATH"
eval "$(devwho init zsh)"
```

For a pipx installation, use its executable directory if it differs from `~/.local/bin`. Open a new terminal and run `devwho list`, then `setdev work`.

Some Bash terminals, including common macOS setups, open a login shell that reads `~/.bash_profile`. If your existing login configuration does not already load `~/.bashrc`, add this to `~/.bash_profile` once:

```sh
if [ -f "$HOME/.bashrc" ]; then
    . "$HOME/.bashrc"
fi
```

DevWho prints initialization code but never edits startup files itself. Keep your existing shell setup and add the small integration block to it.

## Update or uninstall

For the single-file installation, run these inside a clean source checkout:

```sh
git pull --ff-only
python3 scripts/build_zipapp.py
install -m 755 dist/devwho-0.1.0rc1.pyz "$HOME/.local/bin/devwho"
```

Then open a new terminal and check `devwho --version`. For pipx, reinstall from the updated checkout with `pipx install --force .`.

To uninstall, first remove the DevWho initialization line from your shell startup file. For the single-file method, remove `~/.local/bin/devwho`; for pipx, run `pipx uninstall devwho`. Open a new terminal. Keep the PATH line if other tools use it. Your DevWho configuration and any gh login directories remain available for you to keep or remove separately.

Next: [choose a daily workflow](use-cases.md), [connect existing accounts](accounts.md), or [troubleshoot a problem](troubleshooting.md).
