# Command and configuration reference

[English](reference.md) | [简体中文](zh-CN/reference.md) · [Documentation](README.md)

Use this page to look up a setting or precise behavior. For your first setup, start with [Getting started](getting-started.md).

This describes the shared behavior implemented by the Python, Go, Rust, and Bash compatibility cores. Choose one [core implementation](../implementations/README.md). The [native environment convention](../spec/environment-v1.md) is a separate draft; the repository includes a reference consumer example but does not claim third-party adoption.

## Commands

| Command | Purpose |
|---|---|
| `devwho list` | List configured profile names. |
| `devwho show PROFILE` | Show profile metadata; custom environment values are hidden. |
| `devwho current [--verbose]` | Show the active profile and, optionally, effective Git identity and CLI paths. |
| `devwho doctor [PROFILE] [--offline]` | Compare actual tool identity with the profile. |
| `devwho exec PROFILE -- COMMAND ...` | Give one command and its descendants a profile. |
| `devwho config path` | Print the selected config file path. |
| `devwho config init` | Create a private TOML example config; refuse to overwrite. Unavailable in dotenv mode. |
| `devwho config export-env PROFILE` | Export generic environment values to literal dotenv; refuse lossy conversion. |
| `devwho init bash` / `devwho init zsh` | Print integration to evaluate in the current shell. |
| `setdev PROFILE` | Activate a profile in an initialized shell. |
| `setdev` | Activate `settings.shortcut_profile`, if configured. |
| `unsetdev` | Restore this shell’s original baseline. |

Use `devwho --config /absolute/path/config.toml COMMAND` to choose a different file for a command.

## Explicit dotenv input

Use `--env-file PATH [--env-profile NAME]` instead of `--config` to select the optional literal dotenv format. The file must select one profile with `DEVWHO_PROFILE`, or the caller must provide `--env-profile`; if both are present, they must match. Values are data: files are never sourced, interpolated, or merged with TOML. `config export-env PROFILE` exports only generic environment values and refuses profiles containing Git, SSH, GitHub, or explicit unset settings. See the [dotenv v1 contract](../spec/dotenv-v1.md) for grammar and limits.

## Profiles

Configuration lives at `$XDG_CONFIG_HOME/devwho/config.toml`, or `~/.config/devwho/config.toml`. `DEVWHO_CONFIG` or `devwho --config PATH ...` selects another file.

```toml
version = 1

[profiles.personal.git]
name = "Jane Doe"
email = "jane@example.com"

[profiles.personal.env]
TOOL_PROFILE = "personal"

[profiles.work.git]
name = "Jane Doe"
email = "jane@company.example"

[profiles.work.env]
TOOL_PROFILE = "work"
NEW_TOOL_ACCOUNT = "work"
```

`env` values are literal strings: `$HOME`, backticks and `$(...)` are not expanded. You can also use `unset_env = ["VARIABLE"]` at profile level. SSH key and GitHub config paths must be absolute, `~`, or start with `~/`; home-relative paths use the effective HOME after switching. Relative paths and `~other-user` are rejected. See [the runnable example](../examples/config.toml).

`show` displays identity metadata and custom variable names, with custom values hidden. Configuration is trusted local input: tools may interpret variables or explicit Git configuration as executable settings. DevWho quotes shell output; it does not sandbox those tools or isolate the shared OS account.

`current --verbose` displays effective Git author/committer metadata and the GitHub CLI configuration location. Use `doctor` to compare them with the profile and verify an actual GitHub login.

## Switch and restore

`setdev PROFILE` affects the current shell and future descendants. Other terminals and already-running applications retain their environments.

`unsetdev` restores the baseline captured before the first activation. Unset, empty and nonempty values are distinct. A → B → C → unset returns to the original baseline, rather than the previous profile. A variable dropped by a new profile is restored immediately. Subsequent user edits to that now-unmanaged variable are preserved.

Shell state is held in a non-exported `__DEVWHO_STATE` variable. Children inherit the active environment, without inheriting the parent's restoration state. In an inherited shell, its inherited environment is its own baseline; initialization preserves its `DEVWHO_PROFILE` marker.

Optional preferences make a shared machine convenient:

