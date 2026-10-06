# Configuration files and the application environment

[English](configuration-formats.md) | [简体中文](zh-CN/configuration-formats.md) · [Ecosystem](ecosystem.md)

Applications need only `DEVWHO_PROFILE`. They do not need a TOML parser, dotenv library, DevWho SDK, or access to another program's files. How a user edits and saves profiles is a separate choice.

## Choose the input that fits the job

| Need | Use |
|---|---|
| Configure Git, accounts and defaults through prompts | The optional [English/Chinese configuration frontend](configuration-ui.md). It saves ordinary TOML for every core. |
| Full Git/GitHub/SSH settings, several profiles, ordered Git pairs or explicit unsets | Version-1 TOML, with the existing schema and validation. |
| A small collection of literal environment values | Explicit dotenv input, supported by Python, Go, Rust and Bash. |
| Add native support to an application | Read the process environment and apply your own account mapping; no producer file is required. |

```text
configuration UI / machine write API → validated profile store (TOML today)
literal dotenv input ────────────────→ validated profile
                                      ↓
                                 session transition
                                      ↓
                        DEVWHO_PROFILE + existing tool adapters

native application → reads DEVWHO_PROFILE → its own account mapping
```

There is no daemon or global current-account file. Saving a profile and activating it are separate operations. A future storage backend can use the same validation and session model without changing the application convention.

## Try a dotenv profile

Save this as a private `work.env` file:

```dotenv
DEVWHO_PROFILE=work
EDITOR=vim
APP_ACCOUNT=work
```

```sh
devwho --env-file ./work.env exec work -- env
eval "$(devwho --env-file ./work.env init bash)"  # use zsh for Zsh
setdev
unsetdev
```

The first command displays the child environment; use it only where printing your environment is appropriate. `setdev` applies values through the same reversible engine. A file without a marker needs `--env-profile work`. There is no automatic `.env` discovery or merging with TOML. `$HOME` and command-like text remain literal.

An env-only TOML profile can be exported with `devwho config export-env PROFILE`. Semantic Git/GitHub/SSH settings and explicit unsets cannot be exported to this simple format: export reports an error instead of losing them. Missing keys and empty values have different meanings. See the [exact grammar, selection and export contract](../spec/dotenv-v1.md).

## Why the profile store still uses TOML

Ordinary env assignments cannot fully describe ordered repeated Git configuration, default/shortcut profiles, explicit removal, or expected GitHub accounts. Encoding these as numbered variables or JSON strings would introduce another structured protocol. The editor hides this detail from beginners; applications never parse it.

TOML is the current replaceable storage format and a compatibility commitment to existing users, not an ecosystem requirement. Dotenv is useful for the simpler input it can express faithfully. Neither needs a `DEVWHO_SPEC_VERSION` environment variable. File schema versions and specification revisions have separate purposes.
