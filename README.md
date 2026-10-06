# DevWho

**Switch developer identities in your terminal. Keep your projects where they are.**

[English](README.md) | [简体中文](README.zh-CN.md)

[![CI](https://github.com/lin594/devwho/actions/workflows/ci.yml/badge.svg)](https://github.com/lin594/devwho/actions/workflows/ci.yml) · [MIT license](LICENSE) · [Documentation](docs/README.md) · [Get help](https://github.com/lin594/devwho/issues)

DevWho helps people who use more than one developer identity: personal and work accounts, client projects, or two people sharing a development machine. Save each identity once, then choose it for the terminal you are using.

Your next Git commit uses the selected name and email. You can also choose a Git SSH key, a GitHub CLI account configuration, and other tools' environment settings. Your existing project folders and installed tools stay in place.

## When is this useful?

| Your situation | What DevWho helps you do |
|---|---|
| You use personal and work Git identities. | Switch before working, then check the name and email Git will use. |
| Two people share one development machine. | Give a new terminal a default identity and make the other identity an explicit choice. |
| You need different identities in two terminals. | Select each independently, even in the same project directory. |
| A command needs a particular tool configuration. | Run it with a profile while keeping the parent terminal as it was. |

If Git's directory-based `includeIf` already solves your problem, you may not need DevWho. It is most useful when identity depends on **who is using this terminal**, rather than where a repository lives. [Compare approaches →](docs/alternatives.md)

## A shared convention, with compatibility for today's tools

The goal is to choose a context once and have applications use it, much like applications read proxy environment variables. Native applications would read `DEVWHO_PROFILE` and map the context to their own accounts. They would not need a Python module, a version variable, or a separate DevWho variable for every application. This [environment convention](spec/environment-v1.md) is currently a **draft**.

Today, a **compatibility core** makes existing tools work by translating profiles into Git runtime configuration, `GH_CONFIG_DIR`, and other existing interfaces. Independent Python, Go, Rust, and Bash implementations share the same switching contract. Choose one core that fits your machine; Go and Rust binaries run without Python or a compiler.

[How the ecosystem fits together](docs/ecosystem.md) · [Implementation status and roadmap](implementations/README.md)

The runtime convention is independent of file formats. All four cores read complete TOML profiles and optional [literal dotenv input](docs/configuration-formats.md). An optional [configuration frontend](docs/configuration-ui.md) provides English/Chinese prompts and safe saves, so beginners need not edit TOML. Native applications need only the resulting environment, not the producer's files.

## What daily use looks like

After the one-time setup below, `work` and `personal` are names you choose for saved identities:

```sh
setdev work
git config user.email
# jane.work@example.test

setdev personal
git config user.email
# jane.personal@example.test

unsetdev                 # Restore this terminal's identity from before switching
```

Only this terminal and programs subsequently launched from it receive the change. Other terminals and already-running applications keep their own settings. Switching in a terminal does **not** switch an existing VS Code window, Copilot, or browser login.

## What you need today

| Requirement | When you need it |
|---|---|
| Linux, WSL, or macOS with Bash or Zsh | To use the terminal integration. Ubuntu/macOS and Python 3.11/3.13 run in [CI](https://github.com/lin594/devwho/actions/workflows/ci.yml); WSL is also checked locally. |
| One core | Go/Rust binary, Bash + jq + Perl, **or** Python 3.11+. [Choose one](implementations/README.md). |
| Git **2.31+** | To follow this guide and switch Git identity. |
| GitHub CLI (`gh`) | Optional: only for GitHub CLI account profiles and online identity checks. |
| OpenSSH and an existing key | Optional: only for selecting a Git SSH key. |

There are **no third-party Python dependencies at runtime**. The installation below uses your existing Python; pipx, Node.js, and Docker are not required. Windows PowerShell integration is planned; Windows users should use WSL for now.

**No Python installed?** Choose a tested Go/Rust artifact from the [v0.1.0-rc.1 pre-release](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1), or install the [Bash core](implementations/bash/README.md). See the [download/build instructions and actual dependencies](implementations/README.md). Release assets include a combined SHA256SUMS and commit manifest. CI artifacts remain development builds and require GitHub sign-in.

## Try it

DevWho is an early **v0.1** project. The first tagged candidate is [v0.1.0-rc.1](https://github.com/lin594/devwho/releases/tag/v0.1.0-rc.1); package registry publication is deferred. Already have `devwho --version` working? Continue with step 2.

### 1. Install once

Choose [one core](implementations/README.md) first. The following source-install example is for users who already have Python 3.11+. With a Go/Rust/Bash core installed, skip to step 2.

Run these commands in a Bash or Zsh terminal:

```sh
git clone https://github.com/lin594/devwho.git
cd devwho
python3 scripts/build_zipapp.py
mkdir -p "$HOME/.local/bin"
install -m 755 dist/devwho-0.1.0rc1.pyz "$HOME/.local/bin/devwho"
export PATH="$HOME/.local/bin:$PATH"
devwho --version
```

Expected output: `devwho 0.1.0-rc.1`. This installs one executable for your OS user, shared by all profiles. See [Getting started](docs/getting-started.md) for version checks, a pipx alternative, and updating or removing it.

### 2. Save your identities

With the optional Go configuration frontend installed, run `devwho-setup configure` and follow the prompts. It saves the same file used by every core. Otherwise, use the editable example below. [Configuration UI and backups →](docs/configuration-ui.md)

```sh
devwho config init
devwho config path
```

Open the printed file in your text editor. For a new configuration, replace the starter contents with the example below, then replace Jane's names and emails with the identities you use. If you already have profiles, keep them and add or adjust only the profiles you need. These are commit details, not passwords or GitHub usernames. You can name the profiles anything you like.

```toml
version = 1

[profiles.personal.git]
name = "Jane Doe"
email = "jane.personal@example.test"

[profiles.work.git]
name = "Jane Doe"
email = "jane.work@example.test"
```

An existing configuration is kept: if `config init` says the file already exists, edit that file instead. Most users will find it at `~/.config/devwho/config.toml`.

### 3. Switch and check

Initialize **your current shell** using one of these lines:

```sh
eval "$(devwho init bash)"    # Bash
# eval "$(devwho init zsh)"  # Zsh: use this line instead
```

Then try:

```sh
setdev work
devwho current              # Prints: work
git config user.email       # Prints the work email you saved
devwho doctor --offline     # Checks the effective Git identity locally
unsetdev
devwho current              # Prints: none, in a fresh terminal with this example
```

`none` means no DevWho profile is selected; Git falls back to the settings that terminal had before switching. No commit or push is needed to try this.

To make the commands available in future terminals, add the PATH and matching initialization lines to your shell startup file once. [Exact startup steps →](docs/getting-started.md#make-it-available-in-new-terminals)

## Everyday commands

| I want to… | Command |
|---|---|
| See my saved identities | `devwho list` |
| Switch this terminal | `setdev work` |
| Check the current identity and Git details | `devwho current --verbose` |
| Restore the original terminal settings | `unsetdev` |
| Use a profile for one command | `devwho exec work -- git status` |
| Check that my configured GitHub CLI login is correct | `devwho doctor` |

For a shared computer, [set a default and a shortcut](docs/use-cases.md): a new terminal can start as `personal`, `setdev` can choose `work`, and `unsetdev` can return to `personal`.

## Does this also log me into GitHub?

Git **commit details**, **push credentials**, and the **GitHub CLI login** are separate. The example above selects commit details. To choose a GitHub CLI account or Git SSH key, follow [Accounts and authentication](docs/accounts.md). DevWho uses your existing credential tools; it does not create accounts or log in on your behalf.

When two people share the same working copy, agree on how to hand over uncommitted work and stop the previous person's editing tasks. Selecting a profile does not separate their files or make simultaneous edits safe.

## Where to go next

| Goal | Read |
|---|---|
| Complete setup, update, or uninstall | [Getting started](docs/getting-started.md) |
| Personal/work accounts, shared computers, and one-off commands | [Everyday workflows](docs/use-cases.md) |
| Reuse GitHub CLI logins or Git SSH keys | [Accounts and authentication](docs/accounts.md) |
| Fix `command not found`, login mismatches, or restore errors | [Troubleshooting](docs/troubleshooting.md) |
| Look up a command or TOML setting | [Reference](docs/reference.md) |
| Understand the native convention and current adapters | [Ecosystem design](docs/ecosystem.md) |
| Help build a complete Python-free implementation | [Core implementations](implementations/README.md) |
| Report a bug or help improve DevWho | [Contributing](CONTRIBUTING.md) |

More: [documentation index](docs/README.md) · [changes](CHANGELOG.md) · [security reports](SECURITY.md) · [MIT license](LICENSE)
