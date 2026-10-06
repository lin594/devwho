# Migration notes for the local prototype

This page describes how to move from the earlier local DevWho prototype to the environment-first v0.1 design. The prototype source is not included in this checkout, so verify local paths and exact command names before removing anything.

## Before migrating

1. Keep a backup of any local prototype configuration and shell snippets.
2. Do not copy tokens, GitHub CLI login data, SSH private keys, or private-key contents into the new DevWho configuration.
3. Inspect shell startup files and remove only the old DevWho initialization lines after confirming the replacement works. The v0.1 initialization is explicit; it does not edit rc files for you.
4. Check for old installer changes to VS Code settings and GitHub CLI config directories. Do not copy those machine-specific changes as part of migration.

## Configure the new profile

Create the v1 TOML file at the path reported by `devwho config path`. Define Git name/email and, if needed, Git SSH and GitHub CLI metadata. Use the generic `env` table for tools that accept environment variables. See [`examples/config.toml`](../examples/config.toml) for fictional, portable examples.

Keep the local default profile in `[settings]` if desired. For example, set `default_profile = "personal"` and `shortcut_profile = "work"`. The configured default becomes the baseline restored by `unsetdev`.

## Activate and verify

After installing the new executable, explicitly initialize the current shell with `eval "$(devwho init zsh)"` or the Bash equivalent. Then activate a profile with `setdev <profile>`. Use `devwho doctor` when you want to verify actual Git and GitHub CLI identity; activation itself does not make network requests.

The v0.1 design keeps state in the current shell. `unsetdev` restores the environment that existed before the first DevWho activation, including a configured local default baseline. `devwho exec <profile> -- <command>` gives only the child process tree that profile and leaves the parent shell unchanged.

## Behavior changes to account for

- The prior prototype used Git runtime include configuration and a separate `GH_CONFIG_DIR`; v0.1 compiles profile fields into a process environment patch and uses `GH_CONFIG_DIR` for GitHub CLI context.
- There is no global current-profile file. Two terminals can hold different profiles at once.
- No installer copies `gh` authentication state or modifies VS Code settings.
- DevWho does not persistently export `GIT_AUTHOR_*` or `GIT_COMMITTER_*`. This protects replayed commits from having their original author replaced. Existing direct author/committer override variables or conflicting credential selectors should produce a clear activation error; migration must not silently unset user-owned values.
- SSH key and GitHub config paths in examples are optional references. Confirm that local paths exist and that the credentials remain managed by SSH agent, GitHub CLI, or the operating system's credential provider.

Do not remove old local configuration until the new profile has been checked in a disposable repository and the intended shell restoration behavior has been confirmed.
