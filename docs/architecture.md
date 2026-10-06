# Architecture decision: environment-first identity

**Status:** accepted for v0.1 design  
**Date:** 2026-10-06

This page describes the **current compatibility core**. The separate [ecosystem design](ecosystem.md) and [environment convention draft](../spec/environment-v1.md) describe future native consumers. Python is the current implementation language, not a requirement for that convention. Full Go, Rust, and Bash ports target the [same core contract](../spec/compatibility-core-v1.md).

## Decision

DevWho treats a developer profile as configuration that compiles into an environment patch. The patch is applied at a shell boundary or to a child process. DevWho does not own Git, SSH, GitHub CLI, or other developer tools, and it does not maintain machine-global active identity.

The data path is:

```text
TOML profile → parse and validate → compile EnvironmentPatch → shell transition or child environment
```

`EnvironmentPatch` represents both values to set and keys to unset. Generic `[profiles.<name>.env]` values are literal strings. They are never evaluated by a shell. Explicit path fields such as SSH key and GitHub config paths may expand `~` using structured code, without `eval` or command substitution.

SSH key and GitHub config paths must be absolute or start with `~/` (or be `~`). They are compiled against the effective HOME after restoring variables dropped by the previous profile and applying the target profile's environment. This keeps account selection independent of the current working directory and previous profile. Conflicting inherited author or token overrides are still checked before restoration.

## Configuration model

The configuration is versioned TOML (`version = 1`) at `$XDG_CONFIG_HOME/devwho/config.toml`, falling back to `~/.config/devwho/config.toml`. The schema supports optional `[settings]` values `default_profile` and `shortcut_profile`, plus named profiles with:

- `git.name` and `git.email`;
- `git_ssh.identity_file` and `git_ssh.identities_only`;
- `github.hostname`, `github.expected_user`, and `github.config_dir`;
- arbitrary literal values under `env`;
- optional `unset_env` keys.

Git identity is supplied through Git runtime configuration for `user.name`, `user.email`, `author.name`, `author.email`, `committer.name`, and `committer.email`. DevWho does not persistently export `GIT_AUTHOR_*` or `GIT_COMMITTER_*`: direct author environment variables can override replay or rebase metadata and would defeat the requirement to preserve original authors. When pre-existing identity override variables (including direct author variables or `GH_TOKEN`) conflict with activation, activation should fail with an actionable diagnostic and leave the shell unchanged; it must not silently delete them.

Git SSH settings are scoped to Git operations, for example via `GIT_SSH_COMMAND`; DevWho does not claim to configure every OpenSSH use and does not edit `~/.ssh/config`. GitHub CLI profiles use `GH_CONFIG_DIR`. A configured directory or `DEVWHO_PROFILE` marker alone is not proof of the actual account; `doctor` performs consumer-level checks when requested.

## Shell lifecycle

`devwho init bash` and `devwho init zsh` print integration code. The user explicitly evaluates that output in their shell. The integration defines `setdev` and `unsetdev` functions and keeps `__DEVWHO_STATE` as a non-exported shell variable.

On the first activation, DevWho snapshots the original set/unset state and value of every managed key. Switching profiles applies a transition from that baseline, so keys removed by the new profile return to their original baseline. Repeated activation is idempotent. `unsetdev` restores the captured baseline. If the user configured `settings.default_profile`, it is the local startup baseline. Public examples use fictional profiles.

All profile resolution, validation, patch compilation, and shell rendering must finish before the shell applies any changes. Invalid configuration or profile references leave the shell unchanged. Shell output is a security boundary: Bash and Zsh rendering must quote values as data, including quotes, dollar signs, command substitutions, newlines, control characters, and Unicode.

## Child processes

`devwho exec <profile> -- <command...>` compiles the same patch and applies it only to the spawned command's environment. Parent state remains unchanged; descendants inherit the selected context normally. `devwho exec work -- bash` is the supported context-subshell pattern.

## Network and credentials

`setdev` is local, fast, and deterministic. It does not contact GitHub or inspect tokens. `doctor` may invoke local Git/SSH checks and, when GitHub configuration is present, `gh api user` to compare the actual login with `expected_user`; unavailable network/API results are `UNVERIFIED`, not identity mismatches. DevWho stores metadata and paths, never credential contents or copied login state. Status and profile inspection do not dump arbitrary environment values.

## Deliberate v0.1 limits

Bash and Zsh are the supported shell integrations. No automatic directory switching, daemon, GUI/TUI, broad cloud-tool integration suite, or complex remote policy engine is included. PowerShell and editor integrations remain experimental follow-up work. No claim in this decision document means implementation or validation has already passed.
