# Everyday workflows

[English](use-cases.md) | [简体中文](zh-CN/use-cases.md) · [Documentation](README.md)

These examples assume you completed [Getting started](getting-started.md) and created `personal` and `work` profiles.

## Use personal and work identities in the same project

Open your existing project directory and select the identity before working:

```sh
setdev work
devwho current --verbose
git status
```

The next Git commit uses the profile's name and email. A second, independently opened terminal can run `setdev personal` without changing the first terminal. Folder names such as `workspace/owner/repo` do not determine the person making a commit.

When finished, `unsetdev` restores the settings from before this shell's first activation. If you switch personal → work → personal, `unsetdev` still returns to that original state; it does not act as a back button.

## Give a shared computer a simple default

Put this **top-level** table in the same configuration file, before the profile tables:

```toml
[settings]
default_profile = "personal"
shortcut_profile = "work"
handoff_warning = true
```

Keep `version = 1` at the top of the file, and retain both profiles. After opening a new, independent terminal:

| Action | Active profile |
|---|---|
| Open a terminal | `personal` |
| Run `setdev` | `work` |
| Run `unsetdev` | `personal` |
| Run `setdev personal` | `personal` |

You can use people's names instead of `personal` and `work`. An experienced user gets a short command, while the default user can work normally.

The optional handoff warning checks the current repository for uncommitted changes after a switch. It does not stash, clean files, switch branches, or decide who owns existing changes. Before sharing one working copy, handle or explicitly hand over uncommitted work and stop the previous person's editor tasks. Separate copies work with the same commands.

## Give one command a profile

```sh
devwho exec work -- git status
devwho exec work -- gh api user --jq .login
```

The second command needs a configured GitHub profile and a completed login; see [Accounts](accounts.md). After either command exits, the parent terminal has the same identity as before. Commands started by that child inherit its selected environment too.

This also works for other developer tools that consume environment variables. It does not switch an application's separate in-app account automatically.

## Start a child shell

```sh
setdev work
bash
eval "$(devwho init bash)"  # Initialize the child if Bash was not already configured
```

The child starts with `work`. Its own `unsetdev` returns to the environment it inherited, so it cannot restore the parent's earlier personal profile. Use `exit` to return to the parent, then `unsetdev` there, or explicitly select `personal` in the child.

An independently opened terminal uses the configured default instead. This distinction lets deliberate inheritance work while keeping unrelated terminals independent.

## Select environment settings for another tool

Add literal values to a profile:

```toml
[profiles.work.env]
TOOL_PROFILE = "work"
```

After `setdev work`, programs started there see `TOOL_PROFILE=work`. This is useful only if the tool actually reads that variable. DevWho does not invent an account-switching interface for tools that lack one.

Values are literal: `"$HOME/work"` remains that exact text. Only the dedicated Git SSH and GitHub path fields expand home-relative paths. See [Reference](reference.md) for explicit unsets and restoration rules.
