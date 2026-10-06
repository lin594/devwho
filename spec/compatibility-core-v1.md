# Compatibility core v1 — cross-language contract

[English](compatibility-core-v1.md) | [简体中文](compatibility-core-v1.zh-CN.md) · [Implementations](../implementations/README.md)

**Status:** implemented by Python, Go, Rust and Bash, with a [shared executable conformance runner](../conformance/README.md). This is separate from the proposed [native environment convention](environment-v1.md).

The baseline is the behavior of the Python core at [946ad9e](https://github.com/lin594/devwho/tree/946ad9ef771750aab9570992f8af77575a69570b), its [command reference](../docs/reference.md), and regression tests. Fixes to that baseline must be explicit, documented contract changes, not accidental differences between ports. Passing a few switching examples is insufficient to claim full compatibility.

## 1. What a complete implementation means

Each Go, Rust, or Bash implementation owns configuration parsing, validation, environment compilation, reversible transitions, CLI execution, diagnostics, and Bash/Zsh rendering. It must work without invoking Python, a Python-built helper, or another implementation of the core. A language binding, launcher, SDK, or Git-only subset does not complete a port.

Users choose one implementation and retain their profile file and public commands. Development and test dependencies may differ from runtime dependencies. A Python-based test driver is acceptable; Python must be absent from runtime acceptance environments for the new ports.

## 2. Public commands and behavior

Support `--help`, `--version`, global `--config PATH`, and the following commands:

| Interface | Required behavior |
|---|---|
| `list`, `show PROFILE` | List names; display supported profile metadata without dumping generic env values or credentials. |
| `current [--verbose]` | Show the selected marker, or `none`; verbose mode includes effective Git identities and configuration locations. |
| `doctor [PROFILE] [--offline]` | Inspect the current environment without activating the requested profile. Check real Git author/committer and configured values; query gh only for explicit online diagnostics. |
| `exec PROFILE -- COMMAND ...` | Apply the profile to a child process tree, preserve argv and its exit status/signals, and leave the caller unchanged. Missing command returns 127; nonexecutable command returns 126. |
| `config path`, `config init` | Resolve the same configuration path; initialize explicitly, privately, and exclusively without overwriting an existing file. |
| `init bash`, `init zsh` | Print integration code without editing startup files. Pin the selected executable and configuration path. |
| `setdev [PROFILE]`, `unsetdev` | Shell functions that activate an explicit/shortcut profile and restore the shell's baseline. |

For `doctor`, return 0 only when all requested checks pass, 1 for a failure or mismatch, and 2 when checks are incomplete/unverified, including unavailable local tools or skipped network checks. Failures take precedence over unverified results. Diagnostics must not reveal arbitrary environment values, tokens, or raw subprocess error output.

Match command output semantics and exit codes. Help layout, JSON whitespace, and correctly quoted shell-code formatting need not be byte-identical. Generated initialization output must be valid executable shell code; diagnostics go to stderr.

## 3. Configuration parity

Keep the version 1 schema and lookup precedence: explicit `--config`, then `DEVWHO_CONFIG`, then `$XDG_CONFIG_HOME/devwho/config.toml`, then `~/.config/devwho/config.toml`. Native applications are not required to read this file.

TOML is a required **existing compatibility format**, not a permanent restriction on the ecosystem. The optional [dotenv input](dotenv-v1.md) normalizes into the same profile/transition model under its own grammar and selection rules; full TOML support remains required.

All implementations must accept the TOML 1.0 encodings of configurations accepted by the baseline schema, including quoted/dotted keys, inline tables, multiline strings, Unicode escapes, and multiline arrays. They must reject invalid TOML, duplicate definitions, unknown fields, wrong types, and invalid profiles. A line-oriented key/value approximation is not a compatible TOML parser. [TOML 1.0 specification](https://toml.io/en/v1.0.0)

Required schema coverage:

- `settings.default_profile`, `shortcut_profile`, and `handoff_warning`.
- Git name/email together; signing key, format, boolean, and ordered/multivalue `git.config` entries.
- `git_ssh.identity_file` and `identities_only`.
- `github.hostname`, `expected_user`, and `config_dir`.
- Literal generic environment values and explicit `unset_env`; reject reserved/unsafe keys and overlapping semantic settings.

Literal values never undergo shell expansion. Semantic SSH and gh paths must be absolute, `~`, or start with `~/`; they resolve using the target's effective HOME after previous managed values are restored and target env/unsets applied. Reject missing/relative HOME for tilde paths and require the selected SSH key file to exist. Changing directories must not change the selected key or gh context.

## 4. Transitions and adapter parity

1. Validate the entire profile, inherited conflicts, state, and shell writability before applying a transition. Validate Git runtime pairs when the transition adds or previously managed Git runtime configuration; an env-only profile with no runtime ownership preserves even an unrelated malformed count. An unknown profile or any required validation failure leaves the environment and state unchanged.
2. Preserve absent, empty, and nonempty baseline values. Repeated activation is idempotent. A→B→C→unset restores the original baseline, not B or a stack of old profiles. A-only values are restored when B no longer owns them.
3. Preserve existing Git runtime configuration and repeated values in order. Append the managed identity/signing/config block. Preserve unrelated later appendages; reject altered prefixes or managed blocks instead of removing unrelated configuration. Restore overwritten/orphan indexed variables as the baseline does; honor malformed-input and size limits.
4. Compile Git identity through runtime `user`, `author`, and `committer` name/email configuration. Do not persistently export `GIT_AUTHOR_*` or `GIT_COMMITTER_*`. Preserve original authors during cherry-pick and rebase.
5. Reject inherited nonempty `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, and `GIT_COMMITTER_EMAIL` before restoration can hide them. With semantic GitHub settings, also reject `GH_TOKEN`/`GITHUB_TOKEN` in the inherited environment or target generic env. Never silently clear a conflict.
6. Compile Git SSH and GitHub settings through the existing adapter variables. Selection does not prove authentication; ordinary activation is offline. Keep identity, login, and push credentials distinct.
7. Preserve unrelated configuration and proxy settings. Activation must not edit global/repository Git config, saved remotes, SSH config, credentials, files, or branches. Optional handoff warnings do not stash, clean, assign changes, or close windows.

## 5. Shell lifecycle and internal state

Support real Bash and Zsh, including Bash 3.2 as used by the current macOS test coverage. Any different minimum version must be disclosed and recorded as a coverage gap rather than advertised as equal platform support.

A new independent shell may bootstrap the configured default as its baseline. An explicitly inherited profile stays selected; a child captures its inherited environment as its own baseline. Restoration state remains non-exported. Existing terminals and windows do not change when a different terminal switches.

Correctly quote quotes, dollar signs, command substitutions, backticks, newlines, control characters, Unicode, and empty strings as data. Check readonly variables, arrays, and unsupported shell attributes before mutating any managed variable. This applies to every core language; being compiled does not make a renderer safe by itself.

For core-to-core conformance, preserve the baseline's version 1 JSON state semantics (`version`, `profile`, `baseline`, `managed`, `runtime`) and internal transition request behavior. Validate structure and limits, not just JSON syntax. State is an internal transport over stdin and a non-exported shell variable; it remains outside the native app API. Compare parsed state and resulting environments, not JSON serialization whitespace.

Test Python→Go→Rust→Bash transitions using fixtures and internal endpoints. Public `init` pins one executable; cross-implementation state tests do not imply that changing PATH hot-swaps an already initialized shell. Choose another implementation in a fresh terminal or deliberately reinitialize it with compatible state.

## 6. Common acceptance suite

Extract language-neutral inputs and expected results, then run them against each implementation. The common runner must target an executable path rather than import Python core classes. Existing Python unit tests remain useful, but are not by themselves evidence that another port conforms.

| Group | Required evidence |
|---|---|
| Parsing | Equivalent TOML forms, valid/invalid schema, duplicate definitions, Unicode/literal/empty/multiline values, reserved keys, path/HOME cases. |
| Transition | No/empty/existing baseline; repeated switches; A→B→C→unset; unknown profile; state corruption; runtime prefix/owned-block conflicts; appended third-party pairs. |
| Shell | Real Bash 3.2/current Bash and Zsh; readonly/array/attribute failures; startup defaults, shortcuts, child inheritance, independent terminals; no command injection. |
| Git | Actual commit author/committer overriding old repository settings; signing settings; rebase/cherry-pick authors; unchanged config, remotes, branches, dirty files, proxy state. |
| SSH/gh | Safely quoted key path, missing keys, host/config isolation, conflicting author/token variables; deterministic fake gh responses for match/mismatch/unavailable. No credentials required in CI. |
| Process/diagnostics | Exact argv preservation, parent isolation, child status/signals, 126/127 cases; doctor 0/1/2 and redaction; no network during activation. |
| Distribution | Fresh installation and full runtime suite with Python unavailable; executable/script dependency audit; actual supported OS/architecture jobs and checksums. |
| Interoperability | Same config/examples in every implementation; parsed state and transition outputs agree, including cross-implementation restore. |

Live account or remote push checks are separate opt-in integration tests using authorized test accounts. Fake responses must not be reported as verified real authentication.

## 7. Release and compatibility claims

Declare the implemented core contract, runtime requirements, tested platform matrix, known gaps, and artifact provenance. A port can land in stages, but remains experimental until the complete contract passes. Unsupported features must fail clearly; a subset cannot silently succeed or close the full-core implementation issue.

Keep the native environment draft separate. No port should invent its own `DEVWHO_*` vocabulary, change the meaning of the existing profile marker, or require users to convert profile files to a language-specific format.
