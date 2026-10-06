# Literal dotenv input — revision 1

[English](dotenv-v1.md) | [简体中文](dotenv-v1.zh-CN.md)

This optional producer input is implemented by the Python, Go, Rust and Bash compatibility cores. It does not change the native environment convention: applications read `DEVWHO_PROFILE`, without opening a producer's files. Existing version-1 TOML remains supported in full.

## Selection

`devwho --env-file PATH [--env-profile NAME] COMMAND` explicitly selects one file. It cannot be combined with `--config`; `--env-profile` requires `--env-file`. There is no current-directory discovery, merging with TOML, interpolation, shell execution or network access. `DEVWHO_CONFIG` is ignored when an explicit dotenv file is selected.

The input must contain a valid nonempty `DEVWHO_PROFILE`, or the caller must supply `--env-profile`. If both are present, they must match. An invalid or empty marker cannot be overridden. The marker is consumed as profile metadata, and remaining assignments become ordinary `profile.env` entries. This produces one profile, no startup default, and a shortcut to that profile. `setdev` activates it; `unsetdev` restores the baseline. Generated shell integration pins the resolved file and profile, including when the marker originally came from the file.

## Grammar

- UTF-8; LF or CRLF lines. Reject NUL, invalid UTF-8, and lone CR in the input. No BOM or physical multiline values.
- Ignore empty lines and full-line `#` comments after spaces/tabs. An optional literal `export ` prefix is accepted.
- Assignments use `[A-Za-z_][A-Za-z0-9_]*=VALUE`. Spaces/tabs around the key, equals sign and unquoted value are trimmed. Duplicate keys and bare keys are errors.
- Unquoted `$NAME`, `${NAME}`, command substitutions and backticks are literal data. An unquoted `#` begins a comment only when preceded by a space or tab. `VALUE=#literal` therefore retains `#literal`.
- Single-quoted values are literal, with no escape sequences. Double-quoted values use JSON string escapes, including `\n`, `\t`, `\r`, `\uXXXX` and valid surrogate pairs. Reject unknown escapes, unpaired surrogates and decoded NUL.
- After a closing quote, allow only spaces/tabs and an optional `#` comment. A value cannot continue onto another physical line.
- `KEY=` means an explicitly present empty value. A missing key is unmanaged, not an instruction to unset it. Use TOML `unset_env` for explicit removal.

This is DevWho's defined literal subset, not a claim of compatibility with every program named dotenv. Never `source` these files: literal values may be shell syntax.

## Existing validation and export

The complete core's environment-name restrictions, author-conflict checks, readonly-variable preflight, baseline restoration and runtime-Git ownership rules still apply. Raw `GIT_CONFIG_*`, persistent author overrides and reserved DevWho/startup variables are rejected. Generic `GH_CONFIG_DIR` remains a generic value; it does not imply a verified GitHub username.

`devwho [--config PATH] config export-env PROFILE` emits a marker and JSON-quoted generic environment assignments. It also works with an explicit dotenv source. Export fails before output if the profile contains Git/GitHub/SSH semantic settings or `unset_env`, rather than silently discarding them. Output may contain private values: save it deliberately with restrictive permissions and keep it out of version control.

`config path` reports the selected input. `config init` rejects dotenv mode. Configuration frontend writes use TOML; dotenv is a simple alternate input/export, not a second hidden global store.

The executable acceptance cases live in [dotenv fixtures](../conformance/fixtures/dotenv.json) and [shared tests](../conformance/test_dotenv.py).
