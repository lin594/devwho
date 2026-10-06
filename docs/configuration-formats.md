# Does DevWho need TOML? Where dotenv fits

[English](configuration-formats.md) | [简体中文](zh-CN/configuration-formats.md) · [Ecosystem](ecosystem.md)

**Recommendation:** keep the runtime convention independent of file formats, preserve existing TOML profiles, and add dotenv as an optional simple input after defining its parsing and transition rules. Dotenv loading by the DevWho core is proposed, not implemented. Track it in [issue #6](https://github.com/lin594/devwho/issues/6).

## Three separate concerns

| Concern | Contract |
|---|---|
| What a native application reads | `DEVWHO_PROFILE` from its process environment. It need not open a configuration file or know how the value was saved. |
| How a producer stores user choices | A producer choice: existing TOML, proposed dotenv, an IDE setting, or another representation. |
| How the compatibility core switches existing tools | A validated profile becomes a reversible environment patch and ordered Git runtime settings. All core implementations preserve these semantics. |

```text
existing TOML ───────────┐
proposed dotenv input ───┼→ normalized profile → shared validation/transition rules
another producer input ─┘                         → current tool adapters

any context producer → DEVWHO_PROFILE → a native application's own account mapping
```

The common model and behavior matter more than requiring every future producer to use TOML. Today's file format remains part of the current compatibility contract so existing users do not lose working configurations.

## An ordinary dotenv file can carry a native context

For a launcher that already supports dotenv, a file can be as small as:

```dotenv
DEVWHO_PROFILE=work
```

Once loaded by that launcher, a future native consumer reads the resulting environment. It does not need a `version` line, a Python dependency, or the dotenv file itself. This example is not a new `devwho` command and does not make today's Git or gh select an account without adapters.

Dotenv can also store literal settings used by existing tools. For example:

```dotenv
GH_HOST=github.com
GH_CONFIG_DIR=/home/jane/.config/gh-work
EDITOR=vim
```

These are existing tool interfaces, not new universal DevWho variables. A future core loader should apply such values through the same reversible engine, rather than sourcing them and losing baseline/conflict checks. Selecting a gh directory alone does not verify its login.

## Why keep the existing structured format?

| Requirement | Plain `KEY=value` | Existing TOML profiles |
|---|---|---|
| Literal environment settings | Natural fit. | Supported in `env`. |
| An empty value | `KEY=` can express it. | Empty string. |
| Explicit removal of a variable | No universal dotenv representation; absence is not removal. | `unset_env`. |
| Git author, signing, SSH, and expected gh account | Raw tool variables are possible, but do not carry all semantic validation. | Typed fields with conflict checks and diagnostic expectations. |
| Repeated ordered Git configuration | Flat maps cannot naturally preserve duplicate entries. | Arrays of values under `git.config`. |
| Multiple profiles and startup default/shortcut | Needs file selection and a separate metadata convention. | Existing named profiles and `settings`. |

Putting JSON arrays inside env strings or inventing many numbered keys can recreate a structured format less clearly. We should support a simple dotenv use case without pretending that it represents every existing feature. Advanced users can keep TOML; a future complete flat representation needs its own design and shared tests, not silent feature loss.

## Proposed core dotenv loader rules

Dotenv is not one universally specified language: Node explicitly documents its own grammar, while Docker Compose performs interpolation in unquoted and double-quoted values. DevWho must choose and test its behavior rather than inheriting whichever library each language happens to use. [Node documentation](https://nodejs.org/api/environment_variables.html#dotenv), [Compose interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)

Before implementing the optional input:

1. Define a small literal grammar and shared fixtures for UTF-8, LF/CRLF, whitespace, comments, quoting, escapes, duplicate keys, and invalid/NUL input. No `source`, `eval`, command substitution, or implicit `$VAR` interpolation. Reject unsupported syntax clearly.
2. Distinguish a missing key from an empty value and from explicit removal. Do not invent an unset syntax accidentally. Use the existing structured format for removals until an extension is explicitly specified.
3. Choose how an input names a profile, how users explicitly select the file, and how its values compose with TOML/defaults. Reject ambiguity or declare precedence. Do not automatically load a repository's `.env` based on the current directory.
4. Keep `DEVWHO_PROFILE` selection metadata separate from arbitrary env assignments. Resolve any conflict between a selected profile name and a file marker before mutation. Preserve existing reserved-key, author/token, and shell-attribute checks.
5. Reuse normalization, validation, atomicity, restoration, and diagnostics. Raw `GIT_CONFIG_*` blocks need explicit owned-block normalization and index validation if ever accepted; assigning count/index variables directly would overwrite unrelated runtime settings. Persistent `GIT_AUTHOR_*` is not a substitute for the Git adapter.
6. Keep expected-account verification explicit. A generic env-only profile must not claim the semantic GitHub checks that require `expected_user` and the GitHub adapter's conflict rules.
7. Add equivalent tests for every implementation that advertises dotenv support. Preserve TOML compatibility for complete Go/Rust/Bash ports; providing only dotenv does not finish a full port.

The first dotenv implementation should solve a clearly bounded literal-environment workflow. Neither native applications nor other producers must implement DevWho's TOML parser to join the ecosystem. The existing core continues to support TOML until an explicit compatible migration exists.