```toml
[settings]
default_profile = "personal"
shortcut_profile = "work"
handoff_warning = true
```

The default is applied on initialization of a fresh, inactive shell and becomes its baseline. Thus `setdev` selects `work`, while `unsetdev` returns to `personal`. Without these settings, initialization leaves identity unchanged and a profile name is required. `handoff_warning` is opt-in: it checks the current repository for uncommitted changes after switching, with a short timeout. It never assigns, stashes or removes those changes.

When sharing one working copy, finish or explicitly hand over uncommitted changes and stop the previous person's editing tasks before taking over. Process environment isolation does not prevent simultaneous writes to one repository.

## Child-process execution

```bash
devwho exec work -- git status
devwho exec work -- bash
devwho exec work -- codex --version
```

The command and its descendants get the selected profile. The parent environment stays unchanged. Existing variables absent from the profile remain inherited; exec is not an environment sandbox. On POSIX the command replaces the DevWho process, retaining normal signals and exit status. No executable or agent-specific login settings are managed by DevWho.

## Git behavior

Git name/email compile into `GIT_CONFIG_COUNT` and indexed runtime settings for `user`, `author` and `committer`. They override config files, including stale repository identity fields; explicit Git `-c` options and explicit author controls retain Git's normal precedence. No `.gitconfig` or repository config is rewritten.

DevWho deliberately avoids long-lived `GIT_AUTHOR_*` and `GIT_COMMITTER_*`, so cherry-pick and rebase retain original authors. Nonempty inherited direct identity overrides cause activation to fail; their values are not printed or silently cleared.

Existing runtime pairs are preserved. Third-party pairs appended during activation survive switching and restoration. If the existing prefix or DevWho's managed block is changed, restoration fails rather than deleting unidentified configuration; reopen a fresh shell or undo the external edit. This conservative limit is intentional.

Basic signing settings `signing_key`, `signing_format` and `sign_commits` compile to Git runtime configuration. DevWho does not generate keys or prove a signature is trusted. For other runtime settings:

```toml
[profiles.work.git.config]
"commit.gpgSign" = "false"
```

Values are strings or arrays of strings, preserving repeated config keys. Signing configured by itself does not require Git name/email.

## Git SSH

```toml
[profiles.work.git_ssh]
identity_file = "~/.ssh/id_ed25519_work"
identities_only = true
```

The key must exist. DevWho safely quotes its path in `GIT_SSH_COMMAND`; Git fetch/pull/push inherit this command. It does not rewrite `~/.ssh/config`, create keys, manage agents, or select identity for standalone `ssh`. An existing separate agent can be selected through generic `SSH_AUTH_SOCK`.

The local doctor checks the configured command/key, not remote SSH account ownership. Remote authentication remains a separate verification step.

## GitHub CLI

```toml
[profiles.work.github]
hostname = "github.com"
expected_user = "jane-work"
config_dir = "~/.config/devwho/github/work"
```

DevWho exports `GH_CONFIG_DIR` and `GH_HOST`. Perform the one-time login in each context with `devwho exec work -- gh auth login`. DevWho never copies or prints tokens. GitHub CLI manages its credentials. Nonempty `GH_TOKEN` or `GITHUB_TOKEN` conflicts with a GitHub profile and causes local activation to fail.

Git commit identity, Git transport credentials, and GitHub CLI login are separate. A matching `gh` login does not prove Git HTTPS/GCM uses that account. Configure and verify the transport separately; ordinary profile activation does not rewrite remotes or automatically convert SSH to HTTPS.

## Diagnose

```bash
devwho doctor
devwho doctor work --offline
```

Doctor inspects the current environment against the requested profile; it does not switch it first. Git identities are checked through real Git. Configured GitHub identities are checked using `gh api user`. Mismatches include expected and actual account metadata. API failures are `UNVERIFIED`, never silently treated as success. `--offline` skips that request.

Exit codes: `0` verified checks passed, `1` failure/mismatch, `2` a required check is unavailable or skipped, including local tool failures or skipped online verification. Exec retains the child exit code, with `127` for a missing command and `126` for a non-executable command. Activation and ordinary inspection are offline; network requests occur only in explicit live doctor checks. Optional handoff notices perform a local repository check.

